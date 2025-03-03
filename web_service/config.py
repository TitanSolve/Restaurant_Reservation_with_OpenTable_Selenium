import logging
import pytz
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Define Mexico City timezone
MEXICO_TZ = pytz.timezone("America/Mexico_City")

class MexicoTimeFormatter(logging.Formatter):
    """Custom formatter to log times in Mexico City time zone."""
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=MEXICO_TZ)
        return dt.strftime(datefmt or "%Y-%m-%d %H:%M:%S %Z")

# Log format and date format
log_format = "%(asctime)s %(levelname)s: %(message)s"
date_format = "%Y-%m-%d %H:%M:%S %Z"
log_file = "app.log"

# Create rotating file handler
file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
file_formatter = MexicoTimeFormatter(fmt=log_format, datefmt=date_format)
file_handler.setFormatter(file_formatter)

# Create console handler
console_handler = logging.StreamHandler()
console_formatter = MexicoTimeFormatter(fmt=log_format, datefmt=date_format)
console_handler.setFormatter(console_formatter)

# Configure root logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Change to DEBUG for more details
logger.addHandler(file_handler)
logger.addHandler(console_handler)
