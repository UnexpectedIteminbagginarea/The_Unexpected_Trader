# The Unexpected Trader - Competition Entry

Project Vision

My goal creating this bot is to demonstrate what can be done without writing a single line of code by hand. I acted as project manager and creative director, while Claude executed the vision. The trade strategy and algorythm was designed and tested through natural language collaboration with AI.


## 📈 Trading Strategy

I wanted a "less is more" approach. Rather than battling it out with the market through scalping, I modeled the strategy after my own manual trading methodology - targeting high-conviction, mid-to-long term plays with patience and discipline. 

I decided to focus only on BTC as it is the most liquid and most traded asset on the market. Also staying highly focused on one currency I believe allows easier tracking, monitoring and specialisation of the trade strategy rather than a scattergun approach. 

### Core Strategy: Fibonacci Golden Pocket

The bot continuously monitors Bitcoin price action, specifically targeting the 61.8%-65% Fibonacci retracement zone (the "golden pocket") - a historically significant support level where institutional buying often occurs.

**Key Technical Levels:**
- **4H Timeframe**: Swing high $126,104 (Oct 6) → Swing low $108,755 (Oct 17)
- **Daily Timeframe**: Swing high $126,104 (Oct 6) → Swing low $98,387 (June 22)
- **Golden Pocket Zones**: $111,463-$112,189 (4H), $108,088-$108,975 (Daily)

### Multi-Factor Confluence System

The bot doesn't just enter blindly at Fibonacci levels. It validates each opportunity using CoinGlass market sentiment data:

**CoinGlass Indicators:**
1. **Fear & Greed Index** - Detects extreme fear (<40) as contrarian buy signal
2. **Long/Short Ratio** - Monitors Binance trader positioning; >1.2 indicates bullish sentiment
3. **Funding Rate** - Negative rates (<0) signal oversold conditions and potential reversal
4. **Bounce Confirmation** - Validates price has actually reacted to the Fibonacci level (0.1% bounce from recent low)

**Entry Requirements:**
- Price within golden pocket zone (with 0.5% buffer for flexibility)
- Minimum 2 confluence factors confirmed
- Recent bounce detected (proving level is holding)

### Risk Management: Scale-In Instead of Stop-Loss

Unlike traditional stop-loss approaches, the bot employs a **conviction-based scaling strategy**:

**Progressive Accumulation:**
- Initial: 35% capital @ 3x leverage
- Scale-in #1: -1% → Add 20% @ 3x
- Scale-in #2: -2% → Add 25% @ 4x (increasing conviction)
- Scale-in #3: -4% → Add 25% @ 5x
- Scale-in #4: -6% → Add 30% @ 5x

**Philosophy**: If the trade thesis remains valid, price dips are opportunities to improve average entry, not reasons to panic exit.

**Profit Taking:**
- Systematic exits at +5%, +10%, +15% from average entry
- Partial exits (25% each) to lock gains while maintaining upside exposure

**True Invalidation:**
- Only exits at -40% leveraged loss (structural break of thesis)
- Not arbitrary stop levels that get hunted

## 🤖 Autonomous Operation

AI 
Claude monitors the data at 20 minute intervals and is called to make decisions if any of the core algorythms are triggered. Claude has a directive sheet for context that informs his decisions. So he opperates autonomously but within a trading framework of my design. When trigger by the algorythm in scale trades within an agreed range based on his reading of the market conditions. During the trade reviews every 20mins Claude can choose to make smaller possitions changes of 5% up to 3 times a day.

**24/7 Cloud Deployment:**
- Runs on DigitalOcean VPS with PM2 process management
- Automatic position recovery on restart
- Complete audit trail of every decision with reasoning

**Data Sources:**
- Aster API: Real-time price, order book, funding rates
- CoinGlass API: Market sentiment and positioning data
- Binance: Historical price data for backtesting validation

**Monitoring:**
- Live dashboard showing real-time position and P&L
- Historical price chart with trade executions plotted
- Complete decision log with bot reasoning for each trade

## 📊 Live Results

**Current Position:**
- Entered: Oct 29, 5:48 PM @ $111,091
- Scale-in #1: Oct 29, 7:39 PM @ $109,935 (-1%)
- Scale-in #2: Oct 30, 5:27 AM @ $108,767 (-2%)
- Average Entry: $109,979.94
- Current P&L: +0.59% ROE (as of Nov 1, 8:20 AM)

**Performance Highlights:**
- Successfully navigated -10.5% drawdown (Oct 30)
- Recovered to profitable within 24 hours
- Scale-in strategy lowered average from $111,091 to $109,979
- Position currently profitable after surviving significant volatility

## 🏗️ Technical Architecture

**Built with Claude Code:**
- Python trading bot with Aster API integration
- Position recovery system for resilience
- Comprehensive logging for transparency
- Flask API server for data access
- Next.js dashboard with real-time visualization

**Dashboard Features:**
- Animated starfield background (inspired by space trading theme)
- Glass-morphism design for professional presentation
- Real-time BTC price chart with trade executions plotted
- Auto-refreshing data every 30 seconds
- Complete decision history with bot reasoning

**Repository:** https://github.com/UnexpectedIteminbagginarea/Unexpected_vibe_trader
**Dashboard:** [Live URL when deployed]

## 💡 What Makes This Unique

1. **No-Code Development**: Entire bot built through conversation with Claude Code
2. **Sentiment-Aware**: Integrates CoinGlass market psychology data
3. **Conviction Scaling**: Adds to winners instead of cutting losers prematurely
4. **Complete Transparency**: Every decision logged with full reasoning
5. **Production-Ready**: 24/7 VPS deployment with auto-recovery

---

**Built by**: @UnexpectedIteminbagginarea
**Powered by**: Claude Code, Aster API, CoinGlass Data
**Competition**: Aster Vibe Trading Arena
**Submission Date**: November 2025
