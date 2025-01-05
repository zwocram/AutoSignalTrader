import logging
import os

def setup_logging(log_file: str = "app.log", log_level: int = logging.INFO) -> None:
    """
    Set up logging for the application.
    
    Parameters:
        log_file (str): Path to the log file.
        log_level (int): Logging level. Use logging.DEBUG, logging.INFO, etc.
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),  # Log to file
            logging.StreamHandler()        # Log to console
        ]
    )

    # Log startup message
    logging.info("Logging is set up successfully.")


if __name__ == "__main__":
    # Example usage
    setup_logging(log_file="logs/application.log", log_level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logger.info("This is an informational message.")
    logger.debug("This is a debug message.")
    logger.error("This is an error message.")
