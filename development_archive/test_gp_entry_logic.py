"""
Test golden pocket entry logic
Find out why GP signals aren't triggering trades
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.historical_data_fetcher import HistoricalDataFetcher
from core.multi_timeframe_golden_pocket import MultiTimeframeGoldenPocket
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

async def test_gp_entries():
    fetcher = HistoricalDataFetcher()
    detector = MultiTimeframeGoldenPocket()

    # Fetch data
    end_date = '2025-10-29'
    start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')
    df = await fetcher.fetch_btc_historical_data(start_date, end_date, '1h')

    # Calculate indicators for ultra-aggressive strategy
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Volume analysis
    df['volume_ma'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma']

    # Price momentum
    df['momentum'] = df['close'].pct_change(10) * 100

    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(20).mean()
    std = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_middle'] + (std * 2)
    df['bb_lower'] = df['bb_middle'] - (std * 2)
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

    # Detect GPs
    timeframe_data = detector.detect_all_timeframes(df)
    confluence_df = detector.find_confluence_zones(timeframe_data)

    # Merge indicators
    for col in ['rsi', 'volume_ratio', 'momentum', 'bb_position']:
        if col in df.columns:
            confluence_df[col] = df[col]

    # Track why GP signals don't convert to trades
    gp_signals_found = 0
    gp_trades_taken = 0
    reasons_not_taken = {}
    position_open = False
    last_trade_time = None
    cooldown_hours = 2

    print("=" * 80)
    print("GOLDEN POCKET ENTRY ANALYSIS")
    print("=" * 80)

    # Simulate entry logic
    for i in range(50, len(confluence_df)):
        row = confluence_df.iloc[i]
        current_time = confluence_df.index[i]

        # Skip if position already open
        if position_open:
            # Simulate exit after 10 bars
            if i % 10 == 0:
                position_open = False
            continue

        # Check for GP signal
        if row['gp_confirmations'] >= 1:
            gp_signals_found += 1

            # Track why we might not enter
            reasons = []

            # Check cooldown
            if last_trade_time:
                hours_since = (current_time - last_trade_time).total_seconds() / 3600
                if hours_since < cooldown_hours:
                    reasons.append(f"Cooldown ({hours_since:.1f}h < {cooldown_hours}h)")

            # Check confidence
            confidence = row['gp_confidence']
            if confidence < 0.60:  # Medium confidence threshold
                reasons.append(f"Low confidence ({confidence:.2%} < 60%)")

            # Check other signals from ultra-aggressive strategy
            signals = {
                'momentum_spike': False,
                'volume_breakout': False,
                'oversold_bounce': False,
                'bb_squeeze': False,
                'total_score': 0
            }

            # Golden pocket base score
            signals['total_score'] += 40
            if row['gp_confirmations'] >= 2:
                signals['total_score'] += 20

            # Momentum
            if pd.notna(row.get('momentum')) and row['momentum'] > 2:
                signals['momentum_spike'] = True
                signals['total_score'] += 25

            # Volume
            if pd.notna(row.get('volume_ratio')) and row['volume_ratio'] > 1.5:
                signals['volume_breakout'] = True
                signals['total_score'] += 20

            # RSI
            if pd.notna(row.get('rsi')):
                if row['rsi'] < 35:
                    signals['oversold_bounce'] = True
                    signals['total_score'] += 25
                elif 40 <= row['rsi'] <= 60:
                    signals['total_score'] += 10

            # BB position
            if pd.notna(row.get('bb_position')):
                if row['bb_position'] < 0.2:
                    signals['bb_squeeze'] = True
                    signals['total_score'] += 20

            # Calculate final confidence
            total_confidence = min(signals['total_score'] / 100, 1.0)

            # Would we enter?
            if not reasons and confidence >= 0.60:
                gp_trades_taken += 1
                position_open = True
                last_trade_time = current_time

                leverage = 10.0 if row['gp_confirmations'] >= 2 else 5.0

                print(f"\n✅ GP TRADE TAKEN at {current_time}")
                print(f"   Confirmations: {int(row['gp_confirmations'])}")
                print(f"   GP Confidence: {confidence:.2%}")
                print(f"   Total Score: {signals['total_score']}")
                print(f"   Leverage: {leverage}x")
                print(f"   Price: ${row['close']:.0f}")

                active_signals = [k for k, v in signals.items()
                                if k.endswith(('_spike', '_breakout', '_bounce', '_squeeze')) and v]
                if active_signals:
                    print(f"   Additional Signals: {', '.join(active_signals)}")
            else:
                # Track why not taken
                reason_key = ', '.join(reasons) if reasons else 'Unknown'
                reasons_not_taken[reason_key] = reasons_not_taken.get(reason_key, 0) + 1

                if gp_signals_found <= 5:  # Show first 5
                    print(f"\n❌ GP SIGNAL NOT TAKEN at {current_time}")
                    print(f"   Confirmations: {int(row['gp_confirmations'])}")
                    print(f"   GP Confidence: {confidence:.2%}")
                    print(f"   Total Score: {signals['total_score']}")
                    print(f"   Price: ${row['close']:.0f}")
                    if reasons:
                        print(f"   Reasons: {', '.join(reasons)}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Golden Pocket Signals Found: {gp_signals_found}")
    print(f"Golden Pocket Trades Taken: {gp_trades_taken}")
    print(f"Conversion Rate: {gp_trades_taken/gp_signals_found*100:.1f}%" if gp_signals_found > 0 else "N/A")

    if reasons_not_taken:
        print(f"\nReasons GP signals not taken:")
        for reason, count in sorted(reasons_not_taken.items(), key=lambda x: x[1], reverse=True):
            print(f"  {reason}: {count} times")

if __name__ == "__main__":
    asyncio.run(test_gp_entries())