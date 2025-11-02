#!/usr/bin/env python3
"""
Test CoinGlass Taker Buy/Sell Volume endpoint
"""
import requests
import json

API_KEY = "YOUR_COINGLASS_API_KEY"
BASE_URL = "https://open-api-v4.coinglass.com"

headers = {
    'accept': 'application/json',
    'CG-API-KEY': API_KEY
}

print("\n" + "="*60)
print("TESTING TAKER BUY/SELL VOLUME")
print("="*60)

# Test endpoint with correct parameters
endpoint = "/api/futures/taker-buy-sell-volume/history"

test_cases = [
    {
        'name': 'BTC on Binance',
        'params': {
            'exchange': 'Binance',
            'symbol': 'BTCUSDT',
            'interval': '4h',
            'limit': 6
        }
    },
    {
        'name': 'SOL on Binance',
        'params': {
            'exchange': 'Binance',
            'symbol': 'SOLUSDT',
            'interval': '4h',
            'limit': 6
        }
    },
    {
        'name': 'ASTER on Binance',
        'params': {
            'exchange': 'Binance',
            'symbol': 'ASTERUSDT',
            'interval': '4h',
            'limit': 6
        }
    }
]

for test in test_cases:
    print(f"\nTesting: {test['name']}")
    print("-"*40)

    try:
        response = requests.get(
            f"{BASE_URL}{endpoint}",
            headers=headers,
            params=test['params'],
            timeout=10
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                print("✅ SUCCESS!")

                if 'data' in data and data['data']:
                    # Calculate 24h totals (6 periods of 4h)
                    total_buy = sum(float(item.get('taker_buy_volume_usd', 0)) for item in data['data'])
                    total_sell = sum(float(item.get('taker_sell_volume_usd', 0)) for item in data['data'])
                    total_volume = total_buy + total_sell

                    if total_volume > 0:
                        buy_ratio = (total_buy / total_volume) * 100
                        sell_ratio = (total_sell / total_volume) * 100

                        print(f"24h Taker Volume:")
                        print(f"  Buy Volume:  ${total_buy:,.0f} ({buy_ratio:.1f}%)")
                        print(f"  Sell Volume: ${total_sell:,.0f} ({sell_ratio:.1f}%)")
                        print(f"  Total:       ${total_volume:,.0f}")

                        if buy_ratio > 55:
                            print(f"  Signal: 🟢 Bullish (aggressive buying)")
                        elif buy_ratio < 45:
                            print(f"  Signal: 🔴 Bearish (aggressive selling)")
                        else:
                            print(f"  Signal: ⚪ Neutral")

                    # Show latest period
                    latest = data['data'][0]
                    print(f"\nLatest 4h period:")
                    print(f"  {json.dumps(latest, indent=2)[:300]}")
            else:
                print(f"❌ Error: {data.get('msg')}")
        else:
            print(f"❌ HTTP Error {response.status_code}")

    except Exception as e:
        print(f"❌ Exception: {e}")

print("\n" + "="*60)
print("TAKER BUY/SELL TEST COMPLETE")
print("="*60)