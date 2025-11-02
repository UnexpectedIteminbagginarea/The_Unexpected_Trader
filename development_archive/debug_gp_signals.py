"""
Debug golden pocket signal generation
Check why GP signals aren't converting to trades
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.historical_data_fetcher import HistoricalDataFetcher
from core.multi_timeframe_golden_pocket import MultiTimeframeGoldenPocket
from datetime import datetime, timedelta
import pandas as pd

async def check_gp():
    fetcher = HistoricalDataFetcher()
    detector = MultiTimeframeGoldenPocket()

    # Fetch data
    end_date = '2025-10-29'
    start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')
    df = await fetcher.fetch_btc_historical_data(start_date, end_date, '1h')

    # Detect GPs
    timeframe_data = detector.detect_all_timeframes(df)
    confluence_df = detector.find_confluence_zones(timeframe_data)

    # Check GP signals
    gp_signals = confluence_df[confluence_df['gp_confirmations'] > 0]
    print(f'Total bars: {len(confluence_df)}')
    print(f'Bars with GP signals: {len(gp_signals)}')
    print(f'\nGP confirmation distribution:')
    print(confluence_df['gp_confirmations'].value_counts().sort_index())

    # Check confidence levels
    print(f'\nGP Confidence stats:')
    gp_conf = confluence_df[confluence_df['gp_confidence'] > 0]['gp_confidence']
    if len(gp_conf) > 0:
        print(f'Min confidence: {gp_conf.min():.2%}')
        print(f'Max confidence: {gp_conf.max():.2%}')
        print(f'Mean confidence: {gp_conf.mean():.2%}')
        print(f'Signals above 40%: {(gp_conf >= 0.40).sum()}')
        print(f'Signals above 50%: {(gp_conf >= 0.50).sum()}')
        print(f'Signals above 60%: {(gp_conf >= 0.60).sum()}')

    # Show some actual GP entries
    print(f'\nSample GP signals (first 10 with conf >= 40%):')
    high_conf = gp_signals[gp_signals['gp_confidence'] >= 0.40]
    for idx, row in high_conf.head(10).iterrows():
        print(f'{idx}: Conf={int(row["gp_confirmations"])}, '
              f'Confidence={row["gp_confidence"]:.2%}, '
              f'Price=${row["close"]:.0f}')

    # Check for multi-timeframe confluence
    multi_tf = confluence_df[confluence_df['gp_confirmations'] >= 2]
    print(f'\nMulti-timeframe GP signals (2+ confirmations): {len(multi_tf)}')
    if len(multi_tf) > 0:
        print('First 5 multi-TF signals:')
        for idx, row in multi_tf.head(5).iterrows():
            print(f'{idx}: {int(row["gp_confirmations"])} TFs, '
                  f'Conf={row["gp_confidence"]:.2%}, '
                  f'Price=${row["close"]:.0f}')

if __name__ == "__main__":
    asyncio.run(check_gp())