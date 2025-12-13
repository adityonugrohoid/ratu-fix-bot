"""
Tests for the FIX connector module.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_import_fix_connector():
    """Test that the FIX connector can be imported."""
    from binance_fix_connector.fix_connector import BinanceFixConnector
    assert BinanceFixConnector is not None


def test_import_session_creators():
    """Test that session creator functions can be imported."""
    from binance_fix_connector.fix_connector import (
        create_drop_copy_session,
        create_market_data_session,
        create_order_entry_session,
    )
    assert create_market_data_session is not None
    assert create_order_entry_session is not None
    assert create_drop_copy_session is not None


def test_fix_tags():
    """Test FIX tags constants."""
    from binance_fix_connector.fix_connector import FixTags
    
    assert FixTags.BEGIN_STRING == "8"
    assert FixTags.MSG_TYPE == "35"
    assert FixTags.SENDER_COMP_ID == "49"
    assert FixTags.CHECKSUM == "10"


def test_fix_msg_types():
    """Test FIX message type constants."""
    from binance_fix_connector.fix_connector import FixMsgTypes
    
    assert FixMsgTypes.LOGON == "A"
    assert FixMsgTypes.LOGOUT == "5"
    assert FixMsgTypes.HEARTBEAT == "0"
