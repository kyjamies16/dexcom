# main.py
import configparser
from display import DisplayManager

def main():
    # Load configuration
    config = configparser.ConfigParser()
    config.read('config.ini')

    # Create an instance of DisplayManager
    display_manager = DisplayManager(config)

    # Run the display system
    display_manager.run()

if __name__ == "__main__":
    main()