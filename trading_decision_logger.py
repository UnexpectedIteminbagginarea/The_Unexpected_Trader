"""
Trading Decision Logger
Records all bot decisions with clear reasoning for competition judging
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

class TradingDecisionLogger:
    """
    Logs every trading decision with reasoning in both human-readable
    and structured format for competition judging
    """

    def __init__(self, log_dir="logs"):
        """Initialize logger with directory for logs"""
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        # Different log files for different purposes
        self.decision_log_file = os.path.join(log_dir, "trading_decisions.json")
        self.readable_log_file = os.path.join(log_dir, "trading_decisions_readable.txt")
        self.summary_log_file = os.path.join(log_dir, "decision_summary.md")

        # Initialize logs
        self.decisions = self._load_existing_decisions()
        self.current_position = None

    def _load_existing_decisions(self) -> List[Dict]:
        """Load existing decisions if file exists"""
        if os.path.exists(self.decision_log_file):
            with open(self.decision_log_file, 'r') as f:
                return json.load(f)
        return []

    def _save_decisions(self):
        """Save decisions to JSON file"""
        with open(self.decision_log_file, 'w') as f:
            json.dump(self.decisions, f, indent=2, default=str)

    def _append_readable_log(self, message: str):
        """Append to human-readable log file"""
        with open(self.readable_log_file, 'a') as f:
            f.write(f"\n{message}\n")

    def _update_summary(self):
        """Update the markdown summary file for easy viewing"""
        with open(self.summary_log_file, 'w') as f:
            f.write("# 🤖 Trading Bot Decision Log\n\n")
            f.write(f"**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Current position summary
            if self.current_position:
                f.write("## 📊 Current Position\n\n")
                f.write(f"- **Status**: {self.current_position['status']}\n")
                f.write(f"- **Size**: {self.current_position['size']}% @ {self.current_position['leverage']}x\n")
                f.write(f"- **Entry**: ${self.current_position['entry_price']:,.2f}\n")
                f.write(f"- **Average**: ${self.current_position.get('average_price', self.current_position['entry_price']):,.2f}\n")
                f.write(f"- **P&L**: {self.current_position.get('unrealized_pnl', 0):+.2f}%\n\n")
            else:
                f.write("## 📊 Current Position\n\n")
                f.write("No open position\n\n")

            # Recent decisions
            f.write("## 📝 Recent Decisions (Last 10)\n\n")
            recent = self.decisions[-10:] if len(self.decisions) > 10 else self.decisions

            for decision in reversed(recent):  # Show newest first
                f.write(f"### {decision['timestamp']}\n")
                f.write(f"**Action**: {decision['action']}\n")
                f.write(f"**Reasoning**: {decision['reasoning']}\n")
                if 'details' in decision:
                    f.write(f"**Details**: {decision['details']}\n")
                f.write("\n---\n\n")

    def log_market_analysis(self, price: float, fib_levels: Dict, sentiment: Dict) -> Dict:
        """
        Log market analysis without taking action
        Returns the analysis for use by trading bot
        """
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'action': 'ANALYZE',
            'price': price,
            'fib_position': self._analyze_fib_position(price, fib_levels),
            'sentiment': sentiment,
            'reasoning': self._generate_analysis_reasoning(price, fib_levels, sentiment)
        }

        # Log but don't save to decisions (too frequent)
        readable = f"[{analysis['timestamp']}] MARKET ANALYSIS\n"
        readable += f"  Price: ${price:,.2f}\n"
        readable += f"  {analysis['reasoning']}\n"

        self._append_readable_log(readable)

        return analysis

    def log_entry_decision(self, price: float, size: float, leverage: float,
                          fib_zone: str, sentiment: Dict, confluence: List[str]) -> Dict:
        """
        Log entry decision with full reasoning
        """
        decision = {
            'timestamp': datetime.now().isoformat(),
            'action': 'ENTRY',
            'price': price,
            'size': size,
            'leverage': leverage,
            'fib_zone': fib_zone,
            'sentiment_scores': sentiment,
            'confluence_factors': confluence,
            'reasoning': self._generate_entry_reasoning(fib_zone, sentiment, confluence),
            'details': f"Entered {size}% position @ {leverage}x leverage at ${price:,.2f}"
        }

        # Update current position
        self.current_position = {
            'status': 'OPEN',
            'entry_price': price,
            'average_price': price,
            'size': size,
            'leverage': leverage,
            'entry_time': decision['timestamp']
        }

        # Save decision
        self.decisions.append(decision)
        self._save_decisions()

        # Human readable log
        readable = f"\n{'='*60}\n"
        readable += f"[{decision['timestamp']}] 🎯 ENTRY SIGNAL\n"
        readable += f"  Action: BUY {size}% @ {leverage}x leverage\n"
        readable += f"  Price: ${price:,.2f}\n"
        readable += f"  Zone: {fib_zone}\n"
        readable += f"  Reasoning: {decision['reasoning']}\n"
        readable += f"  Confluence: {', '.join(confluence)}\n"
        readable += f"{'='*60}\n"

        self._append_readable_log(readable)
        self._update_summary()

        return decision

    def log_scale_decision(self, price: float, add_size: float, new_leverage: float,
                          deviation: float, reason: str) -> Dict:
        """
        Log scale-in decision
        """
        old_avg = self.current_position['average_price']
        old_size = self.current_position['size']

        # Calculate new average
        new_size = old_size + add_size
        new_avg = (old_size * old_avg + add_size * price) / new_size

        decision = {
            'timestamp': datetime.now().isoformat(),
            'action': 'SCALE_IN',
            'price': price,
            'added_size': add_size,
            'new_total_size': new_size,
            'new_leverage': new_leverage,
            'deviation_from_entry': deviation,
            'old_average': old_avg,
            'new_average': new_avg,
            'reasoning': f"Price dropped {deviation:.1f}% from entry. {reason}",
            'details': f"Added {add_size}% at ${price:,.2f}, new avg: ${new_avg:,.2f}"
        }

        # Update position
        self.current_position['size'] = new_size
        self.current_position['average_price'] = new_avg
        self.current_position['leverage'] = new_leverage

        # Save
        self.decisions.append(decision)
        self._save_decisions()

        # Readable log
        readable = f"[{decision['timestamp']}] 📈 SCALE IN\n"
        readable += f"  Added: {add_size}% at ${price:,.2f}\n"
        readable += f"  Reasoning: {decision['reasoning']}\n"
        readable += f"  New position: {new_size}% @ ${new_avg:,.2f} avg\n"

        self._append_readable_log(readable)
        self._update_summary()

        return decision

    def log_exit_decision(self, price: float, exit_size: float, pnl: float,
                         reason: str, exit_type: str = "PARTIAL") -> Dict:
        """
        Log exit decision (partial or full)
        """
        decision = {
            'timestamp': datetime.now().isoformat(),
            'action': f'{exit_type}_EXIT',
            'price': price,
            'exit_size': exit_size,
            'pnl': pnl,
            'pnl_percent': (price - self.current_position['average_price']) / self.current_position['average_price'] * 100,
            'reasoning': reason,
            'details': f"Exited {exit_size}% at ${price:,.2f} for ${pnl:,.2f} profit"
        }

        # Update position
        if exit_type == "FULL":
            self.current_position = None
        else:
            self.current_position['size'] -= exit_size
            if 'total_pnl' not in self.current_position:
                self.current_position['total_pnl'] = 0
            self.current_position['total_pnl'] += pnl

        # Save
        self.decisions.append(decision)
        self._save_decisions()

        # Readable log
        emoji = "💰" if pnl > 0 else "📉"
        readable = f"[{decision['timestamp']}] {emoji} {exit_type} EXIT\n"
        readable += f"  Exited: {exit_size}% at ${price:,.2f}\n"
        readable += f"  P&L: ${pnl:,.2f} ({decision['pnl_percent']:+.2f}%)\n"
        readable += f"  Reasoning: {reason}\n"

        self._append_readable_log(readable)
        self._update_summary()

        return decision

    def log_hold_decision(self, price: float, reason: str) -> Dict:
        """
        Log decision to hold/wait
        """
        decision = {
            'timestamp': datetime.now().isoformat(),
            'action': 'HOLD',
            'price': price,
            'reasoning': reason
        }

        # Don't save holds to main decisions (too many), just readable log
        readable = f"[{decision['timestamp']}] ⏳ HOLD - {reason}"
        self._append_readable_log(readable)

        return decision

    def _analyze_fib_position(self, price: float, fib_levels: Dict) -> str:
        """Analyze where price is relative to Fib levels"""
        # Check 4H levels
        if 'h4' in fib_levels:
            h4 = fib_levels['h4']
            if 'gp_bottom' in h4 and 'gp_top' in h4:
                if h4['gp_bottom'] <= price <= h4['gp_top']:
                    return "In 4H Golden Pocket"
            if 'fib_50' in h4:
                if abs(price - h4['fib_50']) / price < 0.005:
                    return "At 4H 50% retracement"

        # Check daily levels
        if 'daily' in fib_levels:
            daily = fib_levels['daily']
            if 'gp_bottom' in daily and 'gp_top' in daily:
                if daily['gp_bottom'] <= price <= daily['gp_top']:
                    return "In Daily Golden Pocket"

        return "Between Fibonacci levels"

    def _generate_entry_reasoning(self, fib_zone: str, sentiment: Dict,
                                 confluence: List[str]) -> str:
        """Generate concise reasoning for entry"""
        reasons = []

        # Fib zone is primary
        reasons.append(f"Price at {fib_zone}")

        # Add sentiment if notable
        if sentiment.get('fear_greed', 50) < 30:
            reasons.append("Fear sentiment supports longs")
        if sentiment.get('funding_rate', 0) < 0:
            reasons.append("Negative funding (oversold)")
        if sentiment.get('ls_ratio', 1) > 2:
            reasons.append("High L/S ratio (bullish)")

        # Add confluence count
        if len(confluence) >= 3:
            reasons.append(f"Strong confluence ({len(confluence)} factors)")

        return ". ".join(reasons)

    def _generate_analysis_reasoning(self, price: float, fib_levels: Dict,
                                    sentiment: Dict) -> str:
        """Generate reasoning for market analysis"""
        position = self._analyze_fib_position(price, fib_levels)

        if "Golden Pocket" in position:
            return f"{position} - watching for entry signal"
        elif "50%" in position:
            return f"{position} - waiting for bounce confirmation"
        else:
            return f"{position} - no trade setup"

    def get_performance_summary(self) -> Dict:
        """Get summary statistics for dashboard/reporting"""
        if not self.decisions:
            return {'total_trades': 0}

        entries = [d for d in self.decisions if d['action'] == 'ENTRY']
        exits = [d for d in self.decisions if 'EXIT' in d['action']]
        scale_ins = [d for d in self.decisions if d['action'] == 'SCALE_IN']

        total_pnl = sum(d.get('pnl', 0) for d in exits)

        return {
            'total_trades': len(entries),
            'total_exits': len(exits),
            'total_scale_ins': len(scale_ins),
            'total_pnl': total_pnl,
            'win_rate': len([d for d in exits if d['pnl'] > 0]) / len(exits) * 100 if exits else 0,
            'current_position': self.current_position is not None
        }

    def export_for_competition(self, output_file: str = "competition_log.md"):
        """
        Export a clean log formatted for competition judges
        """
        output_path = os.path.join(self.log_dir, output_file)

        with open(output_path, 'w') as f:
            f.write("# 🏆 Aster Vibe Trading Competition - Decision Log\n\n")
            f.write(f"**Bot Name**: Fibonacci Golden Pocket Trader\n")
            f.write(f"**Strategy**: Scale-in at Fibonacci retracements with sentiment confirmation\n")
            f.write(f"**Period**: {self.decisions[0]['timestamp'][:10] if self.decisions else 'N/A'} to {datetime.now().strftime('%Y-%m-%d')}\n\n")

            # Performance summary
            perf = self.get_performance_summary()
            f.write("## 📊 Performance Summary\n\n")
            f.write(f"- Total Trades: {perf['total_trades']}\n")
            f.write(f"- Scale-ins: {perf['total_scale_ins']}\n")
            f.write(f"- Win Rate: {perf['win_rate']:.1f}%\n")
            f.write(f"- Total P&L: ${perf['total_pnl']:,.2f}\n\n")

            # Decision log
            f.write("## 📝 Trading Decisions\n\n")

            for decision in self.decisions:
                if decision['action'] in ['ENTRY', 'SCALE_IN', 'PARTIAL_EXIT', 'FULL_EXIT']:
                    f.write(f"**{decision['timestamp']}**\n")
                    f.write(f"- Action: {decision['action']}\n")
                    f.write(f"- Price: ${decision['price']:,.2f}\n")
                    f.write(f"- Reasoning: {decision['reasoning']}\n")

                    if 'pnl' in decision:
                        f.write(f"- P&L: ${decision['pnl']:,.2f}\n")

                    f.write("\n")

        print(f"Competition log exported to: {output_path}")
        return output_path


# Example usage
if __name__ == "__main__":
    logger = TradingDecisionLogger()

    # Example market analysis
    logger.log_market_analysis(
        price=112400,
        fib_levels={
            'h4': {'gp_top': 112189, 'gp_bottom': 111463, 'fib_50': 114864},
            'daily': {'gp_top': 108975, 'gp_bottom': 108088, 'fib_50': 112246}
        },
        sentiment={'fear_greed': 30, 'funding_rate': 0.001, 'ls_ratio': 1.5}
    )

    # Example entry
    logger.log_entry_decision(
        price=112189,
        size=35,
        leverage=3,
        fib_zone="4H Golden Pocket",
        sentiment={'fear_greed': 30, 'funding_rate': -0.001},
        confluence=["Golden Pocket", "Fear sentiment", "Negative funding", "Price bounce"]
    )

    # Example scale-in
    logger.log_scale_decision(
        price=110941,
        add_size=20,
        new_leverage=3,
        deviation=-1.3,
        reason="Price at support, sentiment remains positive"
    )

    # Export for judges
    logger.export_for_competition()