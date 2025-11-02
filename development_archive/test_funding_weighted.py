#!/usr/bin/env python3
"""
Test weighted funding rate endpoints with correct paths
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
print("TESTING WEIGHTED FUNDING RATE ENDPOINTS")
print("="*60)

working = []

# Test corrected endpoints
tests = [
    {
        'name': 'Funding Rate OI Weighted',
        'endpoint': '/api/futures/funding-rate/oi-weight-history',
        'params': {'symbol': 'BTC', 'interval': '1d'},
        'description': 'Funding weighted by open interest - more accurate'
    },
    {
        'name': 'Funding Rate Volume Weighted',
        'endpoint': '/api/futures/funding-rate/vol-weight-history',
        'params': {'symbol': 'BTC', 'interval': '1d'},
        'description': 'Funding weighted by volume - shows active market funding'
    },
    {
        'name': 'Accumulated Funding by Exchange',
        'endpoint': '/api/futures/funding-rate/accumulated-exchange-list',
        'params': {'range': '1d'},
        'description': 'Cumulative funding across exchanges'
    }
]

for test in tests:
    print(f"\n{'='*40}")
    print(f"Testing: {test['name']}")
    print(f"Path: {test['endpoint']}")
    print(f"Params: {test['params']}")
    print(f"Purpose: {test['description']}")
    print('-'*40)

    try:
        response = requests.get(
            f"{BASE_URL}{test['endpoint']}",
            headers=headers,
            params=test['params'],
            timeout=10
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                print(f"✅ SUCCESS!")
                working.append(test['name'])

                # Show sample data
                if 'data' in data and data['data']:
                    if isinstance(data['data'], list) and len(data['data']) > 0:
                        first = data['data'][0]
                        print(f"\nSample data:")

                        # Parse specific fields
                        if 'oi_weight_funding_rate' in first:
                            oi_rate = first['oi_weight_funding_rate']
                            print(f"  OI Weighted Rate: {oi_rate*100:.4f}%")
                        elif 'vol_weight_funding_rate' in first:
                            vol_rate = first['vol_weight_funding_rate']
                            print(f"  Volume Weighted Rate: {vol_rate*100:.4f}%")
                        elif 'accumulated_funding_rate' in first:
                            acc_rate = first['accumulated_funding_rate']
                            exchange = first.get('exchange', 'Unknown')
                            print(f"  {exchange} Accumulated: {acc_rate*100:.4f}%")
                        else:
                            print(json.dumps(first, indent=2)[:300])
                    else:
                        print(f"Data: {json.dumps(data['data'], indent=2)[:300]}")
            else:
                print(f"❌ API Error: {data.get('msg')}")
        else:
            print(f"❌ HTTP {response.status_code}")

    except Exception as e:
        print(f"❌ Exception: {e}")

print("\n" + "="*60)
print("SUMMARY")
print("="*60)

if working:
    print(f"\n🎉 NEW DISCOVERIES! Found {len(working)} working endpoints:")
    for name in working:
        print(f"  ✅ {name}")

    print("\n💡 Why These Are Valuable:")
    print("1. OI-Weighted Funding: Shows funding where the BIG positions are")
    print("2. Volume-Weighted Funding: Shows funding where ACTIVE trading is")
    print("3. Accumulated Funding: Shows total funding paid/received over time")
    print("\nThese give MUCH better funding analysis than raw rates!")
else:
    print("\n❌ None of these endpoints worked")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)