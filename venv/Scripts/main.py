# main.py
import configparser
from display import DisplayManager

def main():
    # Load configuration
    config = configparser.ConfigParser()
    config.read('config.ini')

    # Determine environment
    environment = config.get('Environment', 'name', fallback='prod').lower()

    # Create an instance of DisplayManager
    display_manager = DisplayManager(config)

    # Run the display system
    display_manager.run()

if __name__ == "__main__":
    main()