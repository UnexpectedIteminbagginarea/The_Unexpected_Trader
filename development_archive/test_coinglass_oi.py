#!/usr/bin/env python3
"""
Test CoinGlass Open Interest with correct parameters
"""
import requests
import json
from datetime import datetime

API_KEY = "YOUR_COINGLASS_API_KEY"
BASE_URL = "https://open-api-v4.coinglass.com"

headers = {
    'accept': 'application/json',
    'CG-API-KEY': API_KEY
}

print("\n" + "="*60)
print("TESTING OPEN INTEREST ENDPOINTS")
print("="*60)

# Test different endpoint variations for Open Interest
endpoints_to_try = [
    "/api/futures/openInterest/ohlc-history",
    "/api/futures/open-interest/ohlc-history",
    "/api/futures/openInterest/history",
    "/api/futures/open-interest/history",
    "/api/openInterest/history"
]

test_params = {
    'exchange': 'Binance',
    'symbol': 'BTCUSDT',
    'interval': '4h',  # Minimum for Hobbyist
    'limit': 10,
    'unit': 'usd'
}

for endpoint in endpoints_to_try:
    print(f"\nTrying: {endpoint}")
    print("-"*40)

    try:
        response = requests.get(
            f"{BASE_URL}{endpoint}",
            headers=headers,
            params=test_params,
            timeout=10
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                print(f"✅ SUCCESS! Found working endpoint!")
                print(f"Response preview:")
                if 'data' in data:
                    if isinstance(data['data'], list) and len(data['data']) > 0:
                        print(json.dumps(data['data'][0], indent=2))
                    else:
                        print(json.dumps(data['data'], indent=2)[:500])
                break
            else:
                print(f"API Error: {data.get('msg')}")
        elif response.status_code == 404:
            print("404 - Endpoint not found")
    except Exception as e:
        print(f"Exception: {e}")

# Also test for other symbols
print("\n" + "="*60)
print("TESTING OTHER SYMBOLS IF ENDPOINT WORKS")
print("="*60)

working_endpoint = None
for endpoint in endpoints_to_try:
    response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=test_params, timeout=10)
    if response.status_code == 200:
        data = response.json()
        if data.get('code') == '0':
            working_endpoint = endpoint
            break

if working_endpoint:
    for symbol in ['SOLUSDT', 'ASTERUSDT']:
        print(f"\nTesting {symbol}:")
        params = {
            'exchange': 'Binance',
            'symbol': symbol,
            'interval': '4h',
            'limit': 1,
            'unit': 'usd'
        }

        try:
            response = requests.get(f"{BASE_URL}{working_endpoint}", headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '0':
                    print(f"✅ {symbol} works!")
                    if 'data' in data and data['data']:
                        if isinstance(data['data'], list):
                            latest = data['data'][0]
                            print(f"   Latest OI: {json.dumps(latest, indent=2)[:200]}")
                else:
                    print(f"❌ {data.get('msg')}")
        except Exception as e:
            print(f"❌ Exception: {e}")
else:
    print("❌ Could not find working Open Interest endpoint")

print("\n" + "="*60)
print("OPEN INTEREST TEST COMPLETE")
print("="*60)