#!/usr/bin/env python3
"""
Test alternative endpoint paths and variations
Many endpoints might have different URL structures
"""
import requests
import json

API_KEY = "YOUR_COINGLASS_API_KEY"
BASE_URL = "https://open-api-v4.coinglass.com"

headers = {
    'accept': 'application/json',
    'CG-API-KEY': API_KEY
}

working_endpoints = []

def test_variations(base_name, variations, params):
    """Test multiple variations of an endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing variations for: {base_name}")
    print('-'*40)

    for endpoint in variations:
        print(f"Trying: {endpoint}")
        try:
            response = requests.get(
                f"{BASE_URL}{endpoint}",
                headers=headers,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '0':
                    print(f"  ✅ SUCCESS!")
                    working_endpoints.append(endpoint)

                    if 'data' in data:
                        if isinstance(data['data'], list) and len(data['data']) > 0:
                            print(f"  Sample: {json.dumps(data['data'][0], indent=2)[:200]}")
                        elif isinstance(data['data'], dict):
                            print(f"  Sample: {json.dumps(data['data'], indent=2)[:200]}")
                    return True
                else:
                    print(f"  ❌ {data.get('msg')}")
            else:
                print(f"  ❌ HTTP {response.status_code}")
        except Exception as e:
            print(f"  ❌ {str(e)[:50]}")

    return False

print("\n" + "="*60)
print("TESTING ALTERNATIVE ENDPOINT PATHS")
print("="*60)

# Test Funding Rate variations
test_variations(
    "Funding Rates",
    [
        "/api/futures/funding-rate/history",
        "/api/futures/funding-rate",
        "/api/funding-rate/history",
        "/api/futures/funding/history",
        "/api/futures/funding-rates/history"
    ],
    {'exchange': 'Binance', 'symbol': 'BTCUSDT', 'interval': '8h', 'limit': 5}
)

# Test Order Book variations
test_variations(
    "Order Book",
    [
        "/api/futures/orderbook/history",
        "/api/futures/order-book/history",
        "/api/futures/orderbook",
        "/api/orderbook/history",
        "/api/futures/depth/history"
    ],
    {'exchange': 'Binance', 'symbol': 'BTCUSDT', 'limit': 1}
)

# Test RSI variations
test_variations(
    "RSI",
    [
        "/api/indicators/rsi",
        "/api/index/rsi",
        "/api/indicator/rsi-list",
        "/api/indicators/rsi-history",
        "/api/technical/rsi"
    ],
    {'symbol': 'BTC', 'interval': '4h'}
)

# Test aggregated OI variations
test_variations(
    "Aggregated Open Interest",
    [
        "/api/futures/aggregated-oi-history",
        "/api/futures/aggregated/open-interest",
        "/api/futures/oi/aggregated",
        "/api/aggregated/open-interest/history",
        "/api/futures/total-open-interest"
    ],
    {'symbol': 'BTC', 'interval': '4h', 'limit': 5}
)

# Test exchange info endpoints
test_variations(
    "Exchange Info",
    [
        "/api/futures/exchanges",
        "/api/futures/exchange-list",
        "/api/exchanges",
        "/api/futures/supported-exchanges",
        "/api/supported/exchanges"
    ],
    {}
)

# Test market overview
test_variations(
    "Market Overview",
    [
        "/api/futures/market-overview",
        "/api/market/overview",
        "/api/futures/summary",
        "/api/market-summary",
        "/api/overview"
    ],
    {}
)

# Test basis/premium
test_variations(
    "Basis/Premium",
    [
        "/api/futures/basis/history",
        "/api/futures/premium-index",
        "/api/basis/history",
        "/api/futures/spot-futures-spread",
        "/api/futures/basis"
    ],
    {'symbol': 'BTC', 'exchange': 'Binance'}
)

# Test whale/large trades
test_variations(
    "Whale Trades",
    [
        "/api/futures/whale-trades",
        "/api/futures/large-trades",
        "/api/futures/big-trades",
        "/api/trades/large",
        "/api/futures/whale-orders"
    ],
    {'symbol': 'BTCUSDT', 'exchange': 'Binance', 'limit': 10}
)

# Test OHLC variations
test_variations(
    "OHLC Price Data",
    [
        "/api/futures/ohlc",
        "/api/futures/price/ohlc",
        "/api/futures/kline",
        "/api/futures/candles",
        "/api/ohlc/history"
    ],
    {'symbol': 'BTCUSDT', 'exchange': 'Binance', 'interval': '4h', 'limit': 10}
)

# Test Stablecoin Margin
test_variations(
    "Stablecoin Margin OI",
    [
        "/api/futures/stablecoin-margin/history",
        "/api/futures/stable-margin/oi",
        "/api/futures/usdt-margin/history",
        "/api/futures/oi/stablecoin",
        "/api/futures/stablecoin/open-interest"
    ],
    {'symbol': 'BTC', 'interval': '4h', 'limit': 5}
)

# SUMMARY
print("\n\n" + "="*60)
print("SUMMARY OF WORKING ENDPOINTS")
print("="*60)

if working_endpoints:
    print(f"\n✅ Found {len(working_endpoints)} working endpoints:")
    for ep in working_endpoints:
        print(f"  - {ep}")
else:
    print("\n❌ No additional working endpoints found")

print("\n" + "="*60)
print("END OF ALTERNATIVE PATH TESTING")
print("="*60)