"""
Aster Trading Client - Real Order Execution
Uses SOL as collateral for BTC perpetual futures
"""
import os
import time
import hmac
import hashlib
import requests
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class AsterTradingClient:
    """Handle real order execution on Aster exchange"""

    def __init__(self):
        """Initialize trading client"""
        self.api_key = os.getenv('ASTER_API_KEY')
        self.api_secret = os.getenv('ASTER_API_SECRET')
        self.base_url = "https://fapi.asterdex.com"

        # Headers for authenticated requests
        self.headers = {
            'X-MBX-APIKEY': self.api_key
        }

        # Track current position
        self.position = None
        self.orders = []

    def _generate_signature(self, query_string: str) -> str:
        """Generate HMAC SHA256 signature"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _make_request(self, method: str, endpoint: str, params: Dict = None) -> Dict:
        """Make authenticated request to Aster"""
        # Add timestamp
        if params is None:
            params = {}
        params['timestamp'] = int(time.time() * 1000)

        # Create query string
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])

        # Generate signature
        signature = self._generate_signature(query_string)
        query_string += f"&signature={signature}"

        # Make request
        url = f"{self.base_url}{endpoint}?{query_string}"

        if method == 'GET':
            response = requests.get(url, headers=self.headers)
        elif method == 'POST':
            response = requests.post(url, headers=self.headers)
        elif method == 'DELETE':
            response = requests.delete(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API Error {response.status_code}: {response.text}")
            return None

    def get_account_info(self) -> Dict:
        """Get account balance and info"""
        balances = self._make_request('GET', '/fapi/v2/balance')

        if balances:
            sol_balance = 0
            for balance in balances:
                if balance['asset'] == 'SOL':
                    sol_balance = float(balance['balance'])
                    print(f"💰 SOL Balance: {sol_balance:.4f} SOL")

                    # Calculate USD value (approx)
                    sol_price = 170  # Approximate SOL price
                    usd_value = sol_balance * sol_price
                    print(f"   ≈ ${usd_value:,.2f} USD")

            return {'sol': sol_balance, 'usd_value': usd_value}
        return None

    def get_current_position(self) -> Optional[Dict]:
        """Get current BTC position if any"""
        positions = self._make_request('GET', '/fapi/v2/positionRisk')

        if positions:
            for pos in positions:
                if pos['symbol'] == 'BTCUSDT' and float(pos.get('positionAmt', 0)) != 0:
                    position = {
                        'symbol': pos['symbol'],
                        'side': 'LONG' if float(pos['positionAmt']) > 0 else 'SHORT',
                        'amount': abs(float(pos['positionAmt'])),
                        'entry_price': float(pos.get('entryPrice', 0)),
                        'mark_price': float(pos.get('markPrice', 0)),
                        'pnl': float(pos.get('unrealizedProfit', 0)),
                        'leverage': float(pos.get('leverage', 1))
                    }
                    print(f"📊 Current Position: {position['amount']} BTC @ ${position['entry_price']:,.2f}")
                    print(f"   P&L: ${position['pnl']:,.2f}")
                    return position

        print("📊 No open positions")
        return None

    def place_market_order(self, side: str, quantity: float, reduce_only: bool = False) -> Dict:
        """
        Place a market order
        side: 'BUY' or 'SELL'
        quantity: BTC amount
        """
        params = {
            'symbol': 'BTCUSDT',
            'side': side,
            'type': 'MARKET',
            'quantity': quantity,
        }

        if reduce_only:
            params['reduceOnly'] = 'true'

        print(f"\n🔄 Placing {side} order for {quantity} BTC...")

        result = self._make_request('POST', '/fapi/v1/order', params)

        if result:
            print(f"✅ Order placed successfully!")
            print(f"   Order ID: {result['orderId']}")
            print(f"   Status: {result['status']}")
            print(f"   Executed Qty: {result.get('executedQty', 0)}")
            print(f"   Avg Price: ${float(result.get('avgPrice', 0)):,.2f}")

            self.orders.append(result)
            return result

        return None

    def set_leverage(self, leverage: int) -> bool:
        """Set leverage for BTCUSDT"""
        params = {
            'symbol': 'BTCUSDT',
            'leverage': leverage
        }

        result = self._make_request('POST', '/fapi/v1/leverage', params)

        if result:
            print(f"⚙️ Leverage set to {leverage}x")
            return True
        return False

    def calculate_position_size(self, percentage: float, leverage: int, current_price: float) -> float:
        """
        Calculate BTC position size based on percentage of account
        percentage: 0.35 for 35%
        leverage: 3 for 3x
        """
        account = self.get_account_info()

        if account:
            # Calculate position value in USD
            account_value = account['usd_value']
            position_value = account_value * percentage * leverage

            # Convert to BTC
            btc_amount = position_value / current_price

            # Round to appropriate decimals (Aster usually accepts 3 decimals)
            btc_amount = round(btc_amount, 3)

            print(f"\n📐 Position Calculation:")
            print(f"   Account: ${account_value:,.2f}")
            print(f"   Using: {percentage*100:.0f}% = ${account_value * percentage:,.2f}")
            print(f"   With {leverage}x leverage = ${position_value:,.2f}")
            print(f"   BTC amount: {btc_amount} BTC")

            return btc_amount

        return 0

    def enter_long_position(self, percentage: float, leverage: int, current_price: float) -> bool:
        """
        Enter a long position
        Returns True if successful
        """
        # Set leverage first
        self.set_leverage(leverage)

        # Calculate position size
        btc_amount = self.calculate_position_size(percentage, leverage, current_price)

        if btc_amount > 0:
            # Place the order
            order = self.place_market_order('BUY', btc_amount)

            if order:
                self.position = {
                    'entry_time': datetime.now(),
                    'entry_price': float(order.get('avgPrice', current_price)),
                    'amount': btc_amount,
                    'leverage': leverage,
                    'side': 'LONG'
                }
                return True

        return False

    def scale_in_position(self, add_percentage: float, new_leverage: int, current_price: float) -> bool:
        """Add to existing position"""
        # Update leverage if needed
        if new_leverage != self.position.get('leverage'):
            self.set_leverage(new_leverage)

        # Calculate additional size
        btc_amount = self.calculate_position_size(add_percentage, new_leverage, current_price)

        if btc_amount > 0:
            order = self.place_market_order('BUY', btc_amount)

            if order:
                # Update position tracking
                old_amount = self.position['amount']
                old_price = self.position['entry_price']
                new_amount = old_amount + btc_amount
                new_price = (old_amount * old_price + btc_amount * current_price) / new_amount

                self.position['amount'] = new_amount
                self.position['entry_price'] = new_price
                self.position['leverage'] = new_leverage

                print(f"📊 Position updated:")
                print(f"   Total size: {new_amount} BTC")
                print(f"   Avg price: ${new_price:,.2f}")

                return True

        return False

    def close_position(self, percentage: float = 1.0) -> bool:
        """
        Close position (partial or full)
        percentage: 1.0 for full, 0.5 for 50%, etc
        """
        current_pos = self.get_current_position()

        if current_pos:
            close_amount = round(current_pos['amount'] * percentage, 3)

            # For longs, we sell to close
            side = 'SELL' if current_pos['side'] == 'LONG' else 'BUY'

            print(f"\n🔴 Closing {percentage*100:.0f}% of position ({close_amount} BTC)")

            order = self.place_market_order(side, close_amount, reduce_only=True)

            if order:
                if percentage >= 1.0:
                    self.position = None
                    print("✅ Position fully closed")
                else:
                    self.position['amount'] -= close_amount
                    print(f"✅ Partial close complete. Remaining: {self.position['amount']} BTC")

                return True

        return False

    def place_stop_loss(self, stop_price: float) -> bool:
        """Place a stop loss order"""
        current_pos = self.get_current_position()

        if current_pos:
            params = {
                'symbol': 'BTCUSDT',
                'side': 'SELL' if current_pos['side'] == 'LONG' else 'BUY',
                'type': 'STOP_MARKET',
                'stopPrice': stop_price,
                'closePosition': 'true',
                'priceProtect': 'true'
            }

            result = self._make_request('POST', '/fapi/v1/order', params)

            if result:
                print(f"🛡️ Stop loss set at ${stop_price:,.2f}")
                return True

        return False


# Test the client
if __name__ == "__main__":
    client = AsterTradingClient()

    print("=" * 60)
    print("ASTER TRADING CLIENT TEST")
    print("=" * 60)

    # Check account
    client.get_account_info()

    # Check position
    client.get_current_position()

    # Calculate what position size would be
    current_price = 111500
    client.calculate_position_size(0.35, 3, current_price)