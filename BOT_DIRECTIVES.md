# 🤖 Fibonacci Golden Pocket Trading Bot - Core Directives

## 📋 Bot Identity
**Name**: Fibonacci Golden Pocket Trader
**Strategy**: Scale-in at Fibonacci retracements with sentiment confirmation
**Market**: BTC/USDT Perpetual Futures (Aster Exchange)
**Collateral**: SOL

---

## 🎯 PRIMARY DIRECTIVE: ENTRY LOGIC

### Golden Pocket Detection
```
ENTRY CONDITIONS:
1. Price must be within Golden Pocket zone OR 0.5% buffer below
   - 4H Golden Pocket: $111,463 - $112,189 (primary)
   - Daily Golden Pocket: $108,088 - $108,975 (secondary)
   - Buffer: Accept entries down to 99.5% of pocket bottom

2. Minimum Confluence Required: 2 factors
   - Factor 1: In/Near Golden Pocket (mandatory)
   - Factor 2+: Choose from:
     * Fear sentiment (Fear & Greed < 40)
     * Negative funding rate (< 0)
     * Bullish L/S ratio (> 1.2)
     * Price bounce detected (0.1% bounce from recent low)

3. Bounce Detection:
   - Check last 20 x 5-minute candles
   - If recent low within 2% of golden pocket top
   - AND current price > recent low by 0.1%
   - THEN bounce confirmed

ENTRY EXECUTION:
- Size: 35% of capital
- Leverage: 3x
- Order Type: MARKET
- Log decision with full reasoning
```

---

## 📈 SCALE-IN DIRECTIVES

### Progressive Accumulation Strategy
```
SCALE LEVEL 1 (-1% from initial entry):
- Trigger: Price drops to 99% of first entry price
- Action: Add 20% more capital
- Leverage: 3x (maintain)
- Recalculate average entry price
- Increment scale_in_count to 1

SCALE LEVEL 2 (-2% from initial entry):
- Trigger: Price drops to 98% of first entry price
- Action: Add 25% more capital
- Leverage: 4x (increase conviction)
- Recalculate average entry price
- Increment scale_in_count to 2

SCALE LEVEL 3 (-4% from initial entry):
- Trigger: Price drops to 96% of first entry price
- Action: Add 25% more capital
- Leverage: 5x (maximum conviction)
- Recalculate average entry price
- Increment scale_in_count to 3

SCALE LEVEL 4 (-6% from initial entry):
- Trigger: Price drops to 94% of first entry price
- Action: Add 30% more capital
- Leverage: 5x (maintain max)
- Recalculate average entry price
- Increment scale_in_count to 4

SCALE-IN RULES:
- Always scale from ORIGINAL entry price, not average
- Track scale_in_count to prevent duplicate scales
- Update position.average_price after each scale
- Update position.leverage to new level
- Log each scale with deviation and reasoning
```

---

## 💰 PROFIT-TAKING DIRECTIVES

### Systematic Exit Strategy
```
TARGET 1 (+5% from average entry):
- Action: Close 25% of total position
- Order: MARKET sell with reduceOnly=true
- Reasoning: "Hit profit target +5%"
- Update position size: multiply by 0.75

TARGET 2 (+10% from average entry):
- Action: Close 25% of remaining position
- Reasoning: "Hit profit target +10%"
- Update position size: multiply by 0.75

TARGET 3 (+15% from average entry):
- Action: Close 25% of remaining position
- Reasoning: "Hit profit target +15%"
- Update position size: multiply by 0.75

PROFIT-TAKING RULES:
- Calculate gain from position.average_price (not original entry)
- Use reduceOnly to prevent flipping position
- Log P&L in both USD and percentage
- Update position tracking after each exit
- Continue monitoring for higher targets
```

---

## 🛡️ RISK MANAGEMENT DIRECTIVES

### Invalidation & Stop Loss
```
INVALIDATION LEVEL (-10% from average entry):
- Trigger: Price drops below 90% of average entry
- Action: FULL EXIT (close 100% of position)
- Order: MARKET sell with reduceOnly=true
- Reasoning: "Invalidation - structural break"
- Clear all position tracking
- Log as FULL_EXIT with loss amount

POSITION LIMITS:
- Maximum total capital deployed: 135% (if all scales hit)
- Maximum leverage: 5x
- Maximum position: Never exceed these limits
- Emergency stop if limits approached
```

