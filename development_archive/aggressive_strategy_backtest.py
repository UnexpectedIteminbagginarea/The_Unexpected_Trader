"""
Aggressive Trading Strategy with 5x Leverage and Trailing Profits
Always lock in profits - never let winners turn into losers
"""
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.historical_data_fetcher import HistoricalDataFetcher
from core.multi_timeframe_golden_pocket import MultiTimeframeGoldenPocket


class AggressiveStrategyBacktest:
    """
    Aggressive strategy with 5x leverage and strict profit protection
    """

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.data_fetcher = HistoricalDataFetcher()
        self.gp_detector = MultiTimeframeGoldenPocket()

        # AGGRESSIVE PARAMETERS
        self.params = {
            # Leverage based on confidence
            'leverage_low_confidence': 1.0,      # 1x for low confidence
            'leverage_medium_confidence': 2.0,   # 2x for medium confidence
            'leverage_high_confidence': 5.0,     # 5x for high confidence (multi-TF)

            # Position sizing (% of capital before leverage)
            'base_position_size': 0.20,          # 20% base (becomes 100% with 5x)

            # Initial stops
            'initial_stop_loss': 0.04,           # 4% initial stop (tighter with leverage)

            # Profit taking levels
            'tp1_percent': 0.02,                 # 2% - quick scalp
            'tp2_percent': 0.04,                 # 4% - solid gain
            'tp3_percent': 0.06,                 # 6% - good move
            'tp4_percent': 0.10,                 # 10% - excellent move

            # Profit protection
            'breakeven_trigger': 0.015,          # Move stop to breakeven at 1.5%
            'trailing_activation': 0.03,         # Start trailing at 3%
            'trailing_distance': 0.015,          # Trail 1.5% below high

            # Confidence thresholds (MORE AGGRESSIVE)
            'high_confidence_threshold': 0.70,   # 70%+ = high confidence (5x)
            'medium_confidence_threshold': 0.60, # 60-70% = medium (2x)
            'low_confidence_threshold': 0.55,    # 55-60% = low (1x)
        }

        self.trades = []
        self.equity_curve = []

    async def run_backtest(self, days: int = 30):
        """
        Run aggressive backtest with trailing profits
        """
        print("=" * 80)
        print("AGGRESSIVE STRATEGY BACKTEST - 5X LEVERAGE")
        print("=" * 80)
        print("\n📋 STRATEGY RULES:")
        print("  • 5x leverage on high-confidence trades (multi-TF golden pockets)")
        print("  • 2x leverage on medium-confidence trades")
        print("  • 1x leverage on low-confidence trades")
        print("  • Move stop to breakeven at +1.5%")
        print("  • Trail stop 1.5% below high after +3%")
        print("  • Take partial profits at 2%, 4%, 6%, 10%")
        print("  • NEVER let winners become losers")

        # Fetch data
        end_date = '2025-10-29'
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=days)).strftime('%Y-%m-%d')

        print(f"\n📊 Fetching {days} days of data...")
        df_1h = await self.data_fetcher.fetch_btc_historical_data(start_date, end_date, '1h')

        if df_1h.empty:
            print("Failed to fetch data")
            return

        # Detect golden pockets
        timeframe_data = self.gp_detector.detect_all_timeframes(df_1h)
        confluence_df = self.gp_detector.find_confluence_zones(timeframe_data)

        print(f"✅ Data loaded: {len(confluence_df)} candles")
        print(f"💰 Initial Capital: ${self.initial_capital:,.2f}")

        # Run simulation
        position = None
        trade_num = 0

        for i in range(50, len(confluence_df)):
            row = confluence_df.iloc[i]
            current_price = row['close']

            # ENTRY LOGIC
            if position is None:
                # Check for golden pocket entry
                if row['gp_confirmations'] >= 1:
                    confidence = row['gp_confidence']

                    # Only enter with medium+ confidence
                    if confidence >= self.params['medium_confidence_threshold']:
                        trade_num += 1

                        # Determine leverage based on confidence
                        if confidence >= self.params['high_confidence_threshold']:
                            leverage = self.params['leverage_high_confidence']
                            confidence_level = 'HIGH'
                        elif confidence >= self.params['medium_confidence_threshold']:
                            leverage = self.params['leverage_medium_confidence']
                            confidence_level = 'MEDIUM'
                        else:
                            leverage = self.params['leverage_low_confidence']
                            confidence_level = 'LOW'

                        # Calculate position with leverage
                        base_position = self.current_capital * self.params['base_position_size']
                        leveraged_position = base_position * leverage
                        shares = leveraged_position / current_price

                        position = {
                            'trade_num': trade_num,
                            'entry_idx': i,
                            'entry_time': confluence_df.index[i],
                            'entry_price': current_price,
                            'shares': shares,
                            'base_position': base_position,
                            'leveraged_position': leveraged_position,
                            'leverage': leverage,
                            'confidence': confidence,
                            'confidence_level': confidence_level,
                            'gp_confirmations': row['gp_confirmations'],

                            # Initial stop
                            'stop_loss': current_price * (1 - self.params['initial_stop_loss']),
                            'initial_stop': current_price * (1 - self.params['initial_stop_loss']),

                            # Profit targets
                            'tp1': current_price * (1 + self.params['tp1_percent']),
                            'tp2': current_price * (1 + self.params['tp2_percent']),
                            'tp3': current_price * (1 + self.params['tp3_percent']),
                            'tp4': current_price * (1 + self.params['tp4_percent']),

                            # Tracking
                            'highest_price': current_price,
                            'lowest_price': current_price,
                            'stop_moved_to_breakeven': False,
                            'trailing_activated': False,
                            'partial_exits': [],
                            'remaining_shares': shares
                        }

                        print(f"\n{'='*60}")
                        print(f"🔥 TRADE #{trade_num} OPENED - {confidence_level} CONFIDENCE")
                        print(f"Entry: ${current_price:,.2f}")
                        print(f"Leverage: {leverage}x")
                        print(f"Position: ${leveraged_position:,.2f} (${base_position:,.2f} x {leverage}x)")
                        print(f"Initial Stop: ${position['stop_loss']:,.2f} (-{self.params['initial_stop_loss']:.1%})")
                        print(f"Targets: TP1=${position['tp1']:,.0f} (+2%), TP2=${position['tp2']:,.0f} (+4%), "
                              f"TP3=${position['tp3']:,.0f} (+6%), TP4=${position['tp4']:,.0f} (+10%)")

            # POSITION MANAGEMENT
            elif position is not None:
                # Update highest/lowest price
                position['highest_price'] = max(position['highest_price'], current_price)
                position['lowest_price'] = min(position['lowest_price'], current_price)

                # Calculate current P&L
                price_change_pct = (current_price - position['entry_price']) / position['entry_price']
                unrealized_pnl = (current_price - position['entry_price']) * position['remaining_shares']
                unrealized_pnl_pct = price_change_pct * 100

                # PROFIT PROTECTION LOGIC

                # 1. Move stop to breakeven when up 1.5%
                if not position['stop_moved_to_breakeven'] and price_change_pct >= self.params['breakeven_trigger']:
                    position['stop_loss'] = position['entry_price'] * 1.001  # Slightly above entry
                    position['stop_moved_to_breakeven'] = True
                    print(f"  ✅ Stop moved to BREAKEVEN at ${position['stop_loss']:,.2f}")

                # 2. Activate trailing stop at 3%
                if not position['trailing_activated'] and price_change_pct >= self.params['trailing_activation']:
                    position['trailing_activated'] = True
                    position['stop_loss'] = current_price * (1 - self.params['trailing_distance'])
                    print(f"  ✅ TRAILING STOP activated at ${position['stop_loss']:,.2f}")

                # 3. Update trailing stop if active
                if position['trailing_activated']:
                    new_trailing_stop = position['highest_price'] * (1 - self.params['trailing_distance'])
                    if new_trailing_stop > position['stop_loss']:
                        position['stop_loss'] = new_trailing_stop
                        print(f"  📈 Trailing stop updated to ${position['stop_loss']:,.2f}")

                # PARTIAL PROFIT TAKING
                remaining_pct = position['remaining_shares'] / position['shares']

                # Take 25% at each target
                if current_price >= position['tp1'] and 'tp1' not in position['partial_exits']:
                    exit_shares = position['shares'] * 0.25
                    exit_pnl = (current_price - position['entry_price']) * exit_shares
                    position['remaining_shares'] -= exit_shares
                    position['partial_exits'].append('tp1')
                    self.current_capital += exit_pnl
                    print(f"  💰 TP1 HIT! Took 25% profit at ${current_price:,.2f} (+{self.params['tp1_percent']:.1%})")

                if current_price >= position['tp2'] and 'tp2' not in position['partial_exits']:
                    exit_shares = position['shares'] * 0.25
                    exit_pnl = (current_price - position['entry_price']) * exit_shares
                    position['remaining_shares'] -= exit_shares
                    position['partial_exits'].append('tp2')
                    self.current_capital += exit_pnl
                    print(f"  💰 TP2 HIT! Took 25% profit at ${current_price:,.2f} (+{self.params['tp2_percent']:.1%})")

                if current_price >= position['tp3'] and 'tp3' not in position['partial_exits']:
                    exit_shares = position['shares'] * 0.25
                    exit_pnl = (current_price - position['entry_price']) * exit_shares
                    position['remaining_shares'] -= exit_shares
                    position['partial_exits'].append('tp3')
                    self.current_capital += exit_pnl
                    print(f"  💰 TP3 HIT! Took 25% profit at ${current_price:,.2f} (+{self.params['tp3_percent']:.1%})")

                if current_price >= position['tp4'] and 'tp4' not in position['partial_exits']:
                    # Exit remaining position at TP4
                    exit_shares = position['remaining_shares']
                    exit_pnl = (current_price - position['entry_price']) * exit_shares
                    position['remaining_shares'] = 0
                    position['partial_exits'].append('tp4')
                    self.current_capital += exit_pnl
                    print(f"  🎯 TP4 HIT! Closed remaining position at ${current_price:,.2f} (+{self.params['tp4_percent']:.1%})")

                # EXIT CONDITIONS
                hit_stop = current_price <= position['stop_loss']
                no_shares_left = position['remaining_shares'] <= 0
                end_of_data = i == len(confluence_df) - 1

                if hit_stop or no_shares_left or end_of_data:
                    # Close any remaining position
                    if position['remaining_shares'] > 0:
                        final_pnl = (current_price - position['entry_price']) * position['remaining_shares']
                        self.current_capital += final_pnl

                    # Calculate total trade P&L
                    total_shares_exited = position['shares'] - position['remaining_shares']
                    avg_exit_price = current_price  # Simplified
                    total_pnl = (avg_exit_price - position['entry_price']) * position['shares']
                    total_pnl_pct = ((avg_exit_price - position['entry_price']) / position['entry_price']) * 100

                    # Determine exit reason
                    if hit_stop:
                        if position['stop_moved_to_breakeven']:
                            exit_reason = 'BREAKEVEN_STOP'
                        elif position['trailing_activated']:
                            exit_reason = 'TRAILING_STOP'
                        else:
                            exit_reason = 'INITIAL_STOP'
                    elif no_shares_left:
                        exit_reason = 'ALL_TARGETS_HIT'
                    else:
                        exit_reason = 'END_OF_DATA'

                    # Record trade
                    self.trades.append({
                        'trade_num': position['trade_num'],
                        'entry_time': position['entry_time'],
                        'exit_time': confluence_df.index[i],
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'leverage': position['leverage'],
                        'confidence_level': position['confidence_level'],
                        'pnl': total_pnl,
                        'pnl_pct': total_pnl_pct,
                        'exit_reason': exit_reason,
                        'partial_exits': position['partial_exits'],
                        'highest_price': position['highest_price'],
                        'max_profit_pct': ((position['highest_price'] - position['entry_price']) / position['entry_price']) * 100
                    })

                    print(f"\n🏁 TRADE #{position['trade_num']} CLOSED")
                    print(f"Exit: ${current_price:,.2f}")
                    print(f"Exit Reason: {exit_reason}")
                    print(f"P&L: ${total_pnl:,.2f} ({total_pnl_pct:+.2f}%)")
                    print(f"Max Profit: {self.trades[-1]['max_profit_pct']:+.2f}%")
                    print(f"Partial Exits: {position['partial_exits']}")
                    print(f"Final Capital: ${self.current_capital:,.2f}")

                    position = None

            # Track equity
            self.equity_curve.append(self.current_capital)

        return self.analyze_results()

    def analyze_results(self) -> Dict:
        """
        Analyze backtest results
        """
        if not self.trades:
            return {'total_trades': 0, 'message': 'No trades executed'}

        # Calculate metrics
        df_trades = pd.DataFrame(self.trades)

        total_trades = len(self.trades)
        winners = df_trades[df_trades['pnl'] > 0]
        losers = df_trades[df_trades['pnl'] <= 0]

        win_rate = len(winners) / total_trades * 100 if total_trades > 0 else 0

        # Return metrics
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital * 100

        # Sharpe ratio
        if len(self.equity_curve) > 1:
            returns = pd.Series(self.equity_curve).pct_change().dropna()
            sharpe = np.sqrt(365 * 24) * (returns.mean() / returns.std()) if returns.std() > 0 else 0
        else:
            sharpe = 0

        # Max drawdown
        equity = pd.Series(self.equity_curve)
        peaks = equity.expanding().max()
        drawdowns = (equity - peaks) / peaks * 100
        max_drawdown = abs(drawdowns.min()) if len(drawdowns) > 0 else 0

        results = {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'winners': len(winners),
            'losers': len(losers),
            'total_return': total_return,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'avg_win': winners['pnl_pct'].mean() if len(winners) > 0 else 0,
            'avg_loss': losers['pnl_pct'].mean() if len(losers) > 0 else 0,
            'best_trade': df_trades['pnl_pct'].max() if total_trades > 0 else 0,
            'worst_trade': df_trades['pnl_pct'].min() if total_trades > 0 else 0,
            'final_capital': self.current_capital,
            'exit_reasons': df_trades['exit_reason'].value_counts().to_dict() if total_trades > 0 else {}
        }

        return results

    def print_results(self, results: Dict):
        """
        Print formatted results
        """
        print("\n" + "=" * 80)
        print("📈 AGGRESSIVE STRATEGY RESULTS")
        print("=" * 80)

        print(f"\n💰 PERFORMANCE:")
        print(f"  Initial Capital: ${self.initial_capital:,.2f}")
        print(f"  Final Capital: ${results['final_capital']:,.2f}")
        print(f"  Total Return: {results['total_return']:+.2f}%")
        print(f"  Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: {results['max_drawdown']:.1f}%")

        print(f"\n📊 TRADE STATISTICS:")
        print(f"  Total Trades: {results['total_trades']}")
        print(f"  Winners: {results['winners']} ({results['win_rate']:.1f}%)")
        print(f"  Losers: {results['losers']}")
        print(f"  Average Win: {results['avg_win']:+.2f}%")
        print(f"  Average Loss: {results['avg_loss']:+.2f}%")
        print(f"  Best Trade: {results['best_trade']:+.2f}%")
        print(f"  Worst Trade: {results['worst_trade']:+.2f}%")

        print(f"\n🚪 EXIT BREAKDOWN:")
        for reason, count in results['exit_reasons'].items():
            print(f"  {reason}: {count}")

        print("\n" + "=" * 80)


async def main():
    """
    Run aggressive strategy backtest
    """
    print("🚀 AGGRESSIVE TRADING STRATEGY WITH 5X LEVERAGE")
    print("=" * 80)

    # Test different periods
    for days in [30, 60]:
        print(f"\n📅 Testing {days} days...")

        backtester = AggressiveStrategyBacktest(initial_capital=10000)
        results = await backtester.run_backtest(days)

        if results.get('total_trades', 0) > 0:
            backtester.print_results(results)

    print("\n✅ Aggressive Strategy Backtest Complete!")


if __name__ == "__main__":
    asyncio.run(main())