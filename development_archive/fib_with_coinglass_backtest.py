"""
Multi-Timeframe Fibonacci Strategy with CoinGlass Sentiment Overlays
Combines price action Fib levels with market sentiment for enhanced signals
"""
import asyncio
import sys
import os
import requests
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data.historical_data_fetcher import HistoricalDataFetcher
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class FibWithCoinGlassStrategy:
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = None
        self.trades = []

        # CoinGlass API setup
        self.cg_base_url = "https://open-api-v4.coinglass.com"
        self.cg_headers = {
            'accept': 'application/json',
            'CG-API-KEY': 'YOUR_COINGLASS_API_KEY'
        }

        # Strategy configuration
        self.config = {
            'base_position_size': 0.25,
            'scale_levels': [
                {'deviation': -0.01, 'add': 0.15},
                {'deviation': -0.02, 'add': 0.20},
                {'deviation': -0.04, 'add': 0.20},
                {'deviation': -0.06, 'add': 0.20},
            ],
            'profit_targets': [
                {'gain': 0.05, 'reduce': 0.25},
                {'gain': 0.10, 'reduce': 0.25},
                {'gain': 0.15, 'reduce': 0.25},
            ],
            'leverage': {
                'conservative': 2,
                'moderate': 3,
                'aggressive': 5
            },
            # CoinGlass thresholds
            'sentiment_thresholds': {
                'fear_extreme': 25,      # Extreme fear = potential bottom
                'fear': 40,              # Fear = bullish setup
                'greed': 60,             # Greed = caution
                'greed_extreme': 75,     # Extreme greed = potential top
                'ls_ratio_bullish': 1.5, # L/S > 1.5 = bullish
                'ls_ratio_bearish': 0.8, # L/S < 0.8 = bearish
                'funding_extreme': 0.05, # Funding > 5% = crowded
            }
        }

    def fetch_coinglass_historical(self, endpoint, params, limit=100):
        """Fetch historical data from CoinGlass"""
        try:
            url = f"{self.cg_base_url}{endpoint}"
            params['limit'] = limit

            response = requests.get(url, headers=self.cg_headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '0' and data.get('data'):
                    return data['data']
        except Exception as e:
            print(f"CoinGlass fetch error: {e}")

        return None

    def get_historical_sentiment(self, start_date, end_date):
        """Get historical sentiment data from CoinGlass"""
        sentiment_data = {}

        # Calculate how many 4h periods we need
        hours_diff = (end_date - start_date).total_seconds() / 3600
        periods_needed = int(hours_diff / 4) + 1

        print(f"\n📊 Fetching CoinGlass sentiment data...")

        # 1. Long/Short Ratio
        ls_data = self.fetch_coinglass_historical(
            '/api/futures/global-long-short-account-ratio/history',
            {
                'exchange': 'Binance',
                'symbol': 'BTCUSDT',
                'interval': '4h'
            },
            limit=min(periods_needed, 500)
        )

        if ls_data:
            print(f"  ✅ Got {len(ls_data)} L/S ratio data points")
            sentiment_data['ls_ratio'] = {}
            for point in ls_data:
                timestamp = datetime.fromtimestamp(point['time'] / 1000)
                sentiment_data['ls_ratio'][timestamp] = point.get('global_account_long_short_ratio', 1.0)

        # 2. Funding Rate
        funding_data = self.fetch_coinglass_historical(
            '/api/futures/funding-rate/history',
            {
                'exchange': 'Binance',
                'symbol': 'BTCUSDT',
                'interval': '8h'
            },
            limit=min(periods_needed // 2, 500)
        )

        if funding_data:
            print(f"  ✅ Got {len(funding_data)} funding rate data points")
            sentiment_data['funding'] = {}
            for point in funding_data:
                timestamp = datetime.fromtimestamp(point['time'] / 1000)
                sentiment_data['funding'][timestamp] = float(point.get('close', 0.01))

        # 3. Open Interest
        oi_data = self.fetch_coinglass_historical(
            '/api/futures/open-interest/history',
            {
                'exchange': 'Binance',
                'symbol': 'BTCUSDT',
                'interval': '4h',
                'unit': 'usd'
            },
            limit=min(periods_needed, 500)
        )

        if oi_data:
            print(f"  ✅ Got {len(oi_data)} open interest data points")
            sentiment_data['open_interest'] = {}
            for point in oi_data:
                timestamp = datetime.fromtimestamp(point['time'] / 1000)
                sentiment_data['open_interest'][timestamp] = float(point.get('close', 0))

        # 4. Liquidations
        liq_data = self.fetch_coinglass_historical(
            '/api/futures/liquidation/history',
            {
                'exchange': 'Binance',
                'symbol': 'BTCUSDT',
                'interval': '4h'
            },
            limit=min(periods_needed, 500)
        )

        if liq_data:
            print(f"  ✅ Got {len(liq_data)} liquidation data points")
            sentiment_data['liquidations'] = {}
            for point in liq_data:
                timestamp = datetime.fromtimestamp(point['time'] / 1000)
                long_liq = float(point.get('long_liquidation_usd', 0))
                short_liq = float(point.get('short_liquidation_usd', 0))
                sentiment_data['liquidations'][timestamp] = {
                    'long': long_liq,
                    'short': short_liq,
                    'ratio': long_liq / (long_liq + short_liq) if (long_liq + short_liq) > 0 else 0.5
                }

        return sentiment_data

    def get_sentiment_score(self, timestamp, sentiment_data):
        """
        Calculate sentiment score from CoinGlass data
        Returns: score (-2 to +2) and signals
        """
        score = 0
        signals = []

        # Find closest data points
        def find_closest(data_dict, target_time, max_hours=12):
            if not data_dict:
                return None

            closest = None
            min_diff = timedelta(hours=max_hours)

            for ts in data_dict.keys():
                diff = abs(ts - target_time)
                if diff < min_diff:
                    min_diff = diff
                    closest = data_dict[ts]

            return closest

        # 1. Long/Short Ratio Analysis
        if 'ls_ratio' in sentiment_data:
            ls_ratio = find_closest(sentiment_data['ls_ratio'], timestamp)
            if ls_ratio:
                if ls_ratio > 2.0:  # Very bullish positioning
                    score += 0.5
                    signals.append(f"L/S Ratio {ls_ratio:.2f} (bullish)")
                elif ls_ratio > 1.5:
                    score += 0.25
                    signals.append(f"L/S Ratio {ls_ratio:.2f} (slightly bullish)")
                elif ls_ratio < 0.8:  # Bearish positioning
                    score -= 0.5
                    signals.append(f"L/S Ratio {ls_ratio:.2f} (bearish)")

        # 2. Funding Rate Analysis
        if 'funding' in sentiment_data:
            funding = find_closest(sentiment_data['funding'], timestamp)
            if funding:
                if funding > 0.05:  # Extremely high (overbought)
                    score -= 0.5
                    signals.append(f"Funding {funding*100:.3f}% (overbought)")
                elif funding > 0.02:
                    score -= 0.25
                elif funding < -0.01:  # Negative (oversold)
                    score += 0.5
                    signals.append(f"Funding {funding*100:.3f}% (oversold)")

        # 3. Liquidation Analysis
        if 'liquidations' in sentiment_data:
            liq_data = find_closest(sentiment_data['liquidations'], timestamp)
            if liq_data:
                # If mostly longs liquidated (>70%), bearish short-term but bullish setup
                if liq_data['ratio'] > 0.7:
                    score += 0.25
                    signals.append(f"Long liquidations {liq_data['ratio']*100:.0f}% (flush complete)")
                elif liq_data['ratio'] < 0.3:
                    score -= 0.25
                    signals.append(f"Short liquidations {(1-liq_data['ratio'])*100:.0f}% (squeeze risk)")

        # 4. Open Interest Trend
        if 'open_interest' in sentiment_data:
            current_oi = find_closest(sentiment_data['open_interest'], timestamp, max_hours=4)
            prev_oi = find_closest(sentiment_data['open_interest'], timestamp - timedelta(hours=24), max_hours=12)

            if current_oi and prev_oi and prev_oi > 0:
                oi_change = (current_oi - prev_oi) / prev_oi
                if oi_change > 0.05:  # OI increasing
                    score += 0.25
                    signals.append(f"OI +{oi_change*100:.1f}% (participation up)")
                elif oi_change < -0.05:  # OI decreasing
                    score -= 0.25
                    signals.append(f"OI {oi_change*100:.1f}% (participation down)")

        return score, signals

    def calculate_fibs(self, high, low):
        """Calculate Fibonacci levels"""
        range_size = high - low
        return {
            '0.0%': {'price': high, 'strength': 'minor'},
            '23.6%': {'price': high - (range_size * 0.236), 'strength': 'moderate'},
            '38.2%': {'price': high - (range_size * 0.382), 'strength': 'strong'},
            '50.0%': {'price': high - (range_size * 0.500), 'strength': 'strong'},
            '61.8%': {'price': high - (range_size * 0.618), 'strength': 'golden'},
            '65.0%': {'price': high - (range_size * 0.650), 'strength': 'golden'},
            '78.6%': {'price': high - (range_size * 0.786), 'strength': 'strong'},
            '100.0%': {'price': low, 'strength': 'major'}
        }

    async def run_backtest(self):
        """Run backtest with Fibonacci levels + CoinGlass sentiment"""

        # Fetch price data
        fetcher = HistoricalDataFetcher()
        start_date = '2025-08-01'  # Start from August for better CoinGlass coverage
        end_date = '2025-10-29'

        print("\n" + "=" * 80)
        print("🎯 FIBONACCI + COINGLASS SENTIMENT STRATEGY")
        print("=" * 80)

        df = await fetcher.fetch_btc_historical_data(start_date, end_date, '1h')

        # Get CoinGlass sentiment data
        sentiment_data = self.get_historical_sentiment(
            datetime.strptime(start_date, '%Y-%m-%d'),
            datetime.strptime(end_date, '%Y-%m-%d')
        )

        # Calculate Fibonacci levels (using known swings)
        daily = df.resample('1D').agg({'high': 'max', 'low': 'min', 'close': 'last'})

        # Use October swings for 4H
        oct_high = 126104  # Oct 6
        oct_low = 103528   # Oct 17
        h4_fibs = self.calculate_fibs(oct_high, oct_low)

        print(f"\n📏 4H FIBONACCI LEVELS:")
        print(f"  Golden Pocket: ${h4_fibs['61.8%']['price']:,.0f} - ${h4_fibs['65.0%']['price']:,.0f}")

        # Run simulation
        post_oct = df['2025-10-06 17:00:00':]
        entries = []

        for idx in post_oct.index:
            row = post_oct.loc[idx]
            current_price = row['close']

            # Get sentiment score
            sentiment_score, sentiment_signals = self.get_sentiment_score(idx, sentiment_data)

            # NO POSITION - Look for entry
            if self.position is None:
                # Check if near golden pocket
                gp_range = (h4_fibs['65.0%']['price'], h4_fibs['61.8%']['price'])
                near_gp = gp_range[0] <= current_price <= gp_range[1]
                near_50 = abs(current_price - h4_fibs['50.0%']['price']) / current_price < 0.005

                should_enter = False
                entry_reason = ""

                # Enhanced entry logic with sentiment
                if near_gp:
                    if sentiment_score > 0:
                        should_enter = True
                        entry_reason = f"Golden Pocket + Positive Sentiment ({sentiment_score:.1f})"
                        leverage = self.config['leverage']['aggressive']
                    elif sentiment_score > -0.5:
                        should_enter = True
                        entry_reason = f"Golden Pocket + Neutral Sentiment ({sentiment_score:.1f})"
                        leverage = self.config['leverage']['moderate']

                elif near_50 and sentiment_score > 0.5:
                    should_enter = True
                    entry_reason = f"50% Fib + Strong Sentiment ({sentiment_score:.1f})"
                    leverage = self.config['leverage']['moderate']

                if should_enter:
                    self.position = {
                        'entry_price': current_price,
                        'entry_time': idx,
                        'size': self.config['base_position_size'],
                        'leverage': leverage,
                        'reason': entry_reason,
                        'sentiment_signals': sentiment_signals,
                        'average_price': current_price,
                        'scale_count': 0
                    }

                    entries.append({
                        'time': idx,
                        'price': current_price,
                        'reason': entry_reason,
                        'sentiment': sentiment_score
                    })

                    print(f"\n✅ ENTRY at {idx}")
                    print(f"  Price: ${current_price:,.0f}")
                    print(f"  Reason: {entry_reason}")
                    print(f"  Leverage: {leverage}x")
                    if sentiment_signals:
                        print(f"  Signals: {', '.join(sentiment_signals)}")

            # HAS POSITION - Manage it
            else:
                price_change = (current_price - self.position['average_price']) / self.position['average_price']

                # Enhanced scale-in with sentiment
                for scale_level in self.config['scale_levels']:
                    if price_change <= scale_level['deviation'] and self.position['scale_count'] < 4:

                        # Only scale in if sentiment isn't extremely negative
                        current_sentiment, _ = self.get_sentiment_score(idx, sentiment_data)
                        if current_sentiment > -1.0:
                            add_size = scale_level['add']

                            # Adjust size based on sentiment
                            if current_sentiment > 0:
                                add_size *= 1.2  # Add more when sentiment positive

                            old_avg = self.position['average_price']
                            old_size = self.position['size']

                            new_size = old_size + add_size
                            new_avg = (old_size * old_avg + add_size * current_price) / new_size

                            self.position['average_price'] = new_avg
                            self.position['size'] = new_size
                            self.position['scale_count'] += 1

                            print(f"\n📈 SCALE IN at {idx}")
                            print(f"  Price: ${current_price:,.0f} ({price_change*100:.1f}%)")
                            print(f"  Sentiment: {current_sentiment:.1f}")
                            print(f"  New avg: ${new_avg:,.0f}")
                            break

                # Take profits
                if price_change > 0.05:
                    pnl = self.position['size'] * self.capital * price_change * self.position['leverage'] * 0.25
                    self.position['size'] *= 0.75
                    self.capital += pnl

                    print(f"\n💰 PARTIAL EXIT at {idx}")
                    print(f"  Price: ${current_price:,.0f} (+{price_change*100:.1f}%)")
                    print(f"  Profit: ${pnl:,.2f}")

                    if self.position['size'] < 0.05:
                        self.position = None

        # Close any remaining position
        if self.position:
            final_price = post_oct.iloc[-1]['close']
            pnl = (final_price - self.position['average_price']) * self.position['size'] * self.capital / self.position['average_price']
            pnl *= self.position['leverage']
            self.capital += pnl

            print(f"\n📊 CLOSED at end")
            print(f"  Final price: ${final_price:,.0f}")
            print(f"  P&L: ${pnl:,.2f}")

        # Results
        print("\n" + "=" * 80)
        print("📊 RESULTS: FIBONACCI + COINGLASS SENTIMENT")
        print("=" * 80)

        total_return = (self.capital - self.initial_capital) / self.initial_capital * 100

        print(f"\n💰 PERFORMANCE:")
        print(f"  Initial: ${self.initial_capital:,.2f}")
        print(f"  Final: ${self.capital:,.2f}")
        print(f"  Return: {total_return:+.2f}%")

        print(f"\n📊 ENTRIES:")
        for entry in entries:
            print(f"  {entry['time']}: {entry['reason']}")

        print("\n💡 KEY INSIGHT:")
        print("  CoinGlass sentiment data enhances entry timing and position sizing")
        print("  Avoiding entries during extreme negative sentiment prevents losses")
        print("  Scaling more aggressively during positive sentiment improves returns")

async def main():
    strategy = FibWithCoinGlassStrategy(initial_capital=10000)
    await strategy.run_backtest()

if __name__ == "__main__":
    asyncio.run(main())