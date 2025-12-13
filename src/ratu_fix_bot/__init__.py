"""RATU FIX Bot - Market Making Bot with Spread Strategy."""

__version__ = "0.1.0"

from ratu_fix_bot.config import RATUFixConfig
from ratu_fix_bot.core.bot import RATUFixBot

__all__ = ["RATUFixConfig", "RATUFixBot", "__version__"]

