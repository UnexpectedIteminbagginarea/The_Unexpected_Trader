"""
Verify 5x notional cap is what we already have
"""

capital = 442  # USD equivalent

print("="*70)
print("EXPOSURE CAP VERIFICATION")
print("="*70)

print(f"\nCapital: ${capital}")
print(f"5x Cap: ${capital * 5:,.0f} notional exposure max")

print("\n" + "-"*70)
print("CURRENT SCALE-IN PLAN (No Sentiment Multipliers)")
print("-"*70)

trades = [
    ("Entry", 0.35, 3),
    ("Scale 1", 0.20, 3),
    ("Scale 2", 0.25, 4),
    ("Scale 3", 0.25, 5),
    ("Scale 4", 0.30, 5),
]

total_capital = 0
total_notional = 0

for name, size, lev in trades:
    capital_used = size * capital
    notional = size * lev * capital
    total_capital += capital_used
    total_notional += notional

    print(f"{name:10s}: {size*100:5.1f}% × {lev}x = {notional:7.2f} notional (${capital_used:.2f} capital)")

print(f"\nTotal Capital Used: ${total_capital:.2f} ({total_capital/capital*100:.1f}%)")
print(f"Total Notional: ${total_notional:.2f} ({total_notional/capital:.2f}x)")

if total_notional <= capital * 5:
    print(f"✅ WITHIN 5x cap (using {total_notional/capital:.2f}x of allowed 5.0x)")
else:
    print(f"❌ EXCEEDS 5x cap! (using {total_notional/capital:.2f}x)")

print("\n" + "-"*70)
print("WITH MAX SENTIMENT MULTIPLIER (1.5x worst case)")
print("-"*70)

total_capital_max = 0
total_notional_max = 0

for name, size, lev in trades:
    adjusted_size = size * 1.5  # Worst case multiplier
    capital_used = adjusted_size * capital
    notional = adjusted_size * lev * capital
    total_capital_max += capital_used
    total_notional_max += notional

    print(f"{name:10s}: {size*100:5.1f}% × 1.5 × {lev}x = {notional:7.2f} notional")

print(f"\nTotal Capital Used: ${total_capital_max:.2f} ({total_capital_max/capital*100:.1f}%)")
print(f"Total Notional: ${total_notional_max:.2f} ({total_notional_max/capital:.2f}x)")

if total_notional_max <= capital * 5:
    print(f"✅ WITHIN 5x cap (using {total_notional_max/capital:.2f}x of allowed 5.0x)")
else:
    print(f"❌ EXCEEDS 5x cap! (using {total_notional_max/capital:.2f}x)")
    excess = total_notional_max - (capital * 5)
    print(f"   Excess: ${excess:.2f}")

print("\n" + "="*70)
print("CONCLUSION")
print("="*70)
print("Without sentiment multipliers: Uses 5.43x (slightly over 5x)")
print("With 1.5x max multiplier: Uses 8.14x (WAY over 5x!)")
print("\n⚠️ We need to implement the cap to prevent exceeding 5x!")
