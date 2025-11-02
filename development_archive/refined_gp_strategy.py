"""
Refined Golden Pocket Strategy
- Prioritize golden pocket trades
- Filter out noisy RSI signals
- Better stop placement using volatility
- Multi-timeframe confirmation
"""
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
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


class RefinedGoldenPocketStrategy:
    """
    Refined strategy focusing on golden pocket trades
    with proper filtering and risk management
    """

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.data_fetcher = HistoricalDataFetcher()
        self.gp_detector = MultiTimeframeGoldenPocket()

        # Refined parameters
        self.params = {
            # Position sizing based on signal quality
            'gp_position_size': 0.40,           # 40% for golden pocket trades
            'confirmed_position_size': 0.25,    # 25% for multi-TF confirmed
            'weak_position_size': 0.15,         # 15% for weak signals
            'max_position_size': 0.60,          # Never exceed 60%

            # Leverage (only for golden pockets)
            'gp_single_leverage': 5.0,          # 5x for single GP
            'gp_multi_leverage': 10.0,          # 10x for multi-TF GP
            'normal_leverage': 1.0,             # No leverage for non-GP

            # Entry filters
            'min_gp_confidence': 0.50,          # Minimum GP confidence
            'require_trend_alignment': True,     # Must align with trend
            'rsi_extreme_only': True,           # Only take RSI < 30 or > 70

            # Dynamic stop loss (ATR-based)
            'atr_multiplier': 2.0,              # Stop at 2x ATR
            'min_stop_distance': 0.02,          # Minimum 2% stop
            'max_stop_distance': 0.05,          # Maximum 5% stop

            # Profit management
            'partial_targets': [
                {'level': 1.5, 'reduce': 0.25},  # Take 25% at 1.5x ATR
                {'level': 2.5, 'reduce': 0.25},  # Take 25% at 2.5x ATR
                {'level': 4.0, 'reduce': 0.25},  # Take 25% at 4x ATR
            ],
            'trailing_atr_multiplier': 1.5,     # Trail at 1.5x ATR
            'breakeven_atr_multiplier': 1.0,    # BE at 1x ATR profit
        }

        self.position = None
        self.trades = []
        self.equity_curve = []

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate comprehensive indicators including ATR
        """
        # ATR for dynamic stops
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(14).mean()
        df['atr_pct'] = df['atr'] / df['close'] * 100

        # Trend detection (multiple timeframes)
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        df['sma_200'] = df['close'].rolling(200).mean()

        # Trend strength
        df['trend_short'] = np.where(df['close'] > df['sma_20'], 1, -1)
        df['trend_medium'] = np.where(df['sma_20'] > df['sma_50'], 1, -1)
        df['trend_long'] = np.where(df['sma_50'] > df['sma_200'], 1, -1)
        df['trend_score'] = df['trend_short'] + df['trend_medium'] + df['trend_long']

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Volume analysis
        df['volume_ma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']

        # Momentum
        df['momentum_10'] = df['close'].pct_change(10) * 100
        df['momentum_20'] = df['close'].pct_change(20) * 100

        return df

    def evaluate_signal_quality(self, row: pd.Series, df: pd.DataFrame, idx: int) -> Dict:
        """
        Comprehensive signal evaluation with multi-timeframe confirmation
        """
        signal = {
            'type': None,
            'strength': 0,
            'direction': None,
            'confidence': 0,
            'position_size': 0,
            'leverage': 1.0,
            'reasons': []
        }

        # PRIORITY 1: Golden Pocket Detection
        try:
            gp_confirmations = row['gp_confirmations']
            gp_confidence = row['gp_confidence']
        except (KeyError, AttributeError):
            gp_confirmations = 0
            gp_confidence = 0

        if gp_confirmations >= 1 and gp_confidence >= self.params['min_gp_confidence']:
            signal['type'] = 'golden_pocket'
            signal['strength'] = 10  # Highest priority
            signal['direction'] = 'long'  # GPs are bullish
            signal['confidence'] = gp_confidence
            signal['reasons'].append(f"GP {gp_confirmations}TF")

            # Position size and leverage based on confirmations
            if gp_confirmations >= 2:
                signal['position_size'] = self.params['gp_position_size']
                signal['leverage'] = self.params['gp_multi_leverage']
                signal['strength'] = 15  # Even higher for multi-TF
            else:
                signal['position_size'] = self.params['gp_position_size']
                signal['leverage'] = self.params['gp_single_leverage']

            return signal  # Return immediately - GP trumps all

        # PRIORITY 2: Trend-aligned extremes only
        trend_score = row.get('trend_score', 0)
        rsi = row.get('rsi', 50)

        # Only take RSI signals at extremes with trend alignment
        if self.params['rsi_extreme_only'] and pd.notna(rsi):
            # Extreme oversold in uptrend
            if rsi < 30 and trend_score > 0:
                signal['type'] = 'oversold_bounce'
                signal['strength'] = 5
                signal['direction'] = 'long'
                signal['confidence'] = 0.60 + (30 - rsi) / 100  # More extreme = higher confidence
                signal['position_size'] = self.params['confirmed_position_size']
                signal['reasons'].append(f"RSI {rsi:.0f} + Uptrend")

            # Extreme overbought in downtrend (for shorts)
            elif rsi > 70 and trend_score < 0:
                signal['type'] = 'overbought_reversal'
                signal['strength'] = 5
                signal['direction'] = 'short'
                signal['confidence'] = 0.60 + (rsi - 70) / 100
                signal['position_size'] = self.params['confirmed_position_size']
                signal['reasons'].append(f"RSI {rsi:.0f} + Downtrend")

        # PRIORITY 3: Strong momentum with volume
        if signal['type'] is None:  # Only if no signal yet
            momentum = row.get('momentum_10', 0)
            volume_ratio = row.get('volume_ratio', 1)

            # Strong bullish momentum with volume
            if momentum > 3 and volume_ratio > 1.5 and trend_score > 0:
                signal['type'] = 'momentum_breakout'
                signal['strength'] = 3
                signal['direction'] = 'long'
                signal['confidence'] = 0.55
                signal['position_size'] = self.params['weak_position_size']
                signal['reasons'].append(f"Momentum {momentum:.1f}% + Vol")

        return signal

    def calculate_dynamic_stop(self, entry_price: float, direction: str, atr: float) -> float:
        """
        Calculate dynamic stop loss based on ATR
        """
        stop_distance = atr * self.params['atr_multiplier']
        stop_distance_pct = stop_distance / entry_price

        # Apply min/max constraints
        stop_distance_pct = max(self.params['min_stop_distance'],
                               min(self.params['max_stop_distance'], stop_distance_pct))

        if direction == 'long':
            stop_price = entry_price * (1 - stop_distance_pct)
        else:
            stop_price = entry_price * (1 + stop_distance_pct)

        return stop_price, stop_distance_pct

    async def run_backtest(self, days: int = 30):
        """
        Run refined strategy backtest
        """
        print("=" * 80)
        print("🎯 REFINED GOLDEN POCKET STRATEGY")
        print("=" * 80)
        print("\n📋 STRATEGY RULES:")
        print("  • PRIORITIZE golden pocket trades (40% position, 5-10x leverage)")
        print("  • FILTER RSI signals (extremes only, trend-aligned)")
        print("  • DYNAMIC stops based on ATR (2x ATR)")
        print("  • PARTIAL profits at ATR multiples")
        print("  • NO leverage for non-GP trades")

        # Fetch data
        end_date = '2025-10-29'
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=days)).strftime('%Y-%m-%d')

        print(f"\n📊 Fetching {days} days of data...")
        df_1h = await self.data_fetcher.fetch_btc_historical_data(start_date, end_date, '1h')

        if df_1h.empty:
            print("Failed to fetch data")
            return

        # Calculate all indicators
        df_1h = self.calculate_indicators(df_1h)

        # Detect golden pockets
        timeframe_data = self.gp_detector.detect_all_timeframes(df_1h)
        confluence_df = self.gp_detector.find_confluence_zones(timeframe_data)

        # Merge all indicators
        for col in ['atr', 'atr_pct', 'trend_score', 'rsi', 'volume_ratio',
                    'momentum_10', 'sma_20', 'sma_50', 'sma_200']:
            if col in df_1h.columns:
                confluence_df[col] = df_1h[col]

        print(f"✅ Data loaded: {len(confluence_df)} candles")
        print(f"💰 Initial Capital: ${self.initial_capital:,.2f}")

        # Track statistics
        gp_signals = 0
        gp_trades = 0
        signal_types = {}

        # Run simulation
        for i in range(250, len(confluence_df)):  # Start after warmup
            row = confluence_df.iloc[i]
            current_price = row['close']
            current_time = confluence_df.index[i]
            current_atr = row.get('atr', current_price * 0.02)

            # Evaluate signal
            signal = self.evaluate_signal_quality(row, confluence_df, i)

            # Track GP signals
            if signal['type'] == 'golden_pocket':
                gp_signals += 1

            # NO POSITION - Consider entry
            if self.position is None:
                if signal['type'] is not None and signal['confidence'] > 0:
                    # Track signal type
                    signal_types[signal['type']] = signal_types.get(signal['type'], 0) + 1

                    # Track GP trades
                    if signal['type'] == 'golden_pocket':
                        gp_trades += 1

                    # Calculate dynamic stop
                    stop_price, stop_pct = self.calculate_dynamic_stop(
                        current_price, signal['direction'], current_atr
                    )

                    # Open position
                    position_value = self.current_capital * signal['position_size']

                    self.position = {
                        'entry_time': current_time,
                        'entry_price': current_price,
                        'direction': signal['direction'],
                        'signal_type': signal['type'],
                        'size_pct': signal['position_size'],
                        'leverage': signal['leverage'],
                        'value': position_value,
                        'shares': position_value / current_price,
                        'stop_price': stop_price,
                        'stop_pct': stop_pct,
                        'entry_atr': current_atr,
                        'highest': current_price,
                        'lowest': current_price,
                        'partial_exits': [],
                        'breakeven_hit': False,
                        'trailing_active': False,
                        'confidence': signal['confidence']
                    }

                    print(f"\n🎯 TRADE OPENED at {current_time}")
                    print(f"  Type: {signal['type'].upper()}")
                    print(f"  Direction: {signal['direction'].upper()}")
                    print(f"  Price: ${current_price:,.2f}")
                    print(f"  Size: {signal['position_size']:.0%} ({signal['leverage']:.0f}x leverage)")
                    print(f"  Stop: ${stop_price:,.2f} ({stop_pct:.2%})")
                    print(f"  ATR: ${current_atr:.2f}")
                    print(f"  Reasons: {', '.join(signal['reasons'])}")

            # HAVE POSITION - Manage it
            elif self.position is not None:
                # Update highs/lows
                self.position['highest'] = max(self.position['highest'], current_price)
                self.position['lowest'] = min(self.position['lowest'], current_price)

                # Calculate P&L
                if self.position['direction'] == 'long':
                    price_change = current_price - self.position['entry_price']
                    price_change_pct = price_change / self.position['entry_price']
                    price_change_atr = price_change / self.position['entry_atr']
                else:
                    price_change = self.position['entry_price'] - current_price
                    price_change_pct = price_change / self.position['entry_price']
                    price_change_atr = price_change / self.position['entry_atr']

                # Partial profit taking at ATR levels
                for target in self.params['partial_targets']:
                    target_id = f"atr_{target['level']}"
                    if (price_change_atr >= target['level'] and
                        target_id not in self.position['partial_exits']):

                        # Take partial profit
                        reduce_shares = self.position['shares'] * target['reduce']
                        profit = reduce_shares * price_change
                        self.current_capital += profit
                        self.position['shares'] -= reduce_shares

                        self.position['partial_exits'].append(target_id)
                        print(f"  💰 Partial exit at {target['level']:.1f}x ATR: "
                              f"{target['reduce']:.0%} for ${profit:,.2f}")

                # Breakeven stop
                if (not self.position['breakeven_hit'] and
                    price_change_atr >= self.params['breakeven_atr_multiplier']):

                    self.position['stop_price'] = self.position['entry_price'] * 1.001
                    self.position['breakeven_hit'] = True
                    print(f"  ✅ Stop moved to breakeven")

                # Trailing stop
                if price_change_atr >= self.params['trailing_atr_multiplier']:
                    self.position['trailing_active'] = True
                    trail_distance = current_atr * self.params['trailing_atr_multiplier']

                    if self.position['direction'] == 'long':
                        new_stop = self.position['highest'] - trail_distance
                        if new_stop > self.position['stop_price']:
                            self.position['stop_price'] = new_stop
                    else:
                        new_stop = self.position['lowest'] + trail_distance
                        if new_stop < self.position['stop_price']:
                            self.position['stop_price'] = new_stop

                # Check exit conditions
                should_exit = False
                exit_reason = None

                # Stop loss
                if self.position['direction'] == 'long':
                    if current_price <= self.position['stop_price']:
                        should_exit = True
                        exit_reason = 'STOP'
                else:
                    if current_price >= self.position['stop_price']:
                        should_exit = True
                        exit_reason = 'STOP'

                # Signal reversal (only for strong opposite signals)
                if signal['type'] is not None and signal['direction'] != self.position['direction']:
                    if signal['strength'] >= 5:  # Only flip on strong signals
                        should_exit = True
                        exit_reason = 'REVERSAL'

                # End of data
                if i == len(confluence_df) - 1:
                    should_exit = True
                    exit_reason = 'END'

                if should_exit:
                    # Close position
                    if self.position['shares'] > 0:
                        if self.position['direction'] == 'long':
                            final_pnl = (current_price - self.position['entry_price']) * self.position['shares']
                        else:
                            final_pnl = (self.position['entry_price'] - current_price) * self.position['shares']

                        # Apply leverage to P&L
                        leveraged_pnl = final_pnl * self.position['leverage']
                        pnl_pct = price_change_pct * 100

                        self.current_capital += leveraged_pnl

                        # Record trade
                        self.trades.append({
                            'entry_time': self.position['entry_time'],
                            'exit_time': current_time,
                            'signal_type': self.position['signal_type'],
                            'direction': self.position['direction'],
                            'entry_price': self.position['entry_price'],
                            'exit_price': current_price,
                            'leverage': self.position['leverage'],
                            'pnl': leveraged_pnl,
                            'pnl_pct': pnl_pct,
                            'exit_reason': exit_reason,
                            'partial_exits': len(self.position['partial_exits'])
                        })

                        print(f"\n📊 TRADE CLOSED at {current_time}")
                        print(f"  Exit: ${current_price:,.2f}")
                        print(f"  Reason: {exit_reason}")
                        print(f"  P&L: ${leveraged_pnl:,.2f} ({pnl_pct:+.2f}%)")
                        if self.position['leverage'] > 1:
                            print(f"  Leveraged: {self.position['leverage']:.0f}x")
                        print(f"  Capital: ${self.current_capital:,.2f}")

                    self.position = None

            # Track equity
            self.equity_curve.append(self.current_capital)

        # Print results
        self.print_results(gp_signals, gp_trades, signal_types)
        return self.trades

    def print_results(self, gp_signals: int, gp_trades: int, signal_types: Dict):
        """
        Print comprehensive results
        """
        if not self.trades:
            print("\n❌ No trades executed")
            return

        print("\n" + "=" * 80)
        print("📊 REFINED STRATEGY RESULTS")
        print("=" * 80)

        # Performance
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital * 100

        print(f"\n💰 PERFORMANCE:")
        print(f"  Initial: ${self.initial_capital:,.2f}")
        print(f"  Final: ${self.current_capital:,.2f}")
        print(f"  Return: {total_return:+.2f}%")

        # Win/Loss
        winners = [t for t in self.trades if t['pnl'] > 0]
        losers = [t for t in self.trades if t['pnl'] <= 0]

        print(f"\n📊 TRADE STATS:")
        print(f"  Total: {len(self.trades)}")
        print(f"  Winners: {len(winners)} ({len(winners)/len(self.trades)*100:.1f}%)")

        if winners:
            print(f"  Avg Win: {np.mean([t['pnl_pct'] for t in winners]):.2f}%")
            print(f"  Max Win: {max(t['pnl_pct'] for t in winners):.2f}%")
        if losers:
            print(f"  Avg Loss: {np.mean([t['pnl_pct'] for t in losers]):.2f}%")
            print(f"  Max Loss: {min(t['pnl_pct'] for t in losers):.2f}%")

        # Golden Pocket Analysis
        gp_trades_list = [t for t in self.trades if t['signal_type'] == 'golden_pocket']

        print(f"\n✨ GOLDEN POCKET:")
        print(f"  Signals: {gp_signals}")
        print(f"  Trades: {gp_trades}")
        if gp_signals > 0:
            print(f"  Conversion: {gp_trades/gp_signals*100:.1f}%")
        if gp_trades_list:
            gp_winners = [t for t in gp_trades_list if t['pnl'] > 0]
            print(f"  GP Win Rate: {len(gp_winners)/len(gp_trades_list)*100:.1f}%")

        # Signal breakdown
        print(f"\n🎯 SIGNAL TYPES:")
        for signal_type, count in signal_types.items():
            type_trades = [t for t in self.trades if t['signal_type'] == signal_type]
            if type_trades:
                type_winners = [t for t in type_trades if t['pnl'] > 0]
                win_rate = len(type_winners)/len(type_trades)*100
                print(f"  {signal_type}: {count} trades, {win_rate:.0f}% win")

        # Exit analysis
        exit_reasons = {}
        for t in self.trades:
            exit_reasons[t['exit_reason']] = exit_reasons.get(t['exit_reason'], 0) + 1

        print(f"\n🚪 EXITS:")
        for reason, count in exit_reasons.items():
            print(f"  {reason}: {count} ({count/len(self.trades)*100:.0f}%)")

        print("\n" + "=" * 80)


async def main():
    """
    Run refined golden pocket strategy
    """
    print("🎯 REFINED GOLDEN POCKET STRATEGY")
    print("Focus on high-probability golden pocket trades")

    backtester = RefinedGoldenPocketStrategy(initial_capital=10000)
    trades = await backtester.run_backtest(days=30)

    if trades:
        print(f"\n✅ Complete with {len(trades)} trades")


if __name__ == "__main__":
    asyncio.run(main())