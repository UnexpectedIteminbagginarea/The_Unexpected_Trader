"""
Debug version of ultra-aggressive strategy
Shows exactly what's happening with golden pocket signals
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

async def debug_strategy():
    fetcher = HistoricalDataFetcher()
    detector = MultiTimeframeGoldenPocket()

    # Fetch data
    end_date = '2025-10-29'
    start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')

    print("📊 Fetching data...")
    df_1h = await fetcher.fetch_btc_historical_data(start_date, end_date, '1h')

    # Detect golden pockets
    print("🔍 Detecting golden pockets...")
    timeframe_data = detector.detect_all_timeframes(df_1h)
    confluence_df = detector.find_confluence_zones(timeframe_data)

    print(f"✅ Data loaded: {len(confluence_df)} candles")

    # Debug: Show all golden pocket signals
    gp_signals = confluence_df[confluence_df['gp_confirmations'] > 0]
    print(f"\n🎯 Golden Pocket Signals Found: {len(gp_signals)}")

    # Show the first 10 GP signals with their details
    print("\nFirst 10 Golden Pocket Signals:")
    print("-" * 80)
    for idx, row in gp_signals.head(10).iterrows():
        print(f"\nTime: {idx}")
        print(f"  Price: ${row['close']:.2f}")
        print(f"  GP Confirmations: {row['gp_confirmations']}")
        print(f"  GP Confidence: {row['gp_confidence']:.2%}")
        print(f"  GP 1H: {row.get('gp_1h', False)}")
        print(f"  GP 4H: {row.get('gp_4h', False)}")
        print(f"  GP Daily: {row.get('gp_daily', False)}")

    # Now simulate the exact entry logic
    print("\n" + "=" * 80)
    print("SIMULATING ENTRY LOGIC")
    print("=" * 80)

    position = None
    last_trade_time = None
    cooldown_hours = 2
    trade_count = 0
    gp_trades = 0

    for i in range(50, min(200, len(confluence_df))):  # Check first 150 bars after warmup
        row = confluence_df.iloc[i]
        current_time = confluence_df.index[i]
        current_price = row['close']

        # Check if position is open
        if position is not None:
            # Simple exit after 10 bars
            if i - position['entry_idx'] >= 10:
                print(f"  Closing position at {current_time}")
                position = None
            continue

        # Check cooldown
        if last_trade_time:
            hours_since = (current_time - last_trade_time).total_seconds() / 3600
            if hours_since < cooldown_hours:
                if row['gp_confirmations'] >= 1:
                    print(f"\n❌ GP SIGNAL BLOCKED BY COOLDOWN at {current_time}")
                    print(f"  Hours since last trade: {hours_since:.1f} < {cooldown_hours}")
                continue

        # CHECK FOR GOLDEN POCKET
        if row['gp_confirmations'] >= 1 and row['gp_confidence'] >= 0.40:
            trade_count += 1
            gp_trades += 1

            leverage = 10.0 if row['gp_confirmations'] >= 2 else 5.0

            print(f"\n✅ GOLDEN POCKET TRADE #{trade_count} at {current_time}")
            print(f"  Price: ${current_price:.2f}")
            print(f"  Confirmations: {row['gp_confirmations']}")
            print(f"  Confidence: {row['gp_confidence']:.2%}")
            print(f"  Leverage: {leverage}x")

            position = {
                'entry_idx': i,
                'entry_time': current_time,
                'entry_price': current_price
            }
            last_trade_time = current_time

    print(f"\n" + "=" * 80)
    print(f"SUMMARY: {gp_trades} Golden Pocket trades out of {trade_count} total")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(debug_strategy())