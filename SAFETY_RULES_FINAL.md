# 🛡️ Safety Rules - Hard Limits (Cannot Be Overridden)

**Purpose**: Protect capital from catastrophic loss
**Authority**: These override ALL decisions (Algo + Claude)
**Created**: November 1, 2025

---

## 🔐 CORE SAFETY RULES

### 1️⃣ Liquidity Reserve
```python
MIN_LIQUID_COLLATERAL = 0.06  # 6% of capital must stay liquid
MAX_CAPITAL_USAGE = 0.94      # Can deploy max 94%
```

**Rule**: Always keep 6% in reserve
- Current capital: $442 (2.6 SOL)
- Liquid reserve: $26.52 minimum
- Max deployable: $415.48

**Why**:
- Covers funding fees
- Buffer for unexpected costs
- Withdrawal capability
- Emergency reserves

**Check Before Every Trade**:
```python
if total_capital_used + new_trade_size > 0.94:
    REDUCE new_trade_size to fit
    OR BLOCK if cannot fit
```

---

### 2️⃣ Maximum Leverage Cap
```python
MAX_LEVERAGE = 5.0  # 5x on any single position
MAX_POSITION_LEVERAGE = 5.0  # Same limit
```

**Rule**: Never use more than 5x leverage on any position

**Current**: Using 3x-5x scaling (we're compliant)

**Why**:
- Prevents excessive liquidation risk
- Aster may have platform limits
- 5x is already aggressive
- Keeps liquidation distance safe

**Enforcement**:
```python
if proposed_leverage > 5.0:
    BLOCK trade
    LOG "Attempted >5x leverage - blocked by safety"
```

---

### 3️⃣ Total Notional Exposure Cap
```python
MAX_TOTAL_NOTIONAL = 5.0  # 500% of capital
```

**Rule**: Sum of all (position_size × leverage) cannot exceed 5x capital

**Current Status**:
- Position: 80% capital @ avg 3.67x leverage = 2.94x notional ✅
- Compliant

**Why**:
- Prevents over-leveraging across multiple positions
- Caps total risk exposure
- Aligned with 5x max leverage

**Check**:
```python
current_notional = sum(pos.size × pos.leverage for all positions)
new_notional = new_trade.size × new_trade.leverage

if current_notional + new_notional > 5.0:
    REDUCE new_trade to fit
    OR BLOCK if cannot fit
```

---

### 4️⃣ Liquidation Distance Minimum
```python
MIN_LIQUIDATION_BUFFER = 0.30  # Must be 30% away from liquidation
```

**Rule**: Never let liquidation price get within 30% of current price

**Current**:
- Entry: $109,979
- Liquidation: $67,027
- Buffer: 39% ✅ SAFE

**Why**:
- Extreme moves can happen fast
- Funding fees accumulate
- Slippage in liquidations
- Safety margin for black swans

**Check Before Every Trade**:
```python
estimated_liq_price = calculate_liquidation(total_position, total_leverage)
buffer = (current_price - estimated_liq_price) / current_price

if buffer < 0.30:
    BLOCK new trades
    WARN "Too close to liquidation"
```

---

### 5️⃣ Position Size Limits (Per Trade)
```python
MIN_POSITION_SIZE = 0.25  # 25% minimum
MAX_POSITION_SIZE = 0.75  # 75% maximum
```

**Rule**: Each individual trade must be 25-75% of capital

**Why**:
- Below 20%: Too small to matter (fees eat profit)
- Above 50%: Too concentrated (one bad trade = devastation)
- Forces diversification over time

**Enforcement**:
```python
if trade_size < 0.20:
    INCREASE to 0.20 OR SKIP trade

if trade_size > 0.50:
    REDUCE to 0.50
    LOG "Capped at 50% maximum"
```

---

### 6️⃣ No Reduce While Losing Rule
```python
ALLOW_REDUCE_IN_LOSS = False
```

**Rule**: Cannot partially reduce position if P&L is negative

**Exception**: Emergency full exit (100% close) always allowed

**Current**:
- Starting capital: $442
- Kill switch: $221
- Current equity: ~$442 (essentially flat)

**Why**:
- Ultimate protection against ruin
- Prevents total wipeout
- Forces fresh start if severely wrong

**Check Every Cycle**:
```python
peak_equity = track_highest_account_value()
current_equity = get_account_balance()
drawdown = (current_equity - peak_equity) / peak_equity

if drawdown <= -0.50:
    EMERGENCY_CLOSE_ALL()
    PAUSE_BOT()
    ALERT "Max drawdown hit - all positions closed"
```

---

### 7️⃣ Daily Loss Limit (Optional)
```python
MAX_DAILY_LOSS = -0.15  # -15% of capital per day
```

**Rule**: If we lose 15% of capital in one day, stop trading for 24h

**Current**: Not implemented

**Pros**: Prevents spiral of bad decisions
**Cons**: Might exit during normal volatility with leverage

**Your call**: Add this or skip?

---

### 7️⃣ Adjustment Frequency Limits
```python
MAX_ADJUSTMENTS_PER_DAY = 3
MAX_ADD_PER_REVIEW = 0.05  # 5% maximum
```

**Rule**: Claude can make max 3 adjustments per day, max 5% add each time

**Why**:
- Prevents overtrading
- Forces patience
- Reduces fees
- Keeps strategy clean

**Tracks**:
```python
adjustment_log = {
    "2025-11-01": [
        {"time": "10:00", "action": "ADD 5%"},
        {"time": "12:30", "action": "REDUCE 10%"},
        {"time": "15:00", "action": "ADD 3%"}
    ]
}

if len(today's_adjustments) >= 3:
    BLOCK next adjustment
    ALLOW only: HOLD decisions
```

---

### 9️⃣ No Reduce While Losing Rule
```python
ALLOW_REDUCE_IN_LOSS = False
```

**Rule**: Cannot partially reduce position if P&L is negative

**Your Logic**:
- If thesis invalid → Full exit (emergency)
- If thesis valid → Hold or add (conviction)
- No middle ground (don't lock in partial losses)

**Enforcement**:
```python
if claude_decision == "REDUCE" and position_roi < 0:
    BLOCK
    LOG "Cannot reduce while in loss. Either HOLD or EMERGENCY_EXIT"
    RETURN "Decision blocked by no-reduce-in-loss rule"
```

**Exception**: Emergency full exit (100% close) is always allowed

---

### 🔟 Time-Based Limits
```python
MIN_POSITION_HOLD_TIME = 900  # 15 minutes minimum
```

**Rule**: Must hold position at least 15 minutes before exiting

**Why**:
- Prevents knee-jerk reactions
- Avoids fee churning
- Forces patience

**Exception**: Emergency exits bypass this

---

## 📊 COMPLETE SAFETY RULESET

| Rule | Limit | Purpose |
|------|-------|---------|
| **Liquid Reserve** | 6% minimum | Emergency funds |
| **Max Leverage** | 5x | Liquidation protection |
| **Max Notional** | 5x capital | Total exposure cap |
| **Liquidation Buffer** | 30% minimum | Safety margin |
| **Position Size** | 20-50% | Avoid dust/over-concentration |
| **Max Drawdown** | -50% account | Kill switch |
| **Daily Loss** | -15%/day (optional) | Spiral protection |
| **Adjustments** | 3 per day | Anti-overtrading |
| **No Reduce in Loss** | Hard rule | Don't lock losses |
| **Min Hold Time** | 15 minutes | Prevent churn |

---

## 🎯 SAFETY CHECK FUNCTION (Pseudocode)

```python
def validate_trade(trade, position, account):
    """
    Returns: (approved: bool, reason: str, adjusted_trade: dict)
    """

    # 1. Check liquid reserve
    total_used = account.deployed + trade.size
    if total_used > 0.94:
        return (False, "Would violate 6% liquid reserve", None)

    # 2. Check leverage
    if trade.leverage > 5.0:
        return (False, "Exceeds 5x max leverage", None)

    # 3. Check notional
    new_notional = calculate_notional(position, trade)
    if new_notional > 5.0:
        adjusted = reduce_to_fit_notional(trade, 5.0)
        return (True, "Reduced to fit 5x notional cap", adjusted)

    # 4. Check liquidation distance
    new_liq = estimate_liquidation(position, trade)
    buffer = (current_price - new_liq) / current_price
    if buffer < 0.30:
        return (False, "Liquidation too close (<30%)", None)

    # 5. Check position size
    if trade.size < 0.20:
        return (False, "Position too small (<20%)", None)
    if trade.size > 0.50:
        adjusted = trade.copy()
        adjusted.size = 0.50
        return (True, "Capped at 50% max", adjusted)

    # 6. Check drawdown
    if account.drawdown < -0.50:
        return (False, "Max drawdown reached - bot paused", None)

    # 7. Check reduce-in-loss
    if trade.type == "REDUCE" and position.roi < 0:
        return (False, "Cannot reduce while in loss", None)

    # 8. Check adjustment frequency
    if trade.type in ["ADD", "REDUCE"]:
        if len(today_adjustments) >= 3:
            return (False, "Max 3 adjustments/day reached", None)
        if time_since_last_adjustment < 1800:
            return (False, "Must wait 30 min between adjustments", None)
        if trade.type == "ADD" and trade.size > 0.05:
            adjusted = trade.copy()
            adjusted.size = 0.05
            return (True, "Capped ADD at 5% max", adjusted)

    # All checks passed
    return (True, "Trade approved by safety layer", trade)
```

---

## 🎯 **"Safety" Means:**

**Pre-flight checks** that run BEFORE Claude even sees the proposal:
- Is there enough liquid reserve?
- Would this exceed exposure limits?

**Post-Claude validation** that runs AFTER Claude decides:
- Did Claude exceed size limits? → Reduce to fit
- Did Claude try to reduce in loss? → Block
- Too many adjustments today? → Block

**Safety is NOT**:
- Market analysis
- Strategy decisions
- "Should we trade" judgments

**Safety IS**:
- Mathematical boundaries
- Account protection
- Platform limits
- Anti-ruin measures

---

## ✅ **FINAL RULESET (What to Implement):**

**Hard Caps:**
1. 6% liquid reserve (max 94% deployed)
2. 5x max leverage
3. 5x max notional exposure
4. 30% min liquidation buffer
5. 20-50% position size range
6. -50% account drawdown kill switch

**Operational Limits:**
7. 5% max add per 20-min review
8. 3 adjustments max per day
9. 30 min cooldown between adjustments
10. No reduces while in loss
11. 15 min minimum hold time

**Total: 11 safety rules**

**Simple to implement**: Each is just an if/else check!

**Ready to proceed?**