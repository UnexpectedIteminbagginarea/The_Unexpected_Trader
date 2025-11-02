#!/usr/bin/env python3
"""
Test newly discovered CoinGlass endpoints
On-Chain, ETF, Options data
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
print("TESTING NEW HIGH-VALUE ENDPOINTS")
print("="*60)

# 1. ETF FLOWS (Institutional money)
print("\n📊 ETF FLOW DATA")
print("-"*40)

etf_endpoints = [
    ("/api/etf/flows-history", {}, "ETF Flows History"),
    ("/api/etf/bitcoin/flows-history", {}, "Bitcoin ETF Flows"),
    ("/api/etf/ethereum/flows-history", {}, "Ethereum ETF Flows"),
    ("/api/etf/netassets-history", {}, "ETF Net Assets"),
    ("/api/etf/bitcoin/list", {}, "Bitcoin ETF List"),
]

for endpoint, params, name in etf_endpoints:
    print(f"\nTesting: {name}")
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                print(f"✅ SUCCESS!")
                if 'data' in data:
                    if isinstance(data['data'], list) and len(data['data']) > 0:
                        print(f"Sample: {json.dumps(data['data'][0], indent=2)[:300]}")
                    elif isinstance(data['data'], dict):
                        print(f"Sample: {json.dumps(data['data'], indent=2)[:300]}")
            else:
                print(f"❌ {data.get('msg')}")
    except Exception as e:
        print(f"❌ Exception: {e}")

# 2. ON-CHAIN DATA (Exchange flows!)
print("\n\n📊 ON-CHAIN DATA")
print("-"*40)

onchain_endpoints = [
    ("/api/on-chain/exchange-balance", {'symbol': 'BTC'}, "Exchange Balance"),
    ("/api/on-chain/exchange-flow", {'symbol': 'BTC'}, "Exchange Flow"),
    ("/api/on-chain/large-transfers", {'symbol': 'BTC'}, "Large Transfers"),
    ("/api/on-chain/stablecoin-supply", {}, "Stablecoin Supply"),
    ("/api/on-chain/btc/balance", {}, "BTC On-Chain Balance"),
]

for endpoint, params, name in onchain_endpoints:
    print(f"\nTesting: {name}")
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                print(f"✅ SUCCESS!")
                if 'data' in data:
                    print(f"Sample: {json.dumps(data['data'], indent=2)[:300] if data['data'] else 'Empty'}")
            else:
                print(f"❌ {data.get('msg')}")
        else:
            print(f"❌ HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Exception: {e}")

# 3. OPTIONS DATA
print("\n\n📊 OPTIONS DATA")
print("-"*40)

options_endpoints = [
    ("/api/options/max-pain", {'symbol': 'BTC', 'exchange': 'Deribit'}, "Max Pain"),
    ("/api/options/put-call-ratio", {'symbol': 'BTC'}, "Put/Call Ratio"),
    ("/api/options/volume", {'symbol': 'BTC', 'exchange': 'Deribit'}, "Options Volume"),
    ("/api/options/open-interest", {'symbol': 'BTC', 'exchange': 'Deribit'}, "Options OI"),
    ("/api/options/flow", {'symbol': 'BTC'}, "Options Flow"),
]

for endpoint, params, name in options_endpoints:
    print(f"\nTesting: {name}")
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                print(f"✅ SUCCESS!")
                if 'data' in data:
                    print(f"Sample: {json.dumps(data['data'], indent=2)[:300] if data['data'] else 'Empty'}")
            else:
                print(f"❌ {data.get('msg')}")
        else:
            print(f"❌ HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Exception: {e}")

# 4. INDICATOR DATA
print("\n\n📊 INDICATOR DATA")
print("-"*40)

indicator_endpoints = [
    ("/api/index/bitcoin-rainbow-chart", {}, "Bitcoin Rainbow Chart"),
    ("/api/index/stock-to-flow", {}, "Stock to Flow"),
    ("/api/index/pi-cycle", {}, "Pi Cycle Top"),
    ("/api/index/puell-multiple", {}, "Puell Multiple"),
    ("/api/index/ahr999", {}, "AHR999 Index"),
]

for endpoint, params, name in indicator_endpoints:
    print(f"\nTesting: {name}")
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                print(f"✅ SUCCESS!")
                if 'data' in data:
                    print(f"Sample: {json.dumps(data['data'], indent=2)[:300] if data['data'] else 'Empty'}")
            else:
                print(f"❌ {data.get('msg')}")
        else:
            print(f"❌ HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Exception: {e}")

print("\n" + "="*60)
print("NEW ENDPOINT TESTING COMPLETE")
print("="*60)