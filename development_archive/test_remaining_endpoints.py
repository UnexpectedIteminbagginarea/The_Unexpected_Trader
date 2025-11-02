#!/usr/bin/env python3
"""
Test remaining potentially valuable CoinGlass endpoints
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
print("TESTING REMAINING HIGH-VALUE ENDPOINTS")
print("="*60)

working_endpoints = []

# Test cases
test_cases = [
    # Price movements
    ("/api/futures/coins-price-change", {}, "Coins Price Change"),

    # Advanced Funding metrics
    ("/api/futures/funding-rate/oi-weight-ohlc-history", {'symbol': 'BTC', 'interval': '8h', 'limit': 5}, "Funding OI Weighted"),
    ("/api/futures/funding-rate/vol-weight-ohlc-history", {'symbol': 'BTC', 'interval': '8h', 'limit': 5}, "Funding Vol Weighted"),
    ("/api/futures/funding-rate/cumulative-exchange-list", {'symbol': 'BTC'}, "Cumulative Funding"),
    ("/api/futures/funding-arbitrage", {'symbol': 'BTC'}, "Funding Arbitrage"),

    # Market structure
    ("/api/futures/exchange-rank", {}, "Exchange Rankings"),
    ("/api/futures/delisted-pairs", {}, "Delisted Pairs"),

    # Aggregated metrics
    ("/api/futures/aggregated-stablecoin-margin/history", {'symbol': 'BTC', 'interval': '4h', 'limit': 5}, "Stablecoin Margin OI"),
    ("/api/futures/aggregated-coin-margin/history", {'symbol': 'BTC', 'interval': '4h', 'limit': 5}, "Coin Margin OI"),

    # Hyperliquid (DEX data)
    ("/api/hyperliquid/whale-alert", {}, "Hyperliquid Whale Alert"),
    ("/api/hyperliquid/whale-position", {}, "Hyperliquid Whale Positions"),
    ("/api/hyperliquid/position", {'symbol': 'BTC'}, "Hyperliquid Positions"),

    # Taker flow variations
    ("/api/futures/taker-buy-sell/coin-history", {'symbol': 'BTC', 'interval': '4h', 'limit': 5}, "Coin Taker History"),
    ("/api/futures/footprint-history", {'symbol': 'BTC', 'days': 7}, "Footprint History 90d"),

    # Additional market data
    ("/api/futures/coins-markets", {}, "Coins Markets"),
    ("/api/futures/pairs-markets", {}, "Pairs Markets"),
]

for endpoint, params, name in test_cases:
    print(f"\n{'='*40}")
    print(f"Testing: {name}")
    print(f"Path: {endpoint}")
    if params:
        print(f"Params: {params}")
    print('-'*40)

    try:
        response = requests.get(
            f"{BASE_URL}{endpoint}",
            headers=headers,
            params=params,
            timeout=10
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                print(f"✅ SUCCESS!")
                working_endpoints.append((name, endpoint, params))

                # Show sample data
                if 'data' in data and data['data']:
                    if isinstance(data['data'], list) and len(data['data']) > 0:
                        # Show first item
                        first = data['data'][0]
                        if isinstance(first, dict):
                            # Truncate large values
                            sample = {}
                            for k, v in first.items():
                                if isinstance(v, (int, float)):
                                    sample[k] = v
                                elif isinstance(v, str) and len(v) < 50:
                                    sample[k] = v
                                else:
                                    sample[k] = f"{str(v)[:30]}..."
                            print(f"Sample: {json.dumps(sample, indent=2)[:400]}")
                        else:
                            print(f"Sample: {data['data'][:5]}")
                    elif isinstance(data['data'], dict):
                        print(f"Sample: {json.dumps(data['data'], indent=2)[:400]}")
                    else:
                        print(f"Data type: {type(data['data'])}")
            else:
                print(f"❌ API Error: {data.get('msg')}")
        else:
            print(f"❌ HTTP {response.status_code}")

    except Exception as e:
        print(f"❌ Exception: {str(e)[:100]}")

print("\n" + "="*60)
print("SUMMARY OF NEW DISCOVERIES")
print("="*60)

if working_endpoints:
    print(f"\n✅ Found {len(working_endpoints)} working endpoints:")
    for name, path, params in working_endpoints:
        print(f"  - {name}: {path}")
        if name in ["Funding OI Weighted", "Funding Vol Weighted", "Funding Arbitrage"]:
            print(f"    💎 HIGH VALUE - Better funding rate analysis")
        elif "Hyperliquid" in name:
            print(f"    🐋 WHALE TRACKING - DEX whale positions")
        elif "Price Change" in name:
            print(f"    📈 MOMENTUM - Multi-coin price changes")
else:
    print("\n❌ No new working endpoints found")

print("\n" + "="*60)
print("TESTING COMPLETE")
print("="*60)