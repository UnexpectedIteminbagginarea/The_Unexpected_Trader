"""
Check how much historical data CoinGlass actually provides
"""
import requests
from datetime import datetime, timedelta

def check_history_depth():
    api_key = 'c55e983ae3ba4c039f10e592a623e073'
    headers = {
        'accept': 'application/json',
        'CG-API-KEY': api_key
    }

    print("=" * 80)
    print("🔍 COINGLASS HISTORICAL DATA DEPTH CHECK")
    print("=" * 80)

    # Test different data types with maximum limits
    tests = [
        {
            'name': 'Long/Short Ratio',
            'url': 'https://open-api-v3.coinglass.com/api/futures/globalLongShortAccountRatio',
            'params': {
                'exchange': 'Binance',
                'symbol': 'BTCUSDT',
                'interval': '1h',
                'limit': 500  # Try max limit
            }
        },
        {
            'name': 'Open Interest',
            'url': 'https://open-api-v3.coinglass.com/api/futures/openInterest/chart',
            'params': {
                'symbol': 'BTC',
                'interval': '1h',
                'limit': 500
            }
        },
        {
            'name': 'Funding Rate',
            'url': 'https://open-api-v3.coinglass.com/api/futures/fundingRate/chart',
            'params': {
                'symbol': 'BTC',
                'type': 'C',
                'interval': '1h',
                'limit': 500
            }
        }
    ]

    results = {}

    for test in tests:
        print(f"\n📊 Testing: {test['name']}")
        print(f"   URL: {test['url']}")

        try:
            response = requests.get(test['url'], headers=headers, params=test['params'])

            if response.status_code == 200:
                data = response.json()

                if data.get('code') == '0' and data.get('data'):
                    data_points = data['data']

                    if isinstance(data_points, list) and len(data_points) > 0:
                        print(f"   ✅ Got {len(data_points)} data points")

                        # Check time range
                        first_point = data_points[0]
                        last_point = data_points[-1]

                        # Find timestamp field
                        time_field = None
                        for field in ['time', 't', 'createTime', 'timestamp']:
                            if field in first_point:
                                time_field = field
                                break

                        if time_field:
                            # Convert to datetime
                            first_time = datetime.fromtimestamp(first_point[time_field] / 1000)
                            last_time = datetime.fromtimestamp(last_point[time_field] / 1000)

                            hours_of_data = (last_time - first_time).total_seconds() / 3600
                            days_of_data = hours_of_data / 24

                            print(f"   📅 Date range: {first_time} to {last_time}")
                            print(f"   ⏰ Coverage: {hours_of_data:.1f} hours ({days_of_data:.1f} days)")

                            results[test['name']] = {
                                'points': len(data_points),
                                'hours': hours_of_data,
                                'days': days_of_data,
                                'oldest': first_time
                            }

                            # Show sample data structure
                            print(f"   📈 Sample data point:")
                            for key, value in first_point.items():
                                if key != time_field:
                                    print(f"      • {key}: {value}")
                                    if len(str(first_point)) > 200:
                                        break
                        else:
                            print(f"   ⚠️  No timestamp field found")
                    else:
                        print(f"   ❌ No data points returned")
                else:
                    print(f"   ❌ API Error: {data.get('msg', 'Unknown error')}")
            else:
                print(f"   ❌ HTTP {response.status_code}")

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

    # Summary
    print("\n" + "=" * 80)
    print("📊 HISTORICAL DATA SUMMARY")
    print("=" * 80)

    if results:
        print("\n✅ Available Historical Data:")
        for name, info in results.items():
            print(f"\n   {name}:")
            print(f"      • Points: {info['points']}")
            print(f"      • History: {info['days']:.1f} days")
            print(f"      • Oldest: {info['oldest']}")

        # Recommendation
        max_days = max(r['days'] for r in results.values())
        print(f"\n💡 CONCLUSION:")
        print(f"   Maximum historical depth: {max_days:.1f} days")

        if max_days >= 7:
            print(f"   ✅ We CAN backtest the last week with CoinGlass data!")
            print(f"   This covers the October 17-29 period perfectly")
        elif max_days >= 1:
            print(f"   ⚠️  Limited to {max_days:.1f} days - can test recent setups only")
        else:
            print(f"   ❌ Insufficient history for meaningful backtesting")
    else:
        print("\n❌ No historical data available")

    print("\n📝 NOTES:")
    print("   • CoinGlass is primarily for real-time/recent market sentiment")
    print("   • For deep backtesting, we rely on price action (our Fib strategy)")
    print("   • CoinGlass data can ENHANCE entries in live trading")
    print("   • Perfect for competition: real-time sentiment + Fibonacci levels")

if __name__ == "__main__":
    check_history_depth()