# Fix: Add Available Balance to Claude's Context

**Problem**: Claude keeps suggesting ADD when account is fully allocated ($0 available)

**Simple Solution**: Add available balance to Claude's periodic review context

---

## Implementation

### Step 1: Modify live_trading_bot.py (line ~1076)

**Before Claude review, fetch account info:**

```python
# Check if 20-minute review is due
time_since_review = (datetime.now() - self.last_review_time).total_seconds()
if time_since_review >= self.REVIEW_INTERVAL:
    print(f"\n⏰ 20-MINUTE REVIEW DUE (last: {int(time_since_review/60)} min ago)")
    try:
        # Get market data for Claude
        market_data = self.get_market_data()

        # ADD THIS: Get account info for Claude
        account_info = self.trading_client.get_account_info()

        review_decision = self.claude.periodic_review(
            current_price=current_price,
            position=self.position,
            sentiment=sentiment,
            market_data=market_data,
            account_info=account_info  # NEW: Pass account info
        )
```

### Step 2: Modify claude_supervisor.py periodic_review (line 232)

**Add account_info parameter:**

```python
def periodic_review(self, current_price, position, sentiment, market_data=None, account_info=None):
    """
    20-minute position review
    Can suggest adds (if at Fib) or hold
    """
    context = self.build_context(
        trigger_type="SCHEDULED_REVIEW",
        current_price=current_price,
        position=position,
        sentiment=sentiment,
        market_data=market_data,
        account_info=account_info  # NEW: Pass through
    )
```

### Step 3: Modify build_context (line 37)

**Add account_info parameter and include in context:**

```python
def build_context(self, trigger_type, current_price, position, sentiment, algo_proposal=None, market_data=None, account_info=None):
    """
    Build structured context for Claude
    This is the complete picture Claude sees
    """
    # [existing market_state code...]

    context = {
        "trigger": trigger_type,
        "timestamp": datetime.now().isoformat(),
        "market_state": market_state,
        "position_state": {
            # [existing fields...]
        },
        "fibonacci_levels": {
            # [existing fields...]
        },
        "adjustments_today": self._count_todays_adjustments()
    }

    # NEW: Add account info if provided
    if account_info:
        context["account_state"] = {
            "sol_balance": account_info.get('sol', 0),
            "usd_value": account_info.get('usd_value', 0),
            "available_to_trade": account_info.get('available_balance', 0)  # This is the key field
        }

    # [rest of existing code...]
```

### Step 4: Update get_account_info to return available balance

**Modify aster_trading_client.py line 72-89:**

```python
def get_account_info(self) -> Dict:
    """Get account balance and info"""
    balances = self._make_request('GET', '/fapi/v2/balance')

    # Also get full account for available balance
    account = self._make_request('GET', '/fapi/v1/account')

    if balances:
        sol_balance = 0
        for balance in balances:
            if balance['asset'] == 'SOL':
                sol_balance = float(balance['balance'])

        sol_price = 170  # Approximate
        usd_value = sol_balance * sol_price

        # NEW: Add available balance from account endpoint
        available_balance = 0
        if account:
            available_balance = float(account.get('availableBalance', 0))

        return {
            'sol': sol_balance,
            'usd_value': usd_value,
            'available_balance': available_balance  # NEW: Claude will see this
        }
    return None
```

---

## What Claude Will See

In his context JSON:
```json
{
  "account_state": {
    "sol_balance": 2.6,
    "usd_value": 442.0,
    "available_to_trade": 0.0
  }
}
```

When available_to_trade = 0, Claude will know he can't ADD and should say HOLD.

---

## Benefits

1. **Simple**: 4 small changes across 3 files
2. **Robust**: Uses actual Aster data (source of truth)
3. **Clear**: Claude explicitly sees "available_to_trade": 0
4. **Auto-updating**: Fetched fresh every 20-minute review
5. **No breaking changes**: Only adding data, not modifying existing logic

---

## Testing

Test locally by printing the context before calling Claude:
```python
print(f"Claude context: {json.dumps(context, indent=2)}")
```

Verify account_state appears with correct available_balance.

---

**Risk**: LOW - Only adding information to context, not changing any logic
**Lines changed**: ~20 lines total across 3 files
**Impact**: Claude makes better decisions with complete information
