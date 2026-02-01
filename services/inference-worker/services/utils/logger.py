import json
import logging
import os
import sys


class StreamlitLogHandler(logging.Handler):
    def __init__(self, container):
        super().__init__()
        self.container = container
        self.log_lines = []

    def emit(self, record):
        try:
            log_entry = self.format(record)
            self.log_lines.append(log_entry)
            # Push updates to Streamlit container
            self.container.code("\n".join(self.log_lines), language="plaintext")
        except Exception:
            # self.handleError(record)
            pass


class CustomMessageFormatter(logging.Formatter):
    def formatMessage(self, record):
        # Don't overwrite record.message
        formatted = json.dumps({"message": record.getMessage()})
        return super().formatMessage(record).replace(record.getMessage(), formatted)


# Create a custom handler with the custom formatter
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(CustomMessageFormatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"))

log_level = os.getenv("LOG_LEVEL", "INFO").lower()

# Logger setup
logging.basicConfig(
    level=logging.INFO if log_level == "info" else logging.DEBUG,  # Set root logger to a higher level
    handlers=[stdout_handler],  # Log to stdout
)

# Create a global logger
logger = logging.getLogger("chicory-brewhub")
logger.setLevel(logging.INFO if log_level == "info" else logging.DEBUG)
