"""Configuration module for RATU FIX Bot."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RATUFixConfig:
    """Configuration for RATUFixBot.
    
    Attributes:
        symbol: Trading pair symbol (e.g., "ETHFDUSD")
        order_qty: Order quantity per side
        spread_percent: Spread offset as percentage (0.01 = 0.01%)
        stale_threshold_sec: Seconds before order is considered stale
        md_url: Market data FIX endpoint URL
        oe_url: Order entry FIX endpoint URL
        log_file: Path to log file
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        config_path: Path to config.ini with API credentials
    """
    
    symbol: str = "ETHFDUSD"
    order_qty: float = 0.002
    spread_percent: float = 0.01
    stale_threshold_sec: int = 2
    md_url: str = "tcp+tls://fix-md.binance.com:9000"
    oe_url: str = "tcp+tls://fix-oe.binance.com:9000"
    log_file: str = "bot_log.txt"
    log_level: str = "INFO"
    config_path: str = field(default_factory=lambda: "")
    
    def __post_init__(self):
        """Set default config_path if not provided."""
        if not self.config_path:
            self.config_path = os.path.join(Path(__file__).parent.parent.parent.parent, "config.ini")
    
    @classmethod
    def from_env(cls) -> "RATUFixConfig":
        """Create config from environment variables.
        
        Environment variables:
            RATU_SYMBOL, RATU_ORDER_QTY, RATU_SPREAD_PERCENT,
            RATU_STALE_THRESHOLD_SEC, RATU_MD_URL, RATU_OE_URL,
            RATU_LOG_FILE, RATU_CONFIG_PATH
        """
        return cls(
            symbol=os.getenv("RATU_SYMBOL", "ETHFDUSD"),
            order_qty=float(os.getenv("RATU_ORDER_QTY", "0.002")),
            spread_percent=float(os.getenv("RATU_SPREAD_PERCENT", "0.01")),
            stale_threshold_sec=int(os.getenv("RATU_STALE_THRESHOLD_SEC", "2")),
            md_url=os.getenv("RATU_MD_URL", "tcp+tls://fix-md.binance.com:9000"),
            oe_url=os.getenv("RATU_OE_URL", "tcp+tls://fix-oe.binance.com:9000"),
            log_file=os.getenv("RATU_LOG_FILE", "bot_log.txt"),
            log_level=os.getenv("RATU_LOG_LEVEL", "INFO"),
            config_path=os.getenv("RATU_CONFIG_PATH", ""),
        )