---

## 🔄 MONITORING DIRECTIVES

### Continuous Market Analysis
```
EVERY CYCLE (5 seconds):
1. Fetch current BTC price from Aster
2. Fetch CoinGlass sentiment data:
   - Fear & Greed Index
   - Long/Short Ratio
   - Funding Rate
3. Get recent 5m candles for bounce detection
4. Log market analysis (written to file, not console)

DECISION TREE:
IF no_position:
    → Check entry conditions
    → If met: enter_position()
    → Else: log "Waiting for entry" (every 5 min)

ELSE IF have_position:
    → Check exit conditions first (profits or invalidation)
    → If exit triggered: execute and log
    → Else: Check scale-in conditions
    → If scale triggered: execute and log
    → Else: Monitor and update P&L (every 60 sec)

CONSOLE OUTPUT:
- Position updates: Every 60 seconds
- Status summary: Every 100 cycles (~8 minutes)
- Trade actions: Immediately when executed
```

---

## 💾 LOGGING DIRECTIVES

### Comprehensive Decision Recording
```
LOG EVERY DECISION TO:
1. logs/trading_decisions.json (structured data)
2. logs/trading_decisions_readable.txt (human format)
3. logs/decision_summary.md (current status)
4. logs/position_state.json (for recovery)

ENTRY LOG FORMAT:
{
  "timestamp": ISO 8601,
  "action": "ENTRY",
  "price": entry_price,
  "size": position_size_percent,
  "leverage": leverage_used,
  "fib_zone": "4H Golden Pocket",
  "sentiment_scores": {...},
  "confluence_factors": [...],
  "reasoning": "Why we entered",
  "details": "Human readable summary"
}

SCALE-IN LOG FORMAT:
{
  "timestamp": ISO 8601,
  "action": "SCALE_IN",
  "price": scale_price,
  "added_size": additional_percent,
  "new_total_size": total_position_percent,
  "new_leverage": updated_leverage,
  "deviation_from_entry": percentage,
  "old_average": previous_avg,
  "new_average": new_avg,
  "reasoning": "Hit scale level X at Y%",
  "details": "Added X% at $Y, new avg: $Z"
}

EXIT LOG FORMAT:
{
  "timestamp": ISO 8601,
  "action": "PARTIAL_EXIT" | "FULL_EXIT",
  "price": exit_price,
  "exit_size": size_closed_percent,
  "pnl": profit_loss_usd,
  "pnl_percent": profit_loss_percentage,
  "reasoning": "Hit profit target" | "Invalidation",
  "details": "Exited X% at $Y for $Z profit"
}
```

---

## 🔄 RECOVERY DIRECTIVES

### Position State Persistence
```
ON EVERY TRADE (Entry/Scale/Exit):
1. Save position state to logs/position_state.json:
   {
     "timestamp": current_time,
     "position": {
       "entry_price": original_entry,
       "average_price": current_average,
       "size": total_btc_amount,
       "leverage": current_leverage,
       "entry_time": first_entry_time
     },
     "last_entry_price": for_scale_calculations,
     "scale_in_count": number_of_scales_done
   }

ON BOT STARTUP:
1. Query Aster API for existing positions
2. IF position exists:
   a. Load saved state from logs/position_state.json
   b. Restore position tracking variables
   c. Log recovery event
   d. Continue managing from current state
3. ELSE:
   a. Clean up old state files
   b. Start fresh in entry-seeking mode

RECOVERY RULES:
- ALWAYS check exchange position before saved state
- Exchange position is source of truth for size/entry
- Saved state provides scale_in_count and average_price
- Log recovery clearly for audit trail
```

---

## 📊 DATA SOURCES

### Market Data (Aster API)
```
Price Ticker: /fapi/v1/ticker/24hr?symbol=BTCUSDT
- Provides: lastPrice, volume, 24h change

Order Book: /fapi/v1/depth?symbol=BTCUSDT&limit=20
- Provides: bid/ask depth

Funding Rate: /fapi/v1/fundingRate?symbol=BTCUSDT&limit=1
- Provides: current funding rate

Klines: /fapi/v1/klines?symbol=BTCUSDT&interval=5m&limit=20
- Provides: Recent 5m candles for bounce detection

Position Data: /fapi/v2/positionRisk
- Provides: Current position size, entry, P&L, leverage
```

