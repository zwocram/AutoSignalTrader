# logger_setup.py

import logging

class LoggerSingleton:
    _instance = None

    @staticmethod
    def get_logger(log_file='data/log.txt'):  # Standaard log_file
        if LoggerSingleton._instance is None:
            LoggerSingleton._instance = logging.getLogger("SignalTraderLogger")
            LoggerSingleton._instance.setLevel(logging.INFO)

            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            LoggerSingleton._instance.addHandler(console_handler)

            # File handler
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            LoggerSingleton._instance.addHandler(file_handler)

        return LoggerSingleton._instance
