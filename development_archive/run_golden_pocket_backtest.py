"""
Comprehensive Golden Pocket Backtest with Real BTC Data
Tests our complete strategy with actual market data
"""
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json
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
from core.technical_analyzer import TechnicalAnalyzer


class GoldenPocketBacktest:
    """
    Complete backtest of our golden pocket + unified scoring strategy
    """

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.data_fetcher = HistoricalDataFetcher()
        self.technical = TechnicalAnalyzer()

        # Risk management parameters
        self.risk_params = {
            'max_position_size': 0.5,    # Max 50% of capital per trade
            'stop_loss': 0.05,            # 5% stop loss
            'take_profit': 0.10,          # 10% take profit
            'min_risk_reward': 2.0,       # Minimum 2:1 risk/reward
            'max_drawdown': 0.15,         # Stop trading at 15% drawdown
        }

        # Strategy parameters
        self.strategy_params = {
            'entry_score_threshold': 60,   # Minimum unified score
            'golden_pocket_override': 55,  # Lower threshold with golden pocket
            'min_confidence': 0.65,         # Minimum confidence
            'gp_confidence_boost': 0.80,   # Confidence when in golden pocket
        }

        # Track performance
        self.trades = []
        self.equity_curve = []
        self.current_capital = initial_capital

    async def fetch_data(self, days_back: int = 30) -> pd.DataFrame:
        """
        Fetch real historical data for backtesting
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        logger.info(f"Fetching {days_back} days of real BTC data...")
        df = await self.data_fetcher.create_backtest_dataset(start_date, end_date)

        if df.empty:
            logger.error("Failed to fetch data")
            return pd.DataFrame()

        logger.info(f"Fetched {len(df)} data points from {df.index.min()} to {df.index.max()}")
        logger.info(f"BTC price range: ${df['close'].min():,.0f} - ${df['close'].max():,.0f}")

        return df

    def calculate_golden_pockets(self, df: pd.DataFrame, lookback: int = 50) -> pd.DataFrame:
        """
        Calculate Fibonacci levels and golden pockets for each candle
        """
        df['swing_high'] = df['high'].rolling(lookback).max()
        df['swing_low'] = df['low'].rolling(lookback).min()

        # Calculate Fibonacci levels
        df['fib_range'] = df['swing_high'] - df['swing_low']
        df['fib_0'] = df['swing_high']  # 0% retracement
        df['fib_236'] = df['swing_high'] - (df['fib_range'] * 0.236)
        df['fib_382'] = df['swing_high'] - (df['fib_range'] * 0.382)
        df['fib_500'] = df['swing_high'] - (df['fib_range'] * 0.500)
        df['fib_618'] = df['swing_high'] - (df['fib_range'] * 0.618)  # Golden pocket top
        df['fib_650'] = df['swing_high'] - (df['fib_range'] * 0.650)  # Golden pocket bottom
        df['fib_786'] = df['swing_high'] - (df['fib_range'] * 0.786)
        df['fib_100'] = df['swing_low']  # 100% retracement

        # Check if price is in golden pocket
        df['in_golden_pocket'] = (
            (df['close'] <= df['fib_618']) &
            (df['close'] >= df['fib_650'])
        )

        return df

    def calculate_unified_score(self, row: pd.Series) -> Tuple[float, float]:
        """
        Calculate unified score and confidence for a data point
        """
        # Simplified scoring based on available data
        score_components = {}

        # 1. Technical score (RSI, trend)
        if 'rsi' in row and pd.notna(row['rsi']):
            # Bullish if RSI between 30-70 (not overbought/oversold)
            if 30 <= row['rsi'] <= 70:
                score_components['technical'] = 60 + (70 - row['rsi']) / 2
            else:
                score_components['technical'] = 40

        # 2. Momentum score
        if 'price_change_5' in row and pd.notna(row['price_change_5']):
            # Positive momentum is bullish
            momentum = row['price_change_5']
            score_components['momentum'] = 50 + (momentum * 500)  # Scale to 0-100

        # 3. Volume score
        if 'volume_ratio' in row and pd.notna(row['volume_ratio']):
            # High volume = stronger signal
            vol_ratio = row.get('volume_ratio', 1.0)
            score_components['volume'] = min(100, 50 * vol_ratio)

        # 4. Golden pocket bonus
        if row.get('in_golden_pocket', False):
            score_components['golden_pocket'] = 80  # High score for golden pocket

        # Calculate unified score (average of components)
        if score_components:
            unified_score = np.mean(list(score_components.values()))
        else:
            unified_score = 50  # Neutral if no data

        # Calculate confidence based on data availability and alignment
        available_signals = len(score_components)
        max_signals = 4
        data_confidence = available_signals / max_signals

        # Check signal alignment (all bullish or all bearish)
        if score_components:
            signal_std = np.std(list(score_components.values()))
            alignment_confidence = 1 - (signal_std / 50)  # Lower std = higher confidence
        else:
            alignment_confidence = 0.5

        confidence = (data_confidence * 0.5 + alignment_confidence * 0.5)

        # Golden pocket confidence boost
        if row.get('in_golden_pocket', False) and unified_score > self.strategy_params['golden_pocket_override']:
            confidence = max(confidence, self.strategy_params['gp_confidence_boost'])

        return unified_score, confidence

    def execute_backtest(self, df: pd.DataFrame) -> Dict:
        """
        Run the backtest on historical data
        """
        position = None
        results = {
            'trades': [],
            'equity_curve': [self.initial_capital],
            'dates': [df.index[0]]
        }

        for i in range(50, len(df)):  # Start at 50 to have enough history
            row = df.iloc[i]
            current_price = row['close']

            # Calculate signals
            unified_score, confidence = self.calculate_unified_score(row)

            # Check for entry
            if position is None:
                # Entry conditions
                should_enter = (
                    (unified_score > self.strategy_params['entry_score_threshold'] and
                     confidence > self.strategy_params['min_confidence']) or
                    (row.get('in_golden_pocket', False) and
                     unified_score > self.strategy_params['golden_pocket_override'] and
                     confidence > 0.6)
                )

                if should_enter and self.current_capital > 0:
                    # Calculate position size based on confidence
                    position_size = self.current_capital * self.risk_params['max_position_size'] * confidence

                    position = {
                        'entry_price': current_price,
                        'entry_time': df.index[i],
                        'size': position_size,
                        'shares': position_size / current_price,
                        'unified_score': unified_score,
                        'confidence': confidence,
                        'in_golden_pocket': row.get('in_golden_pocket', False),
                        'stop_loss': current_price * (1 - self.risk_params['stop_loss']),
                        'take_profit': current_price * (1 + self.risk_params['take_profit'])
                    }

                    logger.info(f"ENTRY: {position['entry_time'].strftime('%Y-%m-%d %H:%M')} "
                              f"@ ${current_price:,.2f} "
                              f"(Score: {unified_score:.1f}, Confidence: {confidence:.2%}, "
                              f"GP: {position['in_golden_pocket']})")

            # Check for exit
            elif position is not None:
                # Exit conditions
                hit_stop_loss = current_price <= position['stop_loss']
                hit_take_profit = current_price >= position['take_profit']
                score_flip = unified_score < 40  # Bearish flip

                if hit_stop_loss or hit_take_profit or score_flip or i == len(df) - 1:
                    # Calculate P&L
                    exit_value = position['shares'] * current_price
                    entry_value = position['size']
                    pnl = exit_value - entry_value
                    pnl_pct = (pnl / entry_value) * 100

                    # Update capital
                    self.current_capital += pnl

                    # Record trade
                    trade = {
                        'entry_time': position['entry_time'],
                        'exit_time': df.index[i],
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'unified_score': position['unified_score'],
                        'confidence': position['confidence'],
                        'in_golden_pocket': position['in_golden_pocket'],
                        'exit_reason': 'stop_loss' if hit_stop_loss else 'take_profit' if hit_take_profit else 'signal'
                    }
                    results['trades'].append(trade)

                    logger.info(f"EXIT: {trade['exit_time'].strftime('%Y-%m-%d %H:%M')} "
                              f"@ ${current_price:,.2f} "
                              f"(P&L: {pnl_pct:+.2f}%, Reason: {trade['exit_reason']})")

                    position = None

            # Update equity curve
            current_value = self.current_capital
            if position:
                current_value += position['shares'] * current_price
            results['equity_curve'].append(current_value)
            results['dates'].append(df.index[i])

        return results

    def analyze_results(self, results: Dict) -> Dict:
        """
        Analyze backtest results and calculate metrics
        """
        trades = results['trades']
        equity = np.array(results['equity_curve'])

        if not trades:
            return {
                'error': 'No trades executed',
                'total_trades': 0
            }

        # Calculate metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]

        # Golden pocket analysis
        gp_trades = [t for t in trades if t['in_golden_pocket']]
        gp_winning = [t for t in gp_trades if t['pnl'] > 0]

        # Calculate returns
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital * 100
        returns = np.diff(equity) / equity[:-1]

        # Sharpe ratio (annualized)
        if len(returns) > 0 and np.std(returns) > 0:
            sharpe = np.sqrt(365 * 24) * (np.mean(returns) / np.std(returns))
        else:
            sharpe = 0

        # Max drawdown
        peaks = np.maximum.accumulate(equity)
        drawdowns = (equity - peaks) / peaks
        max_drawdown = np.min(drawdowns) * 100

        # Compile metrics
        metrics = {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / total_trades * 100 if total_trades > 0 else 0,
            'total_pnl': sum(t['pnl'] for t in trades),
            'total_return': total_return,
            'avg_win': np.mean([t['pnl_pct'] for t in winning_trades]) if winning_trades else 0,
            'avg_loss': np.mean([t['pnl_pct'] for t in losing_trades]) if losing_trades else 0,
            'best_trade': max(t['pnl_pct'] for t in trades) if trades else 0,
            'worst_trade': min(t['pnl_pct'] for t in trades) if trades else 0,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'golden_pocket_trades': len(gp_trades),
            'golden_pocket_win_rate': len(gp_winning) / len(gp_trades) * 100 if gp_trades else 0,
            'final_capital': self.current_capital
        }

        return metrics

    def print_results(self, metrics: Dict, results: Dict):
        """
        Print formatted backtest results
        """
        print("\n" + "=" * 60)
        print("GOLDEN POCKET STRATEGY BACKTEST RESULTS")
        print("=" * 60)

        print(f"\n📊 PERFORMANCE SUMMARY")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Final Capital: ${metrics['final_capital']:,.2f}")
        print(f"Total Return: {metrics['total_return']:+.2f}%")
        print(f"Max Drawdown: {metrics['max_drawdown']:.2f}%")
        print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")

        print(f"\n📈 TRADE STATISTICS")
        print(f"Total Trades: {metrics['total_trades']}")
        print(f"Winning Trades: {metrics['winning_trades']} ({metrics['win_rate']:.1f}%)")
        print(f"Losing Trades: {metrics['losing_trades']}")
        print(f"Average Win: {metrics['avg_win']:+.2f}%")
        print(f"Average Loss: {metrics['avg_loss']:+.2f}%")
        print(f"Best Trade: {metrics['best_trade']:+.2f}%")
        print(f"Worst Trade: {metrics['worst_trade']:+.2f}%")

        print(f"\n✨ GOLDEN POCKET ANALYSIS")
        print(f"Golden Pocket Trades: {metrics['golden_pocket_trades']}")
        print(f"Golden Pocket Win Rate: {metrics['golden_pocket_win_rate']:.1f}%")

        # Print recent trades
        if results['trades']:
            print(f"\n📝 RECENT TRADES (Last 5)")
            print("-" * 60)
            for trade in results['trades'][-5:]:
                print(f"{trade['entry_time'].strftime('%m-%d %H:%M')} → "
                      f"{trade['exit_time'].strftime('%m-%d %H:%M')}: "
                      f"${trade['entry_price']:,.0f} → ${trade['exit_price']:,.0f} "
                      f"({trade['pnl_pct']:+.2f}%) "
                      f"{'🌟 GP' if trade['in_golden_pocket'] else ''}")

        print("\n" + "=" * 60)


async def main():
    """
    Run comprehensive golden pocket backtest
    """
    print("🚀 Starting Golden Pocket Strategy Backtest with REAL Data")
    print("-" * 60)

    # Initialize backtester
    backtester = GoldenPocketBacktest(initial_capital=10000)

    # Test different time periods
    test_periods = [
        {'days': 7, 'name': 'Last Week'},
        {'days': 30, 'name': 'Last Month'},
        # {'days': 90, 'name': 'Last Quarter'}  # Commented out for faster testing
    ]

    all_results = []

    for period in test_periods:
        print(f"\n📅 Testing: {period['name']} ({period['days']} days)")
        print("-" * 40)

        # Fetch data
        df = await backtester.fetch_data(period['days'])

        if df.empty:
            print(f"❌ No data available for {period['name']}")
            continue

        # Calculate golden pockets
        df = backtester.calculate_golden_pockets(df)

        # Count golden pocket occurrences
        gp_count = df['in_golden_pocket'].sum()
        print(f"Golden Pocket occurrences: {gp_count}")

        # Run backtest
        results = backtester.execute_backtest(df)

        # Analyze results
        metrics = backtester.analyze_results(results)

        # Store results
        all_results.append({
            'period': period['name'],
            'metrics': metrics,
            'results': results
        })

        # Print results
        backtester.print_results(metrics, results)

        # Reset for next period
        backtester.current_capital = backtester.initial_capital

    # Overall summary
    print("\n" + "=" * 60)
    print("📊 OVERALL PERFORMANCE SUMMARY")
    print("=" * 60)

    for result in all_results:
        if 'error' not in result['metrics']:
            print(f"\n{result['period']}:")
            print(f"  Return: {result['metrics']['total_return']:+.2f}%")
            print(f"  Win Rate: {result['metrics']['win_rate']:.1f}%")
            print(f"  GP Win Rate: {result['metrics']['golden_pocket_win_rate']:.1f}%")
            print(f"  Sharpe: {result['metrics']['sharpe_ratio']:.2f}")

    print("\n✅ Backtest Complete!")


if __name__ == "__main__":
    asyncio.run(main())