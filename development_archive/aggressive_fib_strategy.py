"""
AGGRESSIVE Multi-Timeframe Fibonacci Strategy
Higher leverage, larger positions, scaling leverage with conviction
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

class AggressiveFibStrategy:
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = None
        self.trades = []

        # AGGRESSIVE configuration
        self.config = {
            # LARGER base position
            'base_position_size': 0.35,  # 35% initial (vs 25% conservative)

            # Position sizing based on confluence
            'single_tf_multiplier': 1.0,   # 35% for single timeframe
            'multi_tf_multiplier': 1.2,    # 42% for confluence

            # SAME scale-in levels (these work well)
            'scale_levels': [
                {'deviation': -0.01, 'add': 0.20},  # -1%: Add 20% (vs 15%)
                {'deviation': -0.02, 'add': 0.25},  # -2%: Add 25% (vs 20%)
                {'deviation': -0.04, 'add': 0.25},  # -4%: Add 25% (vs 20%)
                {'deviation': -0.06, 'add': 0.30},  # -6%: Add 30% (vs 20%)
            ],

            # Same invalidation levels
            'daily_invalidation': 0.10,  # 10% below daily GP
            '4h_invalidation': 0.08,      # 8% below 4H GP

            # Same profit targets (these work)
            'profit_targets': [
                {'gain': 0.05, 'reduce': 0.25},  # +5%: Take 25% off
                {'gain': 0.10, 'reduce': 0.25},  # +10%: Take 25% off
                {'gain': 0.15, 'reduce': 0.25},  # +15%: Take 25% off
            ],

            # AGGRESSIVE LEVERAGE - scales with conviction
            'leverage': {
                'base': 3,           # 3x base (vs 2x)
                'single_tf': 3,      # 3x for single timeframe
                'multi_tf': 4,       # 4x for confluence
                'scale_in_1': 3,     # Keep 3x on first scale
                'scale_in_2': 4,     # Increase to 4x
                'scale_in_3': 5,     # Max 5x on deep scales
                'scale_in_4': 5,     # Max 5x leverage
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

    def get_confluence_score(self, price, daily_fibs, h4_fibs):
        """Calculate confluence score based on both timeframes"""
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

        return score, details

    async def run_backtest(self):
        """Run AGGRESSIVE backtest"""

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
        print("🚀 AGGRESSIVE FIBONACCI STRATEGY")
        print("=" * 80)

        print(f"\n⚙️ AGGRESSIVE SETTINGS:")
        print(f"  Initial position: 35% (vs 25% conservative)")
        print(f"  Base leverage: 3x (vs 2x)")
        print(f"  Max leverage: 5x (scales with conviction)")
        print(f"  Scale-in sizes: 20-30% (vs 15-20%)")

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
        max_exposure = 0
        leverage_progression = []

        print(f"\n🏁 Running AGGRESSIVE backtest from Oct 6...")

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
                    leverage = self.config['leverage']['multi_tf']  # 4x

                # Single timeframe GP
                elif confluence >= 1:
                    should_enter = True
                    if "DAILY" in str(details):
                        entry_reason = "Daily golden pocket entry"
                    else:
                        entry_reason = "4H golden pocket entry"
                    position_size = self.config['base_position_size'] * self.config['single_tf_multiplier']
                    leverage = self.config['leverage']['single_tf']  # 3x

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
                            leverage = self.config['leverage']['base']  # 3x

                if should_enter:
                    self.position = {
                        'entry_price': current_price,
                        'entry_time': idx,
                        'size': position_size,
                        'leverage': leverage,
                        'reason': entry_reason,
                        'average_price': current_price,
                        'total_invested': position_size * self.capital,
                        'scale_count': 0,
                        'weighted_leverage': leverage  # Track weighted average leverage
                    }

                    entries.append({
                        'time': idx,
                        'price': current_price,
                        'reason': entry_reason,
                        'confluence': confluence
                    })

                    exposure = position_size * leverage * 100
                    max_exposure = max(max_exposure, exposure)

                    print(f"\n✅ AGGRESSIVE ENTRY at {idx}")
                    print(f"  Price: ${current_price:,.0f}")
                    print(f"  Reason: {entry_reason}")
                    print(f"  Position: {position_size*100:.0f}%")
                    print(f"  Leverage: {leverage}x")
                    print(f"  💥 Exposure: {exposure:.0f}% of account")

                    leverage_progression.append({
                        'action': 'entry',
                        'leverage': leverage,
                        'position': position_size
                    })

            # HAS POSITION - Manage it
            else:
                price_change = (current_price - self.position['average_price']) / self.position['average_price']

                # AGGRESSIVE Scale-in logic with INCREASING LEVERAGE
                for i, scale_level in enumerate(self.config['scale_levels']):
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

                            # INCREASE LEVERAGE AS WE SCALE IN
                            if self.position['scale_count'] == 0:
                                new_leverage = self.config['leverage']['scale_in_1']  # 3x
                            elif self.position['scale_count'] == 1:
                                new_leverage = self.config['leverage']['scale_in_2']  # 4x
                            else:
                                new_leverage = self.config['leverage']['scale_in_3']  # 5x

                            # Calculate new average
                            new_total_invested = (old_size * old_avg) + (add_size * current_price)
                            new_size = old_size + add_size
                            new_avg = new_total_invested / new_size

                            # Update weighted average leverage
                            old_weighted = self.position['weighted_leverage'] * old_size
                            new_weighted = (old_weighted + new_leverage * add_size) / new_size

                            self.position['average_price'] = new_avg
                            self.position['size'] = new_size
                            self.position['scale_count'] += 1
                            self.position['weighted_leverage'] = new_weighted

                            scale_ins.append({
                                'time': idx,
                                'price': current_price,
                                'added': add_size,
                                'new_size': new_size,
                                'leverage': new_leverage
                            })

                            exposure = new_size * new_weighted * 100
                            max_exposure = max(max_exposure, exposure)

                            print(f"\n📈 AGGRESSIVE SCALE IN #{self.position['scale_count']} at {idx}")
                            print(f"  Price: ${current_price:,.0f} ({price_change*100:.1f}%)")
                            print(f"  Added: {add_size*100:.0f}%")
                            print(f"  New leverage: {new_leverage}x (was {self.position['leverage']}x)")
                            print(f"  Total position: {new_size*100:.0f}%")
                            print(f"  New average: ${new_avg:,.0f}")
                            print(f"  💥 Total exposure: {exposure:.0f}% of account")

                            leverage_progression.append({
                                'action': f'scale-in-{self.position["scale_count"]}',
                                'leverage': new_leverage,
                                'position': new_size
                            })
                            break

                # Check invalidation
                daily_gp_bottom = daily_fibs['65.0%']['price']
                h4_gp_bottom = h4_fibs['65.0%']['price']

                # Use tighter invalidation for 4H, wider for daily
                if current_price < daily_gp_bottom * (1 - self.config['daily_invalidation']):
                    # Exit - daily structure broken
                    pnl = (current_price - self.position['average_price']) * self.position['size'] * self.capital / self.position['average_price']
                    pnl *= self.position['weighted_leverage']

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
                    pnl = position_value * price_change * self.position['weighted_leverage'] * reduce_pct

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
            pnl *= self.position['weighted_leverage']
            self.capital += pnl

            print(f"\n📊 CLOSED at end")
            print(f"  Final price: ${final_price:,.0f}")
            print(f"  P&L: ${pnl:,.2f}")

        # Results
        print("\n" + "=" * 80)
        print("📊 AGGRESSIVE STRATEGY RESULTS")
        print("=" * 80)

        total_return = (self.capital - self.initial_capital) / self.initial_capital * 100

        print(f"\n💰 PERFORMANCE:")
        print(f"  Initial: ${self.initial_capital:,.2f}")
        print(f"  Final: ${self.capital:,.2f}")
        print(f"  Return: {total_return:+.2f}%")
        print(f"  Conservative baseline: +6.55%")
        print(f"  Aggressive improvement: {total_return - 6.55:+.2f}%")

        print(f"\n⚡ LEVERAGE PROGRESSION:")
        for prog in leverage_progression:
            print(f"  {prog['action']}: {prog['leverage']}x leverage @ {prog['position']*100:.0f}% position")

        print(f"\n📊 TRADE STATS:")
        print(f"  Entries: {len(entries)}")
        print(f"  Scale-ins: {len(scale_ins)}")
        print(f"  Exits: {len(exits)}")
        print(f"  Max exposure: {max_exposure:.0f}% of account")

        if entries:
            print(f"\n🎯 ENTRY BREAKDOWN:")
            for entry in entries:
                print(f"  {entry['time']}: {entry['reason']} (confluence: {entry['confluence']:.1f})")

        print(f"\n⚠️ RISK METRICS:")
        print(f"  Maximum theoretical loss: {max_exposure/100 * 0.10:.1f}% (10% move with max leverage)")
        print(f"  Break-even needed: {100/(max_exposure/100):.1f}% move")

        print("\n" + "=" * 80)

async def main():
    strategy = AggressiveFibStrategy(initial_capital=10000)
    await strategy.run_backtest()

if __name__ == "__main__":
    asyncio.run(main())