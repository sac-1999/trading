
import logging

# Configure the root logger
logging.basicConfig(
    level=logging.INFO,  # or DEBUG
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),  # Log to file
        logging.StreamHandler()          # Log to console
    ]
)

# Function to get a logger for any module
def get_logger(name):
    return logging.getLogger(name)
