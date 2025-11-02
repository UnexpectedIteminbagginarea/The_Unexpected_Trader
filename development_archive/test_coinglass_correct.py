#!/usr/bin/env python3
"""
Test CoinGlass Long/Short Ratio with CORRECT parameters from documentation
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
print("TESTING WITH CORRECT PARAMETERS FROM DOCS")
print("="*60)

# Test 1: With Binance exchange (as shown in docs)
test_cases = [
    {
        'name': 'Binance BTCUSDT 4h',
        'params': {
            'exchange': 'Binance',
            'symbol': 'BTCUSDT',
            'interval': '4h',  # Minimum for Hobbyist plan
            'limit': 10
        }
    },
    {
        'name': 'OKX BTCUSDT 4h',
        'params': {
            'exchange': 'OKX',
            'symbol': 'BTCUSDT',
            'interval': '4h',
            'limit': 10
        }
    },
    {
        'name': 'Bybit BTCUSDT 1d',
        'params': {
            'exchange': 'Bybit',
            'symbol': 'BTCUSDT',
            'interval': '1d',
            'limit': 10
        }
    },
    {
        'name': 'Binance SOLUSDT 4h',
        'params': {
            'exchange': 'Binance',
            'symbol': 'SOLUSDT',
            'interval': '4h',
            'limit': 5
        }
    },
    {
        'name': 'Binance ASTERUSDT 4h',
        'params': {
            'exchange': 'Binance',
            'symbol': 'ASTERUSDT',
            'interval': '4h',
            'limit': 5
        }
    }
]

working_configs = []

for test in test_cases:
    print(f"\n{'='*60}")
    print(f"Test: {test['name']}")
    print(f"Params: {test['params']}")
    print('-'*60)

    try:
        # Test Global Long/Short Account Ratio
        response = requests.get(
            f"{BASE_URL}/api/futures/global-long-short-account-ratio/history",
            headers=headers,
            params=test['params'],
            timeout=10
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if data.get('code') == '0':
                print(f"✅ SUCCESS!")
                print(f"Response preview:")

                # Show the actual data structure
                if 'data' in data and data['data']:
                    if isinstance(data['data'], list) and len(data['data']) > 0:
                        first_item = data['data'][0]
                        print(json.dumps(first_item, indent=2))
                        working_configs.append(test['name'])
                    else:
                        print(f"Data: {data['data']}")
            else:
                print(f"❌ API Error: {data.get('msg', 'Unknown error')}")

                # If it says "Not Supported", try the top account ratio endpoint
                if data.get('msg') == 'Not Supported':
                    print("\nTrying Top Account Ratio endpoint instead...")
                    response2 = requests.get(
                        f"{BASE_URL}/api/futures/top-long-short-account-ratio/history",
                        headers=headers,
                        params=test['params'],
                        timeout=10
                    )

                    if response2.status_code == 200:
                        data2 = response2.json()
                        if data2.get('code') == '0':
                            print(f"✅ Top Account Ratio works!")
                            if 'data' in data2 and data2['data']:
                                print(json.dumps(data2['data'][0] if isinstance(data2['data'], list) else data2['data'], indent=2)[:300])
                        else:
                            print(f"Top Account also failed: {data2.get('msg')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")

    except Exception as e:
        print(f"❌ Exception: {e}")

# Test getting supported exchanges
print("\n" + "="*60)
print("GETTING SUPPORTED EXCHANGES")
print("="*60)

try:
    response = requests.get(
        f"{BASE_URL}/api/futures/supported-exchange-pair",
        headers=headers,
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()
        if data.get('code') == '0':
            print("✅ Got supported exchanges!")

            # Show unique exchanges
            if 'data' in data and data['data']:
                exchanges = set()
                for item in data['data'][:50]:  # Check first 50 items
                    if 'exchange' in item:
                        exchanges.add(item['exchange'])

                print(f"Available exchanges: {sorted(exchanges)}")

                # Check if ASTER is supported
                aster_pairs = [item for item in data['data'] if 'ASTER' in item.get('symbol', '')]
                if aster_pairs:
                    print(f"\nASTER pairs found: {aster_pairs[:5]}")
        else:
            print(f"Error: {data.get('msg')}")
    else:
        print(f"HTTP Error: {response.status_code}")

except Exception as e:
    print(f"Exception: {e}")

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
if working_configs:
    print(f"✅ Working configurations: {working_configs}")
else:
    print("❌ No working L/S ratio configurations found")
    print("\nThis might be because:")
    print("1. The exchange doesn't support this data")
    print("2. The symbol isn't available on that exchange")
    print("3. The API endpoint requires a different format")
    print("4. The Hobbyist plan doesn't actually include this data despite documentation")