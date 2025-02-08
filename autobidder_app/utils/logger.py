import os
import time
import logging
from django.utils.timezone import now, localtime

def setup_logger(name, log_directory="logs/default", days=7):

    os.makedirs(log_directory, exist_ok=True)

    # Clean old logs
    clean_old_logs(log_directory, days=days)

    # Create log file name based on the current date
    log_filename = os.path.join(log_directory, f"{name}_{localtime(now()).strftime('%Y-%m-%d')}.log")

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Prevent adding duplicate handlers
    if not logger.handlers:
        handler = logging.FileHandler(log_filename)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def clean_old_logs(log_dir, days=7):

    time_now = time.time()

    if not os.path.exists(log_dir):
        return

    for filename in os.listdir(log_dir):
        file_path = os.path.join(log_dir, filename)
        if os.path.isfile(file_path):
            file_age = time_now - os.path.getmtime(file_path)
            if file_age > days * 86400:  # 86400 seconds = 1 day
                os.remove(file_path)