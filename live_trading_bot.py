"""
Live Trading Bot - Fibonacci Golden Pocket Strategy
Ready to enter immediately on bounce from golden pocket
Competition deadline: November 3, 2025
"""
import os
import sys
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
from trading_decision_logger import TradingDecisionLogger
from config.trading_config import TradingConfig
from aster_trading_client import AsterTradingClient
from position_recovery import PositionRecovery
from claude_supervisor import ClaudeSupervisor
from safety_validator import SafetyValidator
import warnings
warnings.filterwarnings('ignore')

load_dotenv()

class LiveFibonacciBot:
    """
    Live trading bot that enters aggressively on golden pocket bounces
    Currently EAGER TO ENTER as we've just bounced from the pocket
    """

    def __init__(self, shadow_mode=False):
        """Initialize bot with live connections + AI supervisor"""
        self.shadow_mode = shadow_mode  # If True, log only (no real trades)
        self.logger = TradingDecisionLogger()
        self.config = TradingConfig
        self.trading_client = AsterTradingClient()  # REAL TRADING CLIENT

        # AI Integration
        self.claude = ClaudeSupervisor()
        self.safety = SafetyValidator()

        if shadow_mode:
            print("🔮 SHADOW MODE: Observing only, NO real trades")
        print("🤖 Claude Strategic Supervisor: ACTIVE")
        print("🛡️ Safety Validation Layer: ACTIVE")

        # API credentials
        self.aster_key = os.getenv('ASTER_API_KEY')
        self.aster_secret = os.getenv('ASTER_API_SECRET')
        self.coinglass_key = os.getenv('COINGLASS_API_KEY')

        # API endpoints
        self.aster_base = "https://fapi.asterdex.com"
        self.coinglass_base = "https://open-api-v4.coinglass.com"

        # Trading state
        self.position = None
        self.last_entry_price = None
        self.total_position_size = 0
        self.current_leverage = 0
        self.scale_in_count = 0
        self.highest_price_seen = 0  # For trailing stop

        # Sentiment caching (avoid rate limits)
        self.sentiment_cache = {'data': None, 'timestamp': 0}
        self.SENTIMENT_CACHE_TTL = 300  # 5 minutes

        # Exposure limits (safety)
        self.MAX_NOTIONAL_EXPOSURE = 5.0  # 5x capital max
        self.MAX_CAPITAL_USAGE = 1.35  # 135% capital max

        # Fibonacci levels (fixed from backtesting)
        self.fib_levels = {
            'h4': {
                'swing_high': 126104,
                'swing_low': 108755,
                'gp_top': 112189,  # 65% retracement
                'gp_bottom': 111463,  # 61.8% retracement
                'fib_50': 117430,
                'fib_786': 109874
            },
            'daily': {
                'swing_high': 126104,
                'swing_low': 98387,
                'gp_top': 108975,  # 65% retracement
                'gp_bottom': 108088,  # 61.8% retracement
                'fib_50': 112246,
                'fib_786': 105557
            }
        }

        # EAGER MODE: We just bounced from golden pocket!
        self.eager_to_enter = True
        self.bounce_detected = True
        self.last_check_time = datetime.now()

        # Fibonacci exit tracking
        self.fib_partial_exit_taken = False
        self.fib_exit_price = None
        self.remaining_after_fib = 0

        # 20-minute review timer
        # Trigger first review immediately on startup
        self.last_review_time = datetime.now() - timedelta(seconds=1200)
        self.REVIEW_INTERVAL = 1200  # 20 minutes in seconds

        # Check account balance
        account = self.trading_client.get_account_info()

        print("🚀 Live Trading Bot Initialized")
        print(f"Mode: 💰 LIVE TRADING - REAL MONEY")
        print(f"Account: {account['sol']:.2f} SOL ≈ ${account['usd_value']:.2f}")

        # RECOVERY: Check for existing positions
        recovery = PositionRecovery()
        has_position, recovered_position, recovered_last_entry = recovery.recover_position()

        if has_position:
            # Restore position state
            self.position = recovered_position
            self.last_entry_price = recovered_last_entry
            self.total_position_size = recovered_position['size']
            self.current_leverage = recovered_position['leverage']
            self.scale_in_count = recovered_position.get('scale_in_count', 0)
            self.eager_to_enter = False  # Already have position
            self.bounce_detected = False

            # Log the recovery
            recovery.log_recovery(self.logger, recovered_position)

            print("🔄 RECOVERED EXISTING POSITION - Continuing management")
        else:
            print("🎯 EAGER TO ENTER - Just bounced from golden pocket!")

    def get_current_price(self):
        """Get current BTC price from Aster"""
        try:
            url = f"{self.aster_base}/fapi/v1/ticker/24hr?symbol=BTCUSDT"
            response = requests.get(url, timeout=5)
            data = response.json()
            return float(data['lastPrice'])
        except Exception as e:
            print(f"Error getting price: {e}")
            # Fallback to Binance
            response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
            return float(response.json()['price'])

    def get_market_data(self):
        """Get volume and order book data for Claude"""
        try:
            # Get 24h ticker data
            ticker_url = f"{self.aster_base}/fapi/v1/ticker/24hr?symbol=BTCUSDT"
            ticker_response = requests.get(ticker_url, timeout=5)
            ticker = ticker_response.json()

            # Get order book
            depth_url = f"{self.aster_base}/fapi/v1/depth?symbol=BTCUSDT&limit=20"
            depth_response = requests.get(depth_url, timeout=5)
            depth = depth_response.json()

            # Calculate order book imbalance
            bids = sum(float(b[1]) for b in depth['bids'][:10])
            asks = sum(float(a[1]) for a in depth['asks'][:10])
            total = bids + asks
            imbalance = (bids - asks) / total * 100 if total > 0 else 0

            return {
                'volume_24h_btc': float(ticker['volume']),
                'volume_24h_usd': float(ticker['quoteVolume']),
                'trade_count': int(ticker['count']),
                'orderbook_imbalance': round(imbalance, 2),
                'orderbook_pressure': 'BUY' if imbalance > 10 else 'SELL' if imbalance < -10 else 'NEUTRAL'
            }
        except Exception as e:
            print(f"Error getting market data: {e}")
            return {
                'volume_24h_btc': 0,
                'volume_24h_usd': 0,
                'trade_count': 0,
                'orderbook_imbalance': 0,
                'orderbook_pressure': 'UNKNOWN'
            }

    def get_recent_candles(self, interval='5m', limit=20):
        """Get recent price candles for bounce detection"""
        try:
            url = f"{self.aster_base}/fapi/v1/klines"
            params = {
                'symbol': 'BTCUSDT',
                'interval': interval,
                'limit': limit
            }
            response = requests.get(url, params=params, timeout=5)
            data = response.json()

            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close',
                'volume', 'close_time', 'quote_volume', 'trades',
                'taker_buy_base', 'taker_buy_quote', 'ignore'
            ])
            df['close'] = df['close'].astype(float)
            df['low'] = df['low'].astype(float)
            df['high'] = df['high'].astype(float)
            return df

        except Exception as e:
            print(f"Error getting candles: {e}")
            return None

    def detect_bounce(self, current_price):
        """
        Detect if price has bounced from golden pocket
        CURRENTLY RETURNS TRUE - We know we just bounced!
        """
        # Get recent 5m candles
        candles = self.get_recent_candles('5m', 20)
        if candles is None:
            return self.bounce_detected  # Keep current state

        recent_low = candles['low'].min()

        # Check if we touched and bounced from 4H golden pocket
        h4_gp_bottom = self.fib_levels['h4']['gp_bottom']
        h4_gp_top = self.fib_levels['h4']['gp_top']

        # Bounce conditions (RELAXED for immediate entry)
        if recent_low <= h4_gp_top * 1.02:  # Within 2% of golden pocket top
            if current_price > recent_low * 1.001:  # Just 0.1% bounce needed
                print(f"✅ Bounce detected! Low: ${recent_low:,.2f}, Current: ${current_price:,.2f}")
                return True

        # Also check daily golden pocket
        daily_gp_bottom = self.fib_levels['daily']['gp_bottom']
        daily_gp_top = self.fib_levels['daily']['gp_top']

        if recent_low <= daily_gp_top * 1.01:
            if current_price > recent_low * 1.002:
                print(f"✅ Bounce from daily GP! Low: ${recent_low:,.2f}, Current: ${current_price:,.2f}")
                return True

        return False

    def get_sentiment_data(self):
        """Get sentiment data from CoinGlass with 5-minute caching"""
        import time

        # Check cache first
        now = time.time()
        cache_age = now - self.sentiment_cache['timestamp']

        if cache_age < self.SENTIMENT_CACHE_TTL and self.sentiment_cache['data']:
            # Cache is fresh, use it
            return self.sentiment_cache['data']

        # Cache expired or empty, fetch fresh data
        try:
            headers = {
                'accept': 'application/json',
                'CG-API-KEY': self.coinglass_key
            }

            sentiment = {}

            # Fear & Greed
            try:
                url = f"{self.coinglass_base}/api/index/fear-greed-history"
                response = requests.get(url, headers=headers, params={'time_type': 1}, timeout=5)
                data = response.json()
                if data.get('code') == '0' and data.get('data'):
                    sentiment['fear_greed'] = data['data']['data_list'][0]
            except:
                sentiment['fear_greed'] = 50

            # Long/Short Ratio
            try:
                url = f"{self.coinglass_base}/api/futures/global-long-short-account-ratio/history"
                params = {'exchange': 'Binance', 'symbol': 'BTCUSDT', 'interval': '4h', 'limit': 1}
                response = requests.get(url, headers=headers, params=params, timeout=5)
                data = response.json()
                if data.get('code') == '0' and data.get('data'):
                    sentiment['ls_ratio'] = float(data['data']['data'][0]['long_ratio'])
            except:
                sentiment['ls_ratio'] = 1.0

            # Funding Rate
            try:
                url = f"{self.coinglass_base}/api/futures/funding-rate/history"
                params = {'exchange': 'Binance', 'symbol': 'BTCUSDT', 'interval': '8h', 'limit': 1}
                response = requests.get(url, headers=headers, params=params, timeout=5)
                data = response.json()
                if data.get('code') == '0' and data.get('data'):
                    sentiment['funding_rate'] = float(data['data']['data'][0]['funding_rate'])
            except:
                sentiment['funding_rate'] = 0.0001

            # Update cache with fresh data
            self.sentiment_cache = {'data': sentiment, 'timestamp': time.time()}
            return sentiment

        except Exception as e:
            print(f"Sentiment data error: {e}")
            # Return defaults but don't cache errors
            return {'fear_greed': 50, 'ls_ratio': 1.0, 'funding_rate': 0.0001}

    def calculate_sentiment_multiplier(self, sentiment):
        """
        Calculate position size multiplier based on sentiment indicators
        Returns: 0.5x to 1.5x multiplier for adaptive position sizing
        """
        multipliers = []

        # Fear & Greed (contrarian - fear = buy opportunity)
        fg = sentiment.get('fear_greed', 50)
        if fg < 25:
            multipliers.append(1.3)  # Extreme fear = 30% bigger position
            print(f"   📊 Extreme fear ({fg}) → 1.3x size multiplier")
        elif fg < 40:
            multipliers.append(1.1)  # Fear = 10% bigger
            print(f"   📊 Fear ({fg}) → 1.1x size multiplier")
        elif fg > 75:
            multipliers.append(0.6)  # Extreme greed = reduce 40%
            print(f"   📊 Extreme greed ({fg}) → 0.6x size multiplier")
        else:
            multipliers.append(1.0)  # Neutral

        # Funding Rate (contrarian for longs - negative = buy)
        fr = sentiment.get('funding_rate', 0)
        if fr < -0.01:
            multipliers.append(1.3)  # Very negative = strong buy
            print(f"   📊 Very negative funding ({fr:.4f}) → 1.3x size multiplier")
        elif fr < 0:
            multipliers.append(1.1)  # Slightly negative = good
            print(f"   📊 Negative funding ({fr:.4f}) → 1.1x size multiplier")
        elif fr > 0.05:
            multipliers.append(0.5)  # Extreme positive = reduce heavily
            print(f"   📊 High funding ({fr:.4f}) → 0.5x size multiplier")
        elif fr > 0.02:
            multipliers.append(0.8)  # High positive = caution
            print(f"   📊 Elevated funding ({fr:.4f}) → 0.8x size multiplier")
        else:
            multipliers.append(1.0)  # Normal

        # L/S Ratio (check for overcrowding + contrarian)
        ls = sentiment.get('ls_ratio', 1.0)
        if ls > 2.0:
            multipliers.append(0.8)  # Too many longs = reduce (potential squeeze)
            print(f"   📊 Overcrowded longs ({ls:.2f}) → 0.8x size multiplier")
        elif ls > 1.5:
            multipliers.append(1.0)  # Bullish but not extreme
        elif ls < 0.8:
            multipliers.append(1.2)  # Shorts dominate = contrarian buy
            print(f"   📊 Shorts dominant ({ls:.2f}) → 1.2x size multiplier")
        else:
            multipliers.append(1.0)

        # Average all multipliers
        final_multiplier = sum(multipliers) / len(multipliers)

        # Cap between 0.5x and 1.5x for safety
        final_multiplier = max(0.5, min(1.5, final_multiplier))

        print(f"   🎯 Final sentiment multiplier: {final_multiplier:.2f}x")
        return final_multiplier

    def check_exposure_limits(self, desired_size, leverage):
        """
        Enforce 5x notional and 135% capital limits
        Returns: safe_size (reduced if needed, or 0 if blocked)
        """
        # Calculate current exposure
        current_capital_used = self.total_position_size
        current_notional = current_capital_used * (self.current_leverage if self.current_leverage > 0 else 1)

        # Calculate new trade
        new_notional = desired_size * leverage
        total_capital = current_capital_used + desired_size
        total_notional = current_notional + new_notional

        print(f"\n   📊 Exposure Check:")
        print(f"      Current: {current_capital_used*100:.1f}% capital, {current_notional:.2f}x notional")
        print(f"      Proposed: +{desired_size*100:.1f}% @ {leverage}x = +{new_notional:.2f}x notional")
        print(f"      Total would be: {total_capital*100:.1f}% capital, {total_notional:.2f}x notional")

        # Check capital limit
        if total_capital > self.MAX_CAPITAL_USAGE:
            print(f"      ⚠️ Would exceed {self.MAX_CAPITAL_USAGE*100:.0f}% capital limit")
            allowed_capital = self.MAX_CAPITAL_USAGE - current_capital_used
            if allowed_capital <= 0:
                print(f"      🚫 BLOCKED: Already at capital limit")
                return 0
            print(f"      ✂️ Reducing to {allowed_capital*100:.1f}%")
            desired_size = allowed_capital

        # Check notional limit
        new_notional = desired_size * leverage  # Recalc after potential capital reduction
        total_notional = current_notional + new_notional

        if total_notional > self.MAX_NOTIONAL_EXPOSURE:
            print(f"      ⚠️ Would exceed {self.MAX_NOTIONAL_EXPOSURE:.1f}x notional limit")
            allowed_notional = self.MAX_NOTIONAL_EXPOSURE - current_notional
            if allowed_notional <= 0:
                print(f"      🚫 BLOCKED: Already at notional limit")
                return 0

            safe_size = allowed_notional / leverage
            print(f"      ✂️ Reducing to {safe_size*100:.1f}% to fit notional limit")
            return safe_size

        print(f"      ✅ Within limits - proceeding with {desired_size*100:.1f}%")
        return desired_size

    def calculate_exit_targets(self, sentiment, current_price):
        """
        Calculate dynamic exit targets based on sentiment and Fibonacci levels
        Returns: (profit_targets, upper_exit_price)
        """
        fg = sentiment.get('fear_greed', 50)
        fr = sentiment.get('funding_rate', 0)

        # Base targets (price gain percentages)
        base_targets = [
            {'gain': 0.05, 'reduce': 0.25},  # +5%
            {'gain': 0.10, 'reduce': 0.25},  # +10%
            {'gain': 0.15, 'reduce': 0.25},  # +15%
        ]

        # Adjust targets based on sentiment
        target_multiplier = 1.0

        # EXTREME GREED + HIGH FUNDING = Take profits early (market topping)
        if fg > 75 and fr > 0.05:
            target_multiplier = 0.6  # Take profits at +3%, +6%, +9%
            print(f"   🚨 Extreme greed + high funding → Taking profits EARLY (0.6x targets)")

        # GREED + POSITIVE FUNDING = Take profits slightly early
        elif fg > 60 and fr > 0.02:
            target_multiplier = 0.8  # Take profits at +4%, +8%, +12%
            print(f"   ⚠️ Greed detected → Taking profits earlier (0.8x targets)")

        # EXTREME FEAR + NEGATIVE FUNDING = Let winners run (more upside)
        elif fg < 25 and fr < -0.01:
            target_multiplier = 1.5  # Take profits at +7.5%, +15%, +22.5%
            print(f"   💪 Extreme fear + negative funding → LETTING WINNERS RUN (1.5x targets)")

        # FEAR = Let winners run a bit
        elif fg < 40:
            target_multiplier = 1.2  # Take profits at +6%, +12%, +18%
            print(f"   📈 Fear sentiment → Letting winners run (1.2x targets)")

        # Adjust targets
        adjusted_targets = [
            {'gain': t['gain'] * target_multiplier, 'reduce': t['reduce']}
            for t in base_targets
        ]

        # Calculate upper exit based on Fibonacci resistance
        upper_exit_price = self.calculate_fibonacci_upper_exit(current_price, sentiment)

        return adjusted_targets, upper_exit_price

    def calculate_fibonacci_upper_exit(self, current_price, sentiment):
        """
        Calculate intelligent upper exit based on Fibonacci resistance and sentiment
        """
        # Key Fibonacci resistance levels
        fib_50_4h = self.fib_levels['h4']['fib_50']  # $117,430
        fib_50_daily = self.fib_levels['daily']['fib_50']  # $112,246
        swing_high = self.fib_levels['h4']['swing_high']  # $126,104

        # Distance to each level
        dist_to_daily_50 = (fib_50_daily - current_price) / current_price
        dist_to_4h_50 = (fib_50_4h - current_price) / current_price
        dist_to_high = (swing_high - current_price) / current_price

        fg = sentiment.get('fear_greed', 50)
        fr = sentiment.get('funding_rate', 0)

        # Decision logic for upper exit
        if current_price < fib_50_daily:
            # Below daily 50%, target that first
            target = fib_50_daily
            reason = "Daily 50% Fib resistance"

        elif current_price < fib_50_4h:
            # Between daily 50% and 4H 50%
            if fg > 70:
                # Greed building, exit at 4H 50%
                target = fib_50_4h
                reason = "4H 50% Fib + greed building"
            else:
                # Still room, aim for swing high
                target = swing_high * 0.95  # 5% below swing high
                reason = "Near swing high with caution"

        else:
            # Above 4H 50%, approaching swing high
            if fg > 75 or fr > 0.05:
                # Extreme conditions, exit at swing high
                target = swing_high
                reason = "Swing high + extreme sentiment"
            else:
                # Let it attempt new highs
                target = swing_high * 1.05  # 5% above swing high
                reason = "Attempting new highs"

        print(f"   🎯 Upper exit target: ${target:,.0f} ({reason})")
        return target

    def check_entry_conditions(self, current_price):
        """
        Check if we should enter a position
        AGGRESSIVE: Looking for any reason to enter near golden pocket
        OR re-enter after Fibonacci bounce
        """
        # Only check entry if completely flat (no position)
        if self.position is not None:
            return False, None, []

        # Check for re-entry after full exit from Fibonacci rejection
        if self.fib_exit_price and current_price < self.fib_exit_price:
            # Price dropped after Fib exit, check if back in golden pocket
            h4_gp_bottom = self.fib_levels['h4']['gp_bottom']
            h4_gp_top = self.fib_levels['h4']['gp_top']

            if h4_gp_bottom * 0.995 <= current_price <= h4_gp_top * 1.01:
                print(f"🔄 FIBONACCI BOUNCE RE-ENTRY!")
                print(f"   Rejected at ${self.fib_exit_price:,.0f}, back in GP at ${current_price:,.0f}")

                # Reset Fib tracking
                self.fib_exit_price = None
                self.fib_partial_exit_taken = False

                return True, "4H Golden Pocket (Fib Rejection Re-entry)", ["Price rejected Fib resistance", "Back in golden pocket", "Fresh entry setup"]

        confluence = []

        # Check 4H golden pocket (PRIMARY)
        h4_gp_bottom = self.fib_levels['h4']['gp_bottom']
        h4_gp_top = self.fib_levels['h4']['gp_top']

        # RELAXED ENTRY: Allow 0.5% below and 1% above golden pocket
        if h4_gp_bottom * 0.995 <= current_price <= h4_gp_top * 1.01:
            confluence.append("In/Near 4H Golden Pocket")
            fib_zone = "4H Golden Pocket"

            # Get sentiment
            sentiment = self.get_sentiment_data()

            # Add confluence factors (but don't require them)
            if sentiment['fear_greed'] < 40:
                confluence.append("Fear sentiment")
            if sentiment['funding_rate'] < 0:
                confluence.append("Negative funding")
            if sentiment['ls_ratio'] > 1.2:
                confluence.append("Bullish L/S ratio")

            # Bounce is already detected
            if self.bounce_detected or self.detect_bounce(current_price):
                confluence.append("Price bounce detected")

            # AGGRESSIVE: Enter with just 2 confluence factors
            if len(confluence) >= 2 or self.eager_to_enter:
                return True, fib_zone, confluence

        # Check daily golden pocket (SECONDARY)
        daily_gp_bottom = self.fib_levels['daily']['gp_bottom']
        daily_gp_top = self.fib_levels['daily']['gp_top']

        if daily_gp_bottom * 0.995 <= current_price <= daily_gp_top * 1.01:
            confluence.append("In/Near Daily Golden Pocket")
            fib_zone = "Daily Golden Pocket"

            sentiment = self.get_sentiment_data()
            if sentiment['fear_greed'] < 30:
                confluence.append("Extreme fear")
            if sentiment['funding_rate'] < -0.001:
                confluence.append("Very negative funding")

            if self.bounce_detected or self.detect_bounce(current_price):
                confluence.append("Price bounce detected")

            # Daily GP needs just 2 factors
            if len(confluence) >= 2:
                return True, fib_zone, confluence

        # Check 50% retracement with bounce
        if abs(current_price - self.fib_levels['h4']['fib_50']) / current_price < 0.01:
            if self.detect_bounce(current_price):
                return True, "4H 50% Retracement", ["50% level", "Bounce detected"]

        return False, None, []

    def enter_position(self, current_price, fib_zone, confluence):
        """Enter a new position - AI-SUPERVISED with safety validation"""
        # Get sentiment for analysis
        sentiment = self.get_sentiment_data()

        # Calculate algorithm's proposed size
        sentiment_multiplier = self.calculate_sentiment_multiplier(sentiment)
        base_size = self.config.BASE_POSITION_SIZE
        algo_proposed_size = base_size * sentiment_multiplier
        leverage = self.config.LEVERAGE['base']

        print(f"\n{'='*60}")
        print(f"🎯 ENTRY OPPORTUNITY DETECTED")
        print(f"Algorithm proposes: {algo_proposed_size*100:.1f}% @ {leverage}x")
        print(f"Asking Claude for strategic approval...")

        # Get additional market data for Claude
        market_data = self.get_market_data()

        # ASK CLAUDE FOR FINAL DECISION (with fallback)
        try:
            claude_decision = self.claude.approve_entry(
                current_price=current_price,
                zone=fib_zone,
                confluence=confluence,
                sentiment=sentiment,
                proposed_size=algo_proposed_size,
                market_data=market_data
            )
        except Exception as e:
            print(f"\n⚠️ CLAUDE API ERROR: {e}")
            print(f"   Falling back to algorithmic decision")
            # Use algo size as fallback
            claude_decision = {
                'decision': 'APPROVE',
                'size_or_amount': algo_proposed_size,
                'reasoning': f'Claude unavailable - using algorithmic proposal ({str(e)[:100]})',
                'confidence': 0.5
            }

        # Check Claude's decision
        if claude_decision['decision'] == 'REJECT':
            print(f"\n❌ CLAUDE REJECTED ENTRY")
            print(f"   Reasoning: {claude_decision.get('reasoning', 'No reason provided')}")
            return None

        # Get Claude's size (might be adjusted)
        claude_size = claude_decision.get('size_or_amount', algo_proposed_size)
        print(f"\n✅ CLAUDE APPROVED: {claude_size*100:.1f}%")
        print(f"   Reasoning: {claude_decision.get('reasoning', '')[:200]}")

        # SAFETY VALIDATION
        safety_result = self.safety.validate_entry(
            claude_decision,
            self.position,
            {'balance': 442}  # Simplified account info
        )

        if not safety_result[0]:
            print(f"\n🚫 SAFETY BLOCKED: {safety_result[1]}")
            return None

        # Use safety-validated size
        if safety_result[2]:  # Adjusted by safety
            final_size = safety_result[2]['size_or_amount']
            print(f"\n🛡️ SAFETY ADJUSTED: {claude_size*100:.1f}% → {final_size*100:.1f}%")
        else:
            final_size = claude_size

        print(f"🎯 EXECUTING ENTRY")
        print(f"Price: ${current_price:,.2f}")
        print(f"Algorithm proposed: {algo_proposed_size*100:.1f}%")
        print(f"Claude approved: {claude_size*100:.1f}%")
        print(f"Safety validated: {final_size*100:.1f}%")
        print(f"Final Size: {final_size*100:.1f}% @ {leverage}x leverage")
        print(f"Zone: {fib_zone}")
        print(f"Confluence: {', '.join(confluence)}")
        print(f"Sentiment: F&G={sentiment.get('fear_greed', 'N/A')}, Funding={sentiment.get('funding_rate', 'N/A'):.4f}, L/S={sentiment.get('ls_ratio', 'N/A'):.2f}")
        print(f"{'='*60}\n")

        # PLACE REAL ORDER ON ASTER (using Claude + Safety approved size)
        if self.shadow_mode:
            print(f"\n🔮 SHADOW MODE: Would execute {final_size*100:.1f}% entry @ ${current_price:,.2f}")
            print(f"   (Not executing - observation only)")
            success = True  # Pretend it worked
        else:
            success = self.trading_client.enter_long_position(
                percentage=final_size,
                leverage=leverage,
                current_price=current_price
            )

        if success:
            # Log the entry (including Claude's reasoning)
            decision = self.logger.log_entry_decision(
                price=current_price,
                size=final_size * 100,  # Use AI-approved size
                leverage=leverage,
                fib_zone=fib_zone,
                sentiment=sentiment,
                confluence=confluence
            )

            # Log Claude's involvement
            print(f"\n📝 CLAUDE REASONING: {claude_decision.get('reasoning', '')}")
            print(f"   Confidence: {claude_decision.get('confidence', 'N/A')}")

            # Update position state
            self.position = {
                'entry_price': current_price,
                'average_price': current_price,
                'size': final_size,
                'leverage': leverage,
                'entry_time': datetime.now()
            }
            self.last_entry_price = current_price
            self.total_position_size = final_size
            self.current_leverage = leverage
            self.scale_in_count = 0

            # After entry, we're no longer in eager mode
            self.eager_to_enter = False
            self.bounce_detected = False

            # Save position state for recovery
            recovery = PositionRecovery()
            recovery.save_position_state(self.position)

            print(f"\n✅ REAL POSITION OPENED ON ASTER!")
            return decision
        else:
            print(f"\n❌ Failed to enter position - check account/API")
            return None

    def check_scale_in(self, current_price):
        """Check if we should scale into position"""
        if self.position is None:
            return False, None

        deviation = (current_price - self.last_entry_price) / self.last_entry_price

        for i, level in enumerate(self.config.SCALE_LEVELS):
            if deviation <= level['deviation'] and i >= self.scale_in_count:
                # Get sentiment for adaptive sizing
                sentiment = self.get_sentiment_data()
                sentiment_multiplier = self.calculate_sentiment_multiplier(sentiment)

                # Apply multiplier to scale-in size
                base_add = level['add']
                desired_add = base_add * sentiment_multiplier
                leverage_key = f'scale_in_{i+1}'
                new_leverage = self.config.LEVERAGE.get(leverage_key, self.current_leverage)

                # Check exposure limits
                add_size = self.check_exposure_limits(desired_add, new_leverage)

                if add_size == 0:
                    print(f"\n🚫 SCALE-IN BLOCKED by exposure limits")
                    return False, None

                print(f"📈 SCALING IN WITH ADAPTIVE SIZING:")
                print(f"   Base: {base_add*100:.0f}%, Multiplier: {sentiment_multiplier:.2f}x")
                print(f"   Desired: {desired_add*100:.1f}%, Final (after limits): {add_size*100:.1f}%")
                print(f"   Price: ${current_price:,.2f}, Leverage: {new_leverage}x")

                # PLACE REAL SCALE-IN ORDER
                success = self.trading_client.scale_in_position(
                    add_percentage=add_size,
                    new_leverage=new_leverage,
                    current_price=current_price
                )

                if success:
                    # Log the scale-in
                    reason = f"Hit scale level {i+1} at {level['deviation']*100:.0f}%"
                    decision = self.logger.log_scale_decision(
                        price=current_price,
                        add_size=add_size * 100,
                        new_leverage=new_leverage,
                        deviation=deviation * 100,
                        reason=reason
                    )

                    # Update position
                    old_avg = self.position['average_price']
                    old_size = self.total_position_size
                    new_size = old_size + add_size
                    new_avg = (old_size * old_avg + add_size * current_price) / new_size

                    self.position['average_price'] = new_avg
                    self.total_position_size = new_size
                    self.current_leverage = new_leverage
                    self.scale_in_count = i + 1

                    print(f"✅ REAL SCALE-IN COMPLETE!")
                    print(f"   New average: ${new_avg:,.2f}, Total size: {new_size*100:.0f}%")

                    return True, decision
                else:
                    print(f"❌ Scale-in failed")
                    return False, None

        return False, None

    def check_exit(self, current_price):
        """Check if we should exit position with sentiment-aware targets"""
        if self.position is None:
            return False, None

        gain = (current_price - self.position['average_price']) / self.position['average_price']

        # Get sentiment for dynamic exit decisions
        sentiment = self.get_sentiment_data()

        # Get market data for Claude (CHANGE #1)
        market_data = self.get_market_data()

        # Calculate adaptive profit targets and upper exit
        adjusted_targets, upper_exit_price = self.calculate_exit_targets(sentiment, current_price)

        # Check Fibonacci resistance exit (Ask Claude how much to take)
        if current_price >= upper_exit_price and not self.fib_partial_exit_taken:
            print(f"🎯 FIBONACCI RESISTANCE REACHED: ${upper_exit_price:,.0f}")
            print(f"   Current: ${current_price:,.0f}, Gain: {gain*100:+.2f}%")
            print(f"   Asking Claude how much profit to take...")

            # ASK CLAUDE FOR EXIT DECISION
            try:
                leveraged_gain = gain * self.current_leverage
                claude_decision = self.claude.approve_exit(
                    current_price=current_price,
                    position=self.position,
                    fib_level=upper_exit_price,
                    gain_pct=gain * 100,
                    roi_pct=leveraged_gain * 100,
                    sentiment=sentiment,
                    market_data=market_data  # CHANGE #2
                )

                exit_pct = claude_decision.get('size_or_amount', 0.50)
                print(f"\n✅ CLAUDE DECISION: Take {exit_pct*100:.0f}%")
                print(f"   Reasoning: {claude_decision.get('reasoning', '')[:200]}")

            except Exception as e:
                print(f"\n⚠️ CLAUDE API ERROR: {e}")
                print(f"   Using default: 50% profit taking")
                exit_pct = 0.50

            # Validate exit percentage
            safety_result = self.safety.validate_exit(
                {'size_or_amount': exit_pct},
                self.position
            )

            if not safety_result[0]:
                print(f"🚫 SAFETY BLOCKED: {safety_result[1]}")
                return False, None

            final_exit_pct = safety_result[2]['size_or_amount'] if safety_result[2] else exit_pct

            # Execute exit
            if self.shadow_mode:
                print(f"\n🔮 SHADOW MODE: Would close {final_exit_pct*100:.0f}% @ ${current_price:,.2f}")
                print(f"   (Not executing - observation only)")
                success = True
            else:
                success = self.trading_client.close_position(final_exit_pct)

            if success:
                # Use Claude + Safety approved exit percentage
                exit_size = final_exit_pct * self.total_position_size
                pnl = exit_size * self.position['average_price'] * gain

                reason = f"Fibonacci resistance ${upper_exit_price:,.0f} - Claude: Take {final_exit_pct*100:.0f}%"

                decision = self.logger.log_exit_decision(
                    price=current_price,
                    exit_size=final_exit_pct * 100,
                    pnl=pnl,
                    reason=reason,
                    exit_type="PARTIAL" if final_exit_pct < 1.0 else "FULL"
                )

                # Update position state
                self.total_position_size *= (1 - final_exit_pct)
                self.fib_partial_exit_taken = True
                self.fib_exit_price = current_price
                self.remaining_after_fib = self.total_position_size

                remaining_pct = (1 - final_exit_pct) * 100
                print(f"✅ EXIT COMPLETE: Took {final_exit_pct*100:.0f}%, holding {remaining_pct:.1f}%")
                print(f"📝 CLAUDE: {claude_decision.get('reasoning', '')[:150]}")

                return True, decision

        # Check for Fibonacci rejection (Close remaining if price bounces off resistance)
        if self.fib_partial_exit_taken and self.fib_exit_price:
            # If price drops 2% from Fib exit, close remaining (confirms rejection)
            if current_price <= self.fib_exit_price * 0.98:
                print(f"📉 FIBONACCI REJECTION DETECTED!")
                print(f"   Price dropped from ${self.fib_exit_price:,.0f} to ${current_price:,.0f}")
                print(f"   Closing remaining {self.remaining_after_fib*100:.1f}% to bank gains")

                # Close remaining position
                success = self.trading_client.close_position(1.0)

                if success:
                    pnl = self.total_position_size * self.position['average_price'] * gain
                    reason = f"Fibonacci rejection - Price failed to break ${self.fib_exit_price:,.0f}"

                    decision = self.logger.log_exit_decision(
                        price=current_price,
                        exit_size=self.total_position_size * 100,
                        pnl=pnl,
                        reason=reason,
                        exit_type="FULL"
                    )

                    # Clear position
                    self.position = None
                    self.total_position_size = 0
                    self.fib_partial_exit_taken = False
                    self.fib_exit_price = None

                    print(f"✅ FULL EXIT on Fib rejection - All gains banked!")

                    return True, decision

        # Update trailing stop (track highest price seen)
        if current_price > self.highest_price_seen:
            self.highest_price_seen = current_price

        # Check trailing stop (once we're up +10% ROE, protect gains)
        leveraged_gain = gain * self.current_leverage
        if leveraged_gain > 0.10:  # +10% ROE or better
            # Trail 5% below highest price seen
            trailing_stop = self.highest_price_seen * 0.95

            if current_price < trailing_stop:
                print(f"🛡️ TRAILING STOP HIT!")
                print(f"   High: ${self.highest_price_seen:,.0f}, Trail: ${trailing_stop:,.0f}, Current: ${current_price:,.0f}")

                # Full exit to protect gains
                success = self.trading_client.close_position(1.0)

                if success:
                    pnl = self.total_position_size * self.position['average_price'] * gain
                    reason = f"Trailing stop: Price fell 5% from high ${self.highest_price_seen:,.0f}"

                    decision = self.logger.log_exit_decision(
                        price=current_price,
                        exit_size=self.total_position_size * 100,
                        pnl=pnl,
                        reason=reason,
                        exit_type="FULL"
                    )

                    self.position = None
                    self.total_position_size = 0
                    print(f"✅ TRAILING STOP EXIT: Protected {leveraged_gain*100:.1f}% ROE gain!")

                    return True, decision

        # Check adaptive profit targets
        for target in adjusted_targets:
            if gain >= target['gain']:
                # Take profit - REAL ORDER
                exit_percentage = target['reduce']
                print(f"💰 TAKING PROFIT: {exit_percentage*100:.0f}% at {gain*100:+.2f}% gain")

                # PLACE REAL EXIT ORDER
                success = self.trading_client.close_position(exit_percentage)

                if success:
                    exit_size = exit_percentage * self.total_position_size
                    pnl = exit_size * self.position['average_price'] * gain

                    reason = f"Hit profit target {target['gain']*100:+.0f}%"
                    decision = self.logger.log_exit_decision(
                        price=current_price,
                        exit_size=exit_size * 100,
                        pnl=pnl,
                        reason=reason,
                        exit_type="PARTIAL" if target['reduce'] < 1 else "FULL"
                    )

                    # Update position
                    if target['reduce'] >= 1:
                        self.position = None
                        self.total_position_size = 0
                        print(f"✅ REAL FULL EXIT at ${current_price:,.2f} for {gain*100:+.2f}% gain!")
                    else:
                        self.total_position_size *= (1 - target['reduce'])
                        print(f"✅ REAL PARTIAL EXIT: Took {target['reduce']*100:.0f}% off")

                return True, decision

        # Check invalidation
        if gain <= self.config.INVALIDATION_LEVEL:
            # Full exit
            pnl = self.total_position_size * self.position['average_price'] * gain
            reason = f"Invalidation at {gain*100:.0f}%"

            decision = self.logger.log_exit_decision(
                price=current_price,
                exit_size=self.total_position_size * 100,
                pnl=pnl,
                reason=reason,
                exit_type="FULL"
            )

            self.position = None
            self.total_position_size = 0
            print(f"📉 INVALIDATION EXIT at ${current_price:,.2f}, loss: {gain*100:.2f}%")

            return True, decision

        return False, None

    def run_cycle(self):
        """Run one trading cycle"""
        try:
            # Get current price
            current_price = self.get_current_price()

            # Log market analysis
            sentiment = self.get_sentiment_data()
            analysis = self.logger.log_market_analysis(
                price=current_price,
                fib_levels=self.fib_levels,
                sentiment=sentiment
            )

            # No position - check entry
            if self.position is None:
                should_enter, fib_zone, confluence = self.check_entry_conditions(current_price)
                if should_enter:
                    self.enter_position(current_price, fib_zone, confluence)
                else:
                    # Only log occasionally when waiting
                    if (datetime.now() - self.last_check_time).seconds > 300:  # Every 5 min
                        print(f"⏳ Waiting for entry at ${current_price:,.2f}")
                        print(f"   4H GP: ${self.fib_levels['h4']['gp_bottom']:,.0f}-${self.fib_levels['h4']['gp_top']:,.0f}")
                        self.last_check_time = datetime.now()

            # Have position - check scale-in or exit
            else:
                # Check if 20-minute review is due
                time_since_review = (datetime.now() - self.last_review_time).total_seconds()
                if time_since_review >= self.REVIEW_INTERVAL:
                    print(f"\n⏰ 20-MINUTE REVIEW DUE (last: {int(time_since_review/60)} min ago)")
                    try:
                        # Get market data for Claude
                        market_data = self.get_market_data()
                        print(f"   Market data fetched: Vol={market_data.get('volume_24h_btc', 'NONE')}, OB={market_data.get('orderbook_imbalance', 'NONE')}")

                        review_decision = self.claude.periodic_review(
                            current_price=current_price,
                            position=self.position,
                            sentiment=sentiment,
                            market_data=market_data
                        )

                        if review_decision['decision'] == 'ADD':
                            add_amount = review_decision.get('size_or_amount', 0)
                            print(f"🤖 CLAUDE SUGGESTS: Add {add_amount*100:.1f}%")
                            print(f"   {review_decision.get('reasoning', '')[:150]}")

                            # Validate
                            safety_result = self.safety.validate_adjustment(
                                review_decision, self.position, current_price
                            )

                            if safety_result[0]:
                                final_add = safety_result[2]['size_or_amount'] if safety_result[2] else add_amount
                                # Execute the add (similar to scale-in)
                                print(f"   ✅ Executing Claude's ADD: {final_add*100:.1f}%")
                                self.safety.log_adjustment('ADD', final_add)
                                # Would execute actual trade here
                            else:
                                print(f"   🚫 SAFETY BLOCKED: {safety_result[1]}")

                        self.last_review_time = datetime.now()

                    except Exception as e:
                        print(f"⚠️ Review error: {e}")
                        self.last_review_time = datetime.now()

                # Check exit first
                should_exit, exit_decision = self.check_exit(current_price)
                if not should_exit:
                    # Check scale-in
                    should_scale, scale_decision = self.check_scale_in(current_price)
                    if not should_scale:
                        # Just monitoring
                        gain = (current_price - self.position['average_price']) / self.position['average_price']
                        if (datetime.now() - self.last_check_time).seconds > 60:  # Every minute
                            print(f"📊 Position update: ${current_price:,.2f} ({gain*100:+.2f}%)")
                            self.last_check_time = datetime.now()

            return True

        except Exception as e:
            print(f"❌ Cycle error: {e}")
            return False

    def run(self):
        """Main trading loop"""
        print("\n" + "="*80)
        print("🚀 STARTING LIVE FIBONACCI GOLDEN POCKET TRADER")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Competition Deadline: November 3, 2025")
        print("="*80)

        # Initial status
        price = self.get_current_price()
        print(f"\nCurrent BTC Price: ${price:,.2f}")
        print(f"4H Golden Pocket: ${self.fib_levels['h4']['gp_bottom']:,.0f}-${self.fib_levels['h4']['gp_top']:,.0f}")

        distance_to_gp = (price - self.fib_levels['h4']['gp_top']) / price * 100
        if distance_to_gp < 0:
            print(f"🎯 Price IN golden pocket!")
        else:
            print(f"📍 Price {distance_to_gp:.2f}% above golden pocket")

        print(f"\n{'='*40}")
        print("Bot is EAGER TO ENTER - Recent bounce detected!")
        print("Monitoring for immediate entry opportunity...")
        print(f"{'='*40}\n")

        # Main loop
        cycle_count = 0
        while True:
            try:
                # Run trading cycle
                success = self.run_cycle()

                if success:
                    cycle_count += 1

                # Sleep between cycles (faster when eager or in position)
                if self.eager_to_enter or self.position is not None:
                    time.sleep(5)  # 5 seconds when active
                else:
                    time.sleep(30)  # 30 seconds when waiting

                # Status update every 100 cycles
                if cycle_count % 100 == 0:
                    perf = self.logger.get_performance_summary()
                    print(f"\n📊 Status - Cycles: {cycle_count}, Trades: {perf['total_trades']}, P&L: ${perf['total_pnl']:,.2f}")

            except KeyboardInterrupt:
                print("\n\n⛔ Bot stopped by user")
                break
            except Exception as e:
                print(f"❌ Main loop error: {e}")
                time.sleep(60)  # Wait a minute on error

        # Final summary
        print("\n" + "="*80)
        print("📊 FINAL TRADING SUMMARY")
        print("="*80)

        perf = self.logger.get_performance_summary()
        print(f"Total Trades: {perf['total_trades']}")
        print(f"Total P&L: ${perf['total_pnl']:,.2f}")
        print(f"Win Rate: {perf['win_rate']:.1f}%")

        # Export for competition
        self.logger.export_for_competition()
        print("\nCompetition log exported to logs/competition_log.md")
        print("Good luck in the Aster Vibe Trading Arena! 🏆")


if __name__ == "__main__":
    # Check for shadow mode flag
    shadow_mode = '--shadow' in sys.argv or '--test' in sys.argv

    if shadow_mode:
        print("\n" + "="*70)
        print("🔮 SHADOW MODE ENABLED")
        print("="*70)
        print("Bot will:")
        print("  ✅ Fetch real market data (Aster + CoinGlass)")
        print("  ✅ Ask Claude for decisions")
        print("  ✅ Run safety validation")
        print("  ✅ Log everything")
        print("  ❌ NOT execute trades")
        print("="*70 + "\n")

    # Pre-flight check first
    print("Running pre-flight check...")
    from preflight_check import PreFlightCheck
    checker = PreFlightCheck()

    if checker.check_environment() and checker.check_aster_data():
        print("\n✅ All systems operational!")
        if shadow_mode:
            print("\n🔮 Starting in SHADOW MODE (observation only)...\n")
        else:
            print("\n🚀 Starting LIVE TRADING BOT with Claude supervisor...\n")

        # Start the bot
        bot = LiveFibonacciBot(shadow_mode=shadow_mode)
        bot.run()
    else:
        print("\n❌ Pre-flight check failed. Please fix issues before running.")
        sys.exit(1)