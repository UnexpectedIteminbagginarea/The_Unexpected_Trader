"""
Debug script to show exactly how Fibonacci levels are being calculated
and why golden pockets aren't being detected
"""
import pandas as pd
import numpy as np
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.historical_data_fetcher import HistoricalDataFetcher


async def debug_fibonacci_calculation():
    """
    Show exactly what's happening with Fibonacci calculations
    """
    print("=" * 80)
    print("DEBUGGING FIBONACCI & GOLDEN POCKET CALCULATION")
    print("=" * 80)

    # Fetch real data
    fetcher = HistoricalDataFetcher()

    # Get MULTIPLE TIMEFRAMES
    end_date = '2025-10-29'
    start_date = '2025-09-29'

    print("\n📊 FETCHING MULTIPLE TIMEFRAMES...")

    # Fetch 1-hour data
    df_1h = await fetcher.fetch_btc_historical_data(start_date, end_date, '1h')
    print(f"✅ 1H Data: {len(df_1h)} candles")

    # Fetch 4-hour data (using 1h and resample)
    df_4h = df_1h.resample('4H').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    print(f"✅ 4H Data: {len(df_4h)} candles")

    # Fetch daily data
    df_daily = df_1h.resample('D').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    print(f"✅ Daily Data: {len(df_daily)} candles")

    print("\n" + "=" * 80)
    print("CURRENT FIBONACCI CALCULATION METHOD:")
    print("=" * 80)

    def calculate_fibonacci_simple(df, lookback=50):
        """Current simple method"""
        # Rolling window approach (PROBLEMATIC)
        df['swing_high'] = df['high'].rolling(lookback).max()
        df['swing_low'] = df['low'].rolling(lookback).min()
        df['fib_range'] = df['swing_high'] - df['swing_low']

        # Fibonacci levels
        df['fib_618'] = df['swing_high'] - (df['fib_range'] * 0.618)
        df['fib_650'] = df['swing_high'] - (df['fib_range'] * 0.650)

        # Golden pocket detection
        df['in_golden_pocket'] = (
            (df['close'] <= df['fib_618']) &
            (df['close'] >= df['fib_650'])
        )

        return df

    # Apply to 1H data
    df_1h = calculate_fibonacci_simple(df_1h.copy())

    # Show last 10 rows with calculations
    print("\n📈 LAST 10 1H CANDLES WITH FIBONACCI LEVELS:")
    print("-" * 80)

    for i in range(-10, 0):
        row = df_1h.iloc[i]
        print(f"\n{df_1h.index[i].strftime('%Y-%m-%d %H:%M')}")
        print(f"  Price: ${row['close']:,.0f}")
        print(f"  Swing High: ${row['swing_high']:,.0f}")
        print(f"  Swing Low: ${row['swing_low']:,.0f}")
        print(f"  Range: ${row['fib_range']:,.0f}")
        print(f"  Golden Pocket:")
        print(f"    Top (61.8%): ${row['fib_618']:,.0f}")
        print(f"    Bottom (65%): ${row['fib_650']:,.0f}")
        print(f"    Zone Width: ${row['fib_618'] - row['fib_650']:,.0f}")

        # Check if price is in golden pocket
        if row['close'] <= row['fib_618'] and row['close'] >= row['fib_650']:
            print(f"  ✅ IN GOLDEN POCKET!")
        else:
            distance_to_gp = min(
                abs(row['close'] - row['fib_618']),
                abs(row['close'] - row['fib_650'])
            )
            print(f"  ❌ NOT in GP (${distance_to_gp:,.0f} away)")

    print("\n" + "=" * 80)
    print("WHY GOLDEN POCKETS AREN'T BEING DETECTED:")
    print("=" * 80)

    # Analysis
    latest = df_1h.iloc[-1]
    gp_zone_width = latest['fib_618'] - latest['fib_650']
    gp_zone_pct = gp_zone_width / latest['close'] * 100

    print(f"\n1. ZONE TOO NARROW:")
    print(f"   Golden Pocket width: ${gp_zone_width:,.0f} ({gp_zone_pct:.2f}% of price)")
    print(f"   At BTC price ${latest['close']:,.0f}, this is only a {gp_zone_pct:.2f}% zone!")

    print(f"\n2. PRICE POSITION:")
    print(f"   Current Price: ${latest['close']:,.0f}")
    print(f"   GP Top: ${latest['fib_618']:,.0f}")
    print(f"   GP Bottom: ${latest['fib_650']:,.0f}")

    if latest['close'] > latest['fib_618']:
        pct_above = (latest['close'] - latest['fib_618']) / latest['close'] * 100
        print(f"   Price is {pct_above:.1f}% ABOVE golden pocket")
    elif latest['close'] < latest['fib_650']:
        pct_below = (latest['fib_650'] - latest['close']) / latest['close'] * 100
        print(f"   Price is {pct_below:.1f}% BELOW golden pocket")

    print("\n" + "=" * 80)
    print("MULTI-TIMEFRAME FIBONACCI COMPARISON:")
    print("=" * 80)

    # Calculate Fibonacci for each timeframe
    timeframes = {
        '1H': df_1h,
        '4H': calculate_fibonacci_simple(df_4h.copy(), lookback=20),
        'Daily': calculate_fibonacci_simple(df_daily.copy(), lookback=10)
    }

    print("\n📊 GOLDEN POCKET ZONES BY TIMEFRAME:")
    print("-" * 40)

    overlapping_zones = []

    for tf_name, tf_df in timeframes.items():
        if len(tf_df) > 0:
            latest_tf = tf_df.iloc[-1]
            print(f"\n{tf_name}:")
            print(f"  Swing High: ${latest_tf['swing_high']:,.0f}")
            print(f"  Swing Low: ${latest_tf['swing_low']:,.0f}")
            print(f"  GP Top (61.8%): ${latest_tf['fib_618']:,.0f}")
            print(f"  GP Bottom (65%): ${latest_tf['fib_650']:,.0f}")
            print(f"  Zone Width: ${latest_tf['fib_618'] - latest_tf['fib_650']:,.0f}")

            overlapping_zones.append({
                'timeframe': tf_name,
                'top': latest_tf['fib_618'],
                'bottom': latest_tf['fib_650']
            })

    # Check for overlaps
    print("\n" + "=" * 80)
    print("🎯 MULTI-TIMEFRAME OVERLAP ANALYSIS:")
    print("=" * 80)

    current_price = df_1h.iloc[-1]['close']

    # Find overlapping zones
    if len(overlapping_zones) >= 2:
        # Check 1H vs 4H overlap
        zone_1h = overlapping_zones[0]
        zone_4h = overlapping_zones[1]

        overlap_top = min(zone_1h['top'], zone_4h['top'])
        overlap_bottom = max(zone_1h['bottom'], zone_4h['bottom'])

        if overlap_bottom < overlap_top:
            print(f"\n✅ OVERLAP FOUND between 1H and 4H!")
            print(f"   Overlap Zone: ${overlap_bottom:,.0f} - ${overlap_top:,.0f}")
            print(f"   Zone Width: ${overlap_top - overlap_bottom:,.0f}")

            if current_price >= overlap_bottom and current_price <= overlap_top:
                print(f"   🎯 CURRENT PRICE IS IN OVERLAP ZONE!")
            else:
                print(f"   Current price ${current_price:,.0f} is outside overlap")
        else:
            print(f"\n❌ No overlap between 1H and 4H golden pockets")
            print(f"   1H: ${zone_1h['bottom']:,.0f} - ${zone_1h['top']:,.0f}")
            print(f"   4H: ${zone_4h['bottom']:,.0f} - ${zone_4h['top']:,.0f}")

    print("\n" + "=" * 80)
    print("💡 SOLUTION: WIDEN GOLDEN POCKET ZONE")
    print("=" * 80)

    print("\nCurrent: 61.8% to 65% (3.2% range)")
    print("Better: 61.8% to 70% (8.2% range)")
    print("Or use ATR-based dynamic buffer")

    # Test with wider zone
    print("\n🔧 TESTING WITH WIDER ZONE (61.8% to 70%):")

    df_test = df_1h.copy()
    df_test['fib_700'] = df_test['swing_high'] - (df_test['fib_range'] * 0.70)
    df_test['in_golden_pocket_wide'] = (
        (df_test['close'] <= df_test['fib_618']) &
        (df_test['close'] >= df_test['fib_700'])
    )

    gp_detections_narrow = df_1h['in_golden_pocket'].sum()
    gp_detections_wide = df_test['in_golden_pocket_wide'].sum()

    print(f"\nDetections with narrow zone (61.8-65%): {gp_detections_narrow}")
    print(f"Detections with wider zone (61.8-70%): {gp_detections_wide}")

    if gp_detections_wide > 0:
        print(f"\n✅ FOUND {gp_detections_wide} GOLDEN POCKETS WITH WIDER ZONE!")

        # Show recent wide golden pockets
        recent_gp = df_test[df_test['in_golden_pocket_wide']].tail(5)
        if not recent_gp.empty:
            print("\nRecent Golden Pocket Entries (Wide Zone):")
            for idx, row in recent_gp.iterrows():
                print(f"  {idx}: ${row['close']:,.0f}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(debug_fibonacci_calculation())