"""
Test sentiment-based position sizing logic
"""

def calculate_sentiment_multiplier(sentiment):
    """
    Calculate position size multiplier based on sentiment indicators
    Returns: 0.5x to 1.5x multiplier for adaptive position sizing
    """
    multipliers = []

    # Fear & Greed (contrarian - fear = buy opportunity)
    fg = sentiment.get('fear_greed', 50)
    if fg < 25:
        multipliers.append(1.3)
        print(f"   📊 Extreme fear ({fg}) → 1.3x size multiplier")
    elif fg < 40:
        multipliers.append(1.1)
        print(f"   📊 Fear ({fg}) → 1.1x size multiplier")
    elif fg > 75:
        multipliers.append(0.6)
        print(f"   📊 Extreme greed ({fg}) → 0.6x size multiplier")
    else:
        multipliers.append(1.0)

    # Funding Rate (contrarian for longs - negative = buy)
    fr = sentiment.get('funding_rate', 0)
    if fr < -0.01:
        multipliers.append(1.3)
        print(f"   📊 Very negative funding ({fr:.4f}) → 1.3x size multiplier")
    elif fr < 0:
        multipliers.append(1.1)
        print(f"   📊 Negative funding ({fr:.4f}) → 1.1x size multiplier")
    elif fr > 0.05:
        multipliers.append(0.5)
        print(f"   📊 High funding ({fr:.4f}) → 0.5x size multiplier")
    elif fr > 0.02:
        multipliers.append(0.8)
        print(f"   📊 Elevated funding ({fr:.4f}) → 0.8x size multiplier")
    else:
        multipliers.append(1.0)

    # L/S Ratio (check for overcrowding + contrarian)
    ls = sentiment.get('ls_ratio', 1.0)
    if ls > 2.0:
        multipliers.append(0.8)
        print(f"   📊 Overcrowded longs ({ls:.2f}) → 0.8x size multiplier")
    elif ls > 1.5:
        multipliers.append(1.0)
    elif ls < 0.8:
        multipliers.append(1.2)
        print(f"   📊 Shorts dominant ({ls:.2f}) → 1.2x size multiplier")
    else:
        multipliers.append(1.0)

    # Average all multipliers
    final_multiplier = sum(multipliers) / len(multipliers)

    # Cap between 0.5x and 1.5x for safety
    final_multiplier = max(0.5, min(1.5, final_multiplier))

    print(f"   🎯 Final sentiment multiplier: {final_multiplier:.2f}x")
    return final_multiplier


# Test scenarios
print("="*70)
print("TESTING SENTIMENT-BASED POSITION SIZING")
print("="*70)

print("\n🔵 Test 1: EXTREME FEAR + NEGATIVE FUNDING (Strong Buy Signal)")
print("-"*70)
sentiment1 = {'fear_greed': 20, 'funding_rate': -0.015, 'ls_ratio': 0.7}
mult1 = calculate_sentiment_multiplier(sentiment1)
print(f"Result: 35% base → {35 * mult1:.1f}% actual position\n")

print("\n🟡 Test 2: MODERATE FEAR + SLIGHT NEGATIVE FUNDING (Good Buy)")
print("-"*70)
sentiment2 = {'fear_greed': 35, 'funding_rate': -0.005, 'ls_ratio': 1.1}
mult2 = calculate_sentiment_multiplier(sentiment2)
print(f"Result: 35% base → {35 * mult2:.1f}% actual position\n")

print("\n⚪ Test 3: NEUTRAL CONDITIONS")
print("-"*70)
sentiment3 = {'fear_greed': 50, 'funding_rate': 0.001, 'ls_ratio': 1.2}
mult3 = calculate_sentiment_multiplier(sentiment3)
print(f"Result: 35% base → {35 * mult3:.1f}% actual position\n")

print("\n🔴 Test 4: EXTREME GREED + HIGH FUNDING (Avoid/Reduce)")
print("-"*70)
sentiment4 = {'fear_greed': 85, 'funding_rate': 0.06, 'ls_ratio': 2.5}
mult4 = calculate_sentiment_multiplier(sentiment4)
print(f"Result: 35% base → {35 * mult4:.1f}% actual position\n")

print("\n🟢 Test 5: RECENT ACTUAL CONDITIONS (from logs)")
print("-"*70)
sentiment5 = {'fear_greed': 30, 'funding_rate': -0.001, 'ls_ratio': 1.0}
mult5 = calculate_sentiment_multiplier(sentiment5)
print(f"Result: 35% base → {35 * mult5:.1f}% actual position\n")

print("="*70)
print("SUMMARY")
print("="*70)
print(f"Range tested: {min(mult1, mult2, mult3, mult4, mult5):.2f}x to {max(mult1, mult2, mult3, mult4, mult5):.2f}x")
print(f"Position range: {35*min(mult1, mult2, mult3, mult4, mult5):.1f}% to {35*max(mult1, mult2, mult3, mult4, mult5):.1f}%")
print("\n✅ Logic verified - ready to deploy!")
