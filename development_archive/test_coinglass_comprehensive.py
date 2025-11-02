#!/usr/bin/env python3
"""
Comprehensive test of all CoinGlass API endpoints
Systematically testing what we haven't covered yet
"""
import requests
import json
from datetime import datetime
import time

API_KEY = "YOUR_COINGLASS_API_KEY"
BASE_URL = "https://open-api-v4.coinglass.com"

headers = {
    'accept': 'application/json',
    'CG-API-KEY': API_KEY
}

# Track what works
working_endpoints = []
failed_endpoints = []

def test_endpoint(name, endpoint, params=None, description=""):
    """Test a single endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    if description:
        print(f"Purpose: {description}")
    print(f"Endpoint: {endpoint}")
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
                print("✅ SUCCESS!")
                working_endpoints.append({
                    'name': name,
                    'endpoint': endpoint,
                    'params': params,
                    'description': description
                })

                # Show sample data
                if 'data' in data:
                    if isinstance(data['data'], list) and len(data['data']) > 0:
                        print("Sample data:")
                        print(json.dumps(data['data'][0], indent=2)[:400])
                    elif isinstance(data['data'], dict):
                        print("Sample data:")
                        print(json.dumps(data['data'], indent=2)[:400])
                    else:
                        print(f"Data type: {type(data['data'])}")

                return True
            else:
                print(f"❌ API Error: {data.get('msg')}")
                failed_endpoints.append({'name': name, 'error': data.get('msg')})
        else:
            print(f"❌ HTTP {response.status_code}")
            failed_endpoints.append({'name': name, 'error': f"HTTP {response.status_code}"})

    except Exception as e:
        print(f"❌ Exception: {e}")
        failed_endpoints.append({'name': name, 'error': str(e)})

    return False

print("\n" + "="*60)
print("COMPREHENSIVE COINGLASS API TESTING")
print("="*60)

# 1. FUNDING RATES (Important for trading)
print("\n\n🔍 CATEGORY: FUNDING RATES")
print("="*60)

test_endpoint(
    "Funding Rate OHLC History",
    "/api/futures/funding-rate/ohlc-history",
    {'exchange': 'Binance', 'symbol': 'BTCUSDT', 'interval': '4h', 'limit': 5},
    "Historical funding rates in OHLC format"
)

test_endpoint(
    "Funding Rate by OI Weight",
    "/api/futures/funding-rate/oi-weight-ohlc-history",
    {'symbol': 'BTC', 'interval': '4h', 'limit': 5},
    "Funding weighted by open interest"
)

test_endpoint(
    "Current Funding Rates",
    "/api/futures/funding-rate/list",
    {'symbol': 'BTC'},
    "Current funding rates across exchanges"
)

# 2. ORDER BOOK DATA (Market depth)
print("\n\n🔍 CATEGORY: ORDER BOOK")
print("="*60)

test_endpoint(
    "Order Book Snapshot",
    "/api/futures/order-book/pair-orderbook-history",
    {'exchange': 'Binance', 'symbol': 'BTCUSDT', 'interval': '4h', 'limit': 1},
    "Order book depth snapshot"
)

test_endpoint(
    "Large Orders History",
    "/api/futures/order-book/large-orderbook-history",
    {'exchange': 'Binance', 'symbol': 'BTCUSDT', 'limit': 5},
    "Track whale orders"
)

# 3. INDICATORS
print("\n\n🔍 CATEGORY: INDICATORS")
print("="*60)

test_endpoint(
    "RSI List",
    "/api/index/rsi-list",
    {'time_type': '4h'},
    "RSI values for multiple coins"
)

test_endpoint(
    "Basis (Spot-Futures Spread)",
    "/api/index/basis",
    {'exchange': 'Binance', 'symbol': 'BTC'},
    "Spot vs futures price spread"
)

test_endpoint(
    "CoinGlass Direction Index (CGDI)",
    "/api/index/cgdi",
    {},
    "Proprietary trend indicator"
)

test_endpoint(
    "Altcoin Season Index",
    "/api/index/altcoin-season-index",
    {},
    "Alt season indicator"
)

# 4. TOP TRADER POSITIONS
print("\n\n🔍 CATEGORY: TOP TRADERS")
print("="*60)

test_endpoint(
    "Top Trader Position Ratio",
    "/api/futures/top-long-short-position-ratio/history",
    {'exchange': 'Binance', 'symbol': 'BTCUSDT', 'interval': '4h', 'limit': 5},
    "What whales are doing with positions"
)

# 5. NET POSITION
print("\n\n🔍 CATEGORY: NET POSITIONS")
print("="*60)

test_endpoint(
    "Net Position History",
    "/api/futures/net-long-short-position/history",
    {'exchange': 'Binance', 'symbol': 'BTCUSDT', 'interval': '1d', 'limit': 5},
    "Net long/short positions"
)

# 6. OPTIONS DATA
print("\n\n🔍 CATEGORY: OPTIONS")
print("="*60)

test_endpoint(
    "Max Pain",
    "/api/options/max-pain",
    {'symbol': 'BTC', 'exchange': 'Deribit'},
    "Options max pain levels"
)

# 7. AGGREGATED METRICS
print("\n\n🔍 CATEGORY: AGGREGATED DATA")
print("="*60)

test_endpoint(
    "Aggregated Open Interest",
    "/api/futures/aggregated-open-interest-history",
    {'symbol': 'BTC', 'interval': '4h', 'limit': 5},
    "OI across all exchanges"
)

test_endpoint(
    "Exchange Rankings",
    "/api/futures/exchange-ranking",
    {},
    "Exchange volume rankings"
)

# 8. ARBITRAGE OPPORTUNITIES
print("\n\n🔍 CATEGORY: ARBITRAGE")
print("="*60)

test_endpoint(
    "Funding Arbitrage",
    "/api/futures/funding-arbitrage",
    {'symbol': 'BTC'},
    "Funding rate arbitrage opportunities"
)

# Wait a bit to avoid rate limits
time.sleep(1)

# SUMMARY
print("\n\n" + "="*60)
print("TESTING COMPLETE - SUMMARY")
print("="*60)

print(f"\n✅ WORKING ENDPOINTS ({len(working_endpoints)}):")
for ep in working_endpoints:
    print(f"  - {ep['name']}: {ep['description']}")

print(f"\n❌ FAILED ENDPOINTS ({len(failed_endpoints)}):")
for ep in failed_endpoints:
    print(f"  - {ep['name']}: {ep['error']}")

print("\n" + "="*60)
print("MOST VALUABLE FOR TRADING:")
print("="*60)

valuable = [ep for ep in working_endpoints if any(
    keyword in ep['name'].lower()
    for keyword in ['funding', 'order', 'position', 'rsi', 'basis', 'arbitrage']
)]

if valuable:
    print("High-value endpoints found:")
    for ep in valuable:
        print(f"  🎯 {ep['name']}")
else:
    print("Check working endpoints for valuable data")

print("\n" + "="*60)
print("END OF COMPREHENSIVE TEST")
print("="*60)