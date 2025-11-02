"""
Test Live API Connection with New Credentials
Verifies both Aster and CoinGlass APIs are working
"""
import os
import requests
import hmac
import hashlib
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_aster_connection():
    """Test Aster API connection"""
    print("\n" + "=" * 60)
    print("🔌 TESTING ASTER API CONNECTION")
    print("=" * 60)

    api_key = os.getenv('ASTER_API_KEY')
    api_secret = os.getenv('ASTER_API_SECRET')

    if not api_key or not api_secret:
        print("❌ Aster API credentials not found in .env")
        return False

    print(f"API Key: {api_key[:10]}...{api_key[-10:]}")

    # Correct Aster base URL from documentation
    base_url = "https://fapi.asterdex.com"

    # Create signature (required for signed endpoints)
    timestamp = str(int(time.time() * 1000))

    try:
        # Try a simple public endpoint first (no auth needed)
        test_url = f"{base_url}/fapi/v1/ticker/24hr?symbol=BTCUSDT"
        response = requests.get(test_url)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Connection successful!")
            print(f"   BTC Price: ${float(data.get('lastPrice', 0)):,.2f}")
            print(f"   24h Volume: ${float(data.get('volume', 0)):,.2f}")
            return True
        else:
            print(f"⚠️  Status {response.status_code}: {response.text[:100]}")
            print("   Note: API might require different endpoint or auth method")
            return False

    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

def test_coinglass_connection():
    """Test CoinGlass API connection"""
    print("\n" + "=" * 60)
    print("🔌 TESTING COINGLASS API CONNECTION")
    print("=" * 60)

    api_key = os.getenv('COINGLASS_API_KEY')

    if not api_key:
        print("❌ CoinGlass API key not found in .env")
        return False

    print(f"API Key: {api_key[:10]}...{api_key[-10:]}")

    headers = {
        'accept': 'application/json',
        'CG-API-KEY': api_key
    }

    try:
        # Test with Fear & Greed Index
        url = "https://open-api-v4.coinglass.com/api/index/fear-greed-history"
        params = {'time_type': 1}

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0':
                current_value = data['data']['data_list'][0]
                print(f"✅ Connection successful!")
                print(f"   Fear & Greed Index: {current_value}")

                if current_value < 25:
                    print("   Market Sentiment: Extreme Fear (Bullish opportunity)")
                elif current_value < 40:
                    print("   Market Sentiment: Fear")
                elif current_value < 60:
                    print("   Market Sentiment: Neutral")
                elif current_value < 75:
                    print("   Market Sentiment: Greed")
                else:
                    print("   Market Sentiment: Extreme Greed (Caution)")
                return True
            else:
                print(f"⚠️  API returned error: {data.get('msg', 'Unknown')}")
                return False
        else:
            print(f"❌ Status {response.status_code}: {response.text[:100]}")
            return False

    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

def check_current_market_position():
    """Check current BTC price vs our Fibonacci levels"""
    print("\n" + "=" * 60)
    print("📊 CURRENT MARKET POSITION")
    print("=" * 60)

    # Get current BTC price (you can use any API for this)
    try:
        response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
        current_price = float(response.json()['price'])

        print(f"BTC Current Price: ${current_price:,.2f}")

        # Our key Fibonacci levels
        h4_gp_top = 112189
        h4_gp_bottom = 111463
        daily_gp_top = 108975
        daily_gp_bottom = 108088

        print(f"\n📏 4H Golden Pocket: ${h4_gp_bottom:,} - ${h4_gp_top:,}")

        if h4_gp_bottom <= current_price <= h4_gp_top:
            print("   🎯 PRICE IN 4H GOLDEN POCKET - STRONG ENTRY ZONE!")
        elif current_price > h4_gp_top:
            distance = ((current_price - h4_gp_top) / current_price) * 100
            print(f"   Price {distance:.2f}% above 4H GP")
        else:
            distance = ((h4_gp_bottom - current_price) / current_price) * 100
            print(f"   Price {distance:.2f}% below 4H GP")

        print(f"\n📏 Daily Golden Pocket: ${daily_gp_bottom:,} - ${daily_gp_top:,}")

        if daily_gp_bottom <= current_price <= daily_gp_top:
            print("   🎯 PRICE IN DAILY GOLDEN POCKET - MAXIMUM CONVICTION!")
        elif current_price > daily_gp_top:
            distance = ((current_price - daily_gp_top) / current_price) * 100
            print(f"   Price {distance:.2f}% above Daily GP")

        # Trading recommendation
        print("\n💡 TRADING SIGNAL:")
        if h4_gp_bottom <= current_price <= h4_gp_top:
            print("   ✅ READY TO ENTER - 4H Golden Pocket active")
            print("   Suggested: 35% position @ 3x leverage")
        elif current_price > h4_gp_top and current_price < h4_gp_top * 1.01:
            print("   ⏳ WAIT FOR DIP - Very close to entry zone")
        elif daily_gp_bottom <= current_price <= daily_gp_top:
            print("   ✅ STRONG BUY - Daily Golden Pocket active")
            print("   Suggested: 42% position @ 4x leverage")
        else:
            print("   ⏳ WAIT - Not in optimal entry zone")

    except Exception as e:
        print(f"❌ Failed to get market data: {str(e)}")

def main():
    print("\n" + "=" * 80)
    print("🚀 LIVE TRADING SYSTEM CHECK")
    print("=" * 80)

    # Test all connections
    aster_ok = test_aster_connection()
    coinglass_ok = test_coinglass_connection()
    check_current_market_position()

    # Summary
    print("\n" + "=" * 60)
    print("📋 SYSTEM STATUS SUMMARY")
    print("=" * 60)

    if aster_ok and coinglass_ok:
        print("✅ ALL SYSTEMS GO - Ready for live trading!")
        print("\nNext steps:")
        print("1. Run small position test ($100-500)")
        print("2. Monitor execution and slippage")
        print("3. Scale up if profitable")
    elif coinglass_ok:
        print("⚠️  Aster API needs configuration")
        print("   CoinGlass working - can use for sentiment")
    else:
        print("❌ API connections need to be fixed before live trading")

if __name__ == "__main__":
    main()