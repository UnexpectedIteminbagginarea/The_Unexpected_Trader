"""
Backtest with Multi-Timeframe Golden Pocket Detection
Test the improved strategy with real data
"""
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
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


class MultiTimeframeGPBacktest:
    """
    Backtest using multi-timeframe golden pocket detection
    """

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.data_fetcher = HistoricalDataFetcher()
        self.gp_detector = MultiTimeframeGoldenPocket()

        # Optimized parameters from our grid search
        self.params = {
            'unified_score_buy': 55,
            'unified_score_sell': 35,
            'confidence_threshold': 0.70,
            'stop_loss': 0.06,          # 6% stop (wider for crypto)
            'take_profit': 0.12,         # 12% target
            'max_position_size': 0.60,   # 60% of capital max
            'min_risk_reward': 1.5       # Minimum 1.5:1 R/R
        }

        self.trades = []
        self.equity_curve = []

    async def run_backtest(self, days: int = 30):
        """
        Run backtest with multi-timeframe golden pocket strategy
        """
        print("=" * 80)
        print("MULTI-TIMEFRAME GOLDEN POCKET BACKTEST")
        print("=" * 80)

        # Fetch data
        end_date = '2025-10-29'
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=days)).strftime('%Y-%m-%d')

        print(f"\n📊 Fetching {days} days of data...")
        df_1h = await self.data_fetcher.fetch_btc_historical_data(start_date, end_date, '1h')

        if df_1h.empty:
            print("Failed to fetch data")
            return

        print(f"✅ Data loaded: {len(df_1h)} candles")
        print(f"Price range: ${df_1h['close'].min():,.0f} - ${df_1h['close'].max():,.0f}")

        # Detect golden pockets across timeframes
        print("\n🔍 Detecting multi-timeframe golden pockets...")
        timeframe_data = self.gp_detector.detect_all_timeframes(df_1h)

        # Find confluence zones
        confluence_df = self.gp_detector.find_confluence_zones(timeframe_data)

        # Count golden pocket opportunities
        gp_1h = confluence_df['gp_1h'].sum()
        gp_with_confluence = (confluence_df['gp_confirmations'] >= 2).sum()

        print(f"✅ Golden Pockets found:")
        print(f"  1H only: {gp_1h}")
        print(f"  With 4H/Daily confluence: {gp_with_confluence}")

        # Run simulation
        print("\n💰 Running backtest simulation...")
        position = None

        for i in range(50, len(confluence_df)):  # Start after warmup
            row = confluence_df.iloc[i]
            current_price = row['close']

            # ENTRY LOGIC
            if position is None:
                # Check for golden pocket - more aggressive entry
                if row['gp_confirmations'] >= 1:  # At least 1 timeframe
                    # Calculate position based on confidence
                    confidence = row['gp_confidence']

                    # Additional entry filters
                    entry_score = self.calculate_entry_score(row)

                    # Lower threshold for entry but scale position by confidence
                    # Single TF: 60% confidence, Double: 75%, Triple: 90%
                    if confidence >= 0.55 or row['gp_confirmations'] >= 2:
                        # Calculate position size
                        position_size = self.current_capital * self.params['max_position_size'] * confidence

                        # Open position
                        position = {
                            'entry_idx': i,
                            'entry_time': confluence_df.index[i],
                            'entry_price': current_price,
                            'size': position_size,
                            'shares': position_size / current_price,
                            'confidence': confidence,
                            'gp_confirmations': row['gp_confirmations'],
                            'stop_loss': current_price * (1 - self.params['stop_loss']),
                            'take_profit': current_price * (1 + self.params['take_profit'])
                        }

                        logger.info(f"ENTRY at {position['entry_time']}: ${current_price:,.0f} "
                                  f"(Confirmations: {row['gp_confirmations']}, "
                                  f"Confidence: {confidence:.0%})")

            # EXIT LOGIC
            elif position is not None:
                # Check exit conditions
                hit_stop = current_price <= position['stop_loss']
                hit_target = current_price >= position['take_profit']

                # Also exit if confidence drops significantly
                exit_signal = row.get('unified_score', 50) < self.params['unified_score_sell']

                if hit_stop or hit_target or exit_signal or i == len(confluence_df) - 1:
                    # Calculate P&L
                    exit_price = current_price
                    pnl = (exit_price - position['entry_price']) * position['shares']
                    pnl_pct = (exit_price - position['entry_price']) / position['entry_price'] * 100

                    # Update capital
                    self.current_capital += pnl

                    # Record trade
                    self.trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': confluence_df.index[i],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'confidence': position['confidence'],
                        'gp_confirmations': position['gp_confirmations'],
                        'exit_reason': 'stop_loss' if hit_stop else 'take_profit' if hit_target else 'signal'
                    })

                    logger.info(f"EXIT at {confluence_df.index[i]}: ${exit_price:,.0f} "
                              f"(P&L: {pnl_pct:+.2f}%, Reason: {self.trades[-1]['exit_reason']})")

                    position = None

            # Track equity
            current_equity = self.current_capital
            if position:
                current_equity += position['shares'] * current_price
            self.equity_curve.append(current_equity)

        # Calculate results
        return self.analyze_results(confluence_df)

    def calculate_entry_score(self, row: pd.Series) -> float:
        """
        Calculate additional entry score based on technical factors
        """
        score = 50  # Base score

        # RSI factor
        if 'rsi' in row:
            if 30 <= row['rsi'] <= 70:
                score += 10
            else:
                score -= 10

        # Volume factor
        if 'volume_ratio' in row and pd.notna(row['volume_ratio']):
            if row['volume_ratio'] > 1.2:  # Above average volume
                score += 10

        # Trend alignment
        if row.get('trend') == 'up':
            score += 15

        return score

    def analyze_results(self, df: pd.DataFrame) -> Dict:
        """
        Analyze backtest results
        """
        if not self.trades:
            return {
                'total_trades': 0,
                'message': 'No trades executed'
            }

        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]

        win_rate = len(winning_trades) / total_trades * 100

        # Golden pocket specific analysis
        gp_trades = [t for t in self.trades if t['gp_confirmations'] >= 1]
        gp_confluence_trades = [t for t in self.trades if t['gp_confirmations'] >= 2]

        gp_win_rate = 0
        if gp_trades:
            gp_wins = [t for t in gp_trades if t['pnl'] > 0]
            gp_win_rate = len(gp_wins) / len(gp_trades) * 100

        confluence_win_rate = 0
        if gp_confluence_trades:
            confluence_wins = [t for t in gp_confluence_trades if t['pnl'] > 0]
            confluence_win_rate = len(confluence_wins) / len(gp_confluence_trades) * 100

        # Returns
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital * 100

        # Calculate Sharpe ratio
        if self.equity_curve:
            returns = pd.Series(self.equity_curve).pct_change().dropna()
            if len(returns) > 0 and returns.std() > 0:
                sharpe = np.sqrt(365 * 24) * (returns.mean() / returns.std())
            else:
                sharpe = 0
        else:
            sharpe = 0

        # Max drawdown
        if self.equity_curve:
            equity = pd.Series(self.equity_curve)
            peaks = equity.expanding().max()
            drawdowns = (equity - peaks) / peaks * 100
            max_drawdown = abs(drawdowns.min())
        else:
            max_drawdown = 0

        # Average metrics
        avg_win = np.mean([t['pnl_pct'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losing_trades]) if losing_trades else 0
        best_trade = max(t['pnl_pct'] for t in self.trades) if self.trades else 0
        worst_trade = min(t['pnl_pct'] for t in self.trades) if self.trades else 0

        # Profit factor
        gross_profit = sum(t['pnl'] for t in winning_trades) if winning_trades else 0
        gross_loss = abs(sum(t['pnl'] for t in losing_trades)) if losing_trades else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        results = {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_return': total_return,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'profit_factor': profit_factor,
            'gp_trades': len(gp_trades),
            'gp_win_rate': gp_win_rate,
            'confluence_trades': len(gp_confluence_trades),
            'confluence_win_rate': confluence_win_rate,
            'final_capital': self.current_capital
        }

        return results

    def print_results(self, results: Dict):
        """
        Print formatted results
        """
        print("\n" + "=" * 80)
        print("📈 BACKTEST RESULTS - MULTI-TIMEFRAME GOLDEN POCKETS")
        print("=" * 80)

        print(f"\n💰 PERFORMANCE:")
        print(f"  Initial Capital: ${self.initial_capital:,.2f}")
        print(f"  Final Capital: ${results['final_capital']:,.2f}")
        print(f"  Total Return: {results['total_return']:+.2f}%")
        print(f"  Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: {results['max_drawdown']:.1f}%")
        print(f"  Profit Factor: {results['profit_factor']:.2f}")

        print(f"\n📊 TRADE STATISTICS:")
        print(f"  Total Trades: {results['total_trades']}")
        print(f"  Win Rate: {results['win_rate']:.1f}%")
        print(f"  Average Win: {results['avg_win']:+.2f}%")
        print(f"  Average Loss: {results['avg_loss']:+.2f}%")
        print(f"  Best Trade: {results['best_trade']:+.2f}%")
        print(f"  Worst Trade: {results['worst_trade']:+.2f}%")

        print(f"\n✨ GOLDEN POCKET ANALYSIS:")
        print(f"  GP Trades: {results['gp_trades']}")
        print(f"  GP Win Rate: {results['gp_win_rate']:.1f}%")
        print(f"  Multi-TF Confluence Trades: {results['confluence_trades']}")
        print(f"  Confluence Win Rate: {results['confluence_win_rate']:.1f}%")

        # Show recent trades
        if self.trades:
            print(f"\n📝 LAST 5 TRADES:")
            for trade in self.trades[-5:]:
                print(f"  {trade['entry_time'].strftime('%m-%d %H:%M')} → "
                      f"{trade['exit_time'].strftime('%m-%d %H:%M')}: "
                      f"{trade['pnl_pct']:+.2f}% "
                      f"(Confirmations: {trade['gp_confirmations']})")

        print("\n" + "=" * 80)


async def main():
    """
    Run multi-timeframe golden pocket backtest
    """
    # Test different periods
    test_periods = [
        {'days': 30, 'name': 'Last Month'},
        {'days': 60, 'name': '2 Months'}
    ]

    all_results = []

    for period in test_periods:
        print(f"\n🗓️ Testing: {period['name']} ({period['days']} days)")
        print("-" * 40)

        backtester = MultiTimeframeGPBacktest(initial_capital=10000)
        results = await backtester.run_backtest(period['days'])

        if results and results.get('total_trades', 0) > 0:
            backtester.print_results(results)
            all_results.append({
                'period': period['name'],
                'results': results
            })

    # Summary comparison
    if all_results:
        print("\n" + "=" * 80)
        print("📊 COMPARISON SUMMARY")
        print("=" * 80)

        for item in all_results:
            r = item['results']
            print(f"\n{item['period']}:")
            print(f"  Return: {r['total_return']:+.2f}%")
            print(f"  Win Rate: {r['win_rate']:.1f}%")
            print(f"  GP Win Rate: {r['gp_win_rate']:.1f}%")
            print(f"  Confluence Win Rate: {r['confluence_win_rate']:.1f}%")
            print(f"  Sharpe: {r['sharpe_ratio']:.2f}")

    print("\n✅ Multi-Timeframe Backtest Complete!")


if __name__ == "__main__":
    asyncio.run(main())