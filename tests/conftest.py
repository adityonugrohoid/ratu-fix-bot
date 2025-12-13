"""
Pytest configuration and fixtures for ratu-fix-bot tests.
"""

import pytest


@pytest.fixture
def sample_fix_message():
    """Sample FIX message for testing."""
    return "8=FIX.4.4\x0135=A\x0149=SENDER\x0156=SPOT\x0134=1\x0152=20231212-12:00:00.000000\x0110=123\x01"


@pytest.fixture
def malformed_fix_message():
    """Malformed FIX message for defensive parser testing."""
    return "8=FIX.4.4\x0135=A\x0149=SENDER\x01BADFIELD\x0156=SPOT\x0110=123\x01"


@pytest.fixture
def partial_fix_message():
    """Partial/incomplete FIX message for buffer testing."""
    return "8=FIX.4.4\x0135=A\x0149=SENDER\x0156=SPOT"
