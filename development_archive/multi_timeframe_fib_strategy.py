"""
Multi-Timeframe Fibonacci Strategy
Combines Daily (June-Oct) and 4H (Oct) swings for more opportunities
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data.historical_data_fetcher import HistoricalDataFetcher
import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class MultiTimeframeFibStrategy:
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = None
        self.trades = []

        # Strategy parameters
        self.config = {
            # Position sizing based on timeframe confluence
            'base_position_size': 0.25,  # 25% base
            'single_tf_multiplier': 1.0,  # 1x for single timeframe
            'multi_tf_multiplier': 2.0,   # 2x for confluence

            # Scale-in rules (same as winning strategy)
            'scale_levels': [
                {'deviation': -0.01, 'add': 0.15},  # -1%: Add 15%
                {'deviation': -0.02, 'add': 0.20},  # -2%: Add 20%
                {'deviation': -0.04, 'add': 0.20},  # -4%: Add 20%
                {'deviation': -0.06, 'add': 0.20},  # -6%: Add 20%
            ],

            # Invalidation levels
            'daily_invalidation': 0.10,  # 10% below daily GP
            '4h_invalidation': 0.08,      # 8% below 4H GP

            # Profit targets
            'profit_targets': [
                {'gain': 0.05, 'reduce': 0.25},  # +5%: Take 25% off
                {'gain': 0.10, 'reduce': 0.25},  # +10%: Take 25% off
                {'gain': 0.15, 'reduce': 0.25},  # +15%: Take 25% off
            ],

            # Leverage based on confluence
            'leverage': {
                'single_tf': 2,    # 2x for single timeframe GP
                'multi_tf': 5,     # 5x for confluence
                'strong_bounce': 3  # 3x for strong bounces from GP
            }
        }

    def calculate_fibs(self, high, low):
        """Calculate all Fibonacci levels from swing points"""
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

    def check_fib_zones(self, price, fib_levels, tolerance=0.002):
        """Check which Fib zones price is near (0.2% tolerance)"""
        zones = []
        for level_name, level_data in fib_levels.items():
            fib_price = level_data['price']
            distance = abs(price - fib_price) / price
            if distance <= tolerance:
                zones.append({
                    'level': level_name,
                    'price': fib_price,
                    'strength': level_data['strength'],
                    'distance': distance
                })
        return zones

    def get_confluence_score(self, price, daily_fibs, h4_fibs):
        """
        Calculate confluence score based on both timeframes
        Returns: score (0-2) and details
        """
        daily_zones = self.check_fib_zones(price, daily_fibs)
        h4_zones = self.check_fib_zones(price, h4_fibs)

        score = 0
        details = []

        # Check daily golden pocket
        daily_gp_range = (daily_fibs['65.0%']['price'], daily_fibs['61.8%']['price'])
        if daily_gp_range[0] <= price <= daily_gp_range[1]:
            score += 1
            details.append("In DAILY golden pocket")

        # Check 4H golden pocket
        h4_gp_range = (h4_fibs['65.0%']['price'], h4_fibs['61.8%']['price'])
        if h4_gp_range[0] <= price <= h4_gp_range[1]:
            score += 1
            details.append("In 4H golden pocket")

        # Bonus for exact level confluence
        if daily_zones and h4_zones:
            score += 0.5
            details.append("Near multiple Fib levels")

        return score, details

    async def run_backtest(self):
        """Run backtest with multi-timeframe Fibonacci levels"""

        # Fetch data
        fetcher = HistoricalDataFetcher()
        logging.info("Fetching data from June to October...")

        # Get full dataset
        df = await fetcher.fetch_btc_historical_data('2025-06-01', '2025-10-29', '1h')

        # Calculate timeframe data
        daily = df.resample('1D').agg({'high': 'max', 'low': 'min', 'close': 'last'})
        h4 = df.resample('4h').agg({'high': 'max', 'low': 'min', 'close': 'last'})

        # DAILY TIMEFRAME SWINGS (June-Oct)
        june_july = daily['2025-06-01':'2025-07-31']
        daily_low = june_july['low'].min()

        october_daily = daily['2025-10-01':'2025-10-15']
        daily_high = october_daily['high'].max()

        daily_fibs = self.calculate_fibs(daily_high, daily_low)

        # 4H TIMEFRAME SWINGS (October)
        oct_h4 = h4['2025-10-05':'2025-10-18']
        h4_high = oct_h4.loc['2025-10-05':'2025-10-07', 'high'].max()
        h4_low = oct_h4.loc['2025-10-16':'2025-10-18', 'low'].min()

        h4_fibs = self.calculate_fibs(h4_high, h4_low)

        print("\n" + "=" * 80)
        print("🎯 MULTI-TIMEFRAME FIBONACCI STRATEGY")
        print("=" * 80)

        print(f"\n📏 DAILY FIBS (June {daily_low:,.0f} → Oct {daily_high:,.0f}):")
        print(f"  Golden Pocket: ${daily_fibs['61.8%']['price']:,.0f} - ${daily_fibs['65.0%']['price']:,.0f}")

        print(f"\n📏 4H FIBS (Oct 6 {h4_high:,.0f} → Oct 17 {h4_low:,.0f}):")
        print(f"  Golden Pocket: ${h4_fibs['61.8%']['price']:,.0f} - ${h4_fibs['65.0%']['price']:,.0f}")

        # Run simulation from after October high
        post_high = df['2025-10-06 17:00:00':]

        # Track performance
        entries = []
        scale_ins = []
        exits = []

        print(f"\n🏁 Running backtest from Oct 6...")

        for idx in post_high.index:
            row = post_high.loc[idx]
            current_price = row['close']

            # Get confluence score
            confluence, details = self.get_confluence_score(current_price, daily_fibs, h4_fibs)

            # NO POSITION - Look for entries
            if self.position is None:
                # Entry logic based on confluence
                should_enter = False
                entry_reason = ""

                # Strong confluence (both GPs)
                if confluence >= 2:
                    should_enter = True
                    entry_reason = "STRONG: Both timeframes at golden pocket"
                    position_size = self.config['base_position_size'] * self.config['multi_tf_multiplier']
                    leverage = self.config['leverage']['multi_tf']

                # Single timeframe GP
                elif confluence >= 1:
                    should_enter = True
                    if "DAILY" in str(details):
                        entry_reason = "Daily golden pocket entry"
                    else:
                        entry_reason = "4H golden pocket entry"
                    position_size = self.config['base_position_size'] * self.config['single_tf_multiplier']
                    leverage = self.config['leverage']['single_tf']

                # Check for 50% retracement with momentum
                elif (abs(current_price - daily_fibs['50.0%']['price']) / current_price < 0.005 or
                      abs(current_price - h4_fibs['50.0%']['price']) / current_price < 0.005):
                    # Only enter at 50% if showing bounce signs
                    if idx > post_high.index[3]:  # Need some history
                        prev_low = post_high.loc[:idx].iloc[-3:]['low'].min()
                        if current_price > prev_low * 1.01:  # 1% bounce
                            should_enter = True
                            entry_reason = "50% Fib with bounce confirmation"
                            position_size = self.config['base_position_size']
                            leverage = self.config['leverage']['single_tf']

                if should_enter:
                    self.position = {
                        'entry_price': current_price,
                        'entry_time': idx,
                        'size': position_size,
                        'leverage': leverage,
                        'reason': entry_reason,
                        'average_price': current_price,
                        'total_invested': position_size * self.capital,
                        'scale_count': 0
                    }

                    entries.append({
                        'time': idx,
                        'price': current_price,
                        'reason': entry_reason,
                        'confluence': confluence
                    })

                    print(f"\n✅ ENTRY at {idx}")
                    print(f"  Price: ${current_price:,.0f}")
                    print(f"  Reason: {entry_reason}")
                    print(f"  Position: {position_size*100:.0f}%")
                    print(f"  Leverage: {leverage}x")

            # HAS POSITION - Manage it
            else:
                price_change = (current_price - self.position['average_price']) / self.position['average_price']

                # Scale-in logic
                for scale_level in self.config['scale_levels']:
                    if (price_change <= scale_level['deviation'] and
                        self.position['scale_count'] < len(self.config['scale_levels'])):

                        # Check if we're near support
                        near_support = any(
                            abs(current_price - level['price']) / current_price < 0.005
                            for name, level in {**daily_fibs, **h4_fibs}.items()
                            if level['strength'] in ['golden', 'strong']
                        )

                        if near_support:
                            add_size = scale_level['add']
                            old_avg = self.position['average_price']
                            old_size = self.position['size']

                            # Calculate new average
                            new_total_invested = (old_size * old_avg) + (add_size * current_price)
                            new_size = old_size + add_size
                            new_avg = new_total_invested / new_size

                            self.position['average_price'] = new_avg
                            self.position['size'] = new_size
                            self.position['scale_count'] += 1

                            scale_ins.append({
                                'time': idx,
                                'price': current_price,
                                'added': add_size,
                                'new_size': new_size
                            })

                            print(f"\n📈 SCALE IN at {idx}")
                            print(f"  Price: ${current_price:,.0f} ({price_change*100:.1f}%)")
                            print(f"  Added: {add_size*100:.0f}%")
                            print(f"  New average: ${new_avg:,.0f}")
                            break

                # Check invalidation
                daily_gp_bottom = daily_fibs['65.0%']['price']
                h4_gp_bottom = h4_fibs['65.0%']['price']

                # Use tighter invalidation for 4H, wider for daily
                if current_price < daily_gp_bottom * (1 - self.config['daily_invalidation']):
                    # Exit - daily structure broken
                    pnl = (current_price - self.position['average_price']) * self.position['size'] * self.capital / self.position['average_price']
                    pnl *= self.position['leverage']

                    exits.append({
                        'time': idx,
                        'price': current_price,
                        'pnl': pnl,
                        'reason': 'Daily invalidation'
                    })

                    print(f"\n❌ EXIT (Invalidation) at {idx}")
                    print(f"  Price: ${current_price:,.0f}")
                    print(f"  P&L: ${pnl:,.2f}")

                    self.capital += pnl
                    self.position = None

                # Profit taking
                elif price_change > 0.05:  # 5% profit
                    # Take partial profits
                    reduce_pct = 0.25
                    position_value = self.position['size'] * self.capital
                    pnl = position_value * price_change * self.position['leverage'] * reduce_pct

                    self.position['size'] *= (1 - reduce_pct)
                    self.capital += pnl

                    exits.append({
                        'time': idx,
                        'price': current_price,
                        'pnl': pnl,
                        'reason': f'Partial profit +{price_change*100:.1f}%'
                    })

                    print(f"\n💰 PARTIAL EXIT at {idx}")
                    print(f"  Price: ${current_price:,.0f} (+{price_change*100:.1f}%)")
                    print(f"  Profit taken: ${pnl:,.2f}")

                    if self.position['size'] < 0.05:  # Close if position too small
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

        # Results
        print("\n" + "=" * 80)
        print("📊 MULTI-TIMEFRAME RESULTS")
        print("=" * 80)

        total_return = (self.capital - self.initial_capital) / self.initial_capital * 100

        print(f"\n💰 PERFORMANCE:")
        print(f"  Initial: ${self.initial_capital:,.2f}")
        print(f"  Final: ${self.capital:,.2f}")
        print(f"  Return: {total_return:+.2f}%")

        print(f"\n📊 TRADE STATS:")
        print(f"  Entries: {len(entries)}")
        print(f"  Scale-ins: {len(scale_ins)}")
        print(f"  Exits: {len(exits)}")

        if entries:
            print(f"\n🎯 ENTRY BREAKDOWN:")
            for entry in entries:
                print(f"  {entry['time']}: {entry['reason']} (confluence: {entry['confluence']:.1f})")

        print("\n" + "=" * 80)

async def main():
    strategy = MultiTimeframeFibStrategy(initial_capital=10000)
    await strategy.run_backtest()

if __name__ == "__main__":
    asyncio.run(main())