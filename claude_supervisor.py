"""
Claude Strategic Supervisor
Autonomous AI decision layer for The Unexpected Trader
"""
import os
import json
import time
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

class ClaudeSupervisor:
    """
    Strategic supervisor that makes final trading decisions
    Reads briefing document before every decision
    Operates within defined safety boundaries
    """

    def __init__(self):
        """Initialize Claude supervisor"""
        self.client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.model = "claude-sonnet-4-20250514"  # Current Sonnet 4

        # Load briefing document
        with open('CLAUDE_BRIEFING_DOCUMENT.md', 'r') as f:
            self.briefing = f.read()

        # Track adjustments for daily limits
        self.adjustment_log = {}
        self.last_adjustment_time = 0

        # Decision log for transparency
        self.decision_history = []

    def build_context(self, trigger_type, current_price, position, sentiment, algo_proposal=None, market_data=None):
        """
        Build structured context for Claude
        This is the complete picture Claude sees
        """
        # Add market data if provided
        market_state = {
            "current_price": current_price,
            "fear_greed": sentiment.get('fear_greed', 50),
            "funding_rate": sentiment.get('funding_rate', 0),
            "ls_ratio": sentiment.get('ls_ratio', 1.0)
        }

        if market_data:
            market_state.update({
                "volume_24h_btc": market_data.get('volume_24h_btc', 0),
                "volume_24h_usd": market_data.get('volume_24h_usd', 0),
                "orderbook_imbalance": market_data.get('orderbook_imbalance', 0),
                "orderbook_pressure": market_data.get('orderbook_pressure', 'UNKNOWN')
            })

        context = {
            "trigger": trigger_type,
            "timestamp": datetime.now().isoformat(),
            "market_state": market_state,
            "position_state": {
                "has_position": position is not None,
                "size": position['size'] if position else 0,
                "avg_entry": position['average_price'] if position else 0,
                "leverage": position['leverage'] if position else 0,
                "pnl_pct": self._calculate_pnl_pct(current_price, position) if position else 0,
                "roi_pct": self._calculate_roi_pct(current_price, position) if position else 0
            },
            "fibonacci_levels": {
                "current_zone": self._determine_zone(current_price),
                "nearest_support": self._find_nearest_fib_below(current_price),
                "nearest_resistance": self._find_nearest_fib_above(current_price),
                "in_golden_pocket": self._in_golden_pocket(current_price)
            },
            "adjustments_today": self._count_todays_adjustments()
        }

        # Add algorithm's proposal if provided
        if algo_proposal:
            context["algo_proposal"] = algo_proposal

        return context

    def ask_for_decision(self, trigger_type, context, question):
        """
        Ask Claude for a strategic decision
        Returns: Parsed JSON decision
        """
        # Build prompt with briefing + context + question
        prompt = f"""
{self.briefing}

---

## CURRENT SITUATION

{json.dumps(context, indent=2)}

---

## DECISION REQUIRED

{question}

**Respond ONLY with valid JSON in this exact format:**

```json
{{
    "decision": "APPROVE|ADJUST|REJECT|HOLD|ADD|REDUCE|EMERGENCY_EXIT",
    "size_or_amount": 0.35,
    "reasoning": "Detailed explanation referencing specific data points",
    "confidence": 0.85,
    "data_summary": {{
        "fear_greed": 30,
        "funding": 0.0001,
        "ls_ratio": 1.0,
        "key_observation": "Your main insight"
    }}
}}
```

Do not include any text outside the JSON block.
"""

        try:
            # Call Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.3,  # Lower temp for more consistent decisions
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse response
            response_text = response.content[0].text

            # Extract JSON (remove markdown code blocks if present)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            decision = json.loads(response_text)

            # Log this interaction
            self._log_decision(trigger_type, context, decision, response.usage)

            return decision

        except Exception as e:
            print(f"❌ Claude API error: {e}")
            # Return safe default
            return {
                "decision": "HOLD",
                "reasoning": f"Error calling Claude: {e}",
                "confidence": 0
            }

    def approve_entry(self, current_price, zone, confluence, sentiment, proposed_size, market_data=None):
        """
        Ask Claude to approve/adjust entry decision
        """
        context = self.build_context(
            trigger_type="ENTRY_SIGNAL",
            current_price=current_price,
            position=None,
            sentiment=sentiment,
            market_data=market_data,
            algo_proposal={
                "action": "ENTER",
                "zone": zone,
                "confluence_factors": confluence,
                "proposed_size": proposed_size
            }
        )

        question = f"""
Algorithm detected entry opportunity at {zone}.
Confluence factors: {', '.join(confluence)}
Proposed size: {proposed_size*100:.1f}%

Should we enter? If yes, what size (25-75%)?

Consider:
- Is this a high-quality setup based on the data?
- Should we adjust size based on sentiment strength?
- Any reasons to reject or wait?
"""

        return self.ask_for_decision("ENTRY", context, question)

    def approve_exit(self, current_price, position, fib_level, gain_pct, roi_pct, sentiment, market_data=None):
        """
        Ask Claude how much profit to take at Fibonacci resistance
        """
        context = self.build_context(
            trigger_type="FIBONACCI_RESISTANCE",
            current_price=current_price,
            position=position,
            sentiment=sentiment,
            algo_proposal={
                "action": "TAKE_PROFIT",
                "level": fib_level,
                "gain_pct": gain_pct,
                "roi_pct": roi_pct,
                "proposed": "Take 50% profit"
            }
        )

        question = f"""
Price has reached Fibonacci resistance at ${fib_level:,.0f}.
Current gain: {gain_pct:+.2f}% price / {roi_pct:+.2f}% ROE

How much profit should we take? (25-100%)

Consider:
- Is this a strong rejection or breakout forming?
- What does sentiment suggest about continuation?
- Should we use trailing stop instead?
"""

        return self.ask_for_decision("EXIT", context, question)

    def periodic_review(self, current_price, position, sentiment, market_data=None):
        """
        20-minute position review
        Can suggest adds (if at Fib) or hold
        """
        context = self.build_context(
            trigger_type="SCHEDULED_REVIEW",
            current_price=current_price,
            position=position,
            sentiment=sentiment,
            market_data=market_data  # CRITICAL FIX: Pass market data to context
        )

        question = f"""
20-minute position review.

Can you:
- ADD up to 5% (if at Fibonacci level with strong setup)
- HOLD (most common - no action needed)

You CANNOT reduce (we're in loss) unless emergency.

Current situation:
- Price: ${current_price:,.0f}
- Position: {position['size']} BTC @ ${position['average_price']:,.0f}
- P&L: {context['position_state']['roi_pct']:+.2f}% ROE

Should we take any action?
"""

        return self.ask_for_decision("REVIEW", context, question)

    # Helper methods
    def _calculate_pnl_pct(self, current_price, position):
        if not position or not position.get('average_price'):
            return 0
        return ((current_price - position['average_price']) / position['average_price']) * 100

    def _calculate_roi_pct(self, current_price, position):
        if not position:
            return 0
        pnl_pct = self._calculate_pnl_pct(current_price, position)
        leverage = position.get('leverage', 1)
        return pnl_pct * leverage

    def _determine_zone(self, price):
        if 111463 <= price <= 112189:
            return "4H Golden Pocket"
        elif 108088 <= price <= 108975:
            return "Daily Golden Pocket"
        elif price > 112189:
            return "Above Golden Pocket"
        else:
            return "Below Golden Pocket"

    def _in_golden_pocket(self, price):
        return (111463 * 0.995 <= price <= 112189 * 1.01) or (108088 * 0.995 <= price <= 108975 * 1.01)

    def _find_nearest_fib_below(self, price):
        fibs = [126104, 117430, 112246, 112189, 111463, 109874, 108975, 108088, 105557, 98387]
        for fib in fibs:
            if fib < price:
                return fib
        return 98387

    def _find_nearest_fib_above(self, price):
        fibs = [98387, 105557, 108088, 108975, 109874, 111463, 112189, 112246, 117430, 126104]
        for fib in fibs:
            if fib > price:
                return fib
        return 126104

    def _count_todays_adjustments(self):
        today = datetime.now().date().isoformat()
        return len(self.adjustment_log.get(today, []))

    def _log_decision(self, trigger, context, decision, usage):
        """Log Claude interaction for transparency"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "trigger": trigger,
            "context": context,
            "claude_decision": decision,
            "api_usage": {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens
            }
        }

        self.decision_history.append(log_entry)

        # Save to file
        with open('logs/claude_decisions.json', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

        print(f"📝 Claude decision logged: {decision.get('decision')} - {decision.get('reasoning', '')[:100]}")


# Test the supervisor
if __name__ == "__main__":
    supervisor = ClaudeSupervisor()

    print("Testing Claude Supervisor...")
    print("="*60)

    # Test entry decision
    sentiment = {'fear_greed': 28, 'funding_rate': -0.005, 'ls_ratio': 0.95}

    decision = supervisor.approve_entry(
        current_price=111600,
        zone="4H Golden Pocket",
        confluence=["In golden pocket", "Fear sentiment", "Bounce detected"],
        sentiment=sentiment,
        proposed_size=0.37
    )

    print(f"\nClaude's Decision: {decision['decision']}")
    print(f"Size: {decision.get('size_or_amount', 'N/A')}")
    print(f"Reasoning: {decision.get('reasoning', 'N/A')}")
    print(f"Confidence: {decision.get('confidence', 'N/A')}")
