"""Main RATUFixBot class composing all modules."""

import logging
import os
import time
from datetime import datetime
from pathlib import Path

from ratu_fix_bot.config import RATUFixConfig
from ratu_fix_bot.core.market_data import MarketDataHandler
from ratu_fix_bot.core.order_management import OrderManager
from ratu_fix_bot.core.session import SessionManager


class RATUFixBot:
    """RATU FIX Bot - Spread Market Making using FIX protocol.
    
    This bot maintains a pair of buy/sell limit orders around the current
    market price with a configurable spread offset.
    """
    
    def __init__(self, config: RATUFixConfig):
        """Initialize the bot with configuration.
        
        Args:
            config: Bot configuration
        """
        self.config = config
        self._setup_logging()
        
        self.session = SessionManager(config)
        self.market_data: MarketDataHandler = None
        self.order_manager: OrderManager = None
        
        self._logger = logging.getLogger(__name__)
        self._logger.info("Bot initialized")
    
    def _setup_logging(self) -> None:
        """Configure logging to file and console."""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        
        # Create logs directory in project root
        project_root = Path(__file__).parent.parent.parent.parent
        logs_dir = project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        # Generate timestamped log filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"bot_{timestamp}.txt"
        
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s %(levelname)s %(message)s",
            handlers=[
                logging.FileHandler(log_file, mode='w'),
                logging.StreamHandler()
            ]
        )
    
    def setup(self) -> None:
        """Initialize all sessions and handlers."""
        self.session.setup_md_session()
        self.session.setup_oe_session()
        
        self.market_data = MarketDataHandler(self.config, self.session.client_md)
        self.order_manager = OrderManager(
            self.config, self.session.client_oe, self.market_data
        )
        
        self.market_data.validate_instrument()
        self.market_data.subscribe_ticker()
    
    def run(self) -> None:
        """Main loop to maintain buy/sell order pair."""
        try:
            self.setup()
            
            while True:
                self.order_manager.check_order_status()
                
                if not self.market_data.current_bid or not self.market_data.current_ask:
                    self._logger.info("Waiting for valid ticker data")
                    time.sleep(1)
                    continue
                
                if self.order_manager.is_stale():
                    self._logger.info(
                        f"Stale or missing orders detected: "
                        f"Bid={self.market_data.current_bid}, Ask={self.market_data.current_ask}"
                    )
                    self.order_manager.cancel_quote_orders()
                    time.sleep(1)  # Wait for cancellations
                    self.order_manager.place_quote_orders(
                        place_buy=not self.order_manager.buy_filled,
                        place_sell=not self.order_manager.sell_filled
                    )
                else:
                    self._logger.info(
                        f"Orders active: Buy={self.order_manager.active_buy_price}, "
                        f"Sell={self.order_manager.active_sell_price}"
                    )
                
                time.sleep(5)  # Check every 5 seconds
                
        except KeyboardInterrupt:
            self._logger.info("Shutting down bot")
            self.stop()
        except Exception as e:
            self._logger.error(f"Bot error: {e}", exc_info=True)
            self.stop()
    
    def stop(self) -> None:
        """Stop the bot and close all sessions."""
        if self.market_data:
            self.market_data.stop()
        self.session.close()
