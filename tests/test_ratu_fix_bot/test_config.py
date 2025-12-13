"""Tests for RATUFixConfig."""

import os

import pytest

from ratu_fix_bot.config import RATUFixConfig


class TestRATUFixConfig:
    """Test RATUFixConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = RATUFixConfig()
        
        assert config.symbol == "ETHFDUSD"
        assert config.order_qty == 0.002
        assert config.spread_percent == 0.01
        assert config.stale_threshold_sec == 2
        assert config.md_url == "tcp+tls://fix-md.binance.com:9000"
        assert config.oe_url == "tcp+tls://fix-oe.binance.com:9000"
        assert config.log_file == "bot_log.txt"
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = RATUFixConfig(
            symbol="BTCUSDT",
            order_qty=0.001,
            spread_percent=0.1,
            stale_threshold_sec=10,
            log_file="custom_log.txt"
        )
        
        assert config.symbol == "BTCUSDT"
        assert config.order_qty == 0.001
        assert config.spread_percent == 0.1
        assert config.stale_threshold_sec == 10
        assert config.log_file == "custom_log.txt"
    
    def test_from_env(self, monkeypatch):
        """Test creating config from environment variables."""
        monkeypatch.setenv("RATU_SYMBOL", "BNBUSDT")
        monkeypatch.setenv("RATU_ORDER_QTY", "0.05")
        monkeypatch.setenv("RATU_SPREAD_PERCENT", "0.5")
        monkeypatch.setenv("RATU_STALE_THRESHOLD_SEC", "5")
        
        config = RATUFixConfig.from_env()
        
        assert config.symbol == "BNBUSDT"
        assert config.order_qty == 0.05
        assert config.spread_percent == 0.5
        assert config.stale_threshold_sec == 5
    
    def test_config_path_default(self):
        """Test that config_path has a default value."""
        config = RATUFixConfig()
        assert config.config_path  # Should not be empty
        assert config.config_path.endswith("config.ini")
    
    def test_config_path_custom(self):
        """Test custom config_path."""
        config = RATUFixConfig(config_path="/custom/path/config.ini")
        assert config.config_path == "/custom/path/config.ini"

