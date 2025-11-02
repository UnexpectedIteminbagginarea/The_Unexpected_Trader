"""
Test script to verify real historical data fetching works
"""
import asyncio
from data.historical_data_fetcher import HistoricalDataFetcher
from datetime import datetime, timedelta


async def test_real_data():
    """Test that we can fetch real historical data"""
    print("=" * 60)
    print("TESTING REAL HISTORICAL DATA FETCHER")
    print("=" * 60)

    fetcher = HistoricalDataFetcher()

    # Test 1: Recent data (last 7 days)
    print("\nTest 1: Fetching last 7 days of BTC data...")
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    df = await fetcher.fetch_btc_historical_data(start_date, end_date, '1h')

    if not df.empty:
        print(f"✅ SUCCESS: Fetched {len(df)} hourly candles")
        print(f"   Date range: {df.index.min()} to {df.index.max()}")
        print(f"   Latest price: ${df['close'].iloc[-1]:,.2f}")
        print(f"   Columns: {df.columns.tolist()}")
        print("\n   Sample data (last 5 rows):")
        print(df.tail())
    else:
        print("❌ FAILED: No data returned")

    # Test 2: Medium-term data (last 30 days)
    print("\n" + "=" * 40)
    print("\nTest 2: Fetching last 30 days of BTC data...")
    start_date_30 = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    df_30 = await fetcher.fetch_btc_historical_data(start_date_30, end_date, '4h')

    if not df_30.empty:
        print(f"✅ SUCCESS: Fetched {len(df_30)} 4-hour candles")
        print(f"   Date range: {df_30.index.min()} to {df_30.index.max()}")
        print(f"   Price range: ${df_30['low'].min():,.2f} - ${df_30['high'].max():,.2f}")
    else:
        print("❌ FAILED: No data returned")

    # Test 3: Create full backtest dataset
    print("\n" + "=" * 40)
    print("\nTest 3: Creating comprehensive backtest dataset...")
    backtest_df = await fetcher.create_backtest_dataset(start_date, end_date)

    if not backtest_df.empty:
        print(f"✅ SUCCESS: Created backtest dataset")
        print(f"   Shape: {backtest_df.shape}")
        print(f"   Columns: {backtest_df.columns.tolist()}")

        # Check for technical indicators
        tech_indicators = ['sma_20', 'sma_50', 'rsi', 'bb_upper', 'bb_lower']
        available = [ind for ind in tech_indicators if ind in backtest_df.columns]
        print(f"   Technical indicators: {available}")

        # Check for sentiment data
        sentiment_cols = ['fear_greed', 'long_short_ratio', 'funding_rate']
        available_sent = [col for col in sentiment_cols if col in backtest_df.columns]
        print(f"   Sentiment data: {available_sent}")

        # Data quality
        nan_count = backtest_df.isna().sum().sum()
        completeness = (1 - nan_count / backtest_df.size) * 100
        print(f"   Data completeness: {completeness:.1f}%")
    else:
        print("❌ FAILED: No backtest data created")

    print("\n" + "=" * 60)
    print("REAL DATA FETCHER TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_real_data())