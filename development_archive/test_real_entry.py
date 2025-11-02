"""
Test real entry on Aster with SOL collateral
"""
from aster_trading_client import AsterTradingClient

client = AsterTradingClient()

print("=" * 60)
print("TESTING REAL ENTRY")
print("=" * 60)

# Check account
account = client.get_account_info()

# Get current price
import requests
response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
current_price = float(response.json()['price'])
print(f"\nCurrent BTC Price: ${current_price:,.2f}")

# Check if we're in golden pocket
gp_bottom = 111463
gp_top = 112189

if gp_bottom <= current_price <= gp_top * 1.01:
    print("✅ Price is IN golden pocket - perfect entry!")

    print("\nPlacing REAL order on Aster...")
    print("-" * 40)

    # Enter position: 35% @ 3x leverage
    success = client.enter_long_position(
        percentage=0.35,
        leverage=3,
        current_price=current_price
    )

    if success:
        print("\n🎉 REAL POSITION OPENED!")

        # Check position
        client.get_current_position()
    else:
        print("\n❌ Failed to enter position")
else:
    print(f"❌ Price not in golden pocket")
    print(f"   Golden Pocket: ${gp_bottom:,} - ${gp_top:,}")
    print(f"   Current: ${current_price:,.2f}")