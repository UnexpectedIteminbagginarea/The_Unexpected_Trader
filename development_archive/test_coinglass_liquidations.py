#!/usr/bin/env python3
"""
Test CoinGlass Liquidation endpoints with correct parameters
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
print("TESTING LIQUIDATION ENDPOINTS")
print("="*60)

# First try PAIR liquidation endpoints (single exchange, USDT pairs)
print("\n>>> Testing PAIR Liquidation History")
print("-"*40)

pair_endpoints = [
    "/api/futures/liquidation/history",
    "/api/futures/liquidation/pair-history",
    "/api/futures/pair-liquidation/history"
]

pair_params = {
    'exchange': 'Binance',  # Single exchange
    'symbol': 'BTCUSDT',    # With USDT
    'interval': '4h',
    'limit': 5
}

working_pair_endpoint = None

for endpoint in pair_endpoints:
    print(f"\nTrying: {endpoint}")
    try:
        response = requests.get(
            f"{BASE_URL}{endpoint}",
            headers=headers,
            params=pair_params,
            timeout=10
        )
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                print(f"✅ SUCCESS! Found working PAIR endpoint!")
                working_pair_endpoint = endpoint
                if 'data' in data:
                    print(f"Response preview:")
                    if isinstance(data['data'], list) and len(data['data']) > 0:
                        print(json.dumps(data['data'][0], indent=2)[:400])
                break
            else:
                print(f"API Error: {data.get('msg')}")
    except Exception as e:
        print(f"Exception: {e}")

# Then try COIN liquidation endpoints (exchange_list, coin symbols)
print("\n>>> Testing COIN Liquidation History")
print("-"*40)

coin_endpoints = [
    "/api/futures/liquidation/coin-history",
    "/api/futures/coin-liquidation/history",
    "/api/liquidation/coin-history"
]

# Parameters for Coin Liquidation
coin_params = {
    'exchange_list': 'Binance',  # List format
    'symbol': 'BTC',  # Coin symbol without USDT
    'interval': '4h',
    'limit': 5
}

working_coin_endpoint = None

for endpoint in coin_endpoints:
    print(f"\nTrying: {endpoint}")
    try:
        response = requests.get(
            f"{BASE_URL}{endpoint}",
            headers=headers,
            params=coin_params,
            timeout=10
        )
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                print(f"✅ SUCCESS! Found working COIN endpoint!")
                working_coin_endpoint = endpoint
                if 'data' in data:
                    print(f"Response preview:")
                    if isinstance(data['data'], list) and len(data['data']) > 0:
                        print(json.dumps(data['data'][0], indent=2)[:400])
                break
            else:
                print(f"API Error: {data.get('msg')}")
    except Exception as e:
        print(f"Exception: {e}")

# Test other symbols with working endpoints
print("\n" + "="*60)
print("TESTING OTHER SYMBOLS")
print("="*60)

# Test PAIR endpoint if it worked
if working_pair_endpoint:
    for symbol in ['SOLUSDT', 'ASTERUSDT']:
        print(f"\nTesting PAIR {symbol}:")
        params = {
            'exchange': 'Binance',
            'symbol': symbol,
            'interval': '4h',
            'limit': 1
        }
        try:
            response = requests.get(f"{BASE_URL}{working_pair_endpoint}", headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '0':
                    print(f"✅ {symbol} works!")
                    if 'data' in data and data['data']:
                        if isinstance(data['data'], list):
                            print(f"   Latest: {json.dumps(data['data'][0], indent=2)[:300]}")
                else:
                    print(f"❌ {data.get('msg')}")
        except Exception as e:
            print(f"❌ Exception: {e}")

# Test COIN endpoint if it worked
if working_coin_endpoint:
    for symbol in ['SOL', 'ASTER']:
        print(f"\nTesting COIN {symbol}:")
        params = {
            'exchange_list': 'Binance',
            'symbol': symbol,
            'interval': '4h',
            'limit': 1
        }
        try:
            response = requests.get(f"{BASE_URL}{working_coin_endpoint}", headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '0':
                    print(f"✅ {symbol} works!")
                    if 'data' in data and data['data']:
                        if isinstance(data['data'], list):
                            print(f"   Latest: {json.dumps(data['data'][0], indent=2)[:300]}")
                else:
                    print(f"❌ {data.get('msg')}")
        except Exception as e:
            print(f"❌ Exception: {e}")

print("\n" + "="*60)
print("SUMMARY")
print("="*60)

if working_pair_endpoint:
    print(f"✅ PAIR Liquidation endpoint working: {working_pair_endpoint}")
else:
    print("❌ No working PAIR liquidation endpoint found")

if working_coin_endpoint:
    print(f"✅ COIN Liquidation endpoint working: {working_coin_endpoint}")
else:
    print("❌ No working COIN liquidation endpoint found")

print("\n" + "="*60)
print("LIQUIDATION TEST COMPLETE")
print("="*60)