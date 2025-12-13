"""Session management for FIX connections."""

import logging
import os
from pathlib import Path
from typing import Any

from binance_fix_connector.fix_connector import create_market_data_session, create_order_entry_session
from binance_fix_connector.utils import get_private_key
from ratu_fix_bot.config import RATUFixConfig


def load_credentials(config: RATUFixConfig) -> tuple[str, str]:
    """Load API credentials from environment or config file.
    
    Priority:
    1. Environment variables (BINANCE_ED25519_API_KEY, BINANCE_ED25519_PRIV_PATH)
    2. config.ini file with [keys] section
    
    Returns:
        Tuple of (api_key, private_key_path)
    """
    # Determine project root (where .env is located)
    # Start from this file's location and go up to find .env
    project_root = Path(__file__).parent.parent.parent.parent
    
    # Try environment variables first (supports .env via python-dotenv)
    try:
        from dotenv import load_dotenv
        env_path = project_root / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        else:
            load_dotenv()  # Try default locations
    except ImportError:
        pass  # python-dotenv not installed, rely on system env vars
    
    api_key = os.getenv("BINANCE_ED25519_API_KEY")
    priv_path = os.getenv("BINANCE_ED25519_PRIV_PATH")
    
    if api_key and priv_path:
        # Resolve relative path from project root
        if not os.path.isabs(priv_path):
            priv_path = str(project_root / priv_path)
        return api_key, priv_path
    
    # Fallback to config.ini
    from binance_fix_connector.utils import get_api_key
    return get_api_key(config.config_path)


class SessionManager:
    """Manages FIX Market Data and Order Entry sessions."""
    
    def __init__(self, config: RATUFixConfig):
        """Initialize session manager.
        
        Args:
            config: Bot configuration with credentials path and endpoints
        """
        self.config = config
        self.api_key, self.private_key_path = load_credentials(config)
        self.private_key = get_private_key(self.private_key_path)
        self.client_md: Any = None
        self.client_oe: Any = None
        self._logger = logging.getLogger(__name__)
    
    def setup_md_session(self) -> None:
        """Initialize Market Data session and log Logon response."""
        try:
            self.client_md = create_market_data_session(
                self.api_key, self.private_key, self.config.md_url
            )
            messages = self.client_md.retrieve_messages_until(message_type="A")
            for msg in messages:
                if msg.message_type.decode("utf-8") == "A":
                    session_id = msg.get(25037).decode() if msg.get(25037) else "Unknown"
                    self._logger.info(f"MD session established, SessionID={session_id}")
                elif msg.message_type.decode("utf-8") == "3":
                    text = msg.get(58).decode() if msg.get(58) else "Unknown error"
                    self._logger.error(f"MD Logon rejected: {text}")
                    raise ValueError(f"MD Logon failed: {text}")
        except Exception as e:
            self._logger.error(f"Failed to establish MD session: {e}", exc_info=True)
            raise
        self._logger.info("MD session kept open")
    
    def setup_oe_session(self) -> None:
        """Initialize Order Entry session and log Logon response."""
        try:
            self.client_oe = create_order_entry_session(
                self.api_key, self.private_key, self.config.oe_url
            )
            messages = self.client_oe.retrieve_messages_until(message_type="A")
            for msg in messages:
                if msg.message_type.decode("utf-8") == "A":
                    session_id = msg.get(25037).decode() if msg.get(25037) else "Unknown"
                    self._logger.info(f"OE session established, SessionID={session_id}")
                elif msg.message_type.decode("utf-8") == "3":
                    text = msg.get(58).decode() if msg.get(58) else "Unknown error"
                    self._logger.error(f"OE Logon rejected: {text}")
                    raise ValueError(f"OE Logon failed: {text}")
        except Exception as e:
            self._logger.error(f"Failed to establish OE session: {e}", exc_info=True)
            raise
        self._logger.info("OE session kept open")
    
    def ensure_md_connected(self) -> None:
        """Ensure MD session is connected, reconnect if needed."""
        if not self.client_md or not self.client_md.is_connected:
            self.setup_md_session()
    
    def ensure_oe_connected(self) -> None:
        """Ensure OE session is connected, reconnect if needed."""
        if not self.client_oe or not self.client_oe.is_connected:
            self.setup_oe_session()
    
    def close(self) -> None:
        """Close all sessions gracefully."""
        if self.client_md and self.client_md.is_connected:
            self.client_md.logout()
            self.client_md.disconnect()
            self._logger.info("MD session closed")
        if self.client_oe and self.client_oe.is_connected:
            self.client_oe.logout()
            self.client_oe.disconnect()
            self._logger.info("OE session closed")
