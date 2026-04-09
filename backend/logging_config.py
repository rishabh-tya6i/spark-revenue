import logging
import sys
from pythonjsonlogger import jsonlogger
from datetime import datetime

def setup_logging(level: str = "INFO"):
    logger = logging.getLogger()
    logger.setLevel(level)

    # If there are already handlers, clear them to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    
    # Custom formatter to include timestamp, level, name, and message
    class CustomJsonFormatter(jsonlogger.JsonFormatter):
        def add_fields(self, log_record, record, message_dict):
            super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
            if not log_record.get('timestamp'):
                # now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                now = datetime.now().isoformat()
                log_record['timestamp'] = now
            if log_record.get('level'):
                log_record['level'] = log_record['level'].upper()
            else:
                log_record['level'] = record.levelname

    formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s %(module)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

# Initialize logging when module is imported
logger = setup_logging()
