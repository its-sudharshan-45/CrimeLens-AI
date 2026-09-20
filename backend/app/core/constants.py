from app.core.config import settings

# Application Information
APP_NAME = settings.PROJECT_NAME
API_VERSION = "1.0.0"
API_PREFIX = settings.API_V1_STR

# Pagination Defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Common Messages
MSG_APP_RUNNING = f"{APP_NAME} Backend Running"
MSG_HEALTH_OK = "healthy"
MSG_DB_CONNECTED = "Database Connected"

# Error Messages
ERROR_DB_CONNECTION = "Could not connect to the database."
ERROR_UNAUTHORIZED = "Unauthorized access."
