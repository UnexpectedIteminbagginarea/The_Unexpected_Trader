"""
Check Aster wallet balance and account info
"""
import os
import requests
import hmac
import hashlib
import time
from dotenv import load_dotenv

load_dotenv()

# API credentials
api_key = os.getenv('ASTER_API_KEY')
api_secret = os.getenv('ASTER_API_SECRET')

base_url = "https://fapi.asterdex.com"

def generate_signature(query_string, secret):
    """Generate HMAC SHA256 signature"""
    return hmac.new(
        secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

# Check account info
timestamp = int(time.time() * 1000)
query_string = f"timestamp={timestamp}"
signature = generate_signature(query_string, api_secret)

headers = {
    'X-MBX-APIKEY': api_key
}

# Get account balance
url = f"{base_url}/fapi/v2/balance?{query_string}&signature={signature}"
response = requests.get(url, headers=headers)

print("=" * 60)
print("ASTER ACCOUNT STATUS")
print("=" * 60)

if response.status_code == 200:
    balances = response.json()

    for balance in balances:
        if float(balance.get('balance', 0)) > 0:
            print(f"\nAsset: {balance['asset']}")
            print(f"  Free: {balance.get('free', 0)}")
            print(f"  Locked: {balance.get('locked', 0)}")
            print(f"  Total: {balance.get('balance', 0)}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)

# Check open positions
url = f"{base_url}/fapi/v2/positionRisk?{query_string}&signature={signature}"
response = requests.get(url, headers=headers)

if response.status_code == 200:
    positions = response.json()

    print("\n" + "=" * 60)
    print("OPEN POSITIONS")
    print("=" * 60)

    has_positions = False
    for pos in positions:
        if float(pos.get('positionAmt', 0)) != 0:
            has_positions = True
            print(f"\nSymbol: {pos['symbol']}")
            print(f"  Position: {pos['positionAmt']}")
            print(f"  Entry Price: {pos.get('entryPrice', 0)}")
            print(f"  Mark Price: {pos.get('markPrice', 0)}")
            print(f"  Unrealized PNL: {pos.get('unrealizedProfit', 0)}")

    if not has_positions:
        print("\nNo open positions")
else:
    print(f"Error checking positions: {response.text}")