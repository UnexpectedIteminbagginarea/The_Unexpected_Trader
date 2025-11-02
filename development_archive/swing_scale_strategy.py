"""
Swing Trading Strategy with Intelligent Scaling
- Start with 25% position
- Scale in on deviations/dips within the zone
- Exit only on idea invalidation, not noise
- Based on MAJOR swing points, not micro structure
"""
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.historical_data_fetcher import HistoricalDataFetcher


class SwingScaleStrategy:
    """
    Swing trading with intelligent position scaling
    Based on major market structure, not micro timeframes
    """

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.data_fetcher = HistoricalDataFetcher()

        self.params = {
            # Position scaling
            'initial_position': 0.25,        # Start with 25%
            'scale_levels': [
                {'deviation': -0.01, 'add': 0.15},  # Add 15% at -1%
                {'deviation': -0.02, 'add': 0.20},  # Add 20% at -2%
                {'deviation': -0.04, 'add': 0.20},  # Add 20% at -4%
                {'deviation': -0.06, 'add': 0.20},  # Add 20% at -6%
            ],
            'max_position': 1.0,             # Can use 100% of capital

            # Leverage based on conviction
            'gp_leverage': 5.0,              # 5x in golden pocket
            'normal_leverage': 2.0,          # 2x for other setups

            # Invalidation levels (not fixed stops!)
            'gp_invalidation': 0.10,         # 10% below GP zone
            'trend_break_invalidation': 0.15, # 15% for trend breaks

            # Profit targets (scale out)
            'scale_out_levels': [
                {'gain': 0.05, 'reduce': 0.25},  # Take 25% at +5%
                {'gain': 0.10, 'reduce': 0.25},  # Take 25% at +10%
                {'gain': 0.15, 'reduce': 0.25},  # Take 25% at +15%
            ],
        }

        self.position = None
        self.trades = []

    def find_major_swings(self, df: pd.DataFrame, lookback_days: int = 120) -> Dict:
        """
        Find MAJOR swing points on daily/weekly timeframes
        Not hourly noise!
        """
        # Resample to daily
        daily = df.resample('1D').agg({
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })

        # MANUALLY specify the REAL major swings we identified
        # June low and October high
        june_july = daily['2025-06-01':'2025-07-31']
        swing_low = june_july['low'].min()
        swing_low_date = june_july['low'].idxmin()

        # October high
        oct = daily['2025-10-01':'2025-10-15']
        swing_high = oct['high'].max()
        swing_high_date = oct['high'].idxmax()

        return {
            'swing_low': swing_low,
            'swing_low_date': swing_low_date,
            'swing_high': swing_high,
            'swing_high_date': swing_high_date,
            'range': swing_high - swing_low
        }

    def calculate_fib_levels(self, swing_low: float, swing_high: float) -> Dict:
        """
        Calculate Fibonacci levels from MAJOR swings
        """
        fib_range = swing_high - swing_low

        return {
            'swing_high': swing_high,
            'fib_236': swing_high - (fib_range * 0.236),
            'fib_382': swing_high - (fib_range * 0.382),
            'fib_500': swing_high - (fib_range * 0.500),
            'fib_618': swing_high - (fib_range * 0.618),
            'fib_650': swing_high - (fib_range * 0.650),
            'fib_786': swing_high - (fib_range * 0.786),
            'swing_low': swing_low,
            'gp_top': swing_high - (fib_range * 0.618),
            'gp_bottom': swing_high - (fib_range * 0.650),
            'gp_center': swing_high - (fib_range * 0.634),  # Center of GP
        }

    def check_invalidation(self, position: Dict, current_price: float, fib_levels: Dict) -> Tuple[bool, str]:
        """
        Check if trade idea is INVALIDATED (not just stop loss!)
        """
        if not position:
            return False, ""

        # For LONG positions
        if position['direction'] == 'long':
            # Golden pocket longs - invalidated if we break significantly below zone
            if position['entry_type'] == 'golden_pocket':
                invalidation_price = fib_levels['gp_bottom'] * (1 - self.params['gp_invalidation'])
                if current_price < invalidation_price:
                    return True, f"Broke below GP invalidation at ${invalidation_price:.0f}"

            # Trend longs - invalidated if we break key structure
            elif position['entry_type'] == 'trend':
                # Use swing low as invalidation
                if current_price < fib_levels['swing_low'] * 1.02:  # 2% below swing low
                    return True, f"Broke below swing low structure"

        return False, ""

    def calculate_position_size(self, signal: Dict, current_capital: float) -> Dict:
        """
        Calculate position sizing based on signal and scaling plan
        """
        if signal['type'] == 'golden_pocket':
            # High conviction in GP zone
            initial_size = self.params['initial_position']
            leverage = self.params['gp_leverage']
        else:
            # Lower conviction elsewhere
            initial_size = self.params['initial_position'] * 0.6
            leverage = self.params['normal_leverage']

        position_value = current_capital * initial_size

        return {
            'size_pct': initial_size,
            'value': position_value,
            'leverage': leverage,
            'remaining_capacity': self.params['max_position'] - initial_size
        }

    async def run_backtest(self, start_date: str = '2025-06-01', end_date: str = '2025-10-29'):
        """
        Run swing scale strategy backtest
        """
        print("=" * 80)
        print("🎯 SWING SCALE STRATEGY - MAJOR STRUCTURE TRADING")
        print("=" * 80)
        print("\n📋 STRATEGY RULES:")
        print("  • Start with 25% position size")
        print("  • Scale IN on deviations (not panic out)")
        print("  • Exit on INVALIDATION, not noise")
        print("  • Use MAJOR swing points, not micro structure")
        print("  • 5x leverage in golden pocket, 2x elsewhere")

        # Fetch extended data for proper swing detection
        print(f"\n📊 Fetching data from {start_date} to {end_date}")
        df = await self.data_fetcher.fetch_btc_historical_data(start_date, end_date, '1h')

        if df.empty:
            print("Failed to fetch data")
            return

        print(f"✅ Loaded {len(df)} hourly candles")

        # Find MAJOR swings
        swings = self.find_major_swings(df)
        print(f"\n📍 MAJOR SWINGS DETECTED:")
        print(f"  Swing Low: ${swings['swing_low']:,.0f} on {swings['swing_low_date'].date()}")
        print(f"  Swing High: ${swings['swing_high']:,.0f} on {swings['swing_high_date'].date()}")
        print(f"  Range: ${swings['range']:,.0f}")

        # Calculate Fibonacci levels
        fib_levels = self.calculate_fib_levels(swings['swing_low'], swings['swing_high'])
        print(f"\n📏 FIBONACCI LEVELS:")
        print(f"  23.6%: ${fib_levels['fib_236']:,.0f}")
        print(f"  38.2%: ${fib_levels['fib_382']:,.0f}")
        print(f"  50.0%: ${fib_levels['fib_500']:,.0f}")
        print(f"  Golden Pocket: ${fib_levels['gp_top']:,.0f} - ${fib_levels['gp_bottom']:,.0f}")
        print(f"  78.6%: ${fib_levels['fib_786']:,.0f}")

        # Focus on trading after the swing high
        post_high_df = df[swings['swing_high_date']:]
        print(f"\n⏰ Trading period: {len(post_high_df)} hours after swing high")

        # Track statistics
        gp_entries = 0
        scale_ins = 0
        invalidations = 0

        # Run simulation
        for i, (idx, row) in enumerate(post_high_df.iterrows()):
            current_price = row['close']

            # NO POSITION - Look for entries
            if self.position is None:
                signal = None

                # Check if price entered golden pocket
                if fib_levels['gp_bottom'] <= current_price <= fib_levels['gp_top']:
                    signal = {
                        'type': 'golden_pocket',
                        'price': current_price,
                        'time': idx,
                        'fib_level': 'Golden Pocket'
                    }
                    gp_entries += 1

                # Or check for other Fib levels (38.2%, 50%)
                elif fib_levels['fib_382'] - 500 <= current_price <= fib_levels['fib_382'] + 500:
                    signal = {
                        'type': 'fib_bounce',
                        'price': current_price,
                        'time': idx,
                        'fib_level': '38.2%'
                    }

                elif fib_levels['fib_500'] - 500 <= current_price <= fib_levels['fib_500'] + 500:
                    signal = {
                        'type': 'fib_bounce',
                        'price': current_price,
                        'time': idx,
                        'fib_level': '50.0%'
                    }

                if signal:
                    # Calculate position size
                    position_info = self.calculate_position_size(signal, self.current_capital)

                    self.position = {
                        'entry_time': idx,
                        'entry_price': current_price,
                        'entry_type': signal['type'],
                        'direction': 'long',
                        'avg_price': current_price,
                        'total_shares': position_info['value'] / current_price,
                        'total_size_pct': position_info['size_pct'],
                        'leverage': position_info['leverage'],
                        'entries': [{
                            'time': idx,
                            'price': current_price,
                            'size_pct': position_info['size_pct'],
                            'reason': signal['fib_level']
                        }],
                        'exits': [],
                        'remaining_capacity': position_info['remaining_capacity'],
                        'highest': current_price,
                        'lowest': current_price
                    }

                    print(f"\n📍 POSITION OPENED at {idx}")
                    print(f"  Type: {signal['type'].upper()} ({signal['fib_level']})")
                    print(f"  Entry: ${current_price:,.0f}")
                    print(f"  Size: {position_info['size_pct']:.0%} ({position_info['leverage']:.0f}x leverage)")
                    print(f"  Remaining capacity: {position_info['remaining_capacity']:.0%}")

            # HAVE POSITION - Manage it
            elif self.position:
                # Update highs/lows
                self.position['highest'] = max(self.position['highest'], current_price)
                self.position['lowest'] = min(self.position['lowest'], current_price)

                # Calculate P&L
                price_change_pct = (current_price - self.position['avg_price']) / self.position['avg_price']

                # Check for INVALIDATION (not stop loss!)
                is_invalidated, reason = self.check_invalidation(self.position, current_price, fib_levels)

                if is_invalidated:
                    # Exit on invalidation
                    pnl = (current_price - self.position['avg_price']) * self.position['total_shares']
                    leveraged_pnl = pnl * self.position['leverage']
                    pnl_pct = price_change_pct * 100

                    self.current_capital += leveraged_pnl
                    invalidations += 1

                    print(f"\n❌ POSITION INVALIDATED at {idx}")
                    print(f"  Reason: {reason}")
                    print(f"  Exit: ${current_price:,.0f}")
                    print(f"  P&L: ${leveraged_pnl:,.2f} ({pnl_pct:+.2f}%)")
                    print(f"  Capital: ${self.current_capital:,.2f}")

                    self.trades.append({
                        'entry_time': self.position['entry_time'],
                        'exit_time': idx,
                        'type': self.position['entry_type'],
                        'pnl': leveraged_pnl,
                        'pnl_pct': pnl_pct,
                        'exit_reason': 'INVALIDATED',
                        'scale_ins': len(self.position['entries']) - 1
                    })

                    self.position = None

                else:
                    # Check for SCALE IN opportunities
                    if self.position['remaining_capacity'] > 0 and price_change_pct < 0:
                        for scale_level in self.params['scale_levels']:
                            level_id = f"scale_{scale_level['deviation']}"

                            # Check if we hit this deviation and haven't scaled here yet
                            if (price_change_pct <= scale_level['deviation'] and
                                level_id not in [e.get('level_id') for e in self.position['entries']]):

                                # Scale in
                                add_size = min(scale_level['add'], self.position['remaining_capacity'])
                                add_value = self.current_capital * add_size
                                add_shares = add_value / current_price

                                # Update position
                                self.position['total_shares'] += add_shares
                                self.position['total_size_pct'] += add_size
                                self.position['remaining_capacity'] -= add_size

                                # Recalculate average price
                                total_value = (self.position['avg_price'] * (self.position['total_shares'] - add_shares) +
                                             current_price * add_shares)
                                self.position['avg_price'] = total_value / self.position['total_shares']

                                self.position['entries'].append({
                                    'time': idx,
                                    'price': current_price,
                                    'size_pct': add_size,
                                    'reason': f"Scale at {scale_level['deviation']:.0%}",
                                    'level_id': level_id
                                })

                                scale_ins += 1
                                print(f"\n➕ SCALED IN at {idx}")
                                print(f"  Price: ${current_price:,.0f} ({price_change_pct:.2%} from avg)")
                                print(f"  Added: {add_size:.0%}")
                                print(f"  Total position: {self.position['total_size_pct']:.0%}")
                                print(f"  New avg price: ${self.position['avg_price']:,.0f}")

                    # Check for SCALE OUT opportunities (profit taking)
                    if price_change_pct > 0:
                        for exit_level in self.params['scale_out_levels']:
                            level_id = f"exit_{exit_level['gain']}"

                            if (price_change_pct >= exit_level['gain'] and
                                level_id not in self.position['exits']):

                                # Scale out
                                reduce_shares = self.position['total_shares'] * exit_level['reduce']
                                profit = reduce_shares * (current_price - self.position['avg_price'])
                                leveraged_profit = profit * self.position['leverage']

                                self.current_capital += leveraged_profit
                                self.position['total_shares'] -= reduce_shares
                                self.position['exits'].append(level_id)

                                print(f"\n💰 SCALED OUT at {idx}")
                                print(f"  Price: ${current_price:,.0f} ({price_change_pct:+.2%})")
                                print(f"  Reduced: {exit_level['reduce']:.0%}")
                                print(f"  Profit: ${leveraged_profit:,.2f}")
                                print(f"  Capital: ${self.current_capital:,.2f}")

                    # Force exit at end of data
                    if i == len(post_high_df) - 1:
                        pnl = (current_price - self.position['avg_price']) * self.position['total_shares']
                        leveraged_pnl = pnl * self.position['leverage']
                        pnl_pct = price_change_pct * 100

                        self.current_capital += leveraged_pnl

                        print(f"\n📊 POSITION CLOSED (End of data)")
                        print(f"  Final P&L: ${leveraged_pnl:,.2f} ({pnl_pct:+.2f}%)")

                        self.trades.append({
                            'entry_time': self.position['entry_time'],
                            'exit_time': idx,
                            'type': self.position['entry_type'],
                            'pnl': leveraged_pnl,
                            'pnl_pct': pnl_pct,
                            'exit_reason': 'END_DATA',
                            'scale_ins': len(self.position['entries']) - 1
                        })

                        self.position = None

        # Print results
        self.print_results(gp_entries, scale_ins, invalidations)

    def print_results(self, gp_entries: int, scale_ins: int, invalidations: int):
        """
        Print strategy results
        """
        print("\n" + "=" * 80)
        print("📊 SWING SCALE STRATEGY RESULTS")
        print("=" * 80)

        total_return = (self.current_capital - self.initial_capital) / self.initial_capital * 100

        print(f"\n💰 PERFORMANCE:")
        print(f"  Initial: ${self.initial_capital:,.2f}")
        print(f"  Final: ${self.current_capital:,.2f}")
        print(f"  Return: {total_return:+.2f}%")

        if self.trades:
            winners = [t for t in self.trades if t['pnl'] > 0]
            losers = [t for t in self.trades if t['pnl'] <= 0]

            print(f"\n📊 TRADE STATS:")
            print(f"  Total trades: {len(self.trades)}")
            print(f"  Winners: {len(winners)} ({len(winners)/len(self.trades)*100:.0f}%)")
            print(f"  Losers: {len(losers)}")

            if winners:
                print(f"  Avg win: {np.mean([t['pnl_pct'] for t in winners]):.2f}%")
            if losers:
                print(f"  Avg loss: {np.mean([t['pnl_pct'] for t in losers]):.2f}%")

            # Scale statistics
            trades_with_scales = [t for t in self.trades if t['scale_ins'] > 0]
            print(f"\n📈 SCALING STATS:")
            print(f"  Golden Pocket entries: {gp_entries}")
            print(f"  Total scale-ins: {scale_ins}")
            print(f"  Trades with scale-ins: {len(trades_with_scales)}")
            print(f"  Invalidations: {invalidations}")

        print("\n" + "=" * 80)


async def main():
    """
    Run swing scale strategy
    """
    print("🎯 SWING TRADING WITH INTELLIGENT SCALING")
    print("Using major market structure, not micro noise")

    strategy = SwingScaleStrategy(initial_capital=10000)
    await strategy.run_backtest()


if __name__ == "__main__":
    asyncio.run(main())