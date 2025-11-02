"""
Check if price actually reached the TRUE golden pocket
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data.historical_data_fetcher import HistoricalDataFetcher
import pandas as pd

async def check_true_gp():
    fetcher = HistoricalDataFetcher()

    # Get data from June to October
    df = await fetcher.fetch_btc_historical_data('2025-06-01', '2025-10-29', '1h')

    # Find the ACTUAL swings
    daily = df.resample('1D').agg({'high': 'max', 'low': 'min', 'close': 'last'})

    # June-July low
    june_july = daily['2025-06-01':'2025-07-31']
    swing_low = june_july['low'].min()
    swing_low_date = june_july['low'].idxmin()

    # October high
    oct = daily['2025-10-01':'2025-10-15']
    swing_high = oct['high'].max()
    swing_high_date = oct['high'].idxmax()

    # Calculate TRUE golden pocket
    range_size = swing_high - swing_low
    gp_618 = swing_high - (range_size * 0.618)
    gp_650 = swing_high - (range_size * 0.650)

    print(f'Swing Low: ${swing_low:,.0f} on {swing_low_date.date()}')
    print(f'Swing High: ${swing_high:,.0f} on {swing_high_date.date()}')
    print(f'\nTRUE Golden Pocket: ${gp_618:,.0f} - ${gp_650:,.0f}')
    print(f'GP Zone Width: ${gp_618 - gp_650:,.0f}')

    # Check AFTER the high was made
    post_high = df[swing_high_date:]
    post_high['in_true_gp'] = (post_high['close'] <= gp_618) & (post_high['close'] >= gp_650)

    gp_entries = post_high[post_high['in_true_gp']]

    print(f'\n📍 Times price entered TRUE GP after Oct 6 high:')
    if len(gp_entries) > 0:
        for idx in gp_entries.index[:10]:
            print(f'  {idx}: ${gp_entries.loc[idx, "close"]:,.0f}')
        print(f'  Total: {len(gp_entries)} hours in GP')

        # Check what happened after FIRST entry
        first_entry = gp_entries.index[0]
        first_price = gp_entries.iloc[0]['close']

        print(f'\n🎯 FIRST TRUE GP ENTRY:')
        print(f'  Time: {first_entry}')
        print(f'  Price: ${first_price:,.0f}')

        # Check next 100 bars
        future = df[first_entry:].iloc[1:101]

        # Find low and high after entry
        lowest = future['low'].min()
        highest = future['high'].max()

        print(f'\n📊 AFTER FIRST GP ENTRY:')
        print(f'  Lowest: ${lowest:,.0f} ({(lowest - first_price)/first_price*100:.2f}%)')
        print(f'  Highest: ${highest:,.0f} ({(highest - first_price)/first_price*100:+.2f}%)')

        # Check if various stops would have hit
        for stop_pct in [0.02, 0.04, 0.06, 0.08, 0.10]:
            stop_price = first_price * (1 - stop_pct)
            hit_stop = lowest <= stop_price
            print(f'  {stop_pct*100:.0f}% stop at ${stop_price:,.0f}: {"HIT" if hit_stop else "SAFE"}')

    else:
        print('  NEVER! Price has not reached TRUE golden pocket since the high!')

        # Find closest it got
        min_price = post_high['low'].min()
        min_date = post_high['low'].idxmin()
        distance = min_price - gp_618

        print(f'\n  Closest approach:')
        print(f'    Date: {min_date}')
        print(f'    Price: ${min_price:,.0f}')
        print(f'    Still ${distance:,.0f} above GP ({distance/gp_618*100:.2f}% away)')

if __name__ == "__main__":
    asyncio.run(check_true_gp())