# Implementation Plan: Add Available Balance to Claude's Context

**Goal**: Claude should know when account is fully allocated and say HOLD instead of ADD

**Changes needed**: 3 files, ~15 lines total

---

## Change 1: aster_trading_client.py (Line 72-89)

**Current code**:
```python
def get_account_info(self) -> Dict:
    """Get account balance and info"""
    balances = self._make_request('GET', '/fapi/v2/balance')

    if balances:
        sol_balance = 0
        for balance in balances:
            if balance['asset'] == 'SOL':
                sol_balance = float(balance['balance'])

        sol_price = 170
        usd_value = sol_balance * sol_price

        return {'sol': sol_balance, 'usd_value': usd_value}
    return None
```

**New code**:
```python
def get_account_info(self) -> Dict:
    """Get account balance and info including available margin"""
    balances = self._make_request('GET', '/fapi/v2/balance')

    # Also get full account for available balance
    account = self._make_request('GET', '/fapi/v1/account')

    if balances:
        sol_balance = 0
        for balance in balances:
            if balance['asset'] == 'SOL':
                sol_balance = float(balance['balance'])

        sol_price = 170
        usd_value = sol_balance * sol_price

        # Add available balance from account endpoint
        available_balance = 0
        if account:
            available_balance = float(account.get('availableBalance', 0))

        return {
            'sol': sol_balance,
            'usd_value': usd_value,
            'available_balance': available_balance  # NEW
        }
    return None
```

**Lines changed**: 5 lines added (total method now ~25 lines)

---

## Change 2: claude_supervisor.py (Line 37 and 232)

### 2a. Update build_context signature (line 37)

**Current**:
```python
def build_context(self, trigger_type, current_price, position, sentiment, algo_proposal=None, market_data=None):
```

**New**:
```python
def build_context(self, trigger_type, current_price, position, sentiment, algo_proposal=None, market_data=None, account_info=None):
```

### 2b. Add account_state to context (after line 76)

**Add after "adjustments_today" field**:
```python
context = {
    "trigger": trigger_type,
    "timestamp": datetime.now().isoformat(),
    "market_state": market_state,
    "position_state": {...},
    "fibonacci_levels": {...},
    "adjustments_today": self._count_todays_adjustments()
}

# NEW: Add account state if provided
if account_info:
    context["account_state"] = {
        "sol_balance": account_info.get('sol', 0),
        "usd_value": account_info.get('usd_value', 0),
        "available_to_trade": account_info.get('available_balance', 0)
    }
```

### 2c. Update periodic_review signature (line 232)

**Current**:
```python
def periodic_review(self, current_price, position, sentiment, market_data=None):
```

**New**:
```python
def periodic_review(self, current_price, position, sentiment, market_data=None, account_info=None):
```

### 2d. Pass account_info to build_context (line 237)

**Current**:
```python
context = self.build_context(
    trigger_type="SCHEDULED_REVIEW",
    current_price=current_price,
    position=position,
    sentiment=sentiment,
    market_data=market_data
)
```

**New**:
```python
context = self.build_context(
    trigger_type="SCHEDULED_REVIEW",
    current_price=current_price,
    position=position,
    sentiment=sentiment,
    market_data=market_data,
    account_info=account_info  # NEW
)
```

**Lines changed**: 3 signature updates + 7 lines for account_state = 10 lines

---

## Change 3: live_trading_bot.py (Line ~1076)

**Current code** (before Claude review):
```python
# Check if 20-minute review is due
time_since_review = (datetime.now() - self.last_review_time).total_seconds()
if time_since_review >= self.REVIEW_INTERVAL:
    print(f"\n⏰ 20-MINUTE REVIEW DUE")
    try:
        # Get market data for Claude
        market_data = self.get_market_data()

        review_decision = self.claude.periodic_review(
            current_price=current_price,
            position=self.position,
            sentiment=sentiment,
            market_data=market_data
        )
```

**New code**:
```python
# Check if 20-minute review is due
time_since_review = (datetime.now() - self.last_review_time).total_seconds()
if time_since_review >= self.REVIEW_INTERVAL:
    print(f"\n⏰ 20-MINUTE REVIEW DUE")
    try:
        # Get market data for Claude
        market_data = self.get_market_data()

        # Get account info for Claude (NEW)
        account_info = self.trading_client.get_account_info()

        review_decision = self.claude.periodic_review(
            current_price=current_price,
            position=self.position,
            sentiment=sentiment,
            market_data=market_data,
            account_info=account_info  # NEW
        )
```

**Lines changed**: 2 lines added

---

## Total Changes Summary

| File | Lines Added | Risk | Purpose |
|------|-------------|------|---------|
| aster_trading_client.py | 5 | LOW | Fetch availableBalance from Aster |
| claude_supervisor.py | 10 | LOW | Accept and include account_info in context |
| live_trading_bot.py | 2 | LOW | Fetch and pass account_info to Claude |
| **TOTAL** | **17** | **LOW** | Give Claude capital allocation visibility |

---

## What Claude Will See

**In his context JSON**:
```json
{
  "account_state": {
    "sol_balance": 2.6,
    "usd_value": 442.0,
    "available_to_trade": 0.0
  }
}
```

**Claude's decision making**:
- When available_to_trade > 0: Can suggest ADD
- When available_to_trade = 0: Should say HOLD (fully allocated)

---

## Testing Plan

**Local test**:
```python
# Test get_account_info returns new field
client = AsterTradingClient()
account = client.get_account_info()
print(account)  # Should show: {'sol': 2.6, 'usd_value': 442, 'available_balance': 0.0}
```

**Integration test**:
- Mock account_info with available_balance = 0
- Call claude.periodic_review()
- Print context to verify account_state appears
- Check Claude's response

**VPS deployment**:
- Backup before deployment
- Deploy all 3 files
- Restart bot
- Check next Claude review logs for account_state in context
- Verify Claude says HOLD when available_to_trade = 0

---

## Expected Behavior

**Before change**:
- Claude suggests ADD (doesn't know about $0 available)
- Safety blocks (3/day limit) OR Aster rejects (insufficient margin)
- Looks bad: Claude keeps suggesting impossible actions

**After change**:
- Claude sees available_to_trade = 0
- Claude says HOLD ("Account fully allocated, no capacity to add")
- More intelligent, context-aware decisions
- Better user experience

---

**Ready to implement**: All changes analyzed, low risk, clear benefit
