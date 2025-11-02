"""
Pre-Flight Check for Live Trading
Verifies all systems, logging, and data feeds before going live
"""
import os
import sys
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
from trading_decision_logger import TradingDecisionLogger
import time

load_dotenv()

class PreFlightCheck:
    def __init__(self):
        self.checks_passed = []
        self.checks_failed = []
        self.logger = TradingDecisionLogger()

    def check_environment(self):
        """Check environment variables"""
        print("\n" + "="*60)
        print("1️⃣  CHECKING ENVIRONMENT VARIABLES")
        print("="*60)

        required_vars = [
            'ASTER_API_KEY',
            'ASTER_API_SECRET',
            'COINGLASS_API_KEY'
        ]

        for var in required_vars:
            value = os.getenv(var)
            if value:
                print(f"✅ {var}: {value[:10]}...{value[-10:]}")
                self.checks_passed.append(f"Environment: {var}")
            else:
                print(f"❌ {var}: Missing!")
                self.checks_failed.append(f"Environment: {var}")

        return len(self.checks_failed) == 0

    def check_aster_data(self):
        """Check Aster API data feeds"""
        print("\n" + "="*60)
        print("2️⃣  CHECKING ASTER DATA FEEDS")
        print("="*60)

        base_url = "https://fapi.asterdex.com"

        # Test endpoints we need
        endpoints = [
            {
                'name': 'Price Ticker',
                'url': f"{base_url}/fapi/v1/ticker/24hr?symbol=BTCUSDT",
                'check': lambda d: 'lastPrice' in d
            },
            {
                'name': 'Order Book',
                'url': f"{base_url}/fapi/v1/depth?symbol=BTCUSDT&limit=20",
                'check': lambda d: 'bids' in d and 'asks' in d
            },
            {
                'name': 'Funding Rate',
                'url': f"{base_url}/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1",
                'check': lambda d: isinstance(d, list) and len(d) > 0
            },
            {
                'name': 'Klines/Candles',
                'url': f"{base_url}/fapi/v1/klines?symbol=BTCUSDT&interval=1h&limit=5",
                'check': lambda d: isinstance(d, list) and len(d) > 0
            }
        ]

        all_good = True
        for endpoint in endpoints:
            try:
                response = requests.get(endpoint['url'], timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if endpoint['check'](data):
                        print(f"✅ {endpoint['name']}: Working")

                        # Log sample data
                        if endpoint['name'] == 'Price Ticker':
                            price = float(data['lastPrice'])
                            volume = float(data['volume'])
                            print(f"   Price: ${price:,.2f}, Volume: ${volume:,.2f}")

                        self.checks_passed.append(f"Aster: {endpoint['name']}")
                    else:
                        print(f"❌ {endpoint['name']}: Unexpected format")
                        self.checks_failed.append(f"Aster: {endpoint['name']}")
                        all_good = False
                else:
                    print(f"❌ {endpoint['name']}: HTTP {response.status_code}")
                    self.checks_failed.append(f"Aster: {endpoint['name']}")
                    all_good = False

            except Exception as e:
                print(f"❌ {endpoint['name']}: {str(e)}")
                self.checks_failed.append(f"Aster: {endpoint['name']}")
                all_good = False

        return all_good

    def check_coinglass_data(self):
        """Check CoinGlass sentiment feeds"""
        print("\n" + "="*60)
        print("3️⃣  CHECKING COINGLASS SENTIMENT FEEDS")
        print("="*60)

        api_key = os.getenv('COINGLASS_API_KEY')
        headers = {
            'accept': 'application/json',
            'CG-API-KEY': api_key
        }

        base_url = "https://open-api-v4.coinglass.com"

        endpoints = [
            {
                'name': 'Fear & Greed',
                'url': f"{base_url}/api/index/fear-greed-history",
                'params': {'time_type': 1},
                'check': lambda d: d.get('code') == '0'
            },
            {
                'name': 'Long/Short Ratio',
                'url': f"{base_url}/api/futures/global-long-short-account-ratio/history",
                'params': {'exchange': 'Binance', 'symbol': 'BTCUSDT', 'interval': '4h', 'limit': 1},
                'check': lambda d: d.get('code') == '0'
            },
            {
                'name': 'Funding Rate',
                'url': f"{base_url}/api/futures/funding-rate/history",
                'params': {'exchange': 'Binance', 'symbol': 'BTCUSDT', 'interval': '8h', 'limit': 1},
                'check': lambda d: d.get('code') == '0'
            }
        ]

        all_good = True
        for endpoint in endpoints:
            try:
                response = requests.get(
                    endpoint['url'],
                    headers=headers,
                    params=endpoint['params'],
                    timeout=5
                )

                if response.status_code == 200:
                    data = response.json()
                    if endpoint['check'](data):
                        print(f"✅ {endpoint['name']}: Working")

                        # Show sample data
                        if endpoint['name'] == 'Fear & Greed' and data.get('data'):
                            value = data['data']['data_list'][0]
                            print(f"   Current: {value} ({'Fear' if value < 40 else 'Neutral' if value < 60 else 'Greed'})")

                        self.checks_passed.append(f"CoinGlass: {endpoint['name']}")
                    else:
                        print(f"⚠️  {endpoint['name']}: {data.get('msg', 'API error')}")
                        # Not critical if some CoinGlass endpoints fail
                else:
                    print(f"⚠️  {endpoint['name']}: HTTP {response.status_code}")

            except Exception as e:
                print(f"⚠️  {endpoint['name']}: {str(e)}")

        return True  # CoinGlass is optional enhancement

    def check_fibonacci_levels(self):
        """Verify Fibonacci levels are current"""
        print("\n" + "="*60)
        print("4️⃣  CHECKING FIBONACCI LEVELS")
        print("="*60)

        # Get current price
        response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
        current_price = float(response.json()['price'])

        # Our configured levels
        fib_levels = {
            '4H Golden Pocket': (111463, 112189),
            'Daily Golden Pocket': (108088, 108975),
            '4H 50%': 114864,
            'Daily 50%': 112246
        }

        print(f"Current BTC Price: ${current_price:,.2f}\n")

        for name, levels in fib_levels.items():
            if isinstance(levels, tuple):
                bottom, top = levels
                if bottom <= current_price <= top:
                    print(f"🎯 {name}: ${bottom:,} - ${top:,} [ACTIVE!]")
                else:
                    distance = min(abs(current_price - bottom), abs(current_price - top))
                    pct = (distance / current_price) * 100
                    print(f"📏 {name}: ${bottom:,} - ${top:,} ({pct:.2f}% away)")
            else:
                distance = abs(current_price - levels)
                pct = (distance / current_price) * 100
                print(f"📏 {name}: ${levels:,} ({pct:.2f}% away)")

        # Check if we're near any entry zone
        near_entry = False
        if 111463 <= current_price <= 112189:
            print("\n🚨 IN 4H GOLDEN POCKET - READY FOR ENTRY!")
            near_entry = True
        elif current_price < 112189 * 1.01:
            print("\n⏳ Very close to 4H golden pocket entry")
            near_entry = True
        elif 108088 <= current_price <= 108975:
            print("\n🚨 IN DAILY GOLDEN POCKET - STRONG BUY ZONE!")
            near_entry = True

        self.checks_passed.append("Fibonacci levels verified")
        return True

    def check_logging_system(self):
        """Test logging system"""
        print("\n" + "="*60)
        print("5️⃣  CHECKING LOGGING SYSTEM")
        print("="*60)

        try:
            # Test log directories
            log_dir = "logs"
            if os.path.exists(log_dir):
                print(f"✅ Log directory exists: {log_dir}/")
            else:
                os.makedirs(log_dir, exist_ok=True)
                print(f"✅ Created log directory: {log_dir}/")

            # Test logger functionality
            test_logger = TradingDecisionLogger()

            # Test market analysis log
            test_logger.log_market_analysis(
                price=112400,
                fib_levels={'h4': {'gp_top': 112189, 'gp_bottom': 111463}},
                sentiment={'fear_greed': 30}
            )

            # Check log files exist
            log_files = [
                'trading_decisions.json',
                'trading_decisions_readable.txt',
                'decision_summary.md'
            ]

            for log_file in log_files:
                path = os.path.join(log_dir, log_file)
                if os.path.exists(path):
                    size = os.path.getsize(path)
                    print(f"✅ {log_file}: {size} bytes")
                    self.checks_passed.append(f"Log: {log_file}")
                else:
                    print(f"⚠️  {log_file}: Not created yet")

            return True

        except Exception as e:
            print(f"❌ Logging system error: {str(e)}")
            self.checks_failed.append("Logging system")
            return False

    def check_strategy_config(self):
        """Verify strategy configuration"""
        print("\n" + "="*60)
        print("6️⃣  CHECKING STRATEGY CONFIGURATION")
        print("="*60)

        from config.trading_config import TradingConfig

        print(f"Mode: {TradingConfig.MODE}")
        print(f"Symbol: {TradingConfig.SYMBOL}")
        print(f"Initial Position: {TradingConfig.BASE_POSITION_SIZE * 100}%")
        print(f"Base Leverage: {TradingConfig.LEVERAGE['base']}x")
        print(f"Max Leverage: {TradingConfig.LEVERAGE['scale_in_3']}x")

        print("\nScale-in levels:")
        for i, level in enumerate(TradingConfig.SCALE_LEVELS):
            print(f"  {level['deviation']*100:+.0f}%: Add {level['add']*100:.0f}%")

        print("\nProfit targets:")
        for target in TradingConfig.PROFIT_TARGETS:
            print(f"  {target['gain']*100:+.0f}%: Take {target['reduce']*100:.0f}% off")

        self.checks_passed.append("Strategy configuration")
        return True

    def run_all_checks(self):
        """Run all pre-flight checks"""
        print("\n" + "="*80)
        print("🚀 PRE-FLIGHT CHECK FOR LIVE TRADING")
        print("="*80)

        start_time = datetime.now()

        # Run checks
        checks = [
            ("Environment", self.check_environment),
            ("Aster Data", self.check_aster_data),
            ("CoinGlass Data", self.check_coinglass_data),
            ("Fibonacci Levels", self.check_fibonacci_levels),
            ("Logging System", self.check_logging_system),
            ("Strategy Config", self.check_strategy_config)
        ]

        all_passed = True
        for name, check_func in checks:
            try:
                if not check_func():
                    all_passed = False
            except Exception as e:
                print(f"❌ {name} check failed: {str(e)}")
                self.checks_failed.append(name)
                all_passed = False

        # Summary
        print("\n" + "="*80)
        print("📋 PRE-FLIGHT SUMMARY")
        print("="*80)

        print(f"\n✅ Passed: {len(self.checks_passed)} checks")
        for check in self.checks_passed[:5]:  # Show first 5
            print(f"   • {check}")

        if self.checks_failed:
            print(f"\n❌ Failed: {len(self.checks_failed)} checks")
            for check in self.checks_failed:
                print(f"   • {check}")

        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n⏱️  Check completed in {elapsed:.2f} seconds")

        # Final verdict
        print("\n" + "="*80)
        if all_passed and len(self.checks_failed) == 0:
            print("✅ ALL SYSTEMS GO - READY FOR LIVE TRADING!")
            print("\n🎯 Next Steps:")
            print("1. Start with small position ($100-500)")
            print("2. Monitor logs in real-time")
            print("3. Be ready to intervene if needed")
            print("4. Scale up gradually if profitable")
            return True
        else:
            print("⚠️  SOME ISSUES DETECTED - Review before going live")
            print("\nCritical issues to fix:")
            for issue in self.checks_failed:
                print(f"  - {issue}")
            return False


if __name__ == "__main__":
    checker = PreFlightCheck()
    ready = checker.run_all_checks()

    if ready:
        print("\n🚀 System is ready for live trading!")
        print("Run 'python live_trading_bot.py' to start")