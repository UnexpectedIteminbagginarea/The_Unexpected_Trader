"""
Parameter Optimization Framework for BTC Golden Pocket Strategy
Systematic grid search to find optimal trading parameters
"""
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json
import itertools
from dataclasses import dataclass, asdict
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


@dataclass
class ParameterSet:
    """Single parameter configuration to test"""
    # Entry/Exit Parameters
    unified_score_buy: int          # Minimum score to enter (50-70)
    unified_score_sell: int         # Score to exit (25-40)
    confidence_threshold: float     # Minimum confidence (0.50-0.75)
    golden_pocket_override: int     # Lower threshold for GP (45-60)
    gp_confidence_boost: float      # Confidence boost in GP (0.75-0.90)

    # Risk Management
    max_position_size: float        # Max % of capital per trade (0.3-0.6)
    stop_loss: float                # Stop loss % (0.03-0.08)
    take_profit: float              # Take profit % (0.08-0.15)

    # Scoring Weights
    golden_pocket_weight: float     # Weight for chart patterns (0.25-0.35)

    # Optional Advanced
    require_trend_alignment: bool   # Require EMA alignment
    multi_tf_confirmations: int     # Number of timeframes to confirm (1-3)

    def to_dict(self):
        return asdict(self)


@dataclass
class BacktestResult:
    """Results from a single backtest run"""
    parameter_set: ParameterSet

    # Performance Metrics
    total_trades: int
    win_rate: float
    net_return: float
    sharpe_ratio: float
    max_drawdown: float

    # Golden Pocket Specific
    gp_trades: int
    gp_win_rate: float
    gp_utilization: float  # % of GP opportunities taken

    # Risk Metrics
    avg_win: float
    avg_loss: float
    profit_factor: float

    # Timing Metrics
    avg_hold_time: float  # in hours
    best_trade: float
    worst_trade: float

    # Confidence Analysis
    avg_confidence: float
    confidence_correlation: float  # correlation between confidence and returns

    def score(self) -> float:
        """
        Calculate overall score for this parameter set
        Weighted combination of key metrics
        """
        score = 0

        # Profitability (40% weight)
        score += self.net_return * 0.4

        # Risk-adjusted returns (30% weight)
        if self.sharpe_ratio > 0:
            score += min(self.sharpe_ratio / 3, 1.0) * 30  # Cap at 3

        # Win rate (15% weight)
        score += (self.win_rate - 50) * 0.3  # 0 points at 50%, +15 at 100%

        # Golden pocket performance (10% weight)
        if self.gp_win_rate > 0:
            score += (self.gp_win_rate - 50) * 0.2

        # Drawdown penalty (5% weight)
        score -= max(self.max_drawdown - 15, 0) * 0.5  # Penalty if > 15%

        return score


