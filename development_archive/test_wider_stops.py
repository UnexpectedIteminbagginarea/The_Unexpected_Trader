"""
Test with wider 6% stops and proper swing points
"""
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.historical_data_fetcher import HistoricalDataFetcher
from core.multi_timeframe_golden_pocket import MultiTimeframeGoldenPocket

async def test_wider_stops():
    fetcher = HistoricalDataFetcher()
    detector = MultiTimeframeGoldenPocket()

    # Fetch MORE data to find proper swings
    end_date = '2025-10-29'
    start_date = '2025-06-01'  # Go back to June for proper swings!

    print(f"📊 Fetching data from {start_date} to {end_date}")
    df = await fetcher.fetch_btc_historical_data(start_date, end_date, '1h')

    if df.empty:
        print("Failed to fetch data")
        return

    print(f"✅ Loaded {len(df)} hourly candles")

    # Find ACTUAL swing points on DAILY timeframe
    daily_df = df.resample('1D').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })

    print(f"\n🔍 Finding major swings in daily data...")

    # Find lowest low (June area)
    june_july_data = daily_df['2025-06-01':'2025-07-31']
    swing_low = june_july_data['low'].min()
    swing_low_date = june_july_data['low'].idxmin()

    # Find highest high (October area)
    oct_data = daily_df['2025-10-01':'2025-10-15']
    swing_high = oct_data['high'].max()
    swing_high_date = oct_data['high'].idxmax()

    print(f"\n📍 MAJOR SWINGS FOUND:")
    print(f"  Swing Low: ${swing_low:,.0f} on {swing_low_date.strftime('%Y-%m-%d')}")
    print(f"  Swing High: ${swing_high:,.0f} on {swing_high_date.strftime('%Y-%m-%d')}")
    print(f"  Range: ${swing_high - swing_low:,.0f}")

    # Calculate PROPER Fibonacci levels from these swings
    fib_range = swing_high - swing_low
    fib_levels = {
        '0.0%': swing_high,
        '23.6%': swing_high - (fib_range * 0.236),
        '38.2%': swing_high - (fib_range * 0.382),
        '50.0%': swing_high - (fib_range * 0.500),
        '61.8%': swing_high - (fib_range * 0.618),
        '65.0%': swing_high - (fib_range * 0.650),
        '78.6%': swing_high - (fib_range * 0.786),
        '100.0%': swing_low
    }

    print(f"\n📏 FIBONACCI LEVELS:")
    for level, price in fib_levels.items():
        print(f"  {level}: ${price:,.0f}")

    # Golden Pocket Zone
    gp_top = fib_levels['61.8%']
    gp_bottom = fib_levels['65.0%']
    print(f"\n✨ GOLDEN POCKET ZONE: ${gp_top:,.0f} - ${gp_bottom:,.0f}")
    print(f"  Zone width: ${gp_top - gp_bottom:,.0f} ({(gp_top - gp_bottom)/swing_high*100:.2f}% of price)")

    # Test trades with different stop losses
    print("\n" + "="*60)
    print("TESTING STOP LOSS SCENARIOS")
    print("="*60)

    # Get recent data for testing
    test_df = df['2025-09-29':'2025-10-29']

    # Detect when price enters golden pocket
    test_df['in_golden_pocket'] = (
        (test_df['close'] <= gp_top) &
        (test_df['close'] >= gp_bottom)
    )

    gp_entries = test_df[test_df['in_golden_pocket']]
    print(f"\n📊 Golden Pocket entries in last 30 days: {len(gp_entries)}")

    # Simulate trades with different stops
    stop_percentages = [0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10]

    for stop_pct in stop_percentages:
        wins = 0
        losses = 0
        total_pnl_pct = 0

        # Take first 5 GP entries for testing
        for idx, entry_row in gp_entries.head(5).iterrows():
            entry_price = entry_row['close']
            stop_price = entry_price * (1 - stop_pct)
            target_price = entry_price * 1.10  # 10% target

            # Check what happens after entry
            future_data = test_df[idx:].iloc[1:50]  # Next 50 bars

            if len(future_data) > 0:
                # Check if stop or target hit first
                for _, bar in future_data.iterrows():
                    if bar['low'] <= stop_price:
                        losses += 1
                        total_pnl_pct -= stop_pct * 100
                        break
                    elif bar['high'] >= target_price:
                        wins += 1
                        total_pnl_pct += 10
                        break

        total_trades = wins + losses
        if total_trades > 0:
            win_rate = wins / total_trades * 100
            avg_pnl = total_pnl_pct / total_trades
            print(f"\n{stop_pct*100:.0f}% Stop Loss:")
            print(f"  Wins: {wins}, Losses: {losses}")
            print(f"  Win Rate: {win_rate:.0f}%")
            print(f"  Avg P&L: {avg_pnl:+.2f}%")

    # Check current price position relative to Fibs
    current_price = test_df.iloc[-1]['close']
    print(f"\n📍 CURRENT BTC POSITION:")
    print(f"  Price: ${current_price:,.0f}")

    # Find closest Fib level
    for level, price in fib_levels.items():
        if current_price >= price:
            print(f"  Above {level} (${price:,.0f})")
            break

if __name__ == "__main__":
    asyncio.run(test_wider_stops())