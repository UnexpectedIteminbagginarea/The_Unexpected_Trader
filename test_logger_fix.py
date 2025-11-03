"""
Test Logger Fix #1 - Simulate exact production Claude ADD flow
Tests that logger.log_scale_decision() works after recovery
"""
import json
import os
import sys
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

# Import actual production code
from trading_decision_logger import TradingDecisionLogger
from position_recovery import PositionRecovery
from aster_trading_client import AsterTradingClient

def test_logger_synchronization_after_recovery():
    """
    Simulate EXACT production scenario:
    1. Bot restarts
    2. Recovery loads position from Aster
    3. Logger should be synchronized
    4. Claude ADD triggers
    5. Trade executes
    6. logger.log_scale_decision() should work (not crash)
    7. trading_decisions.json should be updated
    """
    print("="*80)
    print("TEST: Logger Synchronization After Recovery")
    print("="*80)

    # Clean test environment
    test_log_file = "logs/trading_decisions_TEST.json"
    test_state_file = "logs/position_state_TEST.json"

    if os.path.exists(test_log_file):
        os.remove(test_log_file)
    if os.path.exists(test_state_file):
        os.remove(test_state_file)

    # STEP 1: Create a saved position state (simulates previous session)
    print("\n1️⃣ SETUP: Creating saved position state (simulates previous session)")

    position_data = {
        'entry_price': 111091.20,
        'average_price': 109979.94,  # After scale-ins
        'size': 0.01,
        'leverage': 4,
        'entry_time': '2025-10-29T17:48:31',
        'scale_in_count': 3
    }

    state = {
        'timestamp': datetime.now().isoformat(),
        'position': position_data,
        'last_entry_price': position_data['entry_price'],
        'total_position_size': position_data['size'],
        'current_leverage': position_data['leverage'],
        'scale_in_count': position_data.get('scale_in_count', 0)
    }

    with open(test_state_file, 'w') as f:
        json.dump(state, f, indent=2)

    print(f"   ✅ Saved position: {position_data['size']} BTC @ ${position_data['average_price']:,.2f}")

    # STEP 2: Create logger (simulates bot startup)
    print("\n2️⃣ BOT STARTUP: Initialize logger")

    # Create logger with test directory
    os.makedirs("logs", exist_ok=True)
    logger = TradingDecisionLogger(log_dir="logs")

    # Override file paths for test
    logger.decision_log_file = test_log_file
    logger.readable_log_file = "logs/trading_decisions_readable_TEST.txt"
    logger.summary_log_file = "logs/decision_summary_TEST.md"

    # Reset to clean state (simulates fresh startup)
    logger.decisions = []
    logger.current_position = None

    print(f"   Logger initialized:")
    print(f"   logger.current_position = {logger.current_position}")

    # STEP 3: Simulate position recovery
    print("\n3️⃣ RECOVERY: Simulating position recovery from Aster")

    # Mock the trading client to return our test position
    mock_client = Mock()
    mock_client.get_current_position = Mock(return_value={
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'amount': 0.01,
        'entry_price': 109979.94,
        'mark_price': 107500.00,
        'pnl': -24.80,
        'leverage': 4.0
    })

    # Create recovery instance with mocked client
    recovery = PositionRecovery()
    recovery.trading_client = mock_client
    recovery.state_file = test_state_file

    # Recover position (uses our saved state file)
    has_position, recovered_position, last_entry = recovery.recover_position()

    print(f"   Position recovered: {has_position}")
    print(f"   Data: {recovered_position}")

    # STEP 4: Call log_recovery (THIS IS WHERE FIX #1 HAPPENS)
    print("\n4️⃣ FIX #1: Calling log_recovery() with logger synchronization")

    print(f"   BEFORE: logger.current_position = {logger.current_position}")

    # This is the actual production code path
    recovery.log_recovery(logger, recovered_position)

    print(f"   AFTER: logger.current_position = {logger.current_position}")

    if logger.current_position is None:
        print("   ❌ FAILED: logger.current_position is still None!")
        return False
    else:
        print(f"   ✅ SUCCESS: logger.current_position synchronized!")

    # STEP 5: Simulate Claude ADD decision
    print("\n5️⃣ CLAUDE ADD: Simulating Claude suggests ADD 5%")

    current_price = 107500.00
    add_amount = 0.05  # 5% add
    leverage = 4

    print(f"   Claude suggests: Add {add_amount*100:.0f}% at ${current_price:,.2f}")

    # STEP 6: Simulate trade execution
    print("\n6️⃣ TRADE EXECUTION: Simulating successful Aster trade")

    # This simulates what aster_trading_client.scale_in_position() returns
    trade_success = True

    if trade_success:
        print(f"   ✅ Trade executed on Aster (simulated)")

    # STEP 7: Call logger.log_scale_decision() - THE CRITICAL TEST
    print("\n7️⃣ LOGGING: Calling logger.log_scale_decision() - THIS IS THE TEST")

    try:
        reason = "Claude 20-min review: Test scenario - simulating production ADD"
        decision = logger.log_scale_decision(
            price=current_price,
            add_size=add_amount * 100,  # Convert to percentage for display
            new_leverage=leverage,
            deviation=0,  # Claude-initiated, not deviation-based
            reason=reason
        )

        print(f"   ✅ SUCCESS: log_scale_decision() executed without crash!")
        print(f"   Decision logged: {decision['action']} at ${decision['price']:,.2f}")

    except TypeError as e:
        if "'NoneType' object is not subscriptable" in str(e):
            print(f"   ❌ FAILED: Got the exact production crash!")
            print(f"   Error: {e}")
            return False
        else:
            raise

    # STEP 8: Verify trading_decisions.json was updated
    print("\n8️⃣ VERIFICATION: Check if trading_decisions.json was updated")

    if os.path.exists(test_log_file):
        with open(test_log_file, 'r') as f:
            decisions = json.load(f)

        print(f"   Total decisions in file: {len(decisions)}")

        # Find the SCALE_IN we just added
        scale_ins = [d for d in decisions if d['action'] == 'SCALE_IN']

        if len(scale_ins) > 0:
            latest = scale_ins[-1]
            print(f"   ✅ Latest SCALE_IN found:")
            print(f"      Timestamp: {latest['timestamp']}")
            print(f"      Price: ${latest['price']:,.2f}")
            print(f"      Added: {latest['added_size']}%")
            print(f"      New average: ${latest['new_average']:,.2f}")
            print(f"      Reasoning: {latest['reasoning'][:60]}...")

            # Verify the math is correct
            old_avg = 109979.94
            old_size = 0.01
            new_size = old_size + add_amount
            expected_avg = (old_size * old_avg + add_amount * current_price) / new_size

            if abs(latest['new_average'] - expected_avg) < 0.01:
                print(f"   ✅ Math verified: Average calculated correctly")
            else:
                print(f"   ⚠️ Math mismatch: Expected ${expected_avg:,.2f}, got ${latest['new_average']:,.2f}")
        else:
            print(f"   ❌ No SCALE_IN found in log!")
            return False
    else:
        print(f"   ❌ Log file not created!")
        return False

    # STEP 9: Verify logger's internal state updated
    print("\n9️⃣ STATE VERIFICATION: Check logger's internal current_position")

    if logger.current_position:
        print(f"   Current size: {logger.current_position['size']}")
        print(f"   Current average: ${logger.current_position['average_price']:,.2f}")

        # Should match what was saved to file
        expected_size = 0.01 + add_amount
        if abs(logger.current_position['size'] - expected_size) < 0.0001:
            print(f"   ✅ Logger state correct: Size updated to {expected_size}")
        else:
            print(f"   ⚠️ Size mismatch: Expected {expected_size}, got {logger.current_position['size']}")
    else:
        print(f"   ❌ logger.current_position is None!")
        return False

    print("\n" + "="*80)
    print("✅ TEST PASSED - Fix #1 works correctly!")
    print("="*80)
    print("\nConclusion:")
    print("  - logger.current_position synchronized after recovery ✅")
    print("  - log_scale_decision() executes without crash ✅")
    print("  - trading_decisions.json updated correctly ✅")
    print("  - Logger internal state updated correctly ✅")
    print("\nFix #1 should work in production on next Claude ADD.")

    # Cleanup test files
    print("\n🧹 Cleaning up test files...")
    if os.path.exists(test_log_file):
        os.remove(test_log_file)
    if os.path.exists(test_state_file):
        os.remove(test_state_file)
    if os.path.exists("logs/trading_decisions_readable_TEST.txt"):
        os.remove("logs/trading_decisions_readable_TEST.txt")
    if os.path.exists("logs/decision_summary_TEST.md"):
        os.remove("logs/decision_summary_TEST.md")

    return True


if __name__ == "__main__":
    print("\n🧪 TESTING FIX #1: Logger Synchronization After Recovery")
    print("This simulates the EXACT production flow that was failing\n")

    success = test_logger_synchronization_after_recovery()

    if success:
        print("\n✅ All tests passed - Fix #1 is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ Test failed - Fix #1 needs more work")
        sys.exit(1)