class ParameterOptimizer:
    """
    Grid search optimization for trading parameters
    """

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.data_fetcher = HistoricalDataFetcher()
        self.technical = TechnicalAnalyzer()
        self.results = []
        self.best_params = None

    def generate_parameter_grid(self, optimization_level: str = 'quick') -> List[ParameterSet]:
        """
        Generate parameter combinations to test

        Args:
            optimization_level: 'quick', 'standard', or 'comprehensive'
        """
        if optimization_level == 'quick':
            # Quick test - MORE AGGRESSIVE parameters
            grid = {
                'unified_score_buy': [45, 50, 55],  # Lower entries
                'unified_score_sell': [25, 30, 35],  # Various exits
                'confidence_threshold': [0.50, 0.55, 0.60],  # Lower confidence
                'golden_pocket_override': [40, 45, 50],  # Much lower for GP
                'gp_confidence_boost': [0.85, 0.90],  # Higher boost
                'max_position_size': [0.60, 0.70],  # Larger positions
                'stop_loss': [0.06, 0.07],  # Wider stops for crypto
                'take_profit': [0.12, 0.15],  # Bigger targets
                'golden_pocket_weight': [0.35, 0.40],  # More GP weight
                'require_trend_alignment': [False],
                'multi_tf_confirmations': [1]
            }

        elif optimization_level == 'standard':
            # Standard test - ~100 combinations
            grid = {
                'unified_score_buy': [55, 60, 65],
                'unified_score_sell': [30, 35],
                'confidence_threshold': [0.55, 0.65, 0.70],
                'golden_pocket_override': [45, 50, 55],
                'gp_confidence_boost': [0.75, 0.80, 0.85],
                'max_position_size': [0.30, 0.40, 0.50],
                'stop_loss': [0.04, 0.05, 0.06],
                'take_profit': [0.08, 0.10, 0.12],
                'golden_pocket_weight': [0.25, 0.30],
                'require_trend_alignment': [False, True],
                'multi_tf_confirmations': [1]
            }

        else:  # comprehensive
            # Comprehensive test - ~500+ combinations
            grid = {
                'unified_score_buy': [50, 55, 60, 65, 70],
                'unified_score_sell': [25, 30, 35, 40],
                'confidence_threshold': [0.50, 0.55, 0.60, 0.65, 0.70, 0.75],
                'golden_pocket_override': [45, 50, 55, 60],
                'gp_confidence_boost': [0.70, 0.75, 0.80, 0.85, 0.90],
                'max_position_size': [0.30, 0.40, 0.50, 0.60],
                'stop_loss': [0.03, 0.04, 0.05, 0.06, 0.07],
                'take_profit': [0.08, 0.10, 0.12, 0.15],
                'golden_pocket_weight': [0.20, 0.25, 0.30, 0.35],
                'require_trend_alignment': [False, True],
                'multi_tf_confirmations': [1, 2]
            }

        # Generate all combinations
        param_sets = []

        # Get all combinations but limit based on optimization level
        keys = grid.keys()
        values = grid.values()

        for combination in itertools.product(*values):
            params = dict(zip(keys, combination))

            # Validation: sell threshold must be lower than buy threshold
            if params['unified_score_sell'] >= params['unified_score_buy']:
                continue

            # Validation: GP override must be lower than main threshold
            if params['golden_pocket_override'] >= params['unified_score_buy']:
                continue

            param_sets.append(ParameterSet(**params))

        logger.info(f"Generated {len(param_sets)} parameter combinations for {optimization_level} optimization")
        return param_sets

    async def run_single_backtest(self, params: ParameterSet,
                                 df: pd.DataFrame) -> BacktestResult:
        """
        Run backtest with a single parameter set
        """
        # Calculate golden pockets
        df = self.calculate_golden_pockets(df, lookback=50)

        # Track metrics
        trades = []
        position = None
        capital = self.initial_capital
        equity_curve = [capital]

        gp_opportunities = df['in_golden_pocket'].sum()

        for i in range(50, len(df)):
            row = df.iloc[i]
            current_price = row['close']

            # Calculate signals with current parameters
            unified_score, confidence = self.calculate_score_with_params(row, params)

            # Entry logic
            if position is None:
                # Check entry conditions
                should_enter = False

                # Standard entry
                if (unified_score >= params.unified_score_buy and
                    confidence >= params.confidence_threshold):
                    should_enter = True

                # Golden pocket override
                elif (row.get('in_golden_pocket', False) and
                      unified_score >= params.golden_pocket_override):
                    confidence = max(confidence, params.gp_confidence_boost)
                    should_enter = True

                # Trend alignment check (if enabled)
                if should_enter and params.require_trend_alignment:
                    if not self.check_trend_alignment(df, i):
                        should_enter = False

                if should_enter:
                    # Open position
                    position_size = capital * params.max_position_size * confidence
                    position = {
                        'entry_price': current_price,
                        'entry_time': df.index[i],
                        'entry_idx': i,
                        'size': position_size,
                        'shares': position_size / current_price,
                        'unified_score': unified_score,
                        'confidence': confidence,
                        'in_golden_pocket': row.get('in_golden_pocket', False),
                        'stop_loss': current_price * (1 - params.stop_loss),
                        'take_profit': current_price * (1 + params.take_profit)
                    }

            # Exit logic
            elif position is not None:
                # Check exit conditions
                hit_stop = current_price <= position['stop_loss']
                hit_target = current_price >= position['take_profit']
                score_exit = unified_score <= params.unified_score_sell

                if hit_stop or hit_target or score_exit or i == len(df) - 1:
                    # Calculate P&L
                    exit_value = position['shares'] * current_price
                    pnl = exit_value - position['size']
                    pnl_pct = (pnl / position['size']) * 100

                    # Update capital
                    capital += pnl

                    # Record trade
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': df.index[i],
                        'hold_time': (i - position['entry_idx']) / 24,  # hours
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'confidence': position['confidence'],
                        'in_golden_pocket': position['in_golden_pocket']
                    })

                    position = None

            # Update equity
            current_equity = capital
            if position:
                current_equity += position['shares'] * current_price
            equity_curve.append(current_equity)

        # Calculate metrics
        return self.calculate_metrics(params, trades, equity_curve, gp_opportunities)

    def calculate_score_with_params(self, row: pd.Series,
                                   params: ParameterSet) -> Tuple[float, float]:
        """
        Calculate unified score using specified parameters
        """
        # Simplified scoring for optimization
        score_components = {}

        # Technical score
        if 'rsi' in row and pd.notna(row['rsi']):
            if 30 <= row['rsi'] <= 70:
                score_components['technical'] = 60 + (70 - row['rsi']) / 2
            else:
                score_components['technical'] = 40

        # Momentum
        if 'price_change_5' in row and pd.notna(row['price_change_5']):
            momentum = row['price_change_5']
            score_components['momentum'] = 50 + (momentum * 500)

        # Volume
        if 'volume_ratio' in row and pd.notna(row['volume_ratio']):
            score_components['volume'] = min(100, 50 * row['volume_ratio'])

        # Golden pocket with custom weight
        if row.get('in_golden_pocket', False):
            score_components['golden_pocket'] = 80

        # Calculate weighted score
        if score_components:
            # Apply golden pocket weight adjustment
            if 'golden_pocket' in score_components:
                gp_score = score_components['golden_pocket']
                other_scores = [v for k, v in score_components.items() if k != 'golden_pocket']
                if other_scores:
                    other_avg = np.mean(other_scores)
                    unified_score = (gp_score * params.golden_pocket_weight +
                                   other_avg * (1 - params.golden_pocket_weight))
                else:
                    unified_score = gp_score
            else:
                unified_score = np.mean(list(score_components.values()))
        else:
            unified_score = 50

        # Calculate confidence
        available_signals = len(score_components)
        max_signals = 4
        data_confidence = available_signals / max_signals

        if score_components:
            signal_std = np.std(list(score_components.values()))
            alignment_confidence = 1 - (signal_std / 50)
        else:
            alignment_confidence = 0.5

        confidence = (data_confidence * 0.5 + alignment_confidence * 0.5)

        # GP confidence boost
        if row.get('in_golden_pocket', False):
            confidence = max(confidence, params.gp_confidence_boost)

        return unified_score, confidence

    def check_trend_alignment(self, df: pd.DataFrame, idx: int) -> bool:
        """
        Check if EMAs are aligned for trend
        """
        if idx < 50:
            return True  # Not enough data

        current_price = df.iloc[idx]['close']
        sma_20 = df.iloc[idx].get('sma_20', current_price)
        sma_50 = df.iloc[idx].get('sma_50', current_price)

        # Bullish alignment: price > SMA20 > SMA50
        return current_price > sma_20 > sma_50

    def calculate_golden_pockets(self, df: pd.DataFrame, lookback: int = 50) -> pd.DataFrame:
        """
        Calculate Fibonacci levels and golden pockets
        """
        df['swing_high'] = df['high'].rolling(lookback).max()
        df['swing_low'] = df['low'].rolling(lookback).min()

        df['fib_range'] = df['swing_high'] - df['swing_low']
        df['fib_618'] = df['swing_high'] - (df['fib_range'] * 0.618)
        df['fib_650'] = df['swing_high'] - (df['fib_range'] * 0.650)

        df['in_golden_pocket'] = (
            (df['close'] <= df['fib_618']) &
            (df['close'] >= df['fib_650'])
        )

        return df

    def calculate_metrics(self, params: ParameterSet, trades: List[Dict],
                         equity_curve: List[float],
                         gp_opportunities: int) -> BacktestResult:
        """
        Calculate comprehensive metrics from trades
        """
        if not trades:
            return BacktestResult(
                parameter_set=params,
                total_trades=0,
                win_rate=0,
                net_return=0,
                sharpe_ratio=0,
                max_drawdown=0,
                gp_trades=0,
                gp_win_rate=0,
                gp_utilization=0,
                avg_win=0,
                avg_loss=0,
                profit_factor=0,
                avg_hold_time=0,
                best_trade=0,
                worst_trade=0,
                avg_confidence=0,
                confidence_correlation=0
            )

        # Basic metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]

        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0

        # Returns
        net_return = ((equity_curve[-1] - self.initial_capital) /
                     self.initial_capital * 100)

        # Sharpe ratio
        returns = np.diff(equity_curve) / equity_curve[:-1]
        if len(returns) > 0 and np.std(returns) > 0:
            sharpe_ratio = np.sqrt(365 * 24) * (np.mean(returns) / np.std(returns))
        else:
            sharpe_ratio = 0

        # Max drawdown
        peaks = np.maximum.accumulate(equity_curve)
        drawdowns = (np.array(equity_curve) - peaks) / peaks * 100
        max_drawdown = abs(np.min(drawdowns))

        # Golden pocket metrics
        gp_trades = [t for t in trades if t['in_golden_pocket']]
        gp_winning = [t for t in gp_trades if t['pnl'] > 0]
        gp_win_rate = len(gp_winning) / len(gp_trades) * 100 if gp_trades else 0
        gp_utilization = len(gp_trades) / gp_opportunities * 100 if gp_opportunities > 0 else 0

        # Risk metrics
        avg_win = np.mean([t['pnl_pct'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losing_trades]) if losing_trades else 0

        gross_profit = sum(t['pnl'] for t in winning_trades) if winning_trades else 0
        gross_loss = abs(sum(t['pnl'] for t in losing_trades)) if losing_trades else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Timing metrics
        avg_hold_time = np.mean([t['hold_time'] for t in trades])
        best_trade = max(t['pnl_pct'] for t in trades) if trades else 0
        worst_trade = min(t['pnl_pct'] for t in trades) if trades else 0

        # Confidence analysis
        avg_confidence = np.mean([t['confidence'] for t in trades])

        # Correlation between confidence and returns
        if len(trades) > 2:
            confidences = [t['confidence'] for t in trades]
            returns = [t['pnl_pct'] for t in trades]
            confidence_correlation = np.corrcoef(confidences, returns)[0, 1]
        else:
            confidence_correlation = 0

        return BacktestResult(
            parameter_set=params,
            total_trades=total_trades,
            win_rate=win_rate,
            net_return=net_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            gp_trades=len(gp_trades),
            gp_win_rate=gp_win_rate,
            gp_utilization=gp_utilization,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            avg_hold_time=avg_hold_time,
            best_trade=best_trade,
            worst_trade=worst_trade,
            avg_confidence=avg_confidence,
            confidence_correlation=confidence_correlation
        )

    async def optimize(self, days: int = 30, optimization_level: str = 'quick'):
        """
        Run full optimization
        """
        logger.info(f"Starting {optimization_level} optimization for {days} days")

        # Fetch data once
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        logger.info("Fetching historical data...")
        df = await self.data_fetcher.create_backtest_dataset(start_date, end_date)

        if df.empty:
            logger.error("Failed to fetch data")
            return

        logger.info(f"Data fetched: {len(df)} points from {df.index.min()} to {df.index.max()}")

        # Generate parameter grid
        param_sets = self.generate_parameter_grid(optimization_level)

        # Run backtests
        results = []
        for i, params in enumerate(param_sets):
            if i % 10 == 0:
                logger.info(f"Testing parameter set {i+1}/{len(param_sets)}")

            result = await self.run_single_backtest(params, df.copy())
            results.append(result)

        # Sort by score
        results.sort(key=lambda x: x.score(), reverse=True)
        self.results = results
        self.best_params = results[0].parameter_set if results else None

        return results

    def save_results(self, filename: str = 'optimization_results.csv'):
        """
        Save optimization results to CSV
        """
        if not self.results:
            logger.warning("No results to save")
            return

        # Convert to DataFrame
        data = []
        for result in self.results:
            row = result.parameter_set.to_dict()
            row.update({
                'score': result.score(),
                'total_trades': result.total_trades,
                'win_rate': result.win_rate,
                'net_return': result.net_return,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'gp_trades': result.gp_trades,
                'gp_win_rate': result.gp_win_rate,
                'gp_utilization': result.gp_utilization,
                'profit_factor': result.profit_factor
            })
            data.append(row)

        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        logger.info(f"Results saved to {filename}")

    def print_top_results(self, top_n: int = 10):
        """
        Print top parameter sets
        """
        print("\n" + "=" * 80)
        print(f"TOP {top_n} PARAMETER SETS")
        print("=" * 80)

        for i, result in enumerate(self.results[:top_n]):
            print(f"\n#{i+1} - Score: {result.score():.2f}")
            print("-" * 40)

            # Parameters
            params = result.parameter_set
            print("PARAMETERS:")
            print(f"  Entry Score: {params.unified_score_buy}, Exit: {params.unified_score_sell}")
            print(f"  Confidence: {params.confidence_threshold:.0%}")
            print(f"  GP Override: {params.golden_pocket_override}, Boost: {params.gp_confidence_boost:.0%}")
            print(f"  Position Size: {params.max_position_size:.0%}")
            print(f"  Stop/Target: {params.stop_loss:.0%}/{params.take_profit:.0%}")
            print(f"  GP Weight: {params.golden_pocket_weight:.0%}")

            # Results
            print("PERFORMANCE:")
            print(f"  Return: {result.net_return:+.2f}%")
            print(f"  Win Rate: {result.win_rate:.1f}% ({result.total_trades} trades)")
            print(f"  Sharpe: {result.sharpe_ratio:.2f}")
            print(f"  Max DD: {result.max_drawdown:.1f}%")
            print(f"  GP Performance: {result.gp_win_rate:.0f}% win rate, {result.gp_utilization:.0f}% utilization")
            print(f"  Profit Factor: {result.profit_factor:.2f}")

    def create_heatmap_data(self):
        """
        Create data for parameter heatmap visualization
        """
        if not self.results:
            return None

        # Extract key parameter combinations
        data = []
        for result in self.results:
            data.append({
                'score_threshold': result.parameter_set.unified_score_buy,
                'confidence': result.parameter_set.confidence_threshold,
                'stop_loss': result.parameter_set.stop_loss,
                'net_return': result.net_return,
                'sharpe': result.sharpe_ratio,
                'score': result.score()
            })

        return pd.DataFrame(data)


async def main():
    """
    Run parameter optimization
    """
    print("🚀 Starting Parameter Optimization Framework")
    print("-" * 60)

    optimizer = ParameterOptimizer(initial_capital=10000)

    # Run optimization
    optimization_level = 'quick'  # Change to 'standard' or 'comprehensive' for more tests
    results = await optimizer.optimize(days=30, optimization_level=optimization_level)

    if results:
        # Print top results
        optimizer.print_top_results(top_n=5)

        # Save to CSV
        optimizer.save_results('optimization_results.csv')

        # Best parameters
        if optimizer.best_params:
            print("\n" + "=" * 80)
            print("🏆 BEST PARAMETER SET")
            print("=" * 80)
            print(json.dumps(optimizer.best_params.to_dict(), indent=2))

    print("\n✅ Optimization Complete!")


if __name__ == "__main__":
    asyncio.run(main())