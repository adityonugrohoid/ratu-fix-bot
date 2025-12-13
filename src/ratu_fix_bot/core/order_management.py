"""Order management for FIX order entry."""

import logging
import time
from typing import Any, Optional

from ratu_fix_bot.config import RATUFixConfig


class OrderManager:
    """Manages order placement, cancellation, and status tracking."""
    
    def __init__(self, config: RATUFixConfig, client_oe: Any, market_data: Any):
        """Initialize order manager.
        
        Args:
            config: Bot configuration
            client_oe: FIX Order Entry client
            market_data: MarketDataHandler instance for price data
        """
        self.config = config
        self.client_oe = client_oe
        self.market_data = market_data
        self._logger = logging.getLogger(__name__)
        
        # Active order tracking
        self.active_buy_clordid: Optional[str] = None
        self.active_sell_clordid: Optional[str] = None
        self.active_buy_price: Optional[float] = None
        self.active_sell_price: Optional[float] = None
        self.last_order_time: Optional[float] = None
        
        # Fill status
        self.buy_filled = False
        self.sell_filled = False
    
    def place_quote_orders(self, place_buy: bool = True, place_sell: bool = True) -> None:
        """Place buy/sell LIMIT orders with spread offset.
        
        Args:
            place_buy: Whether to place buy order
            place_sell: Whether to place sell order
        """
        if not self.market_data.current_bid or not self.market_data.current_ask:
            self._logger.error("No valid ticker data available for order placement")
            raise ValueError("Missing bid/ask prices")
        
        try:
            # Calculate order prices with spread offset
            min_price_inc = self.market_data.min_price_inc
            spread_offset = self.config.spread_percent / 200
            
            buy_price = round(
                self.market_data.current_bid * (1 - spread_offset) / min_price_inc
            ) * min_price_inc
            sell_price = round(
                self.market_data.current_ask * (1 + spread_offset) / min_price_inc
            ) * min_price_inc
            
            now = int(time.time() * 1e9)  # Nanosecond timestamp for ClOrdID
            buy_clordid = f"buy_{now}"
            sell_clordid = f"sell_{now}"

            # Place BUY order if needed
            if place_buy and not self.buy_filled:
                msg = self.client_oe.create_fix_message_with_basic_header("D")
                msg.append_pair(38, self.config.order_qty)  # OrderQty
                msg.append_pair(40, 2)  # OrdType=LIMIT
                msg.append_pair(11, buy_clordid)  # ClOrdID
                msg.append_pair(44, f"{buy_price:.8f}")  # Price
                msg.append_pair(54, 1)  # Side=BUY
                msg.append_pair(55, self.config.symbol)
                msg.append_pair(59, 1)  # TimeInForce=GTC
                self.client_oe.send_message(msg)
                self._logger.info(f"Placed BUY order: ClOrdID={buy_clordid}, Price={buy_price}")
                self.active_buy_price = buy_price
                self.active_buy_clordid = buy_clordid

            # Place SELL order if needed
            if place_sell and not self.sell_filled:
                msg = self.client_oe.create_fix_message_with_basic_header("D")
                msg.append_pair(38, self.config.order_qty)
                msg.append_pair(40, 2)
                msg.append_pair(11, sell_clordid)
                msg.append_pair(44, f"{sell_price:.8f}")
                msg.append_pair(54, 2)  # Side=SELL
                msg.append_pair(55, self.config.symbol)
                msg.append_pair(59, 1)
                self.client_oe.send_message(msg)
                self._logger.info(f"Placed SELL order: ClOrdID={sell_clordid}, Price={sell_price}")
                self.active_sell_price = sell_price
                self.active_sell_clordid = sell_clordid

            # Process Execution Reports
            self._process_execution_reports(buy_clordid, sell_clordid)
            self.last_order_time = time.time()
            
        except Exception as e:
            self._logger.error(f"Failed to place orders: {e}", exc_info=True)
            raise
        self._logger.info("Quote orders placed, awaiting further action")
    
    def cancel_quote_orders(self) -> None:
        """Cancel active buy/sell orders."""
        if not (self.active_buy_clordid or self.active_sell_clordid):
            self._logger.info("No active orders to cancel")
            return
        
        try:
            # Cancel BUY order
            if self.active_buy_clordid:
                msg = self.client_oe.create_fix_message_with_basic_header("F")
                msg.append_pair(41, self.active_buy_clordid)  # OrigClOrdID
                msg.append_pair(11, f"cancel_{self.active_buy_clordid}")  # New ClOrdID
                msg.append_pair(55, self.config.symbol)
                self.client_oe.send_message(msg)
                self._logger.info(f"Sent cancel for BUY order: ClOrdID={self.active_buy_clordid}")

            # Cancel SELL order
            if self.active_sell_clordid:
                msg = self.client_oe.create_fix_message_with_basic_header("F")
                msg.append_pair(41, self.active_sell_clordid)
                msg.append_pair(11, f"cancel_{self.active_sell_clordid}")
                msg.append_pair(55, self.config.symbol)
                self.client_oe.send_message(msg)
                self._logger.info(f"Sent cancel for SELL order: ClOrdID={self.active_sell_clordid}")

            # Process cancel confirmations
            self._process_cancel_reports()
            
        except Exception as e:
            self._logger.error(f"Failed to cancel orders: {e}", exc_info=True)
            raise
        self._logger.info("Cancel orders processed")
    
    def check_order_status(self) -> None:
        """Check for Execution Reports to update order status."""
        try:
            start_time = time.time()
            while time.time() - start_time < 1:
                for _ in range(self.client_oe.queue_msg_received.qsize()):
                    msg = self.client_oe.queue_msg_received.get()
                    self._handle_execution_report(msg)
                time.sleep(0.1)
        except Exception as e:
            self._logger.error(f"Failed to check order status: {e}", exc_info=True)
            raise
    
    def is_stale(self) -> bool:
        """Check if orders are stale and need refresh."""
        if not self.market_data.current_bid or not self.market_data.current_ask:
            return False
        
        # If both sides filled, reset for new cycle
        if self.buy_filled and self.sell_filled:
            self._reset_cycle()
            return True
        
        mid_price = (self.market_data.current_bid + self.market_data.current_ask) / 2
        threshold = mid_price * (self.config.spread_percent / 200)
        now = time.time()
        
        return (
            (self.active_buy_clordid and 
             self.active_buy_price > self.market_data.current_bid + threshold) or
            (self.active_sell_clordid and 
             self.active_sell_price < self.market_data.current_ask - threshold) or
            (self.last_order_time and 
             now - self.last_order_time > self.config.stale_threshold_sec) or
            (not self.active_buy_clordid and not self.buy_filled) or
            (not self.active_sell_clordid and not self.sell_filled)
        )
    
    def _reset_cycle(self) -> None:
        """Reset fill status to start a new buy/sell cycle."""
        self._logger.info("Both sides filled - starting new cycle")
        self.buy_filled = False
        self.sell_filled = False
        self.active_buy_clordid = None
        self.active_sell_clordid = None
        self.active_buy_price = None
        self.active_sell_price = None
        self.last_order_time = None
    
    def _process_execution_reports(self, buy_clordid: str, sell_clordid: str) -> None:
        """Process execution reports after placing orders."""
        start_time = time.time()
        while time.time() - start_time < 1:
            for _ in range(self.client_oe.queue_msg_received.qsize()):
                msg = self.client_oe.queue_msg_received.get()
                if msg.message_type.decode("utf-8") == "8":
                    clordid = msg.get(11).decode()
                    ord_status = msg.get(39).decode()
                    text = msg.get(58).decode() if msg.get(58) else None
                    
                    if ord_status == "0":  # New
                        self._logger.info(f"Order confirmed: ClOrdID={clordid}, Status=New")
                        if clordid == buy_clordid:
                            self.active_buy_clordid = clordid
                        elif clordid == sell_clordid:
                            self.active_sell_clordid = clordid
                    elif ord_status == "8":  # Rejected
                        self._logger.error(f"Order rejected: ClOrdID={clordid}, Reason={text}")
                    elif ord_status in ("1", "2"):  # Partially/Fully Filled
                        self._logger.warning(f"Order filled: ClOrdID={clordid}, Status={ord_status}")
                        self._handle_fill(clordid, buy_clordid, sell_clordid)
                elif msg.message_type.decode("utf-8") == "3":
                    text = msg.get(58).decode() if msg.get(58) else "Unknown error"
                    self._logger.error(f"Order request rejected: {text}")
            time.sleep(0.1)
    
    def _process_cancel_reports(self) -> None:
        """Process execution reports after cancel requests."""
        start_time = time.time()
        while time.time() - start_time < 1:
            for _ in range(self.client_oe.queue_msg_received.qsize()):
                msg = self.client_oe.queue_msg_received.get()
                if msg.message_type.decode("utf-8") == "8":
                    clordid = msg.get(11).decode()
                    ord_status = msg.get(39).decode()
                    text = msg.get(58).decode() if msg.get(58) else None
                    
                    if ord_status == "4":  # Canceled
                        self._logger.info(f"Order canceled: ClOrdID={clordid}, Status=Canceled")
                        if clordid == f"cancel_{self.active_buy_clordid}":
                            self.active_buy_clordid = None
                            self.active_buy_price = None
                        elif clordid == f"cancel_{self.active_sell_clordid}":
                            self.active_sell_clordid = None
                            self.active_sell_price = None
                    elif ord_status == "8":  # Rejected
                        self._logger.error(f"Cancel rejected: ClOrdID={clordid}, Reason={text}")
                    elif ord_status in ("1", "2"):  # Filled
                        self._logger.warning(f"Order filled: ClOrdID={clordid}, Status={ord_status}")
                        if clordid == self.active_buy_clordid:
                            self.buy_filled = True
                            self.active_buy_clordid = None
                            self.active_buy_price = None
                        elif clordid == self.active_sell_clordid:
                            self.sell_filled = True
                            self.active_sell_clordid = None
                            self.active_sell_price = None
                elif msg.message_type.decode("utf-8") == "3":
                    text = msg.get(58).decode() if msg.get(58) else "Unknown error"
                    self._logger.error(f"Cancel request rejected: {text}")
            time.sleep(0.1)
    
    def _handle_execution_report(self, msg: Any) -> None:
        """Handle a single execution report message."""
        if msg.message_type.decode("utf-8") == "8":
            clordid = msg.get(11).decode()
            ord_status = msg.get(39).decode()
            text = msg.get(58).decode() if msg.get(58) else None
            
            if ord_status == "0":  # New
                self._logger.info(f"Order confirmed: ClOrdID={clordid}, Status=New")
            elif ord_status == "4":  # Canceled
                self._logger.info(f"Order canceled: ClOrdID={clordid}, Status=Canceled")
                if clordid == f"cancel_{self.active_buy_clordid}":
                    self.active_buy_clordid = None
                    self.active_buy_price = None
                elif clordid == f"cancel_{self.active_sell_clordid}":
                    self.active_sell_clordid = None
                    self.active_sell_price = None
            elif ord_status == "8":  # Rejected
                self._logger.error(f"Order rejected: ClOrdID={clordid}, Reason={text}")
            elif ord_status in ("1", "2"):  # Partially/Fully Filled
                self._logger.warning(f"Order filled: ClOrdID={clordid}, Status={ord_status}")
                if clordid == self.active_buy_clordid:
                    self.buy_filled = True
                    self.active_buy_clordid = None
                    self.active_buy_price = None
                elif clordid == self.active_sell_clordid:
                    self.sell_filled = True
                    self.active_sell_clordid = None
                    self.active_sell_price = None
        elif msg.message_type.decode("utf-8") == "3":
            text = msg.get(58).decode() if msg.get(58) else "Unknown error"
            self._logger.error(f"Order request rejected: {text}")
    
    def _handle_fill(self, clordid: str, buy_clordid: str, sell_clordid: str) -> None:
        """Handle order fill event."""
        if clordid == buy_clordid:
            self.buy_filled = True
            self.active_buy_clordid = None
            self.active_buy_price = None
        elif clordid == sell_clordid:
            self.sell_filled = True
            self.active_sell_clordid = None
            self.active_sell_price = None
