"""
Test script to run one trading cycle in paper mode
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.trader import VibeTrader
import asyncio

async def test_single_cycle():
    """Run a single trading cycle for testing"""
    print("🧪 Testing Vibe Trader - Single Cycle")
    print("=" * 50)

    # Create trader instance
    trader = VibeTrader()

    # Make sure we're in paper mode
    if not trader.paper_mode:
        print("⚠️ WARNING: Not in paper mode! Exiting for safety.")
        return

    print(f"✅ Paper mode confirmed")
    print(f"💰 Starting paper balance: ${trader.paper_balance:.2f}")
    print("=" * 50)

    # Run one trading cycle
    trader.run_trading_cycle()

    print("=" * 50)
    print("✅ Test cycle complete!")
    print(f"💰 Final paper balance: ${trader.paper_balance:.2f}")
    if trader.paper_positions:
        print(f"📊 Open positions: {list(trader.paper_positions.keys())}")
    else:
        print("📊 No positions opened")

if __name__ == "__main__":
    asyncio.run(test_single_cycle())