import os
import logging

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("mcp_finance")

# Защитные лимиты
MAX_PRINCIPAL = float(os.getenv("MAX_PRINCIPAL", "1e9"))        # 1 млрд
MAX_CONTRIBUTION = float(os.getenv("MAX_CONTRIBUTION", "1e8"))  # 100 млн
MAX_MONTHS = int(os.getenv("MAX_MONTHS", "600"))                 # 50 лет
MAX_RATE = float(os.getenv("MAX_RATE", "200"))                   # 200% годовых
MAX_BALANCE_CAP = float(os.getenv("MAX_BALANCE_CAP", "1e12"))    # 1 трлн
