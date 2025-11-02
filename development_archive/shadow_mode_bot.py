"""
Shadow Mode Bot - Observes VPS position, logs what Claude would do
NO REAL TRADING - Just analysis and logging
"""
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv
from claude_supervisor import ClaudeSupervisor
from safety_validator import SafetyValidator

load_dotenv()

class ShadowModeBot:
    """
    Watches the real VPS position
    Asks Claude what he would do
    Logs decisions without executing
    """

    def __init__(self):
        """Initialize shadow bot"""
        self.claude = ClaudeSupervisor()
        self.safety = SafetyValidator()

        # VPS API endpoint
        self.vps_api = "https://api.theunexpectedtrader.com"

        # Tracking
        self.last_review_time = datetime.now()
        self.review_count = 0

        print("="*70)
        print("🔮 SHADOW MODE BOT - OBSERVATION ONLY")
        print("="*70)
        print("Watching: VPS position via API")
        print("Mode: NO TRADING - Just logging Claude's decisions")
        print("Purpose: Verify Claude before going live")
        print("="*70 + "\n")

    def get_vps_position(self):
        """Fetch current position from VPS"""
        import requests
        try:
            response = requests.get(f"{self.vps_api}/api/logs/position", timeout=5)
            if response.ok:
                data = response.json()
                if data and data.get('position'):
                    return data['position']
            return None
        except Exception as e:
            print(f"⚠️ Error fetching VPS position: {e}")
            return None

    def get_current_price(self):
        """Get current BTC price"""
        import requests
        try:
            response = requests.get(f"{self.vps_api}/api/price/current", timeout=5)
            if response.ok:
                data = response.json()
                return data['price']
            return 0
        except:
            return 0

    def get_sentiment(self):
        """Get current sentiment from latest decision"""
        import requests
        try:
            response = requests.get(f"{self.vps_api}/api/logs/decisions?limit=1", timeout=5)
            if response.ok:
                data = response.json()
                if data and len(data) > 0 and data[0].get('sentiment_scores'):
                    return data[0]['sentiment_scores']
            return {'fear_greed': 30, 'funding_rate': 0.0001, 'ls_ratio': 1.0}
        except:
            return {'fear_greed': 30, 'funding_rate': 0.0001, 'ls_ratio': 1.0}

    def run_shadow_cycle(self):
        """
        One observation cycle:
        1. Fetch VPS position
        2. Get current price
        3. Ask Claude what he would do
        4. Log it
        """
        try:
            # Get current state
            position = self.get_vps_position()
            price = self.get_current_price()
            sentiment = self.get_sentiment()

            if price == 0:
                print("⚠️ Could not fetch price")
                return

            print(f"\n{'='*70}")
            print(f"🔮 SHADOW CYCLE #{self.review_count + 1}")
            print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
            print(f"Price: ${price:,.2f}")

            if position:
                avg = position.get('average_price', 0)
                size = position.get('size', 0)
                pnl_pct = ((price - avg) / avg * 100) if avg > 0 else 0
                roi_pct = pnl_pct * position.get('leverage', 1)

                print(f"Position: {size} BTC @ ${avg:,.2f}")
                print(f"P&L: {pnl_pct:+.2f}% price / {roi_pct:+.2f}% ROE")
            else:
                print(f"Position: FLAT")

            print(f"Sentiment: F&G={sentiment.get('fear_greed')}, "
                  f"Funding={sentiment.get('funding_rate'):.4f}, "
                  f"L/S={sentiment.get('ls_ratio'):.2f}")

            # Check if review is due (every 20 min)
            time_since_review = (datetime.now() - self.last_review_time).total_seconds()

            if time_since_review >= 1200 and position:  # 20 minutes
                print(f"\n⏰ 20-MINUTE REVIEW TIME")
                print(f"   Asking Claude what he would do...")

                try:
                    decision = self.claude.periodic_review(
                        current_price=price,
                        position=position,
                        sentiment=sentiment
                    )

                    print(f"\n🤖 CLAUDE'S DECISION: {decision['decision']}")
                    if decision['decision'] == 'ADD':
                        print(f"   Would ADD: {decision.get('size_or_amount', 0)*100:.1f}%")
                    print(f"   Reasoning: {decision.get('reasoning', '')[:300]}")

                    # Check safety (but don't execute)
                    if decision['decision'] == 'ADD':
                        safety_result = self.safety.validate_adjustment(
                            decision, position, price
                        )
                        print(f"\n🛡️ Safety Check: {safety_result[0]} - {safety_result[1]}")

                    self.last_review_time = datetime.now()
                    self.review_count += 1

                except Exception as e:
                    print(f"   ❌ Error: {e}")

            else:
                mins_until_review = int((1200 - time_since_review) / 60)
                if position:
                    print(f"⏳ Next review in {mins_until_review} minutes")

            print(f"{'='*70}")

            return True

        except Exception as e:
            print(f"❌ Shadow cycle error: {e}")
            return False

    def run(self, duration_minutes=60):
        """
        Run shadow mode for specified duration
        Default: 1 hour
        """
        print(f"\n🔮 Starting shadow mode observation")
        print(f"Duration: {duration_minutes} minutes")
        print(f"Checking every 30 seconds")
        print(f"Claude reviews: Every 20 minutes\n")

        start_time = datetime.now()
        cycle = 0

        while (datetime.now() - start_time).total_seconds() < duration_minutes * 60:
            cycle += 1
            print(f"\n--- Cycle {cycle} ---")

            self.run_shadow_cycle()

            # Sleep 30 seconds
            time.sleep(30)

        print(f"\n{'='*70}")
        print(f"🔮 SHADOW MODE COMPLETE")
        print(f"{'='*70}")
        print(f"Cycles run: {cycle}")
        print(f"Reviews conducted: {self.review_count}")
        print(f"Duration: {duration_minutes} minutes")
        print(f"\n📊 Check logs/claude_decisions.jsonl for all decisions")
        print(f"✅ If Claude's decisions look good, deploy to VPS!")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🔮 SHADOW MODE BOT")
    print("Observes VPS position, logs what Claude would do")
    print("NO REAL TRADING")
    print("="*70)

    # Check if user wants custom duration
    import sys
    duration = 60  # Default 1 hour

    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except:
            print("Usage: python3 shadow_mode_bot.py [duration_minutes]")
            print("Example: python3 shadow_mode_bot.py 30  # Run for 30 minutes")
            duration = 60

    bot = ShadowModeBot()

    try:
        bot.run(duration_minutes=duration)
    except KeyboardInterrupt:
        print("\n\n⛔ Shadow mode stopped by user")
        print(f"Reviews conducted: {bot.review_count}")
