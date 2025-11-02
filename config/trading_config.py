"""
Trading Configuration for Live Bot
Based on Test #11 Aggressive Strategy (+17.57% returns)
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TradingConfig:
    """Live trading configuration"""

    # API Credentials
    ASTER_API_KEY = os.getenv('ASTER_API_KEY')
    ASTER_API_SECRET = os.getenv('ASTER_API_SECRET')
    COINGLASS_API_KEY = os.getenv('COINGLASS_API_KEY')

    # Trading Mode
    MODE = 'LIVE'  # 'PAPER' or 'LIVE'
    SYMBOL = 'BTCUSDT'

    # Position Sizing (Aggressive Strategy)
    BASE_POSITION_SIZE = 0.35  # 35% initial position

    # Leverage Settings (Scaling up with conviction)
    LEVERAGE = {
        'base': 3,           # 3x for initial entry
        'single_tf': 3,      # 3x for single timeframe
        'multi_tf': 4,       # 4x for confluence
        'scale_in_1': 3,     # Keep 3x on first scale
        'scale_in_2': 4,     # Increase to 4x
        'scale_in_3': 5,     # Max 5x on deep scales
        'scale_in_4': 5,     # Max 5x leverage
    }

    # Scale-in Levels (Proven profitable)
    SCALE_LEVELS = [
        {'deviation': -0.01, 'add': 0.20},  # -1%: Add 20%
        {'deviation': -0.02, 'add': 0.25},  # -2%: Add 25%
        {'deviation': -0.04, 'add': 0.25},  # -4%: Add 25%
        {'deviation': -0.06, 'add': 0.30},  # -6%: Add 30%
    ]

    # Profit Taking (Systematic)
    PROFIT_TARGETS = [
        {'gain': 0.05, 'reduce': 0.25},  # +5%: Take 25% off
        {'gain': 0.10, 'reduce': 0.25},  # +10%: Take 25% off
        {'gain': 0.15, 'reduce': 0.25},  # +15%: Take 25% off
    ]

    # Risk Management
    DAILY_INVALIDATION = 0.10   # Exit if 10% below daily GP
    H4_INVALIDATION = 0.08       # Exit if 8% below 4H GP
    MAX_DRAWDOWN = 0.20          # Maximum 20% account drawdown
    INVALIDATION_LEVEL = -0.40   # Exit if 40% below entry (leveraged P&L)

    # Current Fibonacci Levels (as of Oct 29, 2025)
    FIBONACCI_LEVELS = {
        'daily': {
            'high': 126104,      # Oct 6 high
            'low': 98387,        # June 22 low
            'gp_top': 108975,    # 61.8%
            'gp_bottom': 108088, # 65.0%
            'fib_50': 112246,    # 50%
        },
        '4h': {
            'high': 126200,      # Oct 6 high
            'low': 103528,       # Oct 17 low
            'gp_top': 112189,    # 61.8%
            'gp_bottom': 111463, # 65.0%
            'fib_50': 114864,    # 50%
        }
    }

    # CoinGlass Sentiment Multipliers
    SENTIMENT_ADJUSTMENTS = {
        'ls_ratio': {
            'very_bullish': (2.0, 1.2),   # > 2.0 = 1.2x size
            'bullish': (1.5, 1.0),         # 1.5-2.0 = 1.0x
            'neutral': (1.0, 0.9),         # 1.0-1.5 = 0.9x
            'bearish': (0.0, 0.7),         # < 1.0 = 0.7x
        },
        'funding': {
            'extreme': (0.05, 0.5),        # > 5% = 0.5x (avoid)
            'high': (0.02, 0.8),           # 2-5% = 0.8x
            'neutral': (0.0, 1.0),         # 0-2% = 1.0x
            'negative': (-1.0, 1.3),       # < 0% = 1.3x (oversold)
        },
        'liquidations': {
            'long_flush': (0.7, 1.2),      # > 70% longs = 1.2x
            'balanced': (0.3, 1.0),        # 30-70% = 1.0x
            'short_squeeze': (0.0, 0.8),   # < 30% longs = 0.8x
        }
    }

    # API Endpoints (corrected from documentation)
    ASTER_BASE_URL = 'https://fapi.asterdex.com'
    COINGLASS_BASE_URL = 'https://open-api-v4.coinglass.com'

    # Timing Settings
    CHECK_INTERVAL = 60  # Check every 60 seconds
    COOLDOWN_AFTER_TRADE = 300  # 5 minute cooldown after trade

    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/live_trading.log'

    # Safety Features
    REQUIRE_CONFIRMATION = False  # Set True to require manual confirmation
    MAX_POSITION_SIZE = 1.5      # Never exceed 150% position
    EMERGENCY_STOP = False        # Kill switch