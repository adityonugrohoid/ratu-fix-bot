"""Market data handling for FIX streams."""

import logging
import threading
import time
from typing import Any, Optional

from ratu_fix_bot.config import RATUFixConfig


class MarketDataHandler:
    """Handles market data subscription and ticker stream processing."""
    
    def __init__(self, config: RATUFixConfig, client_md: Any):
        """Initialize market data handler.
        
        Args:
            config: Bot configuration
            client_md: FIX Market Data client
        """
        self.config = config
        self.client_md = client_md
        self._logger = logging.getLogger(__name__)
        
        # Instrument constraints
        self.min_qty: Optional[float] = None
        self.min_price_inc: Optional[float] = None
        
        # Current market state
        self.current_bid: Optional[float] = None
        self.current_ask: Optional[float] = None
        
        # Stream control
        self.ticker_running = False
    
    def validate_instrument(self) -> None:
        """Query instrument constraints using InstrumentListRequest (x)."""
        try:
            msg = self.client_md.create_fix_message_with_basic_header("x")
            msg.append_pair(320, "GetInstrumentList")
            msg.append_pair(559, 0)  # Single symbol
            msg.append_pair(55, self.config.symbol)
            self.client_md.send_message(msg)
            self._logger.info(f"Sent InstrumentListRequest for {self.config.symbol}")
            
            # Poll for response up to 5 seconds
            start_time = time.time()
            while time.time() - start_time < 5:
                for _ in range(self.client_md.queue_msg_received.qsize()):
                    msg = self.client_md.queue_msg_received.get()
                    if msg.message_type.decode("utf-8") == "y":
                        self.min_qty = float(msg.get(25039, 1).decode("utf-8") or 0)
                        self.min_price_inc = float(msg.get(969, 1).decode("utf-8") or 0)
                        self._logger.info(
                            f"Validated: MinQty={self.min_qty}, MinPriceInc={self.min_price_inc}"
                        )
                        break
                else:
                    time.sleep(0.1)
                    continue
                break
            else:
                self._logger.error("No InstrumentListResponse received within 5 seconds")
                raise ValueError(f"Failed to retrieve {self.config.symbol} constraints")
            
            if self.min_qty is None or self.min_price_inc is None:
                self._logger.error(f"Failed to parse {self.config.symbol} constraints")
                raise ValueError(f"Invalid {self.config.symbol} constraints")
            
            if self.config.order_qty < self.min_qty:
                self._logger.error(
                    f"ORDER_QTY {self.config.order_qty} below MinQty {self.min_qty}"
                )
                raise ValueError("Invalid ORDER_QTY")
                
        except Exception as e:
            self._logger.error(f"Failed to validate instrument: {e}", exc_info=True)
            raise
        self._logger.info("Instrument validation complete")
    
    def subscribe_ticker(self) -> None:
        """Subscribe to ticker stream and start background polling."""
        try:
            msg = self.client_md.create_fix_message_with_basic_header("V")
            msg.append_pair(262, "BOOK_TICKER_STREAM")  # MDReqID
            msg.append_pair(263, 1)  # Subscribe
            msg.append_pair(264, 1)  # Depth=1 (top of book)
            msg.append_pair(266, "Y")  # Aggregated book
            msg.append_pair(146, 1)  # NoSymbols
            msg.append_pair(55, self.config.symbol)
            msg.append_pair(267, 2)  # NoMDEntries
            msg.append_pair(269, 0)  # BID
            msg.append_pair(269, 1)  # OFFER
            self.client_md.send_message(msg)
            self._logger.info(f"Subscribed to {self.config.symbol} ticker stream")
        except Exception as e:
            self._logger.error(f"Failed to send ticker subscription: {e}", exc_info=True)
            raise

        # Process snapshot (W)
        self._process_snapshot()
        
        # Start background ticker stream
        threading.Thread(target=self._run_ticker_stream, daemon=True).start()
        self._logger.info("Background ticker stream started")
    
    def _process_snapshot(self) -> None:
        """Process initial market data snapshot."""
        try:
            messages = self.client_md.retrieve_messages_until(message_type="W")
            for msg in messages:
                if msg.message_type.decode("utf-8") == "W":
                    updates = int(msg.get(268).decode() or 0)
                    best_bid, best_ask = None, None
                    for i in range(updates):
                        entry_type = msg.get(269, i + 1).decode()
                        price = float(msg.get(270, i + 1).decode() or 0)
                        qty = float(msg.get(271, i + 1).decode() or 0)
                        if entry_type == "0":
                            best_bid = price
                        elif entry_type == "1":
                            best_ask = price
                        self._logger.debug(f"Snapshot: Type={entry_type}, Price={price}, Qty={qty}")
                    if best_bid and best_ask:
                        self.current_bid = best_bid
                        self.current_ask = best_ask
                        self._logger.debug(f"Snapshot: BestBid={best_bid}, BestAsk={best_ask}")
                elif msg.message_type.decode("utf-8") == "3":
                    text = msg.get(58).decode() if msg.get(58) else "Unknown error"
                    self._logger.error(f"Subscription rejected: {text}")
                    raise ValueError(f"MarketDataRequest rejected: {text}")
        except Exception as e:
            self._logger.error(f"Failed to process snapshot: {e}", exc_info=True)
            raise
    
    def _run_ticker_stream(self) -> None:
        """Run persistent ticker stream in background thread."""
        self._logger.info("Starting persistent ticker stream")
        self.ticker_running = True
        while self.ticker_running:
            try:
                for _ in range(self.client_md.queue_msg_received.qsize()):
                    msg = self.client_md.queue_msg_received.get()
                    if msg.message_type.decode("utf-8") == "X":
                        updates = int(msg.get(268).decode() or 0)
                        for i in range(updates):
                            entry_type = msg.get(269, i + 1).decode()
                            price = float(msg.get(270, i + 1).decode() or 0)
                            qty = float(msg.get(271, i + 1).decode() or 0)
                            if entry_type == "0":
                                self.current_bid = price
                            elif entry_type == "1":
                                self.current_ask = price
                            self._logger.debug(f"Update: Type={entry_type}, Price={price}, Qty={qty}")
                        if self.current_bid and self.current_ask:
                            self._logger.debug(
                                f"Current: BestBid={self.current_bid}, BestAsk={self.current_ask}"
                            )
                    elif msg.message_type.decode("utf-8") == "3":
                        text = msg.get(58).decode() if msg.get(58) else "Unknown error"
                        self._logger.error(f"Update rejected: {text}")
                time.sleep(1)  # Poll every 1s
            except Exception as e:
                self._logger.error(f"Error in ticker stream: {e}", exc_info=True)
                self.ticker_running = False
                break
        self._logger.info("Stopped ticker stream")
    
    def stop(self) -> None:
        """Stop the ticker stream."""
        self.ticker_running = False
