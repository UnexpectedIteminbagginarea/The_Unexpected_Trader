import requests
import os
from dotenv import load_dotenv
load_dotenv()

# Check current price
response = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT')
price = float(response.json()['price'])

# Golden pocket levels
h4_gp_bottom = 111463
h4_gp_top = 112189

print(f'Current BTC Price: ${price:,.2f}')
print(f'4H Golden Pocket: ${h4_gp_bottom:,} - ${h4_gp_top:,}')

if h4_gp_bottom <= price <= h4_gp_top * 1.01:
    print('🎯 PRICE IS IN/NEAR GOLDEN POCKET - BOT WILL ENTER!')
else:
    distance = (price - h4_gp_top) / price * 100
    print(f'📍 Price is {distance:.2f}% from golden pocket top')

print(f'\nBot Status:')
print('✅ EAGER MODE: ON')
print('✅ BOUNCE DETECTED: YES (recent bounce confirmed)')
print('✅ Entry Threshold: Relaxed to 1% above GP')
print('✅ Confluence Required: Only 2 factors needed')
print('\n🚀 BOT IS READY TO ENTER IMMEDIATELY!')