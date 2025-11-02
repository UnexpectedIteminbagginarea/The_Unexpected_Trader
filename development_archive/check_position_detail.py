import os
import time
import hmac
import hashlib
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('ASTER_API_KEY')
api_secret = os.getenv('ASTER_API_SECRET')
base_url = 'https://fapi.asterdex.com'

timestamp = int(time.time() * 1000)
query_string = f'timestamp={timestamp}'
signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

headers = {'X-MBX-APIKEY': api_key}
url = f'{base_url}/fapi/v2/positionRisk?{query_string}&signature={signature}'
response = requests.get(url, headers=headers)

if response.status_code == 200:
    positions = response.json()
    for pos in positions:
        if pos['symbol'] == 'BTCUSDT' and float(pos.get('positionAmt', 0)) != 0:
            print(f'Symbol: {pos["symbol"]}')
            print(f'Position Amount: {pos["positionAmt"]} BTC')
            print(f'Entry Price: ${pos["entryPrice"]}')
            print(f'Mark Price: ${pos["markPrice"]}')
            print(f'Unrealized Profit: ${pos["unRealizedProfit"]}')
            print(f'Leverage: {pos["leverage"]}x')
            print(f'Liquidation Price: {pos.get("liquidationPrice", "N/A")}')

            entry = float(pos['entryPrice'])
            mark = float(pos['markPrice'])
            pnl_pct = ((mark - entry) / entry) * 100
            print(f'\nCalculated P&L %: {pnl_pct:.2f}%')
            print(f'Entry: ${entry:,.2f}')
            print(f'Mark: ${mark:,.2f}')
            print(f'Difference: ${mark - entry:,.2f}')
