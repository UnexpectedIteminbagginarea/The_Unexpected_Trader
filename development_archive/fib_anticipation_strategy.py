"""
Fibonacci Anticipation Strategy
Proactively adjust positions BEFORE hitting Fib levels
Scale out approaching resistance, scale in at support
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


class FibAnticipationStrategy:
    """
    Anticipate price reactions at Fibonacci levels
    Dynamically scale positions based on proximity to levels
    """

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.data_fetcher = HistoricalDataFetcher()

        self.params = {
            # Position sizing ranges
            'min_position': 0.10,           # Minimum 10% position
            'neutral_position': 0.40,       # Normal 40% position
            'max_position': 0.80,           # Maximum 80% position

            # Fib proximity zones (distance from level)
            'anticipation_zone': 0.005,     # 0.5% from Fib level
            'reaction_zone': 0.002,         # 0.2% very close

            # Position adjustments by Fib strength
            'fib_strength': {
                '23.6%': {'resistance': 0.3, 'support': 0.3},   # Weak level
                '38.2%': {'resistance': 0.5, 'support': 0.5},   # Medium level
                '50.0%': {'resistance': 0.6, 'support': 0.6},   # Strong level
                '61.8%': {'resistance': 0.8, 'support': 0.8},   # Golden pocket
                '65.0%': {'resistance': 0.8, 'support': 0.8},   # Golden pocket
                '78.6%': {'resistance': 0.7, 'support': 0.7},   # Deep level
            },

            # Momentum factors
            'momentum_window': 10,          # Bars to measure momentum
            'momentum_threshold': 0.02,     # 2% momentum is strong

            # Risk parameters
            'leverage': 3.0,                # Base leverage
            'invalidation': 0.03,           # 3% below support Fib
        }

        self.position = None
        self.trades = []
        self.fib_levels = {}

    def calculate_fib_levels(self, swing_low: float, swing_high: float) -> Dict:
        """
        Calculate all Fibonacci levels
        """
        fib_range = swing_high - swing_low

        levels = {
            '0.0%': {'price': swing_high, 'type': 'resistance'},
            '23.6%': {'price': swing_high - (fib_range * 0.236), 'type': 'both'},
            '38.2%': {'price': swing_high - (fib_range * 0.382), 'type': 'both'},
            '50.0%': {'price': swing_high - (fib_range * 0.500), 'type': 'both'},
            '61.8%': {'price': swing_high - (fib_range * 0.618), 'type': 'both'},
            '65.0%': {'price': swing_high - (fib_range * 0.650), 'type': 'both'},
            '78.6%': {'price': swing_high - (fib_range * 0.786), 'type': 'both'},
            '100.0%': {'price': swing_low, 'type': 'support'},
        }

        return levels

    def find_nearest_fibs(self, current_price: float) -> Dict:
        """
        Find nearest Fibonacci levels above and below current price
        """
        nearest_above = None
        nearest_below = None
        min_distance_above = float('inf')
        min_distance_below = float('inf')

        for level_name, level_data in self.fib_levels.items():
            level_price = level_data['price']

            if level_price > current_price:
                distance = level_price - current_price
                if distance < min_distance_above:
                    min_distance_above = distance
                    nearest_above = {
                        'name': level_name,
                        'price': level_price,
                        'distance': distance,
                        'distance_pct': distance / current_price
                    }
            elif level_price < current_price:
                distance = current_price - level_price
                if distance < min_distance_below:
                    min_distance_below = distance
                    nearest_below = {
                        'name': level_name,
                        'price': level_price,
                        'distance': distance,
                        'distance_pct': distance / current_price
                    }

        return {
            'above': nearest_above,
            'below': nearest_below,
            'between': f"{nearest_below['name'] if nearest_below else 'None'} - {nearest_above['name'] if nearest_above else 'None'}"
        }

    def calculate_position_adjustment(self, nearest_fibs: Dict, momentum: float,
                                     current_position: float, direction: str) -> Dict:
        """
        Calculate how to adjust position based on proximity to Fibs
        """
        adjustment = {
            'action': 'HOLD',
            'target_position': current_position,
            'reason': '',
            'confidence': 0
        }

        # Get nearest resistance (above) and support (below)
        resistance = nearest_fibs['above']
        support = nearest_fibs['below']

        if direction == 'long':
            # APPROACHING RESISTANCE - Consider scaling out
            if resistance and resistance['distance_pct'] <= self.params['anticipation_zone']:
                fib_strength = self.params['fib_strength'].get(
                    resistance['name'], {'resistance': 0.5}
                )['resistance']

                # Very close to resistance - scale out more
                if resistance['distance_pct'] <= self.params['reaction_zone']:
                    reduction_factor = 0.5 * fib_strength  # Reduce 50% at strong fibs
                    adjustment['target_position'] = current_position * (1 - reduction_factor)
                    adjustment['action'] = 'SCALE_OUT'
                    adjustment['reason'] = f"Very close to {resistance['name']} resistance"
                    adjustment['confidence'] = fib_strength

                    # If momentum is weak, scale out more
                    if momentum < 0:
                        adjustment['target_position'] *= 0.8
                        adjustment['reason'] += ' + weak momentum'

                # In anticipation zone - partial scale out
                else:
                    reduction_factor = 0.25 * fib_strength  # Reduce 25% approaching
                    adjustment['target_position'] = current_position * (1 - reduction_factor)
                    adjustment['action'] = 'PARTIAL_SCALE_OUT'
                    adjustment['reason'] = f"Approaching {resistance['name']} resistance"
                    adjustment['confidence'] = fib_strength * 0.7

            # AT SUPPORT - Consider scaling in
            elif support and support['distance_pct'] <= self.params['anticipation_zone']:
                fib_strength = self.params['fib_strength'].get(
                    support['name'], {'support': 0.5}
                )['support']

                # Very close to support - scale in more
                if support['distance_pct'] <= self.params['reaction_zone']:
                    # Check if we have room to add
                    max_add = self.params['max_position'] - current_position
                    add_factor = min(0.3 * fib_strength, max_add)  # Add up to 30%

                    adjustment['target_position'] = current_position + add_factor
                    adjustment['action'] = 'SCALE_IN'
                    adjustment['reason'] = f"At {support['name']} support"
                    adjustment['confidence'] = fib_strength

                    # If bounce momentum starting, add more
                    if momentum > self.params['momentum_threshold']:
                        additional = min(0.1, self.params['max_position'] - adjustment['target_position'])
                        adjustment['target_position'] += additional
                        adjustment['reason'] += ' + bounce momentum'

        return adjustment

    def calculate_momentum(self, df: pd.DataFrame, idx: int, window: int = 10) -> float:
        """
        Calculate price momentum
        """
        if idx < window:
            return 0

        current_price = df.iloc[idx]['close']
        past_price = df.iloc[idx - window]['close']

        return (current_price - past_price) / past_price

    async def run_backtest(self, start_date: str = '2025-06-01', end_date: str = '2025-10-29'):
        """
        Run Fibonacci anticipation strategy
        """
        print("=" * 80)
        print("🎯 FIBONACCI ANTICIPATION STRATEGY")
        print("=" * 80)
        print("\n📋 STRATEGY RULES:")
        print("  • ANTICIPATE reactions at Fib levels")
        print("  • Scale OUT approaching resistance")
        print("  • Scale IN at support with momentum")
        print("  • Dynamic position sizing based on proximity")
        print("  • Adjust for Fib strength and momentum")

        # Fetch data
        print(f"\n📊 Fetching data from {start_date} to {end_date}")
        df = await self.data_fetcher.fetch_btc_historical_data(start_date, end_date, '1h')

        if df.empty:
            print("Failed to fetch data")
            return

        # Find major swings (June low, October high)
        daily = df.resample('1D').agg({
            'high': 'max',
            'low': 'min',
            'close': 'last'
        })

        june_july = daily['2025-06-01':'2025-07-31']
        swing_low = june_july['low'].min()
        swing_low_date = june_july['low'].idxmin()

        oct = daily['2025-10-01':'2025-10-15']
        swing_high = oct['high'].max()
        swing_high_date = oct['high'].idxmax()

        print(f"\n📍 MAJOR SWINGS:")
        print(f"  Low: ${swing_low:,.0f} ({swing_low_date.date()})")
        print(f"  High: ${swing_high:,.0f} ({swing_high_date.date()})")

        # Calculate Fibonacci levels
        self.fib_levels = self.calculate_fib_levels(swing_low, swing_high)

        print(f"\n📏 FIBONACCI LEVELS:")
        for name, data in self.fib_levels.items():
            print(f"  {name}: ${data['price']:,.0f}")

        # Focus on trading after swing high
        post_high_df = df[swing_high_date:].reset_index()

        # Statistics
        scale_outs = 0
        scale_ins = 0
        fib_reactions = []

        # Run simulation
        for i in range(10, len(post_high_df)):  # Start after warmup
            row = post_high_df.iloc[i]
            current_price = row['close']
            current_time = post_high_df.index[i]

            # Calculate momentum
            momentum = self.calculate_momentum(post_high_df, i)

            # Find nearest Fib levels
            nearest_fibs = self.find_nearest_fibs(current_price)

            # NO POSITION - Look for entry
            if self.position is None:
                # Enter at major Fib levels with momentum confirmation
                for fib_name, fib_data in self.fib_levels.items():
                    fib_price = fib_data['price']
                    distance_pct = abs(current_price - fib_price) / current_price

                    if distance_pct <= self.params['reaction_zone']:
                        # Check for bounce momentum at support
                        if current_price > fib_price and momentum > 0:
                            # Entry at Fib support
                            self.position = {
                                'entry_time': current_time,
                                'entry_price': current_price,
                                'entry_fib': fib_name,
                                'direction': 'long',
                                'current_size': self.params['neutral_position'],
                                'peak_size': self.params['neutral_position'],
                                'trades': [{
                                    'time': current_time,
                                    'price': current_price,
                                    'size': self.params['neutral_position'],
                                    'action': 'ENTRY',
                                    'fib': fib_name
                                }],
                                'pnl': 0
                            }

                            print(f"\n🎯 ENTRY at {current_time}")
                            print(f"  Fib Level: {fib_name} (${fib_price:,.0f})")
                            print(f"  Entry Price: ${current_price:,.0f}")
                            print(f"  Position: {self.params['neutral_position']:.0%}")
                            print(f"  Momentum: {momentum:.3f}")
                            break

            # HAVE POSITION - Manage it
            elif self.position:
                # Calculate position adjustment
                adjustment = self.calculate_position_adjustment(
                    nearest_fibs, momentum,
                    self.position['current_size'],
                    self.position['direction']
                )

                # Execute adjustment if needed
                if adjustment['action'] != 'HOLD':
                    size_change = adjustment['target_position'] - self.position['current_size']

                    if adjustment['action'] in ['SCALE_OUT', 'PARTIAL_SCALE_OUT']:
                        if size_change < 0:  # Reducing position
                            # Calculate profit on scaled portion
                            scale_pnl = abs(size_change) * (current_price - self.position['entry_price'])
                            self.current_capital += scale_pnl * self.params['leverage']
                            self.position['pnl'] += scale_pnl * self.params['leverage']

                            self.position['current_size'] = adjustment['target_position']
                            scale_outs += 1

                            print(f"\n📉 SCALE OUT at {current_time}")
                            print(f"  Reason: {adjustment['reason']}")
                            print(f"  Price: ${current_price:,.0f}")
                            print(f"  Between: {nearest_fibs['between']}")
                            print(f"  Reduced to: {adjustment['target_position']:.0%}")
                            print(f"  Profit taken: ${scale_pnl:.2f}")

                            # Track Fib reaction
                            if nearest_fibs['above']:
                                fib_reactions.append({
                                    'fib': nearest_fibs['above']['name'],
                                    'type': 'resistance',
                                    'action': 'scaled_out',
                                    'success': True
                                })

                    elif adjustment['action'] == 'SCALE_IN':
                        if size_change > 0:  # Adding position
                            add_value = abs(size_change) * self.current_capital
                            self.position['current_size'] = adjustment['target_position']
                            self.position['peak_size'] = max(self.position['peak_size'],
                                                            adjustment['target_position'])
                            scale_ins += 1

                            print(f"\n📈 SCALE IN at {current_time}")
                            print(f"  Reason: {adjustment['reason']}")
                            print(f"  Price: ${current_price:,.0f}")
                            print(f"  Between: {nearest_fibs['between']}")
                            print(f"  Increased to: {adjustment['target_position']:.0%}")

                            # Track Fib reaction
                            if nearest_fibs['below']:
                                fib_reactions.append({
                                    'fib': nearest_fibs['below']['name'],
                                    'type': 'support',
                                    'action': 'scaled_in',
                                    'success': True
                                })

                    self.position['trades'].append({
                        'time': current_time,
                        'price': current_price,
                        'size': self.position['current_size'],
                        'action': adjustment['action'],
                        'reason': adjustment['reason']
                    })

                # Check for invalidation
                if current_price < swing_low * (1 + self.params['invalidation']):
                    # Close position
                    final_pnl = self.position['current_size'] * (current_price - self.position['entry_price'])
                    leveraged_pnl = final_pnl * self.params['leverage']
                    self.current_capital += leveraged_pnl

                    print(f"\n❌ INVALIDATED at {current_time}")
                    print(f"  Exit Price: ${current_price:,.0f}")
                    print(f"  Total P&L: ${self.position['pnl'] + leveraged_pnl:,.2f}")

                    self.trades.append({
                        'entry': self.position['entry_time'],
                        'exit': current_time,
                        'pnl': self.position['pnl'] + leveraged_pnl,
                        'scale_outs': scale_outs,
                        'scale_ins': scale_ins,
                        'peak_size': self.position['peak_size']
                    })

                    self.position = None

                # Force exit at end of data
                elif i == len(post_high_df) - 1:
                    final_pnl = self.position['current_size'] * (current_price - self.position['entry_price'])
                    leveraged_pnl = final_pnl * self.params['leverage']
                    self.current_capital += leveraged_pnl

                    print(f"\n📊 CLOSED (End of data)")
                    print(f"  Final Price: ${current_price:,.0f}")
                    print(f"  Total P&L: ${self.position['pnl'] + leveraged_pnl:,.2f}")

                    self.trades.append({
                        'entry': self.position['entry_time'],
                        'exit': current_time,
                        'pnl': self.position['pnl'] + leveraged_pnl,
                        'scale_outs': scale_outs,
                        'scale_ins': scale_ins,
                        'peak_size': self.position['peak_size']
                    })

                    self.position = None

        # Print results
        self.print_results(fib_reactions, scale_outs, scale_ins)

    def print_results(self, fib_reactions: List, scale_outs: int, scale_ins: int):
        """
        Print strategy results
        """
        print("\n" + "=" * 80)
        print("📊 FIBONACCI ANTICIPATION RESULTS")
        print("=" * 80)

        total_return = (self.current_capital - self.initial_capital) / self.initial_capital * 100

        print(f"\n💰 PERFORMANCE:")
        print(f"  Initial: ${self.initial_capital:,.2f}")
        print(f"  Final: ${self.current_capital:,.2f}")
        print(f"  Return: {total_return:+.2f}%")

        if self.trades:
            total_pnl = sum(t['pnl'] for t in self.trades)
            winners = [t for t in self.trades if t['pnl'] > 0]

            print(f"\n📊 TRADE STATS:")
            print(f"  Total trades: {len(self.trades)}")
            print(f"  Winners: {len(winners)} ({len(winners)/len(self.trades)*100:.0f}%)")
            print(f"  Total P&L: ${total_pnl:,.2f}")

        print(f"\n📈 POSITION MANAGEMENT:")
        print(f"  Total scale-outs: {scale_outs}")
        print(f"  Total scale-ins: {scale_ins}")

        if fib_reactions:
            # Analyze Fib reactions
            resistance_reactions = [f for f in fib_reactions if f['type'] == 'resistance']
            support_reactions = [f for f in fib_reactions if f['type'] == 'support']

            print(f"\n🎯 FIBONACCI REACTIONS:")
            print(f"  Resistance reactions: {len(resistance_reactions)}")
            print(f"  Support reactions: {len(support_reactions)}")

            # Count by Fib level
            from collections import Counter
            fib_counts = Counter(f['fib'] for f in fib_reactions)

            print(f"\n  Most reactive levels:")
            for fib, count in fib_counts.most_common(5):
                print(f"    {fib}: {count} reactions")

        print("\n" + "=" * 80)


async def main():
    """
    Run Fibonacci anticipation strategy
    """
    print("🎯 FIBONACCI ANTICIPATION STRATEGY")
    print("Proactively manage positions around Fib levels")

    strategy = FibAnticipationStrategy(initial_capital=10000)
    await strategy.run_backtest()


if __name__ == "__main__":
    asyncio.run(main())