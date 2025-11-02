"""
Position Scaling Strategy - Single Position with Dynamic Sizing
Build up positions on strong signals, reduce on weakness
"""
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our modules
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.historical_data_fetcher import HistoricalDataFetcher
from core.multi_timeframe_golden_pocket import MultiTimeframeGoldenPocket


class PositionScalingStrategy:
    """
    Single position that scales up/down based on signals
    - Start with base position on first signal
    - Add to position on additional confirming signals
    - Reduce position on partial profit targets
    - Full exit on stop or signal reversal
    """

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.data_fetcher = HistoricalDataFetcher()
        self.gp_detector = MultiTimeframeGoldenPocket()

        # Position scaling parameters
        self.params = {
            # Base position sizes (% of capital)
            'initial_position_size': 0.20,      # 20% on first signal
            'add_position_size': 0.15,          # Add 15% on each additional signal
            'max_position_size': 0.60,          # Never exceed 60% of capital

            # Leverage rules
            'base_leverage': 3.0,               # 3x base leverage
            'gp_leverage': 5.0,                 # 5x on golden pockets
            'multi_gp_leverage': 10.0,          # 10x on multi-TF golden pockets

            # Position management
            'max_adds': 3,                      # Maximum 3 position adds
            'add_cooldown_bars': 4,             # Wait 4 bars between adds
            'scale_in_threshold': 0.50,         # Need 50% confidence to add

            # Risk management
            'initial_stop_loss': 0.04,          # 4% initial stop
            'breakeven_trigger': 0.015,         # Move to BE at 1.5%
            'trailing_activation': 0.03,        # Trail at 3%
            'trailing_distance': 0.015,         # Trail 1.5% below

            # Profit taking (reduce position)
            'reduce_targets': [
                {'level': 0.02, 'reduce_pct': 0.20},   # Reduce 20% at 2%
                {'level': 0.04, 'reduce_pct': 0.20},   # Reduce 20% at 4%
                {'level': 0.06, 'reduce_pct': 0.20},   # Reduce 20% at 6%
                {'level': 0.10, 'reduce_pct': 0.20},   # Reduce 20% at 10%
            ],

            # Signal thresholds
            'gp_confidence_threshold': 0.40,    # Min confidence for GP entry
            'technical_confidence_threshold': 0.45,  # Min for technical signals
        }

        self.position = None
        self.trades = []
        self.equity_curve = []

    def calculate_position_leverage(self, signals: Dict) -> float:
        """
        Determine leverage based on signal strength
        """
        if signals.get('gp_confirmations', 0) >= 2:
            return self.params['multi_gp_leverage']  # 10x
        elif signals.get('gp_confirmations', 0) >= 1:
            return self.params['gp_leverage']  # 5x
        elif signals.get('confidence', 0) >= 0.60:
            return self.params['base_leverage']  # 3x
        else:
            return 1.0  # No leverage for weak signals

    def check_entry_signals(self, row: pd.Series) -> Dict:
        """
        Check for entry/add signals
        """
        signals = {
            'should_enter': False,
            'signal_type': None,
            'confidence': 0,
            'gp_confirmations': 0,
            'direction': None,  # 'long' or 'short'
        }

        # Check golden pocket
        try:
            gp_confirmations = row['gp_confirmations']
            gp_confidence = row['gp_confidence']
        except (KeyError, AttributeError):
            gp_confirmations = 0
            gp_confidence = 0

        if gp_confirmations >= 1 and gp_confidence >= self.params['gp_confidence_threshold']:
            signals['should_enter'] = True
            signals['signal_type'] = 'golden_pocket'
            signals['confidence'] = gp_confidence
            signals['gp_confirmations'] = gp_confirmations
            signals['direction'] = 'long'  # Golden pockets are bullish signals
            return signals

        # Check technical signals (simplified for now)
        # RSI oversold
        if hasattr(row, 'rsi') and pd.notna(row.get('rsi')):
            if row['rsi'] < 30:
                signals['confidence'] = 0.55
                signals['signal_type'] = 'oversold'
                signals['direction'] = 'long'
                signals['should_enter'] = True
            elif row['rsi'] > 70:
                signals['confidence'] = 0.55
                signals['signal_type'] = 'overbought'
                signals['direction'] = 'short'
                signals['should_enter'] = True

        return signals

    async def run_backtest(self, days: int = 30):
        """
        Run position scaling backtest
        """
        print("=" * 80)
        print("📈 POSITION SCALING STRATEGY - DYNAMIC SIZING")
        print("=" * 80)
        print("\n📋 STRATEGY RULES:")
        print("  • Start with 20% position on first signal")
        print("  • Add 15% on each confirming signal (max 60% total)")
        print("  • 5x leverage on golden pockets, 10x on multi-TF")
        print("  • Reduce position by 20% at profit targets")
        print("  • Trail stops after 3% profit")
        print("  • Maximum 3 position adds")

        # Fetch data
        end_date = '2025-10-29'
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=days)).strftime('%Y-%m-%d')

        print(f"\n📊 Fetching {days} days of data...")
        df_1h = await self.data_fetcher.fetch_btc_historical_data(start_date, end_date, '1h')

        if df_1h.empty:
            print("Failed to fetch data")
            return

        # Calculate indicators
        df_1h = self.calculate_indicators(df_1h)

        # Detect golden pockets
        timeframe_data = self.gp_detector.detect_all_timeframes(df_1h)
        confluence_df = self.gp_detector.find_confluence_zones(timeframe_data)

        # Merge indicators
        for col in ['rsi', 'volume_ratio', 'momentum']:
            if col in df_1h.columns:
                confluence_df[col] = df_1h[col]

        print(f"✅ Data loaded: {len(confluence_df)} candles")
        print(f"💰 Initial Capital: ${self.initial_capital:,.2f}")

        # Track golden pocket opportunities
        gp_signals_seen = 0
        gp_trades_taken = 0

        # Run simulation
        for i in range(250, len(confluence_df)):  # Start after warmup
            row = confluence_df.iloc[i]
            current_price = row['close']
            current_time = confluence_df.index[i]

            # Check for signals
            signals = self.check_entry_signals(row)

            # Track GP signals
            if signals.get('gp_confirmations', 0) >= 1:
                gp_signals_seen += 1

            # NO POSITION - Consider opening
            if self.position is None:
                if signals['should_enter']:
                    # Calculate initial position
                    position_size_pct = self.params['initial_position_size']
                    leverage = self.calculate_position_leverage(signals)
                    position_value = self.current_capital * position_size_pct

                    if signals.get('signal_type') == 'golden_pocket':
                        gp_trades_taken += 1

                    self.position = {
                        'entry_time': current_time,
                        'entry_price': current_price,
                        'direction': signals['direction'],
                        'current_size_pct': position_size_pct,
                        'total_invested': position_value,
                        'shares': position_value / current_price,
                        'leverage': leverage,
                        'adds_count': 0,
                        'last_add_bar': i,
                        'entries': [{
                            'time': current_time,
                            'price': current_price,
                            'size_pct': position_size_pct,
                            'signal': signals['signal_type'],
                            'confidence': signals['confidence']
                        }],
                        'reductions': [],
                        'stop_loss': current_price * (1 - self.params['initial_stop_loss']),
                        'highest_price': current_price,
                        'lowest_price': current_price,
                        'breakeven_hit': False,
                        'trailing_active': False
                    }

                    print(f"\n📍 POSITION OPENED at {current_time}")
                    print(f"  Direction: {signals['direction'].upper()}")
                    print(f"  Entry Price: ${current_price:,.2f}")
                    print(f"  Initial Size: {position_size_pct:.0%} of capital")
                    print(f"  Leverage: {leverage:.1f}x")
                    print(f"  Signal: {signals['signal_type']}")
                    if signals.get('gp_confirmations'):
                        print(f"  GP Confirmations: {signals['gp_confirmations']}")

            # HAVE POSITION - Manage it
            elif self.position is not None:
                # Calculate P&L
                if self.position['direction'] == 'long':
                    price_change_pct = (current_price - self.position['entry_price']) / self.position['entry_price']
                    self.position['highest_price'] = max(self.position['highest_price'], current_price)
                else:  # short
                    price_change_pct = (self.position['entry_price'] - current_price) / self.position['entry_price']
                    self.position['lowest_price'] = min(self.position['lowest_price'], current_price)

                # CHECK FOR POSITION ADDS
                can_add = (
                    self.position['adds_count'] < self.params['max_adds'] and
                    (i - self.position['last_add_bar']) >= self.params['add_cooldown_bars'] and
                    self.position['current_size_pct'] < self.params['max_position_size']
                )

                if can_add and signals['should_enter'] and signals['direction'] == self.position['direction']:
                    # Add to position if signal confirms direction
                    if signals['confidence'] >= self.params['scale_in_threshold']:
                        add_size = min(
                            self.params['add_position_size'],
                            self.params['max_position_size'] - self.position['current_size_pct']
                        )

                        if add_size > 0:
                            add_value = self.current_capital * add_size
                            add_shares = add_value / current_price

                            self.position['current_size_pct'] += add_size
                            self.position['total_invested'] += add_value
                            self.position['shares'] += add_shares
                            self.position['adds_count'] += 1
                            self.position['last_add_bar'] = i

                            # Update leverage if stronger signal
                            new_leverage = self.calculate_position_leverage(signals)
                            if new_leverage > self.position['leverage']:
                                self.position['leverage'] = new_leverage

                            self.position['entries'].append({
                                'time': current_time,
                                'price': current_price,
                                'size_pct': add_size,
                                'signal': signals['signal_type'],
                                'confidence': signals['confidence']
                            })

                            print(f"\n➕ POSITION ADDED at {current_time}")
                            print(f"  Add Price: ${current_price:,.2f}")
                            print(f"  Add Size: {add_size:.0%}")
                            print(f"  Total Size: {self.position['current_size_pct']:.0%}")
                            print(f"  Signal: {signals['signal_type']}")

                # PROFIT MANAGEMENT - Reduce position at targets
                for target in self.params['reduce_targets']:
                    if price_change_pct >= target['level'] and not any(r['level'] == target['level'] for r in self.position['reductions']):
                        # Reduce position
                        reduce_shares = self.position['shares'] * target['reduce_pct']
                        reduce_value = reduce_shares * current_price

                        # Calculate profit on reduced portion
                        avg_entry = self.position['total_invested'] / (self.position['shares'] if self.position['shares'] > 0 else 1)
                        profit = (current_price - avg_entry) * reduce_shares

                        self.current_capital += profit
                        self.position['shares'] -= reduce_shares
                        self.position['current_size_pct'] *= (1 - target['reduce_pct'])

                        self.position['reductions'].append({
                            'time': current_time,
                            'price': current_price,
                            'level': target['level'],
                            'reduce_pct': target['reduce_pct'],
                            'profit': profit
                        })

                        print(f"\n💰 POSITION REDUCED at {current_time}")
                        print(f"  Target Hit: {target['level']:.1%}")
                        print(f"  Reduced: {target['reduce_pct']:.0%} of position")
                        print(f"  Profit: ${profit:,.2f}")
                        print(f"  Remaining: {self.position['current_size_pct']:.0%}")

                # STOP LOSS MANAGEMENT
                if not self.position['breakeven_hit'] and price_change_pct >= self.params['breakeven_trigger']:
                    self.position['stop_loss'] = self.position['entry_price'] * 1.001
                    self.position['breakeven_hit'] = True
                    logger.info(f"Stop moved to breakeven")

                if price_change_pct >= self.params['trailing_activation']:
                    self.position['trailing_active'] = True
                    if self.position['direction'] == 'long':
                        trail_stop = self.position['highest_price'] * (1 - self.params['trailing_distance'])
                    else:
                        trail_stop = self.position['lowest_price'] * (1 + self.params['trailing_distance'])

                    if self.position['direction'] == 'long' and trail_stop > self.position['stop_loss']:
                        self.position['stop_loss'] = trail_stop
                    elif self.position['direction'] == 'short' and trail_stop < self.position['stop_loss']:
                        self.position['stop_loss'] = trail_stop

                # EXIT CONDITIONS
                should_exit = False
                exit_reason = None

                # Check stop loss
                if self.position['direction'] == 'long' and current_price <= self.position['stop_loss']:
                    should_exit = True
                    exit_reason = 'STOP_LOSS'
                elif self.position['direction'] == 'short' and current_price >= self.position['stop_loss']:
                    should_exit = True
                    exit_reason = 'STOP_LOSS'

                # Check for signal reversal
                if signals['should_enter'] and signals['direction'] != self.position['direction']:
                    should_exit = True
                    exit_reason = 'SIGNAL_FLIP'

                # End of data
                if i == len(confluence_df) - 1:
                    should_exit = True
                    exit_reason = 'END_OF_DATA'

                if should_exit:
                    # Close remaining position
                    if self.position['shares'] > 0:
                        avg_entry = self.position['total_invested'] / (self.position['shares'] if self.position['shares'] > 0 else 1)

                        if self.position['direction'] == 'long':
                            final_pnl = (current_price - avg_entry) * self.position['shares']
                            final_pnl_pct = (current_price - avg_entry) / avg_entry * 100
                        else:
                            final_pnl = (avg_entry - current_price) * self.position['shares']
                            final_pnl_pct = (avg_entry - current_price) / avg_entry * 100

                        self.current_capital += final_pnl

                        # Record trade
                        self.trades.append({
                            'entry_time': self.position['entry_time'],
                            'exit_time': current_time,
                            'direction': self.position['direction'],
                            'entry_price': self.position['entry_price'],
                            'exit_price': current_price,
                            'adds_count': self.position['adds_count'],
                            'reductions_count': len(self.position['reductions']),
                            'max_size': max(e['size_pct'] for e in self.position['entries']),
                            'leverage': self.position['leverage'],
                            'pnl': final_pnl,
                            'pnl_pct': final_pnl_pct,
                            'exit_reason': exit_reason
                        })

                        print(f"\n📊 POSITION CLOSED at {current_time}")
                        print(f"  Exit Price: ${current_price:,.2f}")
                        print(f"  Exit Reason: {exit_reason}")
                        print(f"  P&L: ${final_pnl:,.2f} ({final_pnl_pct:+.2f}%)")
                        print(f"  Final Capital: ${self.current_capital:,.2f}")

                    self.position = None

            # Track equity
            self.equity_curve.append(self.current_capital)

        # Print results
        self.print_results(gp_signals_seen, gp_trades_taken)
        return self.trades

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators
        """
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Volume
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()

        # Momentum
        df['momentum'] = df['close'].pct_change(10) * 100

        return df

    def print_results(self, gp_signals_seen: int, gp_trades_taken: int):
        """
        Print comprehensive results
        """
        if not self.trades:
            print("\n❌ No trades executed")
            return

        print("\n" + "=" * 80)
        print("📊 BACKTEST RESULTS - POSITION SCALING")
        print("=" * 80)

        # Performance
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital * 100

        print(f"\n💰 PERFORMANCE:")
        print(f"  Initial Capital: ${self.initial_capital:,.2f}")
        print(f"  Final Capital: ${self.current_capital:,.2f}")
        print(f"  Total Return: {total_return:+.2f}%")

        # Trade statistics
        winners = [t for t in self.trades if t['pnl'] > 0]
        losers = [t for t in self.trades if t['pnl'] <= 0]

        print(f"\n📊 TRADE STATISTICS:")
        print(f"  Total Trades: {len(self.trades)}")
        print(f"  Winners: {len(winners)} ({len(winners)/len(self.trades)*100:.1f}%)")
        print(f"  Losers: {len(losers)}")

        if winners:
            print(f"  Avg Win: {np.mean([t['pnl_pct'] for t in winners]):.2f}%")
            print(f"  Best Trade: {max(t['pnl_pct'] for t in winners):.2f}%")
        if losers:
            print(f"  Avg Loss: {np.mean([t['pnl_pct'] for t in losers]):.2f}%")
            print(f"  Worst Trade: {min(t['pnl_pct'] for t in losers):.2f}%")

        # Position management
        trades_with_adds = [t for t in self.trades if t['adds_count'] > 0]
        trades_with_reductions = [t for t in self.trades if t['reductions_count'] > 0]

        print(f"\n📈 POSITION MANAGEMENT:")
        print(f"  Trades with Adds: {len(trades_with_adds)} ({len(trades_with_adds)/len(self.trades)*100:.1f}%)")
        if trades_with_adds:
            print(f"  Avg Adds per Trade: {np.mean([t['adds_count'] for t in trades_with_adds]):.1f}")
        print(f"  Trades with Reductions: {len(trades_with_reductions)} ({len(trades_with_reductions)/len(self.trades)*100:.1f}%)")

        # Golden Pocket Analysis
        print(f"\n✨ GOLDEN POCKET ANALYSIS:")
        print(f"  GP Signals Seen: {gp_signals_seen}")
        print(f"  GP Trades Taken: {gp_trades_taken}")
        if gp_signals_seen > 0:
            print(f"  GP Conversion Rate: {gp_trades_taken/gp_signals_seen*100:.1f}%")

        # Exit analysis
        exit_reasons = {}
        for t in self.trades:
            reason = t['exit_reason']
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        print(f"\n🚪 EXIT ANALYSIS:")
        for reason, count in exit_reasons.items():
            print(f"  {reason}: {count} ({count/len(self.trades)*100:.1f}%)")

        # Recent trades
        print(f"\n📝 LAST 5 TRADES:")
        for t in self.trades[-5:]:
            print(f"  {t['entry_time'].strftime('%m-%d %H:%M')}: "
                  f"{t['direction'].upper()} {t['pnl_pct']:+.2f}% "
                  f"(Adds: {t['adds_count']}, Leverage: {t['leverage']:.0f}x)")

        print("\n" + "=" * 80)


async def main():
    """
    Run position scaling strategy backtest
    """
    print("🎯 POSITION SCALING STRATEGY")
    print("Single position with dynamic sizing based on signals")

    backtester = PositionScalingStrategy(initial_capital=10000)
    trades = await backtester.run_backtest(days=30)

    if trades:
        print(f"\n✅ Strategy complete with {len(trades)} trades")
    else:
        print("\n⚠️ No trades executed")


if __name__ == "__main__":
    asyncio.run(main())