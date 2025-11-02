"""
Test Claude Integration - No Real Trades
Verifies Claude makes sensible decisions in various scenarios
"""
from claude_supervisor import ClaudeSupervisor
from safety_validator import SafetyValidator

def test_entry_decisions():
    """Test Claude's entry approval logic"""
    supervisor = ClaudeSupervisor()
    safety = SafetyValidator()

    print("="*70)
    print("TEST 1: HIGH-QUALITY ENTRY (Extreme Fear + Negative Funding)")
    print("="*70)

    sentiment = {
        'fear_greed': 22,
        'funding_rate': -0.012,
        'ls_ratio': 0.75
    }

    decision = supervisor.approve_entry(
        current_price=111500,
        zone="4H Golden Pocket",
        confluence=["In golden pocket", "Extreme fear", "Negative funding", "Bounce"],
        sentiment=sentiment,
        proposed_size=0.37
    )

    print(f"\n📊 Claude's Decision: {decision['decision']}")
    print(f"   Size: {decision.get('size_or_amount', 0)*100:.1f}%")
    print(f"   Confidence: {decision.get('confidence', 0)}")
    print(f"   Reasoning: {decision.get('reasoning', '')[:200]}")

    # Safety check
    safety_result = safety.validate_entry(decision, None, {'balance': 442})
    print(f"\n🛡️ Safety: {safety_result[0]} - {safety_result[1]}")

    print("\n" + "="*70)
    print("TEST 2: MARGINAL ENTRY (Neutral Sentiment)")
    print("="*70)

    sentiment2 = {
        'fear_greed': 52,
        'funding_rate': 0.002,
        'ls_ratio': 1.15
    }

    decision2 = supervisor.approve_entry(
        current_price=111700,
        zone="4H Golden Pocket",
        confluence=["In golden pocket", "Bounce"],
        sentiment=sentiment2,
        proposed_size=0.35
    )

    print(f"\n📊 Claude's Decision: {decision2['decision']}")
    print(f"   Size: {decision2.get('size_or_amount', 0)*100:.1f}%")
    print(f"   Reasoning: {decision2.get('reasoning', '')[:200]}")

    print("\n" + "="*70)
    print("TEST 3: EXIT AT FIBONACCI ($112,246)")
    print("="*70)

    position = {
        'size': 0.01,
        'average_price': 109979,
        'leverage': 4
    }

    sentiment3 = {
        'fear_greed': 35,
        'funding_rate': 0.0005,
        'ls_ratio': 1.2
    }

    decision3 = supervisor.approve_exit(
        current_price=112246,
        position=position,
        fib_level=112246,
        gain_pct=2.06,
        roi_pct=8.24,
        sentiment=sentiment3
    )

    print(f"\n📊 Claude's Decision: {decision3['decision']}")
    print(f"   Exit %: {decision3.get('size_or_amount', 0)*100:.0f}%")
    print(f"   Reasoning: {decision3.get('reasoning', '')[:200]}")

    print("\n" + "="*70)
    print("TEST 4: 20-MINUTE REVIEW (Normal Conditions)")
    print("="*70)

    decision4 = supervisor.periodic_review(
        current_price=110500,
        position=position,
        sentiment=sentiment3
    )

    print(f"\n📊 Claude's Decision: {decision4['decision']}")
    if decision4['decision'] == 'ADD':
        print(f"   Add: {decision4.get('size_or_amount', 0)*100:.1f}%")
    print(f"   Reasoning: {decision4.get('reasoning', '')[:200]}")

    print("\n" + "="*70)
    print("TEST 5: 20-MINUTE REVIEW (At Fibonacci Support)")
    print("="*70)

    sentiment5 = {
        'fear_greed': 26,
        'funding_rate': -0.006,
        'ls_ratio': 0.88
    }

    decision5 = supervisor.periodic_review(
        current_price=109874,  # Exactly at 78.6% Fib support
        position=position,
        sentiment=sentiment5
    )

    print(f"\n📊 Claude's Decision: {decision5['decision']}")
    if decision5['decision'] == 'ADD':
        print(f"   Add: {decision5.get('size_or_amount', 0)*100:.1f}%")
        print(f"   Reasoning: {decision5.get('reasoning', '')[:250]}")

        # Test safety limits
        safety_result = safety.validate_adjustment(decision5, position, 109874)
        print(f"\n🛡️ Safety: {safety_result[0]} - {safety_result[1]}")

    print("\n" + "="*70)
    print("TESTS COMPLETE")
    print("="*70)
    print("\n✅ If all decisions look sensible, Claude is ready!")
    print("📝 Check that:")
    print("   - Claude references specific data (F&G, funding, etc)")
    print("   - Sizes are reasonable (25-75% for entries)")
    print("   - Reasoning is clear and data-driven")
    print("   - Review mostly returns HOLD (not ADD every time)")

if __name__ == "__main__":
    print("\n🧪 TESTING CLAUDE SUPERVISOR INTEGRATION")
    print("This tests AI decisions WITHOUT executing real trades\n")

    try:
        test_entry_decisions()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
