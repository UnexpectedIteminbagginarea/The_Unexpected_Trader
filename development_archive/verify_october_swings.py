"""
Verify October swing points on 4H timeframe
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data.historical_data_fetcher import HistoricalDataFetcher
import pandas as pd

async def verify_october_swings():
    fetcher = HistoricalDataFetcher()

    # Get October data
    df = await fetcher.fetch_btc_historical_data('2025-10-01', '2025-10-29', '1h')

    # Create 4H timeframe
    df_4h = df.resample('4H').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })

    # Also check daily for comparison
    daily = df.resample('1D').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })

    print("=" * 80)
    print("🔍 OCTOBER SWING ANALYSIS")
    print("=" * 80)

    # Find October 6 area high
    oct_5_7 = df_4h['2025-10-05':'2025-10-07']
    oct_high = oct_5_7['high'].max()
    oct_high_time = oct_5_7['high'].idxmax()

    print(f"\n📈 OCTOBER HIGH (4H):")
    print(f"  Date: {oct_high_time}")
    print(f"  Price: ${oct_high:,.0f}")

    # Find October 17 area low
    oct_16_18 = df_4h['2025-10-16':'2025-10-18']
    oct_low = oct_16_18['low'].min()
    oct_low_time = oct_16_18['low'].idxmin()

    print(f"\n📉 OCTOBER LOW (4H):")
    print(f"  Date: {oct_low_time}")
    print(f"  Price: ${oct_low:,.0f}")

    # Calculate 4H Fibonacci levels
    range_4h = oct_high - oct_low

    print(f"\n📏 4H TIMEFRAME FIBONACCI LEVELS:")
    print(f"  Range: ${range_4h:,.0f}")

    fib_levels_4h = {
        '0.0%': oct_high,
        '23.6%': oct_high - (range_4h * 0.236),
        '38.2%': oct_high - (range_4h * 0.382),
        '50.0%': oct_high - (range_4h * 0.500),
        '61.8%': oct_high - (range_4h * 0.618),
        '65.0%': oct_high - (range_4h * 0.650),
        '78.6%': oct_high - (range_4h * 0.786),
        '100.0%': oct_low
    }

    for level, price in fib_levels_4h.items():
        marker = " ← Golden Pocket Zone" if level in ['61.8%', '65.0%'] else ""
        print(f"  {level:>6}: ${price:,.0f}{marker}")

    print(f"\n🎯 4H GOLDEN POCKET: ${fib_levels_4h['61.8%']:,.0f} - ${fib_levels_4h['65.0%']:,.0f}")

    # Compare with daily timeframe (June-Oct)
    print("\n" + "=" * 80)
    print("📊 COMPARISON WITH DAILY TIMEFRAME")
    print("=" * 80)

    # Get June-July data for daily swings
    df_full = await fetcher.fetch_btc_historical_data('2025-06-01', '2025-10-29', '1h')
    daily_full = df_full.resample('1D').agg({
        'high': 'max',
        'low': 'min',
        'close': 'last'
    })

    # Daily timeframe swings
    june_july = daily_full['2025-06-01':'2025-07-31']
    daily_low = june_july['low'].min()
    daily_low_date = june_july['low'].idxmin()

    october = daily_full['2025-10-01':'2025-10-15']
    daily_high = october['high'].max()
    daily_high_date = october['high'].idxmax()

    range_daily = daily_high - daily_low

    print(f"\n📈 DAILY TIMEFRAME (June-Oct):")
    print(f"  Low: ${daily_low:,.0f} ({daily_low_date.date()})")
    print(f"  High: ${daily_high:,.0f} ({daily_high_date.date()})")
    print(f"  Range: ${range_daily:,.0f}")

    fib_levels_daily = {
        '50.0%': daily_high - (range_daily * 0.500),
        '61.8%': daily_high - (range_daily * 0.618),
        '65.0%': daily_high - (range_daily * 0.650),
    }

    print(f"\n📏 DAILY FIBONACCI LEVELS:")
    for level, price in fib_levels_daily.items():
        print(f"  {level}: ${price:,.0f}")

    print(f"\n🎯 DAILY GOLDEN POCKET: ${fib_levels_daily['61.8%']:,.0f} - ${fib_levels_daily['65.0%']:,.0f}")

    # Check current price position
    current_price = df.iloc[-1]['close']
    print(f"\n💹 CURRENT PRICE: ${current_price:,.0f}")

    # Check position relative to both timeframes
    print("\n📍 POSITION ANALYSIS:")

    # 4H timeframe position
    for level, price in fib_levels_4h.items():
        if current_price >= price:
            print(f"  4H: Currently above {level} (${price:,.0f})")
            break

    # Daily timeframe position
    if current_price > fib_levels_daily['50.0%']:
        print(f"  Daily: Above 50% retracement")
    elif current_price > fib_levels_daily['61.8%']:
        print(f"  Daily: Between 50% and 61.8%")
    elif current_price > fib_levels_daily['65.0%']:
        print(f"  Daily: In golden pocket zone!")
    else:
        print(f"  Daily: Below golden pocket")

    # Trading opportunities
    print("\n🎯 MULTI-TIMEFRAME CONFLUENCE:")
    print("  When BOTH timeframes show golden pocket = HIGHEST conviction")
    print("  When ONE timeframe shows golden pocket = MODERATE conviction")
    print("  Scale position size based on confluence")

    return {
        '4h': {
            'high': oct_high,
            'low': oct_low,
            'fibs': fib_levels_4h
        },
        'daily': {
            'high': daily_high,
            'low': daily_low,
            'fibs': fib_levels_daily
        }
    }

if __name__ == "__main__":
    asyncio.run(verify_october_swings())