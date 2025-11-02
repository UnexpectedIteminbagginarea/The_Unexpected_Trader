# 🎯 The Unexpected Trader

**An AI-supervised Fibonacci trading bot built entirely through natural language collaboration with Claude Code.**

[![Dashboard](https://img.shields.io/badge/Dashboard-Live-green)](https://theunexpectedtrader.com)
[![Competition](https://img.shields.io/badge/Aster-Vibe%20Arena-orange)](https://aster.trade)

## 📖 Overview

The Unexpected Trader demonstrates a new paradigm in algorithmic trading development: sophisticated trading systems built through natural language conversation with AI, without writing a single line of code by hand.

The bot combines algorithmic precision with AI strategic oversight, targeting Bitcoin's Fibonacci "golden pocket" retracement zones while using real-time market sentiment to inform position sizing and risk management.

## 🎯 Core Strategy

**Fibonacci Golden Pocket Trading**
- Targets 61.8%-65% Fibonacci retracement zones on major swings
- Multi-timeframe analysis (Daily + 4H timeframes)
- Conviction-based position scaling at -1%, -2%, -4%, -6% deviations
- Systematic profit-taking at +5%, +10%, +15% gains
- Structural invalidation exits (not arbitrary stops)

**AI Supervision (Claude)**
- Reviews position every 20 minutes
- Full authority on entries (25-75% sizing) and exits
- Can add up to 5% per review (max 3 adjustments/day)
- Analyzes Fear & Greed Index, Funding Rates, L/S Ratios, Volume, Order book
- 8 hard safety rules enforced

## 🏗️ Architecture

### Core Components

```
├── live_trading_bot.py           # Main algorithmic engine (1,200 lines)
├── claude_supervisor.py           # AI decision layer (350 lines)
├── safety_validator.py            # Hard limit enforcement (200 lines)
├── aster_trading_client.py        # Aster API integration
├── trading_decision_logger.py     # Complete audit trail
├── position_recovery.py           # Auto-recovery on restart
└── dashboard/                     # Next.js live dashboard
```

### Data Sources
- **Aster API**: Real-time price, volume, order book, funding rates
- **CoinGlass API**: Fear & Greed Index, Long/Short ratios, Liquidations
- **Binance**: Historical data for backtesting validation

## 🚀 Quick Start

### Prerequisites
```bash
python 3.9+
Node.js 18+ (for dashboard)
```

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/UnexpectedIteminbagginarea/Unexpected_vibe_trader
cd Unexpected_vibe_trader
```

2. **Install Python dependencies**
```bash
pip install anthropic pandas requests python-dotenv flask flask-cors
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. **Run shadow mode (paper trading)**
```bash
python live_trading_bot.py --shadow
```

5. **Run dashboard locally**
```bash
cd dashboard
npm install
npm run dev
# Visit http://localhost:3000
```

## 📊 Live Dashboard

Visit [theunexpectedtrader.com](https://theunexpectedtrader.com) to see:
- Real-time BTC price and position tracking
- Trade history with execution markers on price chart
- Claude AI strategic reviews with full reasoning
- Live market sentiment indicators
- Mobile-responsive design

## 📈 Performance

**Current Live Trade** (as of Nov 2, 2025):
- Entry: $111,091 (Oct 29)
- Scale-ins: $109,935, $108,767
- Average entry: $109,979
- Status: Profitable
- Survived -10.5% drawdown, recovered within 24 hours

**Backtest Results** (June-Oct 2025):
- Conservative strategy: +6.55%
- With sentiment enhancement: +6.68%
- Aggressive leverage scaling: +17.57%
- Win rate: 100% (1/1 trades)

See `BACKTEST_LOG.md` for comprehensive testing documentation.

## 🛡️ Safety Features

**Hard Limits (Always Enforced)**:
1. 6% liquid reserve (max 94% deployed)
2. 5x max leverage per position
3. 5x max total notional exposure
4. 30% liquidation buffer minimum
5. 25-75% position sizes only
6. Cannot reduce while in loss (except on invalidation)
7. Maximum 3 adjustments per day
8. 5% max add per 20-minute review

**Risk Management**:
- Invalidation-based exits (not arbitrary stops)
- Progressive position scaling with increasing leverage (3x→5x)
- Systematic partial profit-taking
- Automatic position recovery on restart

## 📚 Documentation

- **[PROJECT_OUTLINE.md](PROJECT_OUTLINE.md)** - Competition submission and project overview
- **[DEVELOPMENT_JOURNEY.md](DEVELOPMENT_JOURNEY.md)** - Development story and methodology
- **[BACKTEST_LOG.md](BACKTEST_LOG.md)** - Comprehensive testing documentation (11 iterations)
- **[BOT_DIRECTIVES.md](BOT_DIRECTIVES.md)** - Bot operational rules
- **[CLAUDE_BRIEFING_DOCUMENT.md](CLAUDE_BRIEFING_DOCUMENT.md)** - Claude's 30KB instruction manual
- **[SAFETY_RULES_FINAL.md](SAFETY_RULES_FINAL.md)** - Safety boundaries

## 🎓 Development Methodology

This project was built entirely through conversation with Claude Code, demonstrating:
- Natural language specification and iteration
- No-code development workflow
- 11 major backtest iterations with rigorous testing
- Comprehensive documentation of decision-making process
- Transparent development journey

See `DEVELOPMENT_JOURNEY.md` for the complete story.

## 📁 Development Archive

The `development_archive/` folder contains test scripts, debugging tools, and backtest iterations that show the thorough testing process. See `development_archive/README.md` for details.

## 🤖 Claude AI Integration

Claude acts as a strategic supervisor with:
- Full context on market conditions, position status, and strategy rules
- Authority to approve entries, exits, and limited position adjustments
- Structured decision-making with confidence levels
- Complete reasoning logged for every decision
- Boundary enforcement through safety validator

## 🏆 Competition

Built for the **Aster Vibe Trading Arena** competition.
- **Goal**: Demonstrate AI-supervised algorithmic trading
- **Approach**: Fibonacci technical analysis + AI sentiment interpretation
- **Innovation**: True autonomous operation with strategic AI oversight

## 📞 Contact

- **GitHub**: [@UnexpectedIteminbagginarea](https://github.com/UnexpectedIteminbagginarea)
- **Dashboard**: [theunexpectedtrader.com](https://theunexpectedtrader.com)

## 📜 License

This project is submitted as part of the Aster Vibe Trading Arena competition.

---

**Built with Claude Code** | **Powered by Aster API & CoinGlass Data** | **November 2025**
