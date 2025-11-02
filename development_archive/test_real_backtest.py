"""
Test backtesting with REAL historical data
Verify we're no longer using mock data
"""
import asyncio
import logging
from datetime import datetime, timedelta
from backtest.btc_historical_backtest import BTCHistoricalBacktest

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_real_backtest():
    """Test backtesting with real data"""
    print("=" * 60)
    print("TESTING BACKTESTING WITH REAL DATA")
    print("=" * 60)

    # Initialize backtester
    backtester = BTCHistoricalBacktest(initial_capital=10000)

    # Test with recent real data (last 7 days)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    print(f"\nBacktesting Period: {start_date} to {end_date}")
    print("Fetching REAL historical data...")

    # Fetch real data
    df = await backtester.fetch_historical_data(start_date, end_date, '1h')

    if df.empty:
        print("❌ FAILED: No data returned")
        return

    print(f"✅ SUCCESS: Fetched {len(df)} real data points")

    # Verify this is real data by checking price levels
    latest_price = df['close'].iloc[-1]
    price_range = f"${df['low'].min():,.0f} - ${df['high'].max():,.0f}"

    print(f"\nData Verification:")
    print(f"  Latest BTC Price: ${latest_price:,.2f}")
    print(f"  Price Range: {price_range}")
    print(f"  Data Points: {len(df)}")

    # Check if this looks like real BTC data (should be around 100k-120k range)
    if 90000 < latest_price < 130000:
        print("  ✅ Price levels match real BTC market")
    else:
        print("  ⚠️ WARNING: Price levels seem unusual")

    # Run a simple backtest simulation
    print("\nRunning backtest simulation...")

    # Simple strategy: Buy when unified_score > 60
    trades = []
    position = None
    capital = 10000

    for i in range(20, len(df)):  # Start at 20 to have enough history
        row = df.iloc[i]
        price = row['close']

        # Check for unified score (if available)
        score = row.get('unified_score', 50)

        # Entry logic
        if position is None and score > 60:
            position = {
                'entry_price': price,
                'entry_time': df.index[i],
                'score': score
            }
            print(f"  BUY at ${price:,.2f} (score: {score:.1f})")

        # Exit logic
        elif position is not None and (score < 40 or i == len(df) - 1):
            exit_price = price
            pnl = (exit_price - position['entry_price']) / position['entry_price'] * 100
            position['exit_price'] = exit_price
            position['exit_time'] = df.index[i]
            position['pnl_pct'] = pnl
            trades.append(position)
            print(f"  SELL at ${exit_price:,.2f} (P&L: {pnl:+.2f}%)")
            position = None

    # Summary
    print("\n" + "=" * 40)
    print("BACKTEST SUMMARY")
    print("=" * 40)

    if trades:
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t['pnl_pct'] > 0)
        total_pnl = sum(t['pnl_pct'] for t in trades)
        avg_pnl = total_pnl / total_trades

        print(f"Total Trades: {total_trades}")
        print(f"Winning Trades: {winning_trades} ({winning_trades/total_trades*100:.1f}%)")
        print(f"Total P&L: {total_pnl:+.2f}%")
        print(f"Average P&L per Trade: {avg_pnl:+.2f}%")
    else:
        print("No trades executed in test period")

    # Verify data quality
    print("\n" + "=" * 40)
    print("DATA QUALITY CHECK")
    print("=" * 40)

    print(f"Columns available: {df.columns.tolist()}")
    print(f"NaN values: {df.isna().sum().sum()}")
    print(f"Data completeness: {(1 - df.isna().sum().sum() / df.size) * 100:.1f}%")

    # Check for technical indicators
    tech_cols = ['rsi', 'sma_20', 'sma_50', 'momentum']
    available_tech = [col for col in tech_cols if col in df.columns]
    print(f"Technical indicators: {available_tech}")

    print("\n" + "=" * 60)
    print("REAL DATA BACKTEST TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_real_backtest())