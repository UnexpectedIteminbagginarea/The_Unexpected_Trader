"""
Position Recovery Module
Handles bot restart with existing positions
"""
import json
import os
from datetime import datetime
from aster_trading_client import AsterTradingClient

class PositionRecovery:
    """Recover and sync position state after bot restart"""

    def __init__(self):
        self.trading_client = AsterTradingClient()
        self.state_file = "logs/position_state.json"

    def save_position_state(self, position_data):
        """Save current position state to file"""
        state = {
            'timestamp': datetime.now().isoformat(),
            'position': position_data,
            'last_entry_price': position_data.get('entry_price'),
            'total_position_size': position_data.get('size'),
            'current_leverage': position_data.get('leverage'),
            'scale_in_count': position_data.get('scale_in_count', 0)
        }

        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

        print(f"💾 Position state saved to {self.state_file}")

    def recover_position(self):
        """
        Check for existing position on Aster and recover state
        Returns: (has_position, position_data)
        """
        print("\n🔄 Checking for existing positions...")

        # Check actual position on exchange
        live_position = self.trading_client.get_current_position()

        if live_position:
            print(f"⚠️  FOUND EXISTING POSITION!")
            print(f"   Size: {live_position['amount']} BTC")
            print(f"   Entry: ${live_position['entry_price']:,.2f}")
            print(f"   Current P&L: ${live_position['pnl']:,.2f}")

            # Try to load saved state
            saved_state = None
            if os.path.exists(self.state_file):
                try:
                    with open(self.state_file, 'r') as f:
                        saved_state = json.load(f)
                    print(f"📁 Loaded saved state from {saved_state['timestamp']}")
                except:
                    print("⚠️  Could not load saved state, using exchange data only")

            # Build recovered position data
            recovered_position = {
                'entry_price': live_position['entry_price'],
                'average_price': live_position['entry_price'],  # Will be updated if we have saves
                'size': live_position['amount'],
                'leverage': live_position.get('leverage', 3),
                'entry_time': saved_state['timestamp'] if saved_state else datetime.now().isoformat(),
                'scale_in_count': saved_state.get('scale_in_count', 0) if saved_state else 0
            }

            # If we have saved state, use its average price (might be different after scale-ins)
            if saved_state and saved_state.get('position'):
                recovered_position['average_price'] = saved_state['position'].get('average_price', live_position['entry_price'])

            # Calculate what the original entry price was (for scale-in calculations)
            last_entry = saved_state.get('last_entry_price') if saved_state else live_position['entry_price']

            print("\n✅ Position recovered successfully!")
            print(f"   Will continue managing position from here")
            print(f"   Scale-in count: {recovered_position['scale_in_count']}")

            return True, recovered_position, last_entry

        else:
            print("✅ No existing positions found - starting fresh")

            # Clean up old state file if exists
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
                print("🗑️  Cleaned up old position state file")

            return False, None, None

    def log_recovery(self, logger, position_data):
        """Log the recovery event to trading logs"""

        # FIX: Synchronize logger's current_position with recovered position
        # This ensures future log_scale_decision() and log_exit_decision() calls work
        # Without this, logger.current_position stays None and causes crashes
        logger.current_position = {
            'status': 'OPEN',
            'entry_price': position_data['entry_price'],
            'average_price': position_data['average_price'],
            'size': position_data['size'],
            'leverage': position_data['leverage'],
            'entry_time': position_data.get('entry_time', datetime.now().isoformat())
        }

        logger.decisions.append({
            'timestamp': datetime.now().isoformat(),
            'action': 'RECOVERY',
            'details': f"Bot restarted with existing position: {position_data['size']} BTC @ ${position_data['average_price']:,.2f}",
            'reasoning': 'Position recovered after bot restart'
        })
        logger._save_decisions()

        # Also log to readable file
        with open('logs/trading_decisions_readable.txt', 'a') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"[{datetime.now().isoformat()}] 🔄 POSITION RECOVERY\n")
            f.write(f"  Bot restarted with existing position\n")
            f.write(f"  Size: {position_data['size']} BTC\n")
            f.write(f"  Average Price: ${position_data['average_price']:,.2f}\n")
            f.write(f"{'='*60}\n\n")

        print("📝 Recovery event logged")


# Test recovery
if __name__ == "__main__":
    recovery = PositionRecovery()
    has_position, position_data, last_entry = recovery.recover_position()

    if has_position:
        print("\n📊 Recovery Summary:")
        print(f"Has Position: {has_position}")
        print(f"Position Data: {position_data}")
        print(f"Last Entry Price: ${last_entry:,.2f}")
    else:
        print("\nNo position to recover")