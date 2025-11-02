"""
Safety Validation Layer
Enforces hard limits that cannot be overridden by Claude or algorithms
"""
import time
from datetime import datetime, date
from typing import Dict, Tuple, Optional

class SafetyValidator:
    """
    Enforces safety rules before executing any trade
    Returns: (approved: bool, reason: str, adjusted_decision: dict or None)
    """

    # Hard limits (cannot be overridden)
    MIN_LIQUID_RESERVE = 0.06       # 6% must stay liquid
    MAX_CAPITAL_USAGE = 0.94        # Max 94% deployed
    MAX_LEVERAGE = 5.0              # 5x maximum
    MAX_TOTAL_NOTIONAL = 5.0        # 5x capital total exposure
    MIN_LIQUIDATION_BUFFER = 0.30   # 30% away from liquidation
    MIN_POSITION_SIZE = 0.25        # 25% minimum
    MAX_POSITION_SIZE = 0.75        # 75% maximum
    MAX_ADJUSTMENTS_PER_DAY = 3     # 3 per day
    MAX_ADD_PER_REVIEW = 0.05       # 5% max add

    def __init__(self):
        """Initialize validator with tracking"""
        self.adjustment_log = {}  # Track daily adjustments
        self.last_adjustment_time = 0

    def validate_entry(self, decision: Dict, current_position: Optional[Dict], account_info: Dict) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validate an entry decision from Claude
        Returns: (approved, reason, adjusted_decision)
        """
        size = decision.get('size_or_amount', 0)
        leverage = 3  # Base leverage for entries

        print(f"\n🛡️ SAFETY VALIDATION - ENTRY")
        print(f"   Proposed size: {size*100:.1f}%")

        # Check 1: Position size range
        if size < self.MIN_POSITION_SIZE:
            return (False, f"Size {size*100:.1f}% below minimum {self.MIN_POSITION_SIZE*100:.0f}%", None)

        if size > self.MAX_POSITION_SIZE:
            adjusted = decision.copy()
            adjusted['size_or_amount'] = self.MAX_POSITION_SIZE
            print(f"   ⚠️ Size capped: {size*100:.1f}% → {self.MAX_POSITION_SIZE*100:.0f}%")
            return (True, f"Capped at {self.MAX_POSITION_SIZE*100:.0f}% maximum", adjusted)

        # Check 2: Liquid reserve
        current_deployed = current_position['size'] if current_position else 0
        total_deployed = current_deployed + size

        if total_deployed > self.MAX_CAPITAL_USAGE:
            max_allowed = self.MAX_CAPITAL_USAGE - current_deployed
            if max_allowed <= 0:
                return (False, "No capital available (94% already deployed)", None)

            adjusted = decision.copy()
            adjusted['size_or_amount'] = max_allowed
            print(f"   ⚠️ Liquid reserve: {size*100:.1f}% → {max_allowed*100:.1f}%")
            return (True, f"Reduced to maintain 6% liquid reserve", adjusted)

        # Check 3: Notional exposure
        current_notional = self._calculate_current_notional(current_position)
        new_notional = size * leverage
        total_notional = current_notional + new_notional

        print(f"   Current notional: {current_notional:.2f}x")
        print(f"   New trade: {new_notional:.2f}x")
        print(f"   Total: {total_notional:.2f}x")

        if total_notional > self.MAX_TOTAL_NOTIONAL:
            allowed_notional = self.MAX_TOTAL_NOTIONAL - current_notional
            if allowed_notional <= 0:
                return (False, f"Already at {self.MAX_TOTAL_NOTIONAL}x notional limit", None)

            safe_size = allowed_notional / leverage
            adjusted = decision.copy()
            adjusted['size_or_amount'] = safe_size
            print(f"   ⚠️ Notional cap: {size*100:.1f}% → {safe_size*100:.1f}%")
            return (True, f"Reduced to fit {self.MAX_TOTAL_NOTIONAL}x notional limit", adjusted)

        # Check 4: Leverage
        if leverage > self.MAX_LEVERAGE:
            return (False, f"Leverage {leverage}x exceeds maximum {self.MAX_LEVERAGE}x", None)

        print(f"   ✅ All safety checks passed")
        return (True, "Trade approved by safety layer", decision)

    def validate_adjustment(self, decision: Dict, current_position: Dict, current_price: float) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validate a 20-minute review adjustment
        """
        action = decision.get('decision')
        amount = decision.get('size_or_amount', 0)

        print(f"\n🛡️ SAFETY VALIDATION - ADJUSTMENT")
        print(f"   Action: {action}, Amount: {amount*100:.1f}%")

        # Check 1: Daily limit
        today = date.today().isoformat()
        todays_adjustments = self.adjustment_log.get(today, [])

        if len(todays_adjustments) >= self.MAX_ADJUSTMENTS_PER_DAY:
            return (False, f"Already made {self.MAX_ADJUSTMENTS_PER_DAY} adjustments today", None)

        # Check 2: Cooldown (30 minutes)
        time_since_last = time.time() - self.last_adjustment_time
        if time_since_last < 1800 and self.last_adjustment_time > 0:
            return (False, f"Must wait {int((1800 - time_since_last)/60)} more minutes", None)

        # Check 3: ADD specific checks
        if action == "ADD":
            # Cap at 5% max
            if amount > self.MAX_ADD_PER_REVIEW:
                adjusted = decision.copy()
                adjusted['size_or_amount'] = self.MAX_ADD_PER_REVIEW
                print(f"   ⚠️ ADD capped: {amount*100:.1f}% → {self.MAX_ADD_PER_REVIEW*100:.0f}%")
                return (True, "Capped at 5% max add", adjusted)

            # Check notional limits
            new_notional = amount * current_position.get('leverage', 4)
            current_notional = self._calculate_current_notional(current_position)

            if current_notional + new_notional > self.MAX_TOTAL_NOTIONAL:
                return (False, "Would exceed 5x notional limit", None)

        # Check 4: REDUCE specific checks
        if action == "REDUCE":
            # Check if in loss
            roi = self._calculate_roi(current_position, current_price)

            if roi < 0:
                return (False, "BLOCKED: Cannot reduce while in loss (ROE < 0). Either HOLD or EMERGENCY_EXIT.", None)

            # Cap at 20% max
            if amount > 0.20:
                adjusted = decision.copy()
                adjusted['size_or_amount'] = 0.20
                print(f"   ⚠️ REDUCE capped: {amount*100:.1f}% → 20%")
                return (True, "Capped at 20% max reduce", adjusted)

        print(f"   ✅ Adjustment approved")
        return (True, "Adjustment approved", decision)

    def log_adjustment(self, action: str, amount: float):
        """Record adjustment for daily limit tracking"""
        today = date.today().isoformat()

        if today not in self.adjustment_log:
            self.adjustment_log[today] = []

        self.adjustment_log[today].append({
            'time': datetime.now().isoformat(),
            'action': action,
            'amount': amount
        })

        self.last_adjustment_time = time.time()

    def validate_exit(self, decision: Dict, current_position: Dict) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validate an exit decision
        """
        exit_pct = decision.get('size_or_amount', 0)

        print(f"\n🛡️ SAFETY VALIDATION - EXIT")
        print(f"   Exit: {exit_pct*100:.0f}% of position")

        # Exits have fewer restrictions (taking profit is always OK)
        # Just verify percentage is sane
        if exit_pct < 0.25 or exit_pct > 1.0:
            return (False, f"Exit percentage {exit_pct*100:.0f}% outside 25-100% range", None)

        print(f"   ✅ Exit approved")
        return (True, "Exit approved", decision)

    def check_liquidation_distance(self, current_price: float, estimated_liq_price: float) -> bool:
        """
        Check if we're too close to liquidation
        """
        if estimated_liq_price == 0:
            return True  # No position

        buffer = (current_price - estimated_liq_price) / current_price

        if buffer < self.MIN_LIQUIDATION_BUFFER:
            print(f"   🚨 LIQUIDATION WARNING: Only {buffer*100:.1f}% away (min {self.MIN_LIQUIDATION_BUFFER*100:.0f}%)")
            return False

        return True

    # Helper methods
    def _calculate_current_notional(self, position: Optional[Dict]) -> float:
        """Calculate current notional exposure"""
        if not position or position.get('size', 0) == 0:
            return 0.0

        size = position.get('size', 0)
        leverage = position.get('leverage', 1)

        # Convert BTC size to capital percentage (rough estimate)
        # 0.01 BTC @ $110k = $1100 ≈ 2.5x of $442 capital
        # With 4x leverage = 10x notional
        # Simplified: use capital usage × leverage
        capital_pct = position.get('capital_used', 0.80)  # Estimate
        return capital_pct * leverage

    def _calculate_roi(self, position: Dict, current_price: float) -> float:
        """Calculate current ROI percentage"""
        if not position or not position.get('average_price'):
            return 0

        avg_entry = position['average_price']
        leverage = position.get('leverage', 1)

        price_change = (current_price - avg_entry) / avg_entry
        roi = price_change * leverage

        return roi * 100  # As percentage

    def get_stats(self) -> Dict:
        """Get validation statistics"""
        today = date.today().isoformat()
        return {
            'adjustments_today': len(self.adjustment_log.get(today, [])),
            'max_allowed': self.MAX_ADJUSTMENTS_PER_DAY,
            'time_since_last': int(time.time() - self.last_adjustment_time) if self.last_adjustment_time > 0 else 999999
        }


# Test the validator
if __name__ == "__main__":
    validator = SafetyValidator()

    print("Testing Safety Validator")
    print("="*60)

    # Test 1: Normal entry
    decision1 = {'decision': 'APPROVE', 'size_or_amount': 0.35}
    position = {'size': 0.01, 'leverage': 4, 'average_price': 109979, 'capital_used': 0.80}
    account = {'balance': 442}

    result = validator.validate_entry(decision1, position, account)
    print(f"\nTest 1 (Normal entry 35%): {result[0]} - {result[1]}")

    # Test 2: Entry too large
    decision2 = {'decision': 'APPROVE', 'size_or_amount': 0.90}
    result = validator.validate_entry(decision2, position, account)
    print(f"\nTest 2 (Oversized 90%): {result[0]} - {result[1]}")

    # Test 3: Add when at limit
    decision3 = {'decision': 'ADD', 'size_or_amount': 0.08}
    result = validator.validate_adjustment(decision3, position, 110000)
    print(f"\nTest 3 (Add 8% - should cap at 5%): {result[0]} - {result[1]}")

    # Test 4: Reduce while in loss
    decision4 = {'decision': 'REDUCE', 'size_or_amount': 0.15}
    result = validator.validate_adjustment(decision4, position, 108000)  # Price down = loss
    print(f"\nTest 4 (Reduce in loss): {result[0]} - {result[1]}")

    print("\n" + "="*60)
    print("Safety validator tests complete!")