### Sentiment Data (CoinGlass API)
```
Fear & Greed: /api/index/fear-greed-history?time_type=1
- Range: 0-100 (0=extreme fear, 100=extreme greed)
- Use: < 40 = bullish for longs

Long/Short Ratio: /api/futures/global-long-short-account-ratio/history
- Params: exchange=Binance, symbol=BTCUSDT, interval=4h
- Use: > 1.2 = bullish sentiment

Funding Rate: /api/futures/funding-rate/history
- Params: exchange=Binance, symbol=BTCUSDT, interval=8h
- Use: < 0 = oversold (good for longs)
```

---

## ⚙️ OPERATIONAL PARAMETERS

### Fixed Fibonacci Levels
```
4H TIMEFRAME (Primary):
- Swing High: $126,104 (Oct 6, 2025)
- Swing Low: $108,755 (Oct 17, 2025)
- Golden Pocket Top (61.8%): $112,189
- Golden Pocket Bottom (65.0%): $111,463
- 50% Retracement: $117,430
- 78.6% Level: $109,874

DAILY TIMEFRAME (Secondary):
- Swing High: $126,104 (Oct 6, 2025)
- Swing Low: $98,387 (June 22, 2025)
- Golden Pocket Top (61.8%): $108,975
- Golden Pocket Bottom (65.0%): $108,088
- 50% Retracement: $112,246
- 78.6% Level: $105,557

NOTE: Levels are FIXED from backtesting
Do NOT recalculate on every cycle
These are the proven swing points
```

### Timing Parameters
```
CYCLE_INTERVAL:
- With position: 5 seconds
- No position but eager: 5 seconds
- No position, waiting: 30 seconds

CONSOLE_OUTPUT:
- Position P&L: Every 60 seconds
- Status summary: Every 100 cycles
- Waiting message: Every 300 seconds (5 min)

API_TIMEOUTS:
- Price fetch: 5 seconds
- Sentiment fetch: 5 seconds
- Order placement: 10 seconds

ERROR_HANDLING:
- On cycle error: Log and continue
- On API error: Wait 60 seconds, retry
- On fatal error: Log and gracefully shutdown
```

---

## 🎯 SUCCESS METRICS

### Bot Performance Tracking
```
TRACK:
- Total trades executed
- Entry count
- Scale-in count
- Exit count
- Total P&L (USD)
- Win rate (exits with profit / total exits)
- Current position status
- Total cycles completed
- Runtime duration

REPORT EVERY 100 CYCLES:
"📊 Status - Cycles: {count}, Trades: {total}, P&L: ${pnl}"

FINAL SUMMARY ON SHUTDOWN:
- Total trades
- Total P&L
- Win rate
- Export competition log
```

---

## 🏆 COMPETITION REQUIREMENTS

### For Aster Vibe Trading Arena
```
MUST LOG:
1. Every decision with clear reasoning
2. Confluence factors for each entry
3. Sentiment data used in decisions
4. P&L for each exit
5. Scale-in logic and deviations
6. Risk management actions

EXPORT FORMAT:
- competition_log.md for judges
- Clear strategy description
- Full decision history
- Performance metrics
- Reasoning for every trade

DEADLINE: November 3, 2025
PRIZE: $50,000
```

---

## 🔐 SAFETY DIRECTIVES

### Never Break These Rules
```
NEVER:
1. Trade without logging the decision
2. Exceed maximum position size (135%)
3. Use leverage > 5x
4. Skip validation of API responses
5. Trade with missing price data
6. Ignore invalidation level
7. Scale in more than 4 times
8. Enter without minimum confluence (2 factors)
9. Place orders without proper error handling
10. Modify Fibonacci levels during runtime

ALWAYS:
1. Verify order execution status
2. Update position tracking after trades
3. Save state after every trade
4. Check for existing positions on startup
5. Log errors with full context
6. Validate price data before trading
7. Use reduceOnly for exits
8. Calculate from correct reference prices
9. Track scale_in_count accurately
10. Maintain audit trail for competition
```

---

*These directives form the complete decision-making framework for the Fibonacci Golden Pocket Trading Bot. Every action taken by the bot can be traced back to these rules.*