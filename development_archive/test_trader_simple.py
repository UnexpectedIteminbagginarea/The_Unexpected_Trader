"""
Simple test to verify trader works without CoinGlass
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Suppress CoinGlass errors for cleaner output
import logging
logging.getLogger("urllib3").setLevel(logging.WARNING)

from core.trader import VibeTrader
import asyncio

async def test_simple():
    """Run a simple test without CoinGlass"""
    print("=" * 60)
    print("🧪 VIBE TRADER TEST - Paper Trading Mode")
    print("=" * 60)
    print("Note: CoinGlass API not active yet - using dummy sentiment data")
    print("-" * 60)

    # Create trader
    trader = VibeTrader()

    # Verify paper mode
    print(f"✅ Mode: {'PAPER' if trader.paper_mode else 'LIVE'} Trading")
    print(f"💰 Starting Balance: ${trader.paper_balance:.2f}")
    print("-" * 60)

    # Test single decision for SOL
    print("\n📊 Testing SOL Trading Decision...")

    # Get data for SOL
    data = trader.analyzer.get_comprehensive_data("SOLUSDT")
    market_data = data['market_data']

    # Show market data
    print(f"\n📈 SOL Market Data:")
    print(f"  Price: ${market_data.get('price', 0):.2f}")
    print(f"  24h Change: {market_data.get('price_change_24h', 0):.2f}%")
    print(f"  Volume: ${market_data.get('volume_24h', 0):,.0f}")

    # Get AI decision
    print(f"\n🧠 Getting AI Decision...")
    sentiment_data = data['sentiment_data']
    decision = trader.brain.analyze_market(market_data, sentiment_data)

    # Show decision
    print(trader.brain.explain_reasoning(decision))

    # Execute if confident
    if decision['confidence'] >= 0.65:
        print(f"\n💡 Executing Trade...")
        success = trader.execute_decision("SOLUSDT", decision)
        if success:
            print(f"✅ Trade executed successfully!")
            print(f"💰 New Balance: ${trader.paper_balance:.2f}")
            if trader.paper_positions:
                pos = trader.paper_positions.get("SOLUSDT")
                if pos:
                    print(f"📊 Position: {pos['side']} {pos['quantity']:.4f} SOL @ ${pos['entry_price']:.2f}")
        else:
            print(f"❌ Trade not executed")
    else:
        print(f"\n⏭️ Skipping trade - confidence too low ({decision['confidence']:.1%})")

    print("\n" + "=" * 60)
    print("✅ Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    # Suppress deprecation warnings
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    asyncio.run(test_simple())