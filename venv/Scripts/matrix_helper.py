# matrix_helper.py
import configparser
import logging

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')
environment = config.get('Environment', 'name', fallback='prod')

# Conditional import based on environment
if environment == 'dev':
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions, graphics
    logging.info("Using RGBMatrixEmulator for development.")
else:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
    logging.info("Using RGBMatrix for production.")

# Function to initialize the matrix
def initialize_matrix(options):
    return RGBMatrix(options=options)
