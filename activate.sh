#!/bin/bash
# Activation script for The Unexpected Trader environment

echo "🚀 Activating The Unexpected Trader environment..."
source venv/bin/activate
export PYTHONPATH="$(pwd)"
echo "✅ Virtual environment activated"
echo "✅ PYTHONPATH set to: $PYTHONPATH"
echo ""
echo "📝 Quick commands:"
echo "  python live_trading_bot.py --shadow  - Run in shadow mode (paper trading)"
echo "  python live_trading_bot.py           - Run live trading"
echo "  cd dashboard && npm run dev          - Start dashboard locally"
echo ""
echo "💡 Reminder: Use --shadow flag for paper trading"