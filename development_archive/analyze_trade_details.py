"""
Analyze trade details from our backtests
Show leverage, position sizing, and exit strategies
"""
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
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


class TradeAnalyzer:
    """
    Detailed analysis of trade execution
    """

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.data_fetcher = HistoricalDataFetcher()
        self.gp_detector = MultiTimeframeGoldenPocket()

        # Current parameters being used
        self.params = {
            'stop_loss': 0.06,          # 6% stop loss
            'take_profit': 0.12,        # 12% take profit
            'max_position_size': 0.60,   # 60% of capital max
            'confidence_threshold': 0.55 # 55% minimum confidence
        }

    async def analyze_trades_in_detail(self, days: int = 30):
        """
        Analyze each trade in detail
        """
        print("=" * 80)
        print("DETAILED TRADE ANALYSIS")
        print("=" * 80)

        # Fetch data
        end_date = '2025-10-29'
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=days)).strftime('%Y-%m-%d')

        df_1h = await self.data_fetcher.fetch_btc_historical_data(start_date, end_date, '1h')

        if df_1h.empty:
            print("Failed to fetch data")
            return

        print(f"\n📊 Analyzing {days} days of data")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Max Position Size: {self.params['max_position_size']:.0%} of capital")
        print(f"Stop Loss: {self.params['stop_loss']:.0%}")
        print(f"Take Profit: {self.params['take_profit']:.0%}")

        # Detect golden pockets
        timeframe_data = self.gp_detector.detect_all_timeframes(df_1h)
        confluence_df = self.gp_detector.find_confluence_zones(timeframe_data)

        # Simulate trades with detailed tracking
        trades = []
        position = None
        trade_num = 0

        for i in range(50, len(confluence_df)):
            row = confluence_df.iloc[i]
            current_price = row['close']

            # ENTRY
            if position is None and row['gp_confirmations'] >= 1:
                confidence = row['gp_confidence']

                if confidence >= self.params['confidence_threshold'] or row['gp_confirmations'] >= 2:
                    trade_num += 1

                    # Calculate exact position sizing
                    position_size_pct = self.params['max_position_size'] * confidence
                    position_value = self.current_capital * position_size_pct

                    # Calculate effective leverage
                    # If using 60% of capital, that's like 0.6x leverage (no real leverage)
                    effective_leverage = position_size_pct

                    position = {
                        'trade_num': trade_num,
                        'entry_idx': i,
                        'entry_time': confluence_df.index[i],
                        'entry_price': current_price,
                        'capital_at_entry': self.current_capital,
                        'position_size_pct': position_size_pct,
                        'position_value': position_value,
                        'shares': position_value / current_price,
                        'effective_leverage': effective_leverage,
                        'confidence': confidence,
                        'gp_confirmations': row['gp_confirmations'],
                        'stop_loss': current_price * (1 - self.params['stop_loss']),
                        'take_profit': current_price * (1 + self.params['take_profit']),
                        'stop_distance_pct': self.params['stop_loss'],
                        'target_distance_pct': self.params['take_profit'],
                        'risk_amount': position_value * self.params['stop_loss'],
                        'reward_amount': position_value * self.params['take_profit'],
                        'risk_reward_ratio': self.params['take_profit'] / self.params['stop_loss']
                    }

                    print(f"\n" + "=" * 60)
                    print(f"TRADE #{trade_num} OPENED")
                    print(f"Time: {position['entry_time']}")
                    print(f"Entry Price: ${current_price:,.2f}")
                    print(f"Capital: ${self.current_capital:,.2f}")
                    print(f"Position Size: {position_size_pct:.1%} of capital (${position_value:,.2f})")
                    print(f"Effective Leverage: {effective_leverage:.2f}x")
                    print(f"Confidence: {confidence:.0%}")
                    print(f"GP Confirmations: {row['gp_confirmations']}")
                    print(f"Stop Loss: ${position['stop_loss']:,.2f} (-{self.params['stop_loss']:.0%})")
                    print(f"Take Profit: ${position['take_profit']:,.2f} (+{self.params['take_profit']:.0%})")
                    print(f"Risk Amount: ${position['risk_amount']:,.2f}")
                    print(f"Reward Amount: ${position['reward_amount']:,.2f}")
                    print(f"Risk/Reward Ratio: 1:{position['risk_reward_ratio']:.1f}")

            # EXIT
            elif position is not None:
                # Track price movement
                price_change_pct = (current_price - position['entry_price']) / position['entry_price'] * 100

                # Check exit conditions
                hit_stop = current_price <= position['stop_loss']
                hit_target = current_price >= position['take_profit']

                if hit_stop or hit_target or i == len(confluence_df) - 1:
                    exit_price = current_price
                    exit_reason = 'STOP_LOSS' if hit_stop else 'TAKE_PROFIT' if hit_target else 'END_OF_DATA'

                    # Calculate P&L
                    pnl = (exit_price - position['entry_price']) * position['shares']
                    pnl_pct = (exit_price - position['entry_price']) / position['entry_price'] * 100

                    # Update capital
                    self.current_capital += pnl

                    # Calculate actual vs expected
                    if hit_stop:
                        actual_loss_pct = pnl_pct
                        expected_loss_pct = -self.params['stop_loss'] * 100
                        slippage = abs(actual_loss_pct - expected_loss_pct)
                    elif hit_target:
                        actual_gain_pct = pnl_pct
                        expected_gain_pct = self.params['take_profit'] * 100
                        slippage = abs(actual_gain_pct - expected_gain_pct)
                    else:
                        slippage = 0

                    # Record detailed trade
                    trade_record = {
                        **position,
                        'exit_time': confluence_df.index[i],
                        'exit_price': exit_price,
                        'exit_reason': exit_reason,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'hold_time_hours': (i - position['entry_idx']),
                        'capital_after': self.current_capital,
                        'slippage_pct': slippage
                    }
                    trades.append(trade_record)

                    print(f"\nTRADE #{position['trade_num']} CLOSED")
                    print(f"Exit Time: {confluence_df.index[i]}")
                    print(f"Exit Price: ${exit_price:,.2f}")
                    print(f"Exit Reason: {exit_reason}")
                    print(f"P&L: ${pnl:,.2f} ({pnl_pct:+.2f}%)")
                    print(f"Hold Time: {trade_record['hold_time_hours']} hours")
                    print(f"Capital After: ${self.current_capital:,.2f}")
                    if slippage > 0:
                        print(f"Slippage: {slippage:.2f}%")

                    position = None

        # Summary Analysis
        if trades:
            self.print_summary_analysis(trades)

        return trades

    def print_summary_analysis(self, trades: list):
        """
        Print detailed summary analysis
        """
        print("\n" + "=" * 80)
        print("SUMMARY ANALYSIS")
        print("=" * 80)

        df_trades = pd.DataFrame(trades)

        print(f"\n📊 OVERALL STATISTICS:")
        print(f"Total Trades: {len(trades)}")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Final Capital: ${self.current_capital:,.2f}")
        print(f"Total Return: {(self.current_capital - self.initial_capital) / self.initial_capital * 100:+.2f}%")

        # Win/Loss Analysis
        winners = df_trades[df_trades['pnl'] > 0]
        losers = df_trades[df_trades['pnl'] <= 0]

        print(f"\n📈 WIN/LOSS ANALYSIS:")
        print(f"Winners: {len(winners)} ({len(winners)/len(trades)*100:.1f}%)")
        print(f"Losers: {len(losers)} ({len(losers)/len(trades)*100:.1f}%)")
        if len(winners) > 0:
            print(f"Average Win: {winners['pnl_pct'].mean():+.2f}%")
            print(f"Largest Win: {winners['pnl_pct'].max():+.2f}%")
        if len(losers) > 0:
            print(f"Average Loss: {losers['pnl_pct'].mean():+.2f}%")
            print(f"Largest Loss: {losers['pnl_pct'].min():+.2f}%")

        # Position Sizing Analysis
        print(f"\n💰 POSITION SIZING:")
        print(f"Average Position Size: {df_trades['position_size_pct'].mean():.1%} of capital")
        print(f"Largest Position: {df_trades['position_size_pct'].max():.1%} of capital")
        print(f"Smallest Position: {df_trades['position_size_pct'].min():.1%} of capital")
        print(f"Average Position Value: ${df_trades['position_value'].mean():,.2f}")

        # Leverage Analysis
        print(f"\n🔧 LEVERAGE ANALYSIS:")
        print(f"Average Effective Leverage: {df_trades['effective_leverage'].mean():.2f}x")
        print(f"Max Leverage Used: {df_trades['effective_leverage'].max():.2f}x")
        print(f"Note: No actual leverage - just % of capital used")

        # Exit Analysis
        print(f"\n🚪 EXIT ANALYSIS:")
        exit_reasons = df_trades['exit_reason'].value_counts()
        for reason, count in exit_reasons.items():
            print(f"{reason}: {count} ({count/len(trades)*100:.1f}%)")

        # Risk Management
        print(f"\n⚠️ RISK MANAGEMENT:")
        print(f"Average Risk per Trade: ${df_trades['risk_amount'].mean():,.2f}")
        print(f"Average Risk/Reward Ratio: 1:{df_trades['risk_reward_ratio'].mean():.1f}")
        print(f"Stop Loss Hit Rate: {(df_trades['exit_reason'] == 'STOP_LOSS').sum()/len(trades)*100:.1f}%")
        print(f"Take Profit Hit Rate: {(df_trades['exit_reason'] == 'TAKE_PROFIT').sum()/len(trades)*100:.1f}%")

        # Timing Analysis
        print(f"\n⏱️ TIMING ANALYSIS:")
        print(f"Average Hold Time: {df_trades['hold_time_hours'].mean():.1f} hours")
        print(f"Longest Hold: {df_trades['hold_time_hours'].max()} hours")
        print(f"Shortest Hold: {df_trades['hold_time_hours'].min()} hours")

        # Golden Pocket Analysis
        print(f"\n✨ GOLDEN POCKET ANALYSIS:")
        gp_trades = df_trades[df_trades['gp_confirmations'] > 0]
        multi_tf_trades = df_trades[df_trades['gp_confirmations'] >= 2]

        print(f"Trades with GP Signal: {len(gp_trades)} ({len(gp_trades)/len(trades)*100:.1f}%)")
        if len(gp_trades) > 0:
            gp_winners = gp_trades[gp_trades['pnl'] > 0]
            print(f"GP Win Rate: {len(gp_winners)/len(gp_trades)*100:.1f}%")

        if len(multi_tf_trades) > 0:
            print(f"Multi-TF Confluence Trades: {len(multi_tf_trades)}")
            mtf_winners = multi_tf_trades[multi_tf_trades['pnl'] > 0]
            print(f"Multi-TF Win Rate: {len(mtf_winners)/len(multi_tf_trades)*100:.1f}%")

        # Confidence Analysis
        print(f"\n🎯 CONFIDENCE ANALYSIS:")
        print(f"Average Entry Confidence: {df_trades['confidence'].mean():.0%}")

        # Correlation between confidence and success
        if len(df_trades) > 1:
            correlation = df_trades['confidence'].corr(df_trades['pnl_pct'])
            print(f"Confidence-Return Correlation: {correlation:.2f}")
            if correlation > 0.3:
                print("  ✅ Higher confidence correlates with better returns")
            elif correlation < -0.3:
                print("  ❌ Higher confidence correlates with worse returns")
            else:
                print("  ⚠️ No clear correlation between confidence and returns")


async def main():
    """
    Run detailed trade analysis
    """
    analyzer = TradeAnalyzer(initial_capital=10000)

    print("🔍 Analyzing trades with current parameters...")
    trades = await analyzer.analyze_trades_in_detail(days=30)

    if trades:
        print(f"\n✅ Analysis complete! Analyzed {len(trades)} trades")
    else:
        print("\n⚠️ No trades executed in the period")


if __name__ == "__main__":
    asyncio.run(main())