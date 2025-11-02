"""
Configuration file for Vibe Trader
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Aster API Configuration
ASTER_BASE_URL = "https://fapi.asterdex.com"
ASTER_WS_URL = "wss://fstream.asterdex.com"
ASTER_API_KEY = os.getenv("ASTER_API_KEY", "")
ASTER_API_SECRET = os.getenv("ASTER_API_SECRET", "")

# CoinGlass API Configuration
COINGLASS_API_KEY = os.getenv("COINGLASS_API_KEY", "")  # Add when you get it
COINGLASS_BASE_URL = "https://open-api-v4.coinglass.com"

# Claude API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")  # Your Claude API key

# Trading Configuration
TRADING_SYMBOLS = ["SOLUSDT", "BTCUSDT", "ETHUSDT"]
DEFAULT_LEVERAGE = 3
MAX_POSITION_SIZE_USD = 100  # Maximum position size per trade
RISK_PER_TRADE = 0.02  # Risk 2% per trade
MIN_CONFIDENCE = 0.65  # Minimum AI confidence to trade (0-1)

# Paper Trading Mode
PAPER_TRADING = True  # Set to False for live trading
PAPER_BALANCE = 1000  # Starting paper balance

# Decision Making
DECISION_INTERVAL = 300  # Check market every 5 minutes (300 seconds)
MAX_OPEN_POSITIONS = 3  # Maximum concurrent positions

# Dashboard Configuration
DASHBOARD_PORT = 8000
DASHBOARD_HOST = "0.0.0.0"

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "logs/vibe_trader.log"
