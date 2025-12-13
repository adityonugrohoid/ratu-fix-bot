"""Tests for RATUFixBot initialization."""

from unittest.mock import Mock, patch

import pytest

from ratu_fix_bot.config import RATUFixConfig
from ratu_fix_bot.core.bot import RATUFixBot


class TestRATUFixBot:
    """Test RATUFixBot class."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return RATUFixConfig(
            symbol="ETHFDUSD",
            order_qty=0.002,
            spread_percent=0.01,
            stale_threshold_sec=2,
            config_path="tests/test_config.ini"
        )
    
    @patch("ratu_fix_bot.core.session.load_credentials")
    @patch("ratu_fix_bot.core.session.get_private_key")
    def test_bot_initialization(self, mock_get_private_key, mock_load_credentials, config, tmp_path):
        """Test bot initializes with config."""
        # Mock credentials
        mock_load_credentials.return_value = ("test_api_key", "test_key.pem")
        mock_get_private_key.return_value = b"test_private_key"
        
        # Update log file to temp directory
        config.log_file = str(tmp_path / "test_bot_log.txt")
        
        bot = RATUFixBot(config)
        
        assert bot.config == config
        assert bot.session is not None
        assert bot.market_data is None  # Not set until setup()
        assert bot.order_manager is None  # Not set until setup()
    
    def test_config_from_env(self, monkeypatch, tmp_path):
        """Test bot with config from environment."""
        monkeypatch.setenv("RATU_SYMBOL", "BTCUSDT")
        monkeypatch.setenv("RATU_ORDER_QTY", "0.001")
        
        config = RATUFixConfig.from_env()
        config.log_file = str(tmp_path / "test_bot_log.txt")
        
        assert config.symbol == "BTCUSDT"
        assert config.order_qty == 0.001

