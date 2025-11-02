"""
BTC Historical Backtesting Suite
Tests golden pocket strategy across different market regimes
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import logging
from dataclasses import dataclass, asdict
import asyncio
import aiohttp

# Import our modules
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.technical_analyzer import TechnicalAnalyzer
from core.sentiment_scorer import SentimentScorer
from data.aster_client import AsterClient
from data.historical_data_fetcher import HistoricalDataFetcher

logger = logging.getLogger(__name__)


@dataclass
class MarketRegime:
    """Define market regime characteristics"""
    name: str
    start_date: str
    end_date: str
    description: str
    expected_behavior: str


@dataclass
class BacktestResult:
    """Store backtest results"""
    regime: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    golden_pocket_trades: int
    golden_pocket_win_rate: float
    avg_win: float
    avg_loss: float
    best_trade: float
    worst_trade: float
    confidence_correlation: float


class BTCHistoricalBacktest:
    """
    Comprehensive backtesting for BTC golden pocket + unified scoring strategy
    """

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.technical = TechnicalAnalyzer()
        self.scorer = SentimentScorer()
        self.aster = AsterClient()
        self.data_fetcher = HistoricalDataFetcher()  # Use real data fetcher

        # Define market regimes to test
        self.market_regimes = [
            MarketRegime(
                name="Bull_Rally_2024",
                start_date="2024-01-01",
                end_date="2024-03-15",
                description="Strong uptrend from $42k to $73k",
                expected_behavior="Golden pockets should provide excellent entry points"
            ),
            MarketRegime(
                name="Correction_2024",
                start_date="2024-03-15",
                end_date="2024-05-01",
                description="Correction from $73k to $57k",
                expected_behavior="Test risk management and stop losses"
            ),
            MarketRegime(
                name="Sideways_2024",
                start_date="2024-05-01",
                end_date="2024-07-01",
                description="Range-bound between $60k-$70k",
                expected_behavior="Test patience and false signals"
            ),
            MarketRegime(
                name="Volatility_2024",
                start_date="2024-08-01",
                end_date="2024-09-01",
                description="High volatility period",
                expected_behavior="Test position sizing and confidence scoring"
            ),
            MarketRegime(
                name="Recent_2024",
                start_date="2024-09-01",
                end_date="2024-10-30",
                description="Recent market conditions",
                expected_behavior="Most relevant for current strategy"
            )
        ]

        # Strategy parameters to test
        self.default_params = {
            'entry_score_threshold': 60,
            'golden_pocket_override': 55,
            'min_confidence': 0.65,
            'golden_pocket_confidence_boost': 0.80,
            'max_position_pct': 0.50,
            'stop_loss_pct': 0.05,
            'take_profit_pct': 0.10,
            'position_scaling': True,
            'require_confirmations': 2
        }

        # Track all trades for analysis
        self.all_trades = []
        self.regime_results = {}

    async def fetch_historical_data(self, start_date: str, end_date: str,
                                   interval: str = "1h") -> pd.DataFrame:
        """
        Fetch REAL historical BTC data using our data fetcher
        """
        logger.info(f"Fetching REAL BTC data from {start_date} to {end_date}")

        # Use the real data fetcher to get comprehensive backtest dataset
        df = await self.data_fetcher.create_backtest_dataset(start_date, end_date, 'BTC')

        if df.empty:
            logger.error("Failed to fetch real data, falling back to limited dataset")
            # Try to at least get price data
            df = await self.data_fetcher.fetch_btc_historical_data(start_date, end_date, interval)

            if not df.empty:
                # Add technical indicators if we only got price data
                df = self._add_technical_indicators(df)
                # Add estimated sentiment (better than pure random)
                df = self._add_estimated_sentiment(df)

        logger.info(f"Fetched {len(df)} real data points")
        logger.info(f"Data columns: {df.columns.tolist()}")
        logger.info(f"Date range: {df.index.min()} to {df.index.max()}")

        # Ensure we have required columns for backtesting
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return pd.DataFrame()

        return df

    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add technical indicators to dataframe
        """
        # Simple indicators for faster backtesting
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(24).std()
        df['volume_sma'] = df['volume'].rolling(24).mean()
        df['price_sma_20'] = df['close'].rolling(20).mean()
        df['price_sma_50'] = df['close'].rolling(50).mean()

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        return df

    def _add_estimated_sentiment(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add estimated sentiment scores based on technical indicators
        More realistic than pure random, but still not as good as real CoinGlass data
        """
        # Generate realistic sentiment based on price patterns
        df['momentum'] = df['close'].pct_change(periods=24).rolling(3).mean()

        # Estimate unified score (0-100) based on technical factors
        base_score = 50

        # Price momentum influence (stronger momentum = higher sentiment)
        momentum_score = df['momentum'].fillna(0) * 1000  # Scale momentum

        # RSI influence (oversold = fear, overbought = greed)
        rsi_score = (df['rsi'].fillna(50) - 50) * 0.5

        # Volume influence (high volume = stronger conviction)
        if 'volume_ratio' in df.columns:
            volume_score = (df['volume_ratio'].fillna(1) - 1) * 10
        else:
            volume_score = 0

        # Trend influence (above/below moving averages)
        if 'sma_50' in df.columns:
            trend_score = ((df['close'] / df['sma_50'].fillna(df['close']) - 1) * 100).clip(-10, 10)
        else:
            trend_score = 0

        # Combine all factors
        df['unified_score'] = base_score + momentum_score + rsi_score + volume_score + trend_score

        # Add realistic noise and constraints
        np.random.seed(42)
        noise = np.random.normal(0, 5, len(df))
        df['unified_score'] += noise

        # Clip to 0-100
        df['unified_score'] = df['unified_score'].clip(0, 100)

        # Mock confidence (higher in trends, lower in chop)
        df['trend_strength'] = abs(df['price_sma_20'] - df['price_sma_50']) / df['close']
        df['confidence'] = 0.5 + (df['trend_strength'] * 10)
        df['confidence'] = df['confidence'].clip(0.3, 0.95)

        return df

    def _generate_mock_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Generate mock data for testing when API unavailable
        """
        logger.warning("Using mock data for testing")

        # Create date range
        dates = pd.date_range(start=start_date, end=end_date, freq='1H')

        # Generate synthetic price data
        np.random.seed(42)
        prices = []
        price = 50000  # Starting price

        for i in range(len(dates)):
            # Add trend component
            trend = np.sin(i / 100) * 0.001

            # Add volatility
            volatility = np.random.randn() * 0.005

            # Update price
            price = price * (1 + trend + volatility)
            prices.append(price)

        # Create DataFrame
        df = pd.DataFrame({
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': prices,
            'volume': np.random.uniform(100, 1000, len(dates))
        }, index=dates)

        # Add indicators
        df = self._add_technical_indicators(df)
        df = self._add_mock_sentiment(df)

        return df

    async def backtest_regime(self, regime: MarketRegime,
                            params: Dict = None) -> BacktestResult:
        """
        Backtest a specific market regime
        """
        if params is None:
            params = self.default_params

        logger.info(f"\n{'='*60}")
        logger.info(f"Backtesting {regime.name}")
        logger.info(f"Period: {regime.start_date} to {regime.end_date}")
        logger.info(f"Description: {regime.description}")
        logger.info(f"{'='*60}")

        # Fetch data for regime
        df = await self.fetch_historical_data(regime.start_date, regime.end_date)

        # Initialize tracking
        capital = self.initial_capital
        position = None
        trades = []
        equity_curve = [capital]

        # Iterate through data with 100-bar lookback
        for i in range(100, len(df)):
            current = df.iloc[i]
            window = df.iloc[max(0, i-100):i+1]

            # Get signals
            signals = self._generate_signals(window, current, params)

            # Execute trades
            if signals['action'] != 'HOLD':
                if position is None and signals['action'] in ['BUY', 'STRONG_BUY']:
                    # Open position
                    position = self._open_position(capital, current, signals, params)

                elif position and signals['action'] in ['SELL', 'EXIT']:
                    # Close position
                    capital, trade_result = self._close_position(
                        position, current, capital
                    )
                    trades.append(trade_result)
                    position = None

            # Check stop loss / take profit
            if position:
                capital, trade_result = self._check_exits(
                    position, current, capital
                )
                if trade_result:
                    trades.append(trade_result)
                    position = None

            # Update equity curve
            current_equity = capital
            if position:
                unrealized_pnl = (current['close'] - position['entry_price']) * position['size']
                current_equity += unrealized_pnl
            equity_curve.append(current_equity)

        # Close any open position at end
        if position:
            capital, trade_result = self._close_position(
                position, df.iloc[-1], capital
            )
            trades.append(trade_result)

        # Calculate metrics
        result = self._calculate_metrics(trades, equity_curve, regime.name)

        # Store trades
        self.all_trades.extend(trades)
        self.regime_results[regime.name] = result

        # Log summary
        self._log_regime_results(result, regime)

        return result

    def _generate_signals(self, window: pd.DataFrame, current: pd.Series,
                         params: Dict) -> Dict:
        """
        Generate trading signals based on technical + sentiment
        """
        # Convert to klines format for technical analysis
        klines = []
        for idx, row in window.iterrows():
            klines.append([
                int(idx.timestamp() * 1000),
                row['open'], row['high'], row['low'],
                row['close'], row['volume']
            ])

        current_price = current['close']

        # Get technical analysis
        tech_analysis = self.technical.get_comprehensive_analysis(klines, current_price)

        # Check golden pocket
        golden_pocket = tech_analysis.get('golden_pocket', {}).get('in_golden_pocket', False)

        # Get sentiment score
        unified_score = current.get('unified_score', 50)
        confidence = current.get('confidence', 0.5)

        # Generate signal
        signal = {'action': 'HOLD', 'confidence': confidence, 'reason': ''}

        # Golden Pocket Override
        if golden_pocket:
            trend = tech_analysis.get('trend', {}).get('trend', 'UNKNOWN')
            if trend in ['UP', 'STRONG_UP'] and unified_score >= params['golden_pocket_override']:
                signal = {
                    'action': 'STRONG_BUY',
                    'confidence': max(confidence, params['golden_pocket_confidence_boost']),
                    'reason': 'Golden pocket + bullish',
                    'golden_pocket': True
                }
                return signal

        # Standard signals
        if unified_score >= params['entry_score_threshold'] and \
           confidence >= params['min_confidence']:
            # Check for confirmations
            confirmations = self._count_confirmations(tech_analysis, current_price)

            if confirmations >= params['require_confirmations']:
                signal = {
                    'action': 'BUY',
                    'confidence': confidence,
                    'reason': f'Score {unified_score:.0f} + {confirmations} confirmations',
                    'golden_pocket': False
                }
        elif unified_score <= 40 and confidence >= params['min_confidence']:
            signal = {
                'action': 'SELL',
                'confidence': confidence,
                'reason': f'Low score {unified_score:.0f}',
                'golden_pocket': False
            }

        return signal

    def _count_confirmations(self, tech: Dict, price: float) -> int:
        """
        Count technical confirmations
        """
        confirmations = 0

        # Near support
        sr = tech.get('support_resistance', {})
        if sr.get('nearest_support'):
            support_distance = ((price - sr['nearest_support']) / sr['nearest_support']) * 100
            if support_distance < 3:
                confirmations += 1

        # Bullish trend
        if tech.get('trend', {}).get('trend') in ['UP', 'STRONG_UP']:
            confirmations += 1

        # At Fibonacci level
        if tech.get('signals', {}).get('components'):
            if any('FIB' in str(comp) for comp in tech['signals']['components']):
                confirmations += 1

        return confirmations

    def _open_position(self, capital: float, current: pd.Series,
                      signal: Dict, params: Dict) -> Dict:
        """
        Open a new position
        """
        # Calculate position size
        position_pct = params['max_position_pct']
        if params['position_scaling']:
            position_pct *= signal['confidence']

        # Golden pocket gets larger position
        if signal.get('golden_pocket'):
            position_pct *= 1.5

        position_value = capital * position_pct
        position_size = position_value / current['close']

        return {
            'entry_time': current.name,
            'entry_price': current['close'],
            'size': position_size,
            'value': position_value,
            'stop_loss': current['close'] * (1 - params['stop_loss_pct']),
            'take_profit': current['close'] * (1 + params['take_profit_pct']),
            'signal': signal,
            'confidence': signal['confidence'],
            'golden_pocket': signal.get('golden_pocket', False),
            'unified_score': current.get('unified_score', 50)
        }

    def _close_position(self, position: Dict, current: pd.Series,
                       capital: float) -> Tuple[float, Dict]:
        """
        Close position and calculate P&L
        """
        exit_price = current['close']
        pnl = (exit_price - position['entry_price']) * position['size']
        pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100

        trade_result = {
            'entry_time': position['entry_time'],
            'entry_price': position['entry_price'],
            'exit_time': current.name,
            'exit_price': exit_price,
            'size': position['size'],
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'confidence': position['confidence'],
            'golden_pocket': position['golden_pocket'],
            'unified_score_entry': position['unified_score'],
            'unified_score_exit': current.get('unified_score', 50),
            'reason': position['signal']['reason']
        }

        new_capital = capital + pnl
        return new_capital, trade_result

    def _check_exits(self, position: Dict, current: pd.Series,
                    capital: float) -> Tuple[float, Optional[Dict]]:
        """
        Check stop loss and take profit
        """
        if current['low'] <= position['stop_loss']:
            # Stop loss hit
            exit_price = position['stop_loss']
            pnl = (exit_price - position['entry_price']) * position['size']

            trade_result = {
                'entry_time': position['entry_time'],
                'entry_price': position['entry_price'],
                'exit_time': current.name,
                'exit_price': exit_price,
                'size': position['size'],
                'pnl': pnl,
                'pnl_pct': (pnl / position['value']) * 100,
                'confidence': position['confidence'],
                'golden_pocket': position['golden_pocket'],
                'unified_score_entry': position['unified_score'],
                'unified_score_exit': current.get('unified_score', 50),
                'reason': 'Stop loss'
            }

            return capital + pnl, trade_result

        elif current['high'] >= position['take_profit']:
            # Take profit hit
            exit_price = position['take_profit']
            pnl = (exit_price - position['entry_price']) * position['size']

            trade_result = {
                'entry_time': position['entry_time'],
                'entry_price': position['entry_price'],
                'exit_time': current.name,
                'exit_price': exit_price,
                'size': position['size'],
                'pnl': pnl,
                'pnl_pct': (pnl / position['value']) * 100,
                'confidence': position['confidence'],
                'golden_pocket': position['golden_pocket'],
                'unified_score_entry': position['unified_score'],
                'unified_score_exit': current.get('unified_score', 50),
                'reason': 'Take profit'
            }

            return capital + pnl, trade_result

        return capital, None

    def _calculate_metrics(self, trades: List[Dict], equity_curve: List[float],
                          regime_name: str) -> BacktestResult:
        """
        Calculate comprehensive backtest metrics
        """
        if not trades:
            return BacktestResult(
                regime=regime_name,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0,
                total_pnl=0,
                total_return=0,
                sharpe_ratio=0,
                max_drawdown=0,
                golden_pocket_trades=0,
                golden_pocket_win_rate=0,
                avg_win=0,
                avg_loss=0,
                best_trade=0,
                worst_trade=0,
                confidence_correlation=0
            )

        # Basic metrics
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]

        total_pnl = sum(t['pnl'] for t in trades)
        total_return = ((equity_curve[-1] - self.initial_capital) / self.initial_capital) * 100

        # Golden pocket specific
        gp_trades = [t for t in trades if t.get('golden_pocket', False)]
        gp_wins = [t for t in gp_trades if t['pnl'] > 0]
        gp_win_rate = (len(gp_wins) / len(gp_trades) * 100) if gp_trades else 0

        # Risk metrics
        returns = pd.Series(equity_curve).pct_change().dropna()
        sharpe_ratio = (returns.mean() / returns.std() * np.sqrt(365 * 24)) if returns.std() > 0 else 0

        # Drawdown
        equity_series = pd.Series(equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = ((equity_series - rolling_max) / rolling_max * 100)
        max_drawdown = drawdown.min()

        # Confidence correlation
        if len(trades) > 1:
            confidences = [t['confidence'] for t in trades]
            pnls = [t['pnl_pct'] for t in trades]
            confidence_correlation = np.corrcoef(confidences, pnls)[0, 1]
        else:
            confidence_correlation = 0

        return BacktestResult(
            regime=regime_name,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=(len(winning_trades) / len(trades) * 100) if trades else 0,
            total_pnl=total_pnl,
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            golden_pocket_trades=len(gp_trades),
            golden_pocket_win_rate=gp_win_rate,
            avg_win=np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0,
            avg_loss=np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0,
            best_trade=max([t['pnl'] for t in trades]) if trades else 0,
            worst_trade=min([t['pnl'] for t in trades]) if trades else 0,
            confidence_correlation=confidence_correlation
        )

    def _log_regime_results(self, result: BacktestResult, regime: MarketRegime):
        """
        Log detailed results for a regime
        """
        logger.info(f"\n{'='*40}")
        logger.info(f"Results for {regime.name}")
        logger.info(f"{'='*40}")
        logger.info(f"Total Trades: {result.total_trades}")
        logger.info(f"Win Rate: {result.win_rate:.1f}%")
        logger.info(f"Total Return: {result.total_return:.2f}%")
        logger.info(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        logger.info(f"Max Drawdown: {result.max_drawdown:.2f}%")
        logger.info(f"\nGolden Pocket Performance:")
        logger.info(f"  GP Trades: {result.golden_pocket_trades}")
        logger.info(f"  GP Win Rate: {result.golden_pocket_win_rate:.1f}%")
        logger.info(f"\nRisk Metrics:")
        logger.info(f"  Avg Win: ${result.avg_win:.2f}")
        logger.info(f"  Avg Loss: ${result.avg_loss:.2f}")
        logger.info(f"  Best Trade: ${result.best_trade:.2f}")
        logger.info(f"  Worst Trade: ${result.worst_trade:.2f}")
        logger.info(f"  Confidence Correlation: {result.confidence_correlation:.3f}")

    async def run_complete_backtest(self) -> pd.DataFrame:
        """
        Run backtest across all market regimes
        """
        logger.info("\n" + "="*60)
        logger.info("STARTING COMPLETE BTC BACKTEST")
        logger.info("="*60)

        all_results = []

        for regime in self.market_regimes:
            result = await self.backtest_regime(regime)
            all_results.append(asdict(result))

        # Create summary DataFrame
        summary_df = pd.DataFrame(all_results)

        # Add aggregate metrics
        self._add_aggregate_metrics(summary_df)

        return summary_df

    def _add_aggregate_metrics(self, df: pd.DataFrame):
        """
        Add aggregate metrics to summary
        """
        logger.info("\n" + "="*60)
        logger.info("AGGREGATE PERFORMANCE METRICS")
        logger.info("="*60)

        # Overall statistics
        total_trades = df['total_trades'].sum()
        total_wins = df['winning_trades'].sum()
        overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0

        # Golden pocket statistics
        total_gp_trades = df['golden_pocket_trades'].sum()
        if total_gp_trades > 0:
            weighted_gp_win_rate = sum(
                df['golden_pocket_trades'] * df['golden_pocket_win_rate']
            ) / total_gp_trades
        else:
            weighted_gp_win_rate = 0

        logger.info(f"Total Trades Across All Regimes: {total_trades}")
        logger.info(f"Overall Win Rate: {overall_win_rate:.1f}%")
        logger.info(f"Average Sharpe Ratio: {df['sharpe_ratio'].mean():.2f}")
        logger.info(f"Worst Drawdown: {df['max_drawdown'].min():.2f}%")
        logger.info(f"\nGolden Pocket Analysis:")
        logger.info(f"  Total GP Trades: {total_gp_trades}")
        logger.info(f"  Weighted GP Win Rate: {weighted_gp_win_rate:.1f}%")
        logger.info(f"  GP vs Regular Win Rate Diff: {weighted_gp_win_rate - overall_win_rate:+.1f}%")

        # Regime performance ranking
        logger.info(f"\nBest Performing Regimes:")
        ranked = df.sort_values('total_return', ascending=False)
        for i, row in ranked.head(3).iterrows():
            logger.info(f"  {row['regime']}: {row['total_return']:.2f}% return, {row['win_rate']:.1f}% win rate")

    async def optimize_parameters(self, param_grid: Dict = None) -> Dict:
        """
        Grid search for optimal parameters
        """
        if param_grid is None:
            param_grid = {
                'entry_score_threshold': [55, 60, 65],
                'min_confidence': [0.60, 0.65, 0.70],
                'golden_pocket_override': [50, 55, 60],
                'stop_loss_pct': [0.03, 0.05, 0.07],
                'require_confirmations': [1, 2, 3]
            }

        logger.info("\n" + "="*60)
        logger.info("PARAMETER OPTIMIZATION")
        logger.info("="*60)

        best_params = None
        best_sharpe = -np.inf
        results = []

        # Generate all combinations
        from itertools import product
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())

        total_combinations = len(list(product(*param_values)))
        logger.info(f"Testing {total_combinations} parameter combinations...")

        for i, values in enumerate(product(*param_values), 1):
            params = self.default_params.copy()
            params.update(dict(zip(param_names, values)))

            logger.info(f"\nTesting combination {i}/{total_combinations}")

            # Test on most recent regime for speed
            regime = self.market_regimes[-1]  # Recent_2024
            result = await self.backtest_regime(regime, params)

            results.append({
                'params': params.copy(),
                'sharpe': result.sharpe_ratio,
                'win_rate': result.win_rate,
                'return': result.total_return,
                'gp_win_rate': result.golden_pocket_win_rate
            })

            if result.sharpe_ratio > best_sharpe:
                best_sharpe = result.sharpe_ratio
                best_params = params.copy()

        # Sort results
        results.sort(key=lambda x: x['sharpe'], reverse=True)

        logger.info("\n" + "="*40)
        logger.info("TOP 5 PARAMETER COMBINATIONS")
        logger.info("="*40)

        for i, r in enumerate(results[:5], 1):
            logger.info(f"\n{i}. Sharpe: {r['sharpe']:.2f}, Return: {r['return']:.1f}%, Win Rate: {r['win_rate']:.1f}%")
            logger.info(f"   Entry Score: {r['params']['entry_score_threshold']}, "
                       f"Confidence: {r['params']['min_confidence']:.2f}, "
                       f"Confirmations: {r['params']['require_confirmations']}")

        return {
            'best_params': best_params,
            'best_sharpe': best_sharpe,
            'all_results': results[:10]
        }


# Main execution
async def main():
    """
    Run complete backtesting suite
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Initialize backtester
    backtester = BTCHistoricalBacktest(initial_capital=10000)

    # Run complete backtest across all regimes
    summary = await backtester.run_complete_backtest()

    # Save results
    summary.to_csv('backtest_results.csv', index=False)
    logger.info("\nResults saved to backtest_results.csv")

    # Display summary
    print("\n" + "="*60)
    print("BACKTEST SUMMARY TABLE")
    print("="*60)
    print(summary.to_string())

    # Optimize parameters
    print("\n" + "="*60)
    print("RUNNING PARAMETER OPTIMIZATION...")
    print("="*60)

    optimization = await backtester.optimize_parameters()

    print("\nBEST PARAMETERS FOUND:")
    for param, value in optimization['best_params'].items():
        print(f"  {param}: {value}")


if __name__ == "__main__":
    asyncio.run(main())