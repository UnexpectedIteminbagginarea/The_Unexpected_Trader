"""
Test what historical data we can get from CoinGlass
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data.coinglass_client import CoinGlassClient

async def test_historical_availability():
    client = CoinGlassClient()

    print("=" * 80)
    print("🔍 COINGLASS HISTORICAL DATA AVAILABILITY TEST")
    print("=" * 80)

    # Test different endpoints for historical data
    endpoints_to_test = [
        {
            'name': 'Open Interest History',
            'endpoint': '/api/openInterest/v3/chart',
            'params': {
                'symbol': 'BTC',
                'interval': '1h',
                'limit': 168  # Try to get 7 days
            }
        },
        {
            'name': 'Long/Short Ratio History',
            'endpoint': '/api/globalAnalysis/v2/longShort',
            'params': {
                'symbol': 'BTC',
                'interval': '1h'
            }
        },
        {
            'name': 'Funding Rate History',
            'endpoint': '/api/funding/v2/chart',
            'params': {
                'symbol': 'BTC',
                'interval': '1h'
            }
        },
        {
            'name': 'Liquidation History',
            'endpoint': '/api/liquidation/v2/history',
            'params': {
                'symbol': 'BTC',
                'interval': '1h'
            }
        },
        {
            'name': 'Exchange Netflow',
            'endpoint': '/api/exchange-netflow/chart',
            'params': {
                'symbol': 'BTC',
                'exchange': 'all',
                'interval': '1h'
            }
        }
    ]

    results = {}

    for test in endpoints_to_test:
        print(f"\n📊 Testing: {test['name']}")
        print(f"   Endpoint: {test['endpoint']}")

        try:
            # Try to make the request
            url = f"https://open-api-v3.coinglass.com{test['endpoint']}"

            response = await client._make_request(url, test['params'])

            if response and response.get('success'):
                data = response.get('data', {})

                # Check what kind of data we got
                if isinstance(data, list) and len(data) > 0:
                    # List of data points
                    print(f"   ✅ Success: Got {len(data)} data points")

                    # Check date range if timestamps exist
                    if 'time' in data[0] or 't' in data[0] or 'createTime' in data[0]:
                        time_key = 'time' if 'time' in data[0] else ('t' if 't' in data[0] else 'createTime')

                        # Convert timestamps to dates
                        first_time = datetime.fromtimestamp(data[0][time_key] / 1000)
                        last_time = datetime.fromtimestamp(data[-1][time_key] / 1000)

                        days_of_data = (last_time - first_time).days

                        print(f"   📅 Date range: {first_time.strftime('%Y-%m-%d')} to {last_time.strftime('%Y-%m-%d')}")
                        print(f"   📈 Days of history: {days_of_data} days")

                        results[test['name']] = {
                            'available': True,
                            'days': days_of_data,
                            'points': len(data)
                        }
                    else:
                        print(f"   ⚠️  Got data but no timestamps found")
                        results[test['name']] = {'available': True, 'days': 'unknown'}

                elif isinstance(data, dict):
                    # Single data point or structured response
                    print(f"   ✅ Success: Got structured data")

                    # Check for nested time series
                    for key in ['chart', 'history', 'data', 'list']:
                        if key in data and isinstance(data[key], list) and len(data[key]) > 0:
                            print(f"   📊 Found {len(data[key])} points in '{key}'")
                            results[test['name']] = {
                                'available': True,
                                'points': len(data[key])
                            }
                            break
                else:
                    print(f"   ❌ Got response but unclear data structure")
                    results[test['name']] = {'available': False}

            else:
                print(f"   ❌ Failed: {response.get('msg', 'No error message')}")
                results[test['name']] = {'available': False}

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            results[test['name']] = {'available': False, 'error': str(e)}

    # Summary
    print("\n" + "=" * 80)
    print("📊 HISTORICAL DATA SUMMARY")
    print("=" * 80)

    available_for_backtest = []
    limited_data = []
    not_available = []

    for name, result in results.items():
        if result.get('available'):
            if result.get('days', 0) >= 7:
                available_for_backtest.append(name)
            else:
                limited_data.append(name)
        else:
            not_available.append(name)

    print("\n✅ AVAILABLE FOR BACKTESTING (7+ days):")
    for item in available_for_backtest:
        print(f"   • {item}")

    print("\n⚠️  LIMITED HISTORICAL DATA:")
    for item in limited_data:
        print(f"   • {item}")

    print("\n❌ NOT AVAILABLE HISTORICALLY:")
    for item in not_available:
        print(f"   • {item}")

    print("\n💡 RECOMMENDATION:")
    if available_for_backtest:
        print("   We CAN backtest with: " + ", ".join(available_for_backtest))
        print("   This will enhance our Fibonacci strategy with market sentiment data!")
    else:
        print("   Limited historical data - may need to use live data going forward")
        print("   Or use alternative data sources for backtesting")

if __name__ == "__main__":
    asyncio.run(test_historical_availability())