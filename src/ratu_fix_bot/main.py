"""CLI entry point for RATU FIX Bot."""

import argparse
import os
from pathlib import Path

from ratu_fix_bot.config import RATUFixConfig
from ratu_fix_bot.core.bot import RATUFixBot


def main() -> None:
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="RATU FIX Bot - Spread Market Making Bot",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=os.path.join(Path(__file__).parent.parent.parent.parent, "config.ini"),
        help="Path to config.ini with API credentials"
    )
    parser.add_argument(
        "--symbol", "-s",
        type=str,
        default="ETHFDUSD",
        help="Trading pair symbol"
    )
    parser.add_argument(
        "--qty",
        type=float,
        default=0.002,
        help="Order quantity per side"
    )
    parser.add_argument(
        "--spread",
        type=float,
        default=0.01,
        help="Spread offset percentage (0.01 = 0.01%%)"
    )
    parser.add_argument(
        "--stale-threshold",
        type=int,
        default=2,
        help="Seconds before order is considered stale"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="bot_log.txt",
        help="Path to log file"
    )
    parser.add_argument(
        "--md-url",
        type=str,
        default="tcp+tls://fix-md.binance.com:9000",
        help="Market data FIX endpoint"
    )
    parser.add_argument(
        "--oe-url",
        type=str,
        default="tcp+tls://fix-oe.binance.com:9000",
        help="Order entry FIX endpoint"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    config = RATUFixConfig(
        symbol=args.symbol,
        order_qty=args.qty,
        spread_percent=args.spread,
        stale_threshold_sec=args.stale_threshold,
        md_url=args.md_url,
        oe_url=args.oe_url,
        log_file=args.log_file,
        log_level=args.log_level,
        config_path=args.config
    )
    
    bot = RATUFixBot(config)
    bot.run()


if __name__ == "__main__":
    main()
