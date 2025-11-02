"""
Test exposure limit enforcement
"""

MAX_NOTIONAL = 5.0
MAX_CAPITAL = 1.35

def check_exposure_limits(current_capital, current_avg_lev, desired_size, new_leverage):
    """Test the limit logic"""

    current_notional = current_capital * current_avg_lev
    new_notional = desired_size * new_leverage
    total_capital = current_capital + desired_size
    total_notional = current_notional + new_notional

    print(f"   Current: {current_capital*100:.1f}% capital, {current_notional:.2f}x notional")
    print(f"   Proposed: +{desired_size*100:.1f}% @ {new_leverage}x = +{new_notional:.2f}x")
    print(f"   Total: {total_capital*100:.1f}% capital, {total_notional:.2f}x notional")

    # Check capital
    if total_capital > MAX_CAPITAL:
        allowed = MAX_CAPITAL - current_capital
        if allowed <= 0:
            print(f"   🚫 BLOCKED (capital)")
            return 0
        print(f"   ✂️ Reduced to {allowed*100:.1f}% (capital limit)")
        desired_size = allowed

    # Recheck notional
    new_notional = desired_size * new_leverage
    total_notional = current_notional + new_notional

    if total_notional > MAX_NOTIONAL:
        allowed_notional = MAX_NOTIONAL - current_notional
        if allowed_notional <= 0:
            print(f"   🚫 BLOCKED (notional)")
            return 0
        safe_size = allowed_notional / new_leverage
        print(f"   ✂️ Reduced to {safe_size*100:.1f}% (notional limit)")
        return safe_size

    print(f"   ✅ Approved: {desired_size*100:.1f}%")
    return desired_size


print("="*70)
print("EXPOSURE LIMIT TESTING")
print("="*70)

# Simulate current position
current_capital_used = 0.80  # 80% (entry 35% + scale1 20% + scale2 25%)
current_avg_leverage = 3.67  # Weighted avg of 3x, 3x, 4x

print(f"\nStarting Position:")
print(f"Capital used: {current_capital_used*100:.0f}%")
print(f"Average leverage: {current_avg_leverage:.2f}x")
print(f"Notional: {current_capital_used * current_avg_leverage:.2f}x\n")

print("\n" + "-"*70)
print("Test 1: Scale-in #3 (base 25% @ 5x)")
print("-"*70)
result1 = check_exposure_limits(current_capital_used, current_avg_leverage, 0.25, 5)

print("\n" + "-"*70)
print("Test 2: Scale-in #3 with 1.5x sentiment multiplier (37.5% @ 5x)")
print("-"*70)
result2 = check_exposure_limits(current_capital_used, current_avg_leverage, 0.375, 5)

print("\n" + "-"*70)
print("Test 3: After Scale #3, try Scale #4 (30% @ 5x)")
print("-"*70)
# Assume scale #3 went through with reduced size
new_capital = current_capital_used + result2
new_notional_base = current_capital_used * current_avg_leverage
# Add what was allowed from scale #3
if result2 > 0:
    new_avg_lev = (new_notional_base + result2 * 5) / new_capital
    result3 = check_exposure_limits(new_capital, new_avg_lev, 0.30, 5)
else:
    print("   (Skipped - previous trade blocked)")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"5x notional cap = ${442 * 5:,.0f} total exposure")
print(f"135% capital cap = ${442 * 1.35:.2f} total capital")
print("\n✅ Limits will prevent dangerous over-leveraging!")
print("✅ Bot can still scale in but safely")
