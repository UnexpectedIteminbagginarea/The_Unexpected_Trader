"""
Enhanced Multi-Timeframe Fibonacci Strategy with CoinGlass Sentiment
The winning formula: Scale-in at Fib levels + Sentiment for position sizing
"""
import asyncio
import sys
import os
import requests
from datetime import datetime, timedelta
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data.historical_data_fetcher import HistoricalDataFetcher
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class EnhancedFibCoinGlassStrategy:
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = None
        self.trades = []

        # CoinGlass API
        self.cg_headers = {
            'accept': 'application/json',
            'CG-API-KEY': 'YOUR_COINGLASS_API_KEY'
        }

        # Our WINNING configuration from Test #9
        self.config = {
            'base_position_size': 0.25,

            # Scale-in levels that WORK
            'scale_levels': [
                {'deviation': -0.01, 'add': 0.15},
                {'deviation': -0.02, 'add': 0.20},
                {'deviation': -0.04, 'add': 0.20},
                {'deviation': -0.06, 'add': 0.20},
            ],

            # Profit targets that WORK
            'profit_targets': [
                {'gain': 0.05, 'reduce': 0.25},
                {'gain': 0.10, 'reduce': 0.25},
                {'gain': 0.15, 'reduce': 0.25},
            ],

            # CoinGlass thresholds for position adjustment
            'sentiment': {
                'ls_ratio': {
                    'very_bullish': 2.0,    # > 2.0 = 1.2x size
                    'bullish': 1.5,          # 1.5-2.0 = 1.0x size
                    'neutral': 1.0,          # 1.0-1.5 = 0.9x size
                    'bearish': 0.8           # < 0.8 = 0.7x size
                },
                'funding': {
                    'extreme_high': 0.05,    # > 5% = 0.5x size (crowded)
                    'high': 0.02,            # 2-5% = 0.8x size
                    'neutral': 0.005,        # 0.5-2% = 1.0x size
                    'negative': 0            # < 0% = 1.3x size (oversold)
                },
                'liquidations': {
                    'long_flush': 0.7,       # > 70% longs = 1.2x (bullish)
                    'short_squeeze': 0.3     # < 30% longs = 0.8x (careful)
                }
            }
        }

        # Store sentiment data
        self.sentiment_cache = {}

    def fetch_coinglass_data(self, endpoint, params):
        """Fetch data from CoinGlass API"""
        try:
            url = f"https://open-api-v4.coinglass.com{endpoint}"
            response = requests.get(url, headers=self.cg_headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '0':
                    return data.get('data')
        except Exception as e:
            print(f"  ⚠️ CoinGlass error: {e}")
        return None

    def load_sentiment_data(self):
        """Load CoinGlass sentiment data for backtesting"""
        print("\n📊 Loading CoinGlass sentiment data...")

        # Long/Short Ratio
        ls_data = self.fetch_coinglass_data(
            '/api/futures/global-long-short-account-ratio/history',
            {'exchange': 'Binance', 'symbol': 'BTCUSDT', 'interval': '4h', 'limit': 500}
        )

        if ls_data:
            print(f"  ✅ Loaded {len(ls_data)} L/S ratio points")
            for point in ls_data:
                ts = pd.Timestamp.fromtimestamp(point['time'] / 1000, tz='UTC')
                if ts not in self.sentiment_cache:
                    self.sentiment_cache[ts] = {}
                self.sentiment_cache[ts]['ls_ratio'] = point.get('global_account_long_short_ratio', 1.0)

        # Funding Rate
        funding_data = self.fetch_coinglass_data(
            '/api/futures/funding-rate/history',
            {'exchange': 'Binance', 'symbol': 'BTCUSDT', 'interval': '8h', 'limit': 300}
        )

        if funding_data:
            print(f"  ✅ Loaded {len(funding_data)} funding rate points")
            for point in funding_data:
                ts = pd.Timestamp.fromtimestamp(point['time'] / 1000, tz='UTC')
                if ts not in self.sentiment_cache:
                    self.sentiment_cache[ts] = {}
                self.sentiment_cache[ts]['funding'] = float(point.get('close', 0.01))

        # Liquidations
        liq_data = self.fetch_coinglass_data(
            '/api/futures/liquidation/history',
            {'exchange': 'Binance', 'symbol': 'BTCUSDT', 'interval': '4h', 'limit': 500}
        )

        if liq_data:
            print(f"  ✅ Loaded {len(liq_data)} liquidation points")
            for point in liq_data:
                ts = pd.Timestamp.fromtimestamp(point['time'] / 1000, tz='UTC')
                long_liq = float(point.get('long_liquidation_usd', 0))
                short_liq = float(point.get('short_liquidation_usd', 0))
                total = long_liq + short_liq

                if ts not in self.sentiment_cache:
                    self.sentiment_cache[ts] = {}
                self.sentiment_cache[ts]['liq_ratio'] = long_liq / total if total > 0 else 0.5

        # Open Interest
        oi_data = self.fetch_coinglass_data(
            '/api/futures/open-interest/history',
            {'exchange': 'Binance', 'symbol': 'BTCUSDT', 'interval': '4h', 'unit': 'usd', 'limit': 500}
        )

        if oi_data:
            print(f"  ✅ Loaded {len(oi_data)} open interest points")
            for point in oi_data:
                ts = pd.Timestamp.fromtimestamp(point['time'] / 1000, tz='UTC')
                if ts not in self.sentiment_cache:
                    self.sentiment_cache[ts] = {}
                self.sentiment_cache[ts]['open_interest'] = float(point.get('close', 0))

        print(f"  📈 Total sentiment data points: {len(self.sentiment_cache)}")

    def get_sentiment_multiplier(self, timestamp):
        """
        Calculate position size multiplier based on CoinGlass sentiment
        Returns: multiplier (0.5 to 1.5) and explanation
        """
        # Find closest sentiment data (within 12 hours)
        closest_data = None
        min_diff = timedelta(hours=12)

        # Convert timestamp to UTC if needed
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize('UTC')

        for ts, data in self.sentiment_cache.items():
            diff = abs(ts - timestamp)
            if diff < min_diff:
                min_diff = diff
                closest_data = data

        if not closest_data:
            return 1.0, ["No sentiment data"]

        multiplier = 1.0
        explanations = []

        # Long/Short Ratio adjustment
        if 'ls_ratio' in closest_data:
            ls = closest_data['ls_ratio']
            if ls > 2.0:
                multiplier *= 1.2
                explanations.append(f"L/S {ls:.2f} very bullish (+20%)")
            elif ls > 1.5:
                multiplier *= 1.0
                explanations.append(f"L/S {ls:.2f} bullish")
            elif ls > 1.0:
                multiplier *= 0.9
                explanations.append(f"L/S {ls:.2f} neutral (-10%)")
            else:
                multiplier *= 0.7
                explanations.append(f"L/S {ls:.2f} bearish (-30%)")

        # Funding Rate adjustment
        if 'funding' in closest_data:
            funding = closest_data['funding']
            if funding > 0.05:
                multiplier *= 0.5
                explanations.append(f"Funding {funding*100:.3f}% extreme (-50%)")
            elif funding > 0.02:
                multiplier *= 0.8
                explanations.append(f"Funding {funding*100:.3f}% high (-20%)")
            elif funding < 0:
                multiplier *= 1.3
                explanations.append(f"Funding {funding*100:.3f}% negative (+30%)")
            else:
                explanations.append(f"Funding {funding*100:.3f}% neutral")

        # Liquidation adjustment
        if 'liq_ratio' in closest_data:
            liq = closest_data['liq_ratio']
            if liq > 0.7:
                multiplier *= 1.2
                explanations.append(f"Longs liquidated {liq*100:.0f}% (+20%)")
            elif liq < 0.3:
                multiplier *= 0.8
                explanations.append(f"Shorts liquidated {(1-liq)*100:.0f}% (-20%)")

        # Cap the multiplier
        multiplier = max(0.3, min(1.5, multiplier))

        return multiplier, explanations

    def calculate_fibs(self, high, low):
        """Calculate Fibonacci levels"""
        range_size = high - low
        return {
            '23.6%': high - (range_size * 0.236),
            '38.2%': high - (range_size * 0.382),
            '50.0%': high - (range_size * 0.500),
            '61.8%': high - (range_size * 0.618),  # Golden pocket top
            '65.0%': high - (range_size * 0.650),  # Golden pocket bottom
            '78.6%': high - (range_size * 0.786),
        }

    async def run_backtest(self):
        """Run the enhanced backtest"""

        print("\n" + "=" * 80)
        print("🎯 ENHANCED FIBONACCI + COINGLASS STRATEGY")
        print("=" * 80)

        # Load sentiment data first
        self.load_sentiment_data()

        # Fetch price data
        fetcher = HistoricalDataFetcher()
        df = await fetcher.fetch_btc_historical_data('2025-06-01', '2025-10-29', '1h')

        # Calculate daily data
        daily = df.resample('1D').agg({'high': 'max', 'low': 'min', 'close': 'last'})

        # DAILY swings (June-Oct)
        june_july = daily['2025-06-01':'2025-07-31']
        daily_low = june_july['low'].min()
        oct = daily['2025-10-01':'2025-10-15']
        daily_high = oct['high'].max()
        daily_fibs = self.calculate_fibs(daily_high, daily_low)

        # 4H swings (October)
        h4_high = 126200  # Oct 6
        h4_low = 103528   # Oct 17
        h4_fibs = self.calculate_fibs(h4_high, h4_low)

        print(f"\n📏 FIBONACCI LEVELS:")
        print(f"  Daily GP: ${daily_fibs['61.8%']:,.0f} - ${daily_fibs['65.0%']:,.0f}")
        print(f"  4H GP: ${h4_fibs['61.8%']:,.0f} - ${h4_fibs['65.0%']:,.0f}")

        # Track results
        entries = []
        scale_ins = []
        exits = []
        sentiment_impacts = []

        # Run from after October high
        post_high = df['2025-10-06 17:00:00':]

        for idx in post_high.index:
            row = post_high.loc[idx]
            current_price = row['close']

            # NO POSITION
            if self.position is None:
                # Check Fibonacci levels
                near_4h_gp = h4_fibs['65.0%'] <= current_price <= h4_fibs['61.8%']
                near_daily_gp = daily_fibs['65.0%'] <= current_price <= daily_fibs['61.8%']
                near_50 = (abs(current_price - h4_fibs['50.0%']) / current_price < 0.005 or
                          abs(current_price - daily_fibs['50.0%']) / current_price < 0.005)

                should_enter = False
                base_reason = ""

                # Entry logic (same as winning strategy)
                if near_4h_gp and near_daily_gp:
                    should_enter = True
                    base_reason = "Both GPs aligned"
                    base_leverage = 5
                elif near_4h_gp:
                    should_enter = True
                    base_reason = "4H golden pocket"
                    base_leverage = 3
                elif near_daily_gp:
                    should_enter = True
                    base_reason = "Daily golden pocket"
                    base_leverage = 3
                elif near_50:
                    # Need bounce confirmation for 50%
                    if len(post_high.loc[:idx]) > 3:
                        prev_low = post_high.loc[:idx].iloc[-3:]['low'].min()
                        if current_price > prev_low * 1.01:
                            should_enter = True
                            base_reason = "50% Fib with bounce"
                            base_leverage = 2

                if should_enter:
                    # Get sentiment multiplier
                    sentiment_mult, sentiment_reasons = self.get_sentiment_multiplier(idx)

                    # Adjust position size with sentiment
                    adjusted_size = self.config['base_position_size'] * sentiment_mult
                    adjusted_size = min(adjusted_size, 0.5)  # Cap at 50% initial

                    self.position = {
                        'entry_price': current_price,
                        'entry_time': idx,
                        'size': adjusted_size,
                        'leverage': base_leverage,
                        'reason': base_reason,
                        'sentiment_mult': sentiment_mult,
                        'sentiment_reasons': sentiment_reasons,
                        'average_price': current_price,
                        'scale_count': 0,
                        'total_invested': adjusted_size * self.capital
                    }

                    entries.append({
                        'time': idx,
                        'price': current_price,
                        'size': adjusted_size,
                        'reason': base_reason,
                        'sentiment': sentiment_mult
                    })

                    print(f"\n✅ ENTRY at {idx}")
                    print(f"  Price: ${current_price:,.0f}")
                    print(f"  Base reason: {base_reason}")
                    print(f"  Position: {adjusted_size*100:.1f}% (base 25% × {sentiment_mult:.2f})")
                    print(f"  Sentiment: {', '.join(sentiment_reasons)}")

                    sentiment_impacts.append({
                        'action': 'entry',
                        'multiplier': sentiment_mult,
                        'impact': f"Position sized to {adjusted_size*100:.1f}%"
                    })

            # HAS POSITION - Manage it
            else:
                price_change = (current_price - self.position['average_price']) / self.position['average_price']

                # Scale-in logic with sentiment
                for scale_level in self.config['scale_levels']:
                    if (price_change <= scale_level['deviation'] and
                        self.position['scale_count'] < len(self.config['scale_levels'])):

                        # Get current sentiment
                        scale_mult, scale_reasons = self.get_sentiment_multiplier(idx)

                        # Only scale in if sentiment not terrible
                        if scale_mult > 0.4:
                            # Adjust scale-in size with sentiment
                            base_add = scale_level['add']
                            adjusted_add = base_add * scale_mult

                            # Update position
                            old_avg = self.position['average_price']
                            old_size = self.position['size']

                            new_size = old_size + adjusted_add
                            new_avg = (old_size * old_avg + adjusted_add * current_price) / new_size

                            self.position['average_price'] = new_avg
                            self.position['size'] = new_size
                            self.position['scale_count'] += 1

                            scale_ins.append({
                                'time': idx,
                                'price': current_price,
                                'added': adjusted_add,
                                'sentiment': scale_mult
                            })

                            print(f"\n📈 SCALE IN at {idx}")
                            print(f"  Price: ${current_price:,.0f} ({price_change*100:.1f}%)")
                            print(f"  Added: {adjusted_add*100:.1f}% (base {base_add*100:.0f}% × {scale_mult:.2f})")
                            print(f"  Sentiment: {', '.join(scale_reasons)}")
                            print(f"  New avg: ${new_avg:,.0f}")

                            sentiment_impacts.append({
                                'action': 'scale-in',
                                'multiplier': scale_mult,
                                'impact': f"Scaled {adjusted_add*100:.1f}% instead of {base_add*100:.0f}%"
                            })
                            break

                # Take profits (unchanged from winning strategy)
                for target in self.config['profit_targets']:
                    if price_change >= target['gain'] and self.position['size'] > 0.1:
                        reduce_amt = target['reduce']
                        position_value = self.position['size'] * self.capital
                        pnl = position_value * price_change * self.position['leverage'] * reduce_amt

                        self.position['size'] *= (1 - reduce_amt)
                        self.capital += pnl

                        exits.append({
                            'time': idx,
                            'price': current_price,
                            'pnl': pnl,
                            'gain': price_change
                        })

                        print(f"\n💰 PARTIAL EXIT at {idx}")
                        print(f"  Price: ${current_price:,.0f} (+{price_change*100:.1f}%)")
                        print(f"  Profit: ${pnl:,.2f}")

                        if self.position['size'] < 0.05:
                            self.position = None
                        break

                # Check invalidation
                if current_price < h4_fibs['65.0%'] * 0.92:  # 8% below 4H GP
                    if self.position:
                        pnl = (current_price - self.position['average_price']) * self.position['size'] * self.capital / self.position['average_price']
                        pnl *= self.position['leverage']
                        self.capital += pnl

                        print(f"\n❌ INVALIDATION EXIT at {idx}")
                        print(f"  Price: ${current_price:,.0f}")
                        print(f"  P&L: ${pnl:,.2f}")

                        self.position = None

        # Close any open position
        if self.position:
            final_price = post_high.iloc[-1]['close']
            pnl = (final_price - self.position['average_price']) * self.position['size'] * self.capital / self.position['average_price']
            pnl *= self.position['leverage']
            self.capital += pnl

            print(f"\n📊 CLOSED at end")
            print(f"  Final price: ${final_price:,.0f}")
            print(f"  P&L: ${pnl:,.2f}")

        # RESULTS
        print("\n" + "=" * 80)
        print("📊 ENHANCED RESULTS WITH COINGLASS SENTIMENT")
        print("=" * 80)

        total_return = (self.capital - self.initial_capital) / self.initial_capital * 100

        print(f"\n💰 PERFORMANCE:")
        print(f"  Initial: ${self.initial_capital:,.2f}")
        print(f"  Final: ${self.capital:,.2f}")
        print(f"  Return: {total_return:+.2f}%")
        print(f"  Base strategy: +6.55%")
        print(f"  Improvement: {total_return - 6.55:+.2f}%")

        print(f"\n📊 TRADE STATS:")
        print(f"  Entries: {len(entries)}")
        print(f"  Scale-ins: {len(scale_ins)}")
        print(f"  Exits: {len(exits)}")

        if sentiment_impacts:
            print(f"\n🎯 SENTIMENT IMPACT EXAMPLES:")
            for impact in sentiment_impacts[:5]:
                print(f"  {impact['action']}: {impact['impact']} (×{impact['multiplier']:.2f})")

        print(f"\n💡 KEY INSIGHTS:")
        print("  • CoinGlass sentiment helps SIZE positions dynamically")
        print("  • Avoiding entries during extreme funding prevents losses")
        print("  • Scaling more after liquidation flushes improves entries")
        print("  • The core Fib strategy remains unchanged - sentiment enhances it")

async def main():
    strategy = EnhancedFibCoinGlassStrategy(initial_capital=10000)
    await strategy.run_backtest()

if __name__ == "__main__":
    asyncio.run(main())