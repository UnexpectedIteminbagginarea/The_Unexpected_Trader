#!/usr/bin/env python3
"""
Test CoinGlass Long/Short Ratio endpoints with correct parameters
Based on documentation findings
"""
import requests
import json
from datetime import datetime

API_KEY = "YOUR_COINGLASS_API_KEY"
BASE_URL = "https://open-api-v4.coinglass.com"

# Standard headers based on documentation
headers = {
    'accept': 'application/json',
    'CG-API-KEY': API_KEY
}

def test_endpoint(endpoint_name, url, params=None):
    """Test a CoinGlass endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing: {endpoint_name}")
    print(f"URL: {url}")
    if params:
        print(f"Params: {params}")
    print(f"Headers: {headers}")
    print('-'*60)

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)[:500]}...")

            # Check if it's a success response
            if data.get('code') == '0':
                print("✅ SUCCESS - Endpoint working!")
                return True
            else:
                print(f"❌ API Error: {data.get('msg', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")

    except Exception as e:
        print(f"❌ Exception: {e}")

    return False

# Test 1: Global Long/Short Account Ratio - with 4h interval (Hobbyist plan minimum)
print("\n" + "="*60)
print("TESTING LONG/SHORT RATIO ENDPOINTS WITH HOBBYIST PLAN PARAMETERS")
print("="*60)

# According to docs, Hobbyist plan needs interval >= 4h
test_params_4h = {
    'symbol': 'BTC',
    'interval': '4h',  # Minimum for Hobbyist plan
    'limit': 10
}

test_endpoint(
    "Global Long/Short Account Ratio (4h interval)",
    f"{BASE_URL}/api/futures/global-long-short-account-ratio/history",
    test_params_4h
)

# Test with different interval formats
test_params_h4 = {
    'symbol': 'BTC',
    'interval': 'h4',  # Alternative format
    'limit': 10
}

test_endpoint(
    "Global Long/Short Account Ratio (h4 format)",
    f"{BASE_URL}/api/futures/global-long-short-account-ratio/history",
    test_params_h4
)

# Test with 1d interval (should definitely work)
test_params_1d = {
    'symbol': 'BTC',
    'interval': '1d',
    'limit': 10
}

test_endpoint(
    "Global Long/Short Account Ratio (1d interval)",
    f"{BASE_URL}/api/futures/global-long-short-account-ratio/history",
    test_params_1d
)

# Test 2: Top Account Long/Short Ratio
test_params_top = {
    'symbol': 'BTC',
    'interval': '4h',
    'limit': 10
}

test_endpoint(
    "Top Account Long/Short Ratio",
    f"{BASE_URL}/api/futures/top-long-short-account-ratio/history",
    test_params_top
)

# Test 3: Taker Buy/Sell Volume (no interval required)
test_endpoint(
    "Taker Buy/Sell Volume Exchange List",
    f"{BASE_URL}/api/futures/taker-buy-sell-volume/exchange-list",
    None  # No params needed according to docs
)

# Test without symbol parameter (might be required differently)
test_params_no_symbol = {
    'interval': '4h',
    'limit': 10
}

test_endpoint(
    "Global L/S Ratio (no symbol)",
    f"{BASE_URL}/api/futures/global-long-short-account-ratio/history",
    test_params_no_symbol
)

# Test with exchange parameter (some endpoints might need this)
test_params_with_exchange = {
    'symbol': 'BTC',
    'exchange': 'Binance',
    'interval': '4h',
    'limit': 10
}

test_endpoint(
    "Global L/S Ratio (with exchange)",
    f"{BASE_URL}/api/futures/global-long-short-account-ratio/history",
    test_params_with_exchange
)

print("\n" + "="*60)
print("TESTING COMPLETE")
print("="*60)