# main.py
import argparse

from app.config import load_config
from app.display_manager import DisplayManager


def _parse_args():
    parser = argparse.ArgumentParser(description="Dexcom LED wallboard")
    parser.add_argument(
        "--mode",
        choices=["minimal", "full"],
        default="full",
        help="Control optional features/dependencies (default: full)",
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    config = load_config(mode=args.mode)
    display_manager = DisplayManager(config)
    display_manager.run()


if __name__ == "__main__":
    main()
