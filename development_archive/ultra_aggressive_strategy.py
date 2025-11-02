"""
Ultra-Aggressive Trading Strategy with 5x Leverage
This is our most aggressive configuration for maximum trade frequency
while maintaining the profit protection rules
"""
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
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


class UltraAggressiveStrategy:
    """
    Maximum aggression while protecting profits
    - More entry signals
    - Lower thresholds
    - Multiple entry conditions
    - But ALWAYS protect winners
    """

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.data_fetcher = HistoricalDataFetcher()
        self.gp_detector = MultiTimeframeGoldenPocket()

        # ULTRA-AGGRESSIVE PARAMETERS - YOUR EXACT SPECS
        self.params = {
            # Leverage (based on golden pocket signals)
            'leverage_single_gp': 5.0,           # 5x for single GP
            'leverage_multi_gp': 10.0,           # 10x for multi-timeframe GP

            # Position sizing (ALWAYS 60% minimum)
            'min_position_size': 0.60,           # ALWAYS use 60% of capital minimum
            'max_position_size': 0.60,           # Fixed at 60%

            # Entry thresholds (MUCH LOWER)
            'gp_entry_threshold': 0.40,          # Enter GP at 40% confidence
            'momentum_entry_threshold': 0.45,     # Momentum trades at 45%
            'volume_spike_multiplier': 1.5,      # Volume 1.5x average
            'rsi_oversold': 35,                  # RSI below 35
            'rsi_overbought': 65,                # RSI above 65 for shorts

            # Stop losses (tighter with leverage)
            'initial_stop_loss': 0.03,           # 3% initial stop
            'max_stop_loss': 0.05,               # Never wider than 5%

            # Profit protection (CRITICAL)
            'breakeven_trigger': 0.01,           # Move to BE at 1%
            'trailing_activation': 0.02,         # Trail at 2%
            'trailing_distance': 0.01,           # Trail 1% below

            # Profit taking
            'tp1_percent': 0.015,                # 1.5% - quick scalp
            'tp1_size': 0.25,                    # Take 25% off
            'tp2_percent': 0.03,                 # 3% - solid gain
            'tp2_size': 0.25,                    # Take 25% off
            'tp3_percent': 0.05,                 # 5% - good move
            'tp3_size': 0.25,                    # Take 25% off
            'tp4_percent': 0.08,                 # 8% - let rest run

            # Entry signals (multiple conditions)
            'require_any_signal': True,          # Need ANY signal, not all
            'max_trades_per_day': 5,            # Limit daily trades
            'cooldown_hours': 2,                 # Hours between trades
        }

        self.trades = []
        self.equity_curve = []
        self.daily_trades = {}

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate additional technical indicators for entry signals
        """
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Volume analysis
        df['volume_ma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']

        # Price momentum
        df['momentum'] = df['close'].pct_change(10) * 100

        # Moving averages
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()

        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(20).mean()
        std = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (std * 2)
        df['bb_lower'] = df['bb_middle'] - (std * 2)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

        return df

    def check_entry_signals(self, row: pd.Series, df: pd.DataFrame, idx: int) -> Dict:
        """
        Check multiple entry conditions - ANY can trigger
        """
        signals = {
            'golden_pocket': False,
            'momentum_spike': False,
            'volume_breakout': False,
            'oversold_bounce': False,
            'bb_squeeze': False,
            'total_score': 0,
            'confidence': 0,
            'leverage': 1.0
        }

        # 1. Golden Pocket Signal (PRIMARY)
        try:
            gp_confirmations = row['gp_confirmations']
            gp_confidence = row['gp_confidence']
        except (KeyError, AttributeError):
            gp_confirmations = 0
            gp_confidence = 0

        if gp_confirmations >= 1:
            gp_conf = gp_confidence
            if gp_conf >= self.params['gp_entry_threshold']:
                signals['golden_pocket'] = True
                signals['total_score'] += 40

                # Bonus for multi-timeframe
                if gp_confirmations >= 2:
                    signals['total_score'] += 20
                if gp_confirmations >= 3:
                    signals['total_score'] += 10

        # 2. Momentum Spike
        if pd.notna(row.get('momentum')):
            if row['momentum'] > 2:  # 2% move in 10 bars
                signals['momentum_spike'] = True
                signals['total_score'] += 25

        # 3. Volume Breakout
        if pd.notna(row.get('volume_ratio')):
            if row['volume_ratio'] > self.params['volume_spike_multiplier']:
                signals['volume_breakout'] = True
                signals['total_score'] += 20

        # 4. Oversold Bounce
        if pd.notna(row.get('rsi')):
            if row['rsi'] < self.params['rsi_oversold']:
                signals['oversold_bounce'] = True
                signals['total_score'] += 25
            elif 40 <= row['rsi'] <= 60:  # Neutral RSI bonus
                signals['total_score'] += 10

        # 5. Bollinger Band Squeeze/Expansion
        if pd.notna(row.get('bb_position')):
            if row['bb_position'] < 0.2:  # Near lower band
                signals['bb_squeeze'] = True
                signals['total_score'] += 20
            elif row['bb_position'] > 0.8:  # Near upper band (for shorts later)
                signals['total_score'] -= 10

        # Calculate final confidence
        signals['confidence'] = min(signals['total_score'] / 100, 1.0)

        # Determine leverage based on golden pocket confirmations (already have gp_confirmations from above)
        if gp_confirmations >= 2:  # Multi-timeframe golden pocket
            signals['leverage'] = self.params['leverage_multi_gp']  # 10x
        elif gp_confirmations == 1:  # Single golden pocket
            signals['leverage'] = self.params['leverage_single_gp']  # 5x
        else:
            # Non-GP trades still get 5x if other signals are strong
            if signals['confidence'] >= 0.50:
                signals['leverage'] = self.params['leverage_single_gp']  # 5x
            else:
                signals['leverage'] = 1.0  # No leverage for weak non-GP signals

        # Need at least one signal and minimum confidence
        signals['should_enter'] = (
            any([signals['golden_pocket'], signals['momentum_spike'],
                 signals['volume_breakout'], signals['oversold_bounce'],
                 signals['bb_squeeze']])
            and signals['confidence'] >= 0.40
        )

        return signals

    async def run_backtest(self, days: int = 30):
        """
        Run ultra-aggressive backtest
        """
        print("=" * 80)
        print("🔥 ULTRA-AGGRESSIVE STRATEGY - 5X/10X LEVERAGE")
        print("=" * 80)
        print("\n📋 STRATEGY RULES:")
        print("  • 5x leverage on single golden pocket signals")
        print("  • 10x leverage on multi-timeframe golden pockets")
        print("  • ALWAYS use 60% of capital per trade")
        print("  • Breakeven at +1%, Trail at +2%")
        print("  • Partial profits: 25% at 1.5%, 3%, 5%, rest at 8%")
        print("  • Max 5 trades/day, 2hr cooldown")
        print("  • NEVER let winners become losers")

        # Fetch data
        end_date = '2025-10-29'
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=days)).strftime('%Y-%m-%d')

        print(f"\n📊 Fetching {days} days of data...")
        df_1h = await self.data_fetcher.fetch_btc_historical_data(start_date, end_date, '1h')

        if df_1h.empty:
            print("Failed to fetch data")
            return

        # Calculate indicators
        df_1h = self.calculate_technical_indicators(df_1h)

        # Detect golden pockets
        timeframe_data = self.gp_detector.detect_all_timeframes(df_1h)
        confluence_df = self.gp_detector.find_confluence_zones(timeframe_data)

        # Merge technical indicators
        for col in ['rsi', 'volume_ratio', 'momentum', 'bb_position']:
            if col in df_1h.columns:
                confluence_df[col] = df_1h[col]

        print(f"✅ Data loaded: {len(confluence_df)} candles")
        print(f"💰 Initial Capital: ${self.initial_capital:,.2f}")

        # Run simulation
        position = None
        trade_num = 0
        last_trade_time = None

        # Start later to catch golden pocket signals (which start around bar 260)
        for i in range(250, len(confluence_df)):
            row = confluence_df.iloc[i]
            current_price = row['close']
            current_time = confluence_df.index[i]
            current_date = current_time.date()

            # Update daily trade count
            if current_date not in self.daily_trades:
                self.daily_trades[current_date] = 0

            # ENTRY LOGIC
            if position is None:
                # Check cooldown
                if last_trade_time:
                    hours_since_last = (current_time - last_trade_time).total_seconds() / 3600
                    if hours_since_last < self.params['cooldown_hours']:
                        continue

                # Check daily limit
                if self.daily_trades[current_date] >= self.params['max_trades_per_day']:
                    continue

                # Check for any entry signal
                should_enter = False
                entry_reason = ""
                leverage = 1.0
                confidence = 0

                # PRIORITY 1: Check for golden pocket signals FIRST
                # Access Series elements directly (row is a Series from DataFrame.iloc[i])
                try:
                    gp_confirmations = row['gp_confirmations']
                    gp_confidence = row['gp_confidence']
                except (KeyError, AttributeError):
                    gp_confirmations = 0
                    gp_confidence = 0

                # Debug first 5 GP signals
                if i <= 100 and gp_confirmations >= 1:
                    logger.info(f"GP Signal at {current_time}: confirmations={gp_confirmations}, confidence={gp_confidence:.2%}")

                if gp_confirmations >= 1 and gp_confidence >= 0.40:
                    should_enter = True
                    entry_reason = "Golden Pocket"
                    confidence = gp_confidence
                    # Set leverage based on confirmations
                    if gp_confirmations >= 2:
                        leverage = self.params['leverage_multi_gp']  # 10x
                    else:
                        leverage = self.params['leverage_single_gp']  # 5x
                else:
                    # Check other signals
                    signals = self.check_entry_signals(row, confluence_df, i)
                    if signals['should_enter']:
                        should_enter = True
                        entry_reason = "Technical Signals"
                        confidence = signals['confidence']
                        leverage = signals['leverage']

                if should_enter:
                    trade_num += 1
                    self.daily_trades[current_date] += 1
                    last_trade_time = current_time

                    # ALWAYS use 60% of capital as per your requirements
                    position_size_pct = self.params['min_position_size']  # Fixed 60%
                    effective_position = position_size_pct * leverage
                    position_value = self.current_capital * position_size_pct

                    position = {
                        'trade_num': trade_num,
                        'entry_idx': i,
                        'entry_time': current_time,
                        'entry_price': current_price,
                        'position_size_pct': position_size_pct,
                        'leverage': leverage,
                        'effective_position': effective_position,
                        'position_value': position_value,
                        'shares': position_value / current_price,
                        'confidence': confidence,
                        'entry_reason': entry_reason,
                        'gp_confirmations': gp_confirmations,
                        'stop_loss': current_price * (1 - self.params['initial_stop_loss']),
                        'highest_price': current_price,
                        'stop_moved_to_be': False,
                        'trailing_active': False,
                        'partial_exits': [],
                        'remaining_shares': position_value / current_price
                    }

                    print(f"\n🚀 TRADE #{trade_num} OPENED")
                    print(f"  Time: {current_time}")
                    print(f"  Price: ${current_price:,.2f}")
                    print(f"  Entry Reason: {entry_reason}")
                    if entry_reason == "Golden Pocket":
                        print(f"  GP Confirmations: {gp_confirmations}")
                    print(f"  Confidence: {confidence:.0%}")
                    print(f"  Leverage: {leverage:.1f}x")
                    print(f"  Effective Position: {effective_position:.0%} of capital")

            # POSITION MANAGEMENT
            elif position is not None:
                price_change_pct = (current_price - position['entry_price']) / position['entry_price']

                # Update highest price
                if current_price > position['highest_price']:
                    position['highest_price'] = current_price

                # 1. BREAKEVEN STOP
                if not position['stop_moved_to_be'] and price_change_pct >= self.params['breakeven_trigger']:
                    position['stop_loss'] = position['entry_price'] * 1.001  # Slightly above entry
                    position['stop_moved_to_be'] = True
                    logger.info(f"  ✅ Stop moved to breakeven at {current_price:.2f}")

                # 2. TRAILING STOP
                if price_change_pct >= self.params['trailing_activation']:
                    position['trailing_active'] = True
                    trail_price = position['highest_price'] * (1 - self.params['trailing_distance'])
                    if trail_price > position['stop_loss']:
                        position['stop_loss'] = trail_price

                # 3. PARTIAL PROFIT TAKING
                remaining_pct = position['remaining_shares'] / position['shares']

                if remaining_pct > 0.75 and price_change_pct >= self.params['tp1_percent']:
                    # Take 25% at TP1
                    exit_shares = position['shares'] * self.params['tp1_size']
                    position['remaining_shares'] -= exit_shares
                    partial_pnl = exit_shares * (current_price - position['entry_price'])
                    self.current_capital += partial_pnl
                    position['partial_exits'].append({'level': 'TP1', 'price': current_price, 'pct': price_change_pct})
                    logger.info(f"  💰 TP1 hit: Took 25% at {price_change_pct:.2%}")

                elif remaining_pct > 0.50 and price_change_pct >= self.params['tp2_percent']:
                    # Take another 25% at TP2
                    exit_shares = position['shares'] * self.params['tp2_size']
                    position['remaining_shares'] -= exit_shares
                    partial_pnl = exit_shares * (current_price - position['entry_price'])
                    self.current_capital += partial_pnl
                    position['partial_exits'].append({'level': 'TP2', 'price': current_price, 'pct': price_change_pct})
                    logger.info(f"  💰 TP2 hit: Took 25% at {price_change_pct:.2%}")

                elif remaining_pct > 0.25 and price_change_pct >= self.params['tp3_percent']:
                    # Take another 25% at TP3
                    exit_shares = position['shares'] * self.params['tp3_size']
                    position['remaining_shares'] -= exit_shares
                    partial_pnl = exit_shares * (current_price - position['entry_price'])
                    self.current_capital += partial_pnl
                    position['partial_exits'].append({'level': 'TP3', 'price': current_price, 'pct': price_change_pct})
                    logger.info(f"  💰 TP3 hit: Took 25% at {price_change_pct:.2%}")

                # 4. EXIT CONDITIONS
                hit_stop = current_price <= position['stop_loss']
                hit_final_target = price_change_pct >= self.params['tp4_percent']
                end_of_data = i == len(confluence_df) - 1

                if hit_stop or hit_final_target or end_of_data:
                    # Exit remaining position
                    final_pnl = position['remaining_shares'] * (current_price - position['entry_price'])
                    self.current_capital += final_pnl

                    # Calculate total trade P&L
                    total_pnl = (current_price - position['entry_price']) * position['shares']

                    # Account for leverage in P&L calculation
                    leveraged_pnl_pct = price_change_pct * position['leverage']

                    exit_reason = 'STOP' if hit_stop else 'TARGET' if hit_final_target else 'END'

                    self.trades.append({
                        'trade_num': position['trade_num'],
                        'entry_time': position['entry_time'],
                        'exit_time': current_time,
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'pnl': total_pnl,
                        'pnl_pct': price_change_pct * 100,
                        'leveraged_pnl_pct': leveraged_pnl_pct,
                        'leverage': position['leverage'],
                        'confidence': position['confidence'],
                        'exit_reason': exit_reason,
                        'partial_exits': position['partial_exits'],
                        'stop_moved_to_be': position['stop_moved_to_be'],
                        'trailing_active': position['trailing_active']
                    })

                    print(f"\n📊 TRADE #{position['trade_num']} CLOSED")
                    print(f"  Exit Time: {current_time}")
                    print(f"  Exit Price: ${current_price:,.2f}")
                    print(f"  Exit Reason: {exit_reason}")
                    print(f"  P&L: {price_change_pct:.2%} ({leveraged_pnl_pct:.2%} with {position['leverage']:.1f}x)")
                    if position['partial_exits']:
                        print(f"  Partial Exits: {len(position['partial_exits'])}")
                    print(f"  Final Capital: ${self.current_capital:,.2f}")

                    position = None

            # Track equity
            self.equity_curve.append(self.current_capital)

        # Print results
        self.print_results()
        return self.trades

    def print_results(self):
        """
        Print comprehensive results
        """
        if not self.trades:
            print("\n❌ No trades executed")
            return

        print("\n" + "=" * 80)
        print("📊 BACKTEST RESULTS - ULTRA-AGGRESSIVE STRATEGY")
        print("=" * 80)

        # Calculate metrics
        total_trades = len(self.trades)
        winners = [t for t in self.trades if t['pnl'] > 0]
        losers = [t for t in self.trades if t['pnl'] <= 0]
        win_rate = len(winners) / total_trades * 100

        # Profit metrics
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital * 100

        # Leverage analysis
        avg_leverage = np.mean([t['leverage'] for t in self.trades])
        max_leverage = max(t['leverage'] for t in self.trades)

        # Protection analysis
        be_stops = sum(1 for t in self.trades if t['stop_moved_to_be'])
        trailing_stops = sum(1 for t in self.trades if t['trailing_active'])
        partial_exits = sum(1 for t in self.trades if t['partial_exits'])

        print(f"\n💰 PERFORMANCE:")
        print(f"  Initial Capital: ${self.initial_capital:,.2f}")
        print(f"  Final Capital: ${self.current_capital:,.2f}")
        print(f"  Total Return: {total_return:+.2f}%")

        print(f"\n📊 TRADE STATISTICS:")
        print(f"  Total Trades: {total_trades}")
        print(f"  Winners: {len(winners)} ({win_rate:.1f}%)")
        print(f"  Losers: {len(losers)}")
        if winners:
            print(f"  Avg Win: {np.mean([t['pnl_pct'] for t in winners]):.2f}%")
            print(f"  Best Trade: {max(t['pnl_pct'] for t in winners):.2f}%")
        if losers:
            print(f"  Avg Loss: {np.mean([t['pnl_pct'] for t in losers]):.2f}%")
            print(f"  Worst Trade: {min(t['pnl_pct'] for t in losers):.2f}%")

        print(f"\n⚡ LEVERAGE USAGE:")
        print(f"  Average Leverage: {avg_leverage:.1f}x")
        print(f"  Max Leverage Used: {max_leverage:.1f}x")
        leverage_dist = {}
        for t in self.trades:
            lev = f"{t['leverage']:.0f}x"
            leverage_dist[lev] = leverage_dist.get(lev, 0) + 1
        for lev, count in sorted(leverage_dist.items()):
            print(f"  {lev}: {count} trades ({count/total_trades*100:.1f}%)")

        print(f"\n🛡️ PROFIT PROTECTION:")
        print(f"  Breakeven Stops: {be_stops} ({be_stops/total_trades*100:.1f}%)")
        print(f"  Trailing Stops: {trailing_stops} ({trailing_stops/total_trades*100:.1f}%)")
        print(f"  Partial Profits: {partial_exits} ({partial_exits/total_trades*100:.1f}%)")

        print(f"\n📅 DAILY ACTIVITY:")
        for date, count in sorted(self.daily_trades.items())[-5:]:
            print(f"  {date}: {count} trades")

        print(f"\n📝 LAST 5 TRADES:")
        for t in self.trades[-5:]:
            print(f"  {t['entry_time'].strftime('%m-%d %H:%M')}: "
                  f"{t['pnl_pct']:+.2f}% ({t['leverage']:.0f}x) - {t['exit_reason']}")

        print("\n" + "=" * 80)


async def main():
    """
    Run ultra-aggressive strategy backtest
    """
    print("🔥 ULTRA-AGGRESSIVE STRATEGY BACKTEST")
    print("Maximum trade frequency with profit protection")

    backtester = UltraAggressiveStrategy(initial_capital=10000)
    trades = await backtester.run_backtest(days=30)

    if trades:
        print(f"\n✅ Executed {len(trades)} trades with ultra-aggressive strategy")
    else:
        print("\n⚠️ No trades executed - parameters may still be too conservative")


if __name__ == "__main__":
    asyncio.run(main())