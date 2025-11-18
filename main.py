# main.py
from app.config import load_config
from app.display_manager import DisplayManager


def main():
    config = load_config()
    display_manager = DisplayManager(config)
    display_manager.run()


if __name__ == "__main__":
    main()
