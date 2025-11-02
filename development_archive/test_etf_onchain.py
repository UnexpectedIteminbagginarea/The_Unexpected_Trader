#!/usr/bin/env python3
"""
Test ETF and other endpoints with correct paths
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
print("TESTING CORRECTED ENDPOINTS")
print("="*60)

# Working ETF endpoints
print("\n📊 ETF FLOW DATA")
print("-"*40)

etf_tests = [
    ("/api/etf/bitcoin/flow-history", {}, "Bitcoin ETF Flow History"),
    ("/api/etf/bitcoin/net-assets-history", {}, "Bitcoin ETF Net Assets"),
    ("/api/etf/bitcoin/premium-discount-history", {}, "Bitcoin ETF Premium/Discount"),
    ("/api/etf/ethereum/flow-history", {}, "Ethereum ETF Flow History"),
]

working_endpoints = []

for endpoint, params, name in etf_tests:
    print(f"\nTesting: {name}")
    print(f"Path: {endpoint}")

    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                print(f"✅ SUCCESS!")
                working_endpoints.append((name, endpoint))

                if 'data' in data and data['data']:
                    if isinstance(data['data'], list) and len(data['data']) > 0:
                        latest = data['data'][0]
                        print(f"Latest data:")

                        # ETF flow specific parsing
                        if 'flow_usd' in latest:
                            flow_millions = latest['flow_usd'] / 1_000_000
                            print(f"  Net Flow: ${flow_millions:,.1f}M")

                            if 'etf_flows' in latest:
                                print(f"  Individual ETFs:")
                                for etf in latest['etf_flows'][:3]:  # Show top 3
                                    etf_flow = etf['flow_usd'] / 1_000_000
                                    print(f"    {etf['etf_ticker']}: ${etf_flow:+,.1f}M")

                        # Net assets parsing
                        elif 'net_assets_usd' in latest:
                            assets_billions = latest.get('net_assets_usd', 0) / 1_000_000_000
                            print(f"  Net Assets: ${assets_billions:,.1f}B")

                        else:
                            print(f"  {json.dumps(latest, indent=2)[:200]}")
            else:
                print(f"❌ {data.get('msg')}")
        else:
            print(f"❌ HTTP {response.status_code}")

    except Exception as e:
        print(f"❌ Exception: {e}")

# Try spot market endpoints
print("\n\n📊 SPOT MARKET DATA")
print("-"*40)

spot_tests = [
    ("/api/spot/symbol/ticker", {'symbol': 'BTCUSDT'}, "Spot Ticker"),
    ("/api/spot/supported-symbol", {}, "Supported Spot Symbols"),
]

for endpoint, params, name in spot_tests:
    print(f"\nTesting: {name}")

    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                print(f"✅ SUCCESS!")
                working_endpoints.append((name, endpoint))

                if 'data' in data:
                    print(f"Sample: {json.dumps(data['data'], indent=2)[:300] if data['data'] else 'Empty'}")
            else:
                print(f"❌ {data.get('msg')}")

    except Exception as e:
        print(f"❌ Exception: {e}")

print("\n" + "="*60)
print("SUMMARY OF NEW DISCOVERIES")
print("="*60)

if working_endpoints:
    print(f"\n✅ Found {len(working_endpoints)} NEW working endpoints:")
    for name, path in working_endpoints:
        print(f"  - {name}: {path}")
else:
    print("\n❌ No new endpoints found")

print("\n" + "="*60)
print("KEY INSIGHTS")
print("="*60)

print("""
🎯 ETF Flow Data is VALUABLE:
- Shows institutional money movement
- Bitcoin ETF daily flows (billions)
- Individual ETF breakdowns (GBTC outflows vs IBIT inflows)
- Net assets tracking

💡 Trading Applications:
1. Large ETF inflows → Bullish institutional sentiment
2. GBTC outflows slowing → Selling pressure reducing
3. Net assets growing → Long-term accumulation
4. Compare ETF flows to retail L/S ratio for divergence

This adds INSTITUTIONAL SENTIMENT to our retail sentiment!
""")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)