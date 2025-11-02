"use client";

import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot, Legend } from 'recharts';
import { format } from 'date-fns';

interface TradePoint {
  timestamp: string;
  price: number;
  action: string;
  size?: number;
}

interface PriceChartProps {
  trades: TradePoint[];
  currentPrice: number;
}

interface PriceData {
  timestamp: number;
  time: string;
  close: number;
}

export default function PriceChart({ trades, currentPrice }: PriceChartProps) {
  const [priceHistory, setPriceHistory] = useState<PriceData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPriceHistory();
  }, []);

  const fetchPriceHistory = async () => {
    try {
      const response = await fetch('/api/data/price-history');
      if (response.ok) {
        const data = await response.json();
        setPriceHistory(data);
      }
      setLoading(false);
    } catch (error) {
      console.error('Error fetching price history:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="h-96 flex items-center justify-center text-gray-500">
        Loading price chart...
      </div>
    );
  }

  // Handle empty price history
  if (!priceHistory || priceHistory.length === 0) {
    return (
      <div className="h-96 flex items-center justify-center text-gray-500">
        Loading price data...
      </div>
    );
  }

  // Format chart data
  const chartData = priceHistory.map(p => ({
    timestamp: p.timestamp,
    time: format(new Date(p.timestamp), 'MMM d HH:mm'),
    price: p.close
  }));

  // Find min/max for chart domain
  const prices = chartData.map(d => d.price);
  const minPrice = prices.length > 0 ? Math.min(...prices) * 0.995 : 100000;
  const maxPrice = prices.length > 0 ? Math.max(...prices) * 1.005 : 120000;

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />

          <XAxis
            dataKey="time"
            stroke="#888"
            tick={{ fill: '#888', fontSize: 10 }}
            angle={-45}
            textAnchor="end"
            height={80}
            interval={Math.floor(chartData.length / 10)}
          />

          <YAxis
            stroke="#888"
            tick={{ fill: '#888', fontSize: 12 }}
            domain={[minPrice, maxPrice]}
            tickFormatter={(value) => `$${value.toLocaleString()}`}
          />

          <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(0, 0, 0, 0.9)',
              border: '1px solid rgba(255, 145, 77, 0.5)',
              borderRadius: '8px',
              color: '#fff',
              padding: '10px'
            }}
            labelFormatter={(label) => `Time: ${label}`}
            formatter={(value: any) => [`$${Number(value).toLocaleString()}`, 'BTC Price']}
          />

          {/* BTC Price Line */}
          <Line
            type="monotone"
            dataKey="price"
            stroke="#ff914d"
            strokeWidth={2}
            dot={false}
            animationDuration={300}
          />

          {/* Plot trade entry points on the price line */}
          {trades.map((trade, idx) => {
            const tradeTime = new Date(trade.timestamp).getTime();
            // Find the closest price data point
            const closestPoint = chartData.reduce((prev, curr) =>
              Math.abs(curr.timestamp - tradeTime) < Math.abs(prev.timestamp - tradeTime) ? curr : prev
            );

            // Determine label and color
            let label = '';
            let fillColor = '#3b82f6';

            if (idx === 0) {
              label = 'Entry $111,091';
              fillColor = '#3b82f6';  // Blue
            } else if (trade.action === 'SCALE_IN') {
              const scaleNumber = trades.slice(0, idx).filter(t => t.action === 'SCALE_IN').length + 1;
              label = `Scale-in #${scaleNumber} $${Math.round(trade.price).toLocaleString()}`;
              fillColor = '#eab308';  // Yellow
            }

            return (
              <ReferenceDot
                key={`trade-${idx}`}
                x={closestPoint.time}
                y={closestPoint.price}
                r={12}
                fill={fillColor}
                stroke="#fff"
                strokeWidth={3}
                style={{
                  animation: 'pulse-dot 2s ease-in-out infinite',
                  animationDelay: `${idx * 0.3}s`
                }}
                label={{
                  value: label,
                  position: 'top',
                  fill: '#fff',
                  fontSize: 11,
                  fontWeight: 'bold',
                  offset: 15
                }}
              />
            );
          })}

          {/* Current price marker */}
          <ReferenceDot
            x={chartData[chartData.length - 1]?.time}
            y={currentPrice}
            r={10}
            fill="#10b981"
            stroke="#fff"
            strokeWidth={2}
            label={{
              value: 'Now',
              position: 'top',
              fill: '#10b981',
              fontSize: 12,
              fontWeight: 'bold'
            }}
          />

          <Legend
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="circle"
            formatter={(value) => <span style={{ color: '#888' }}>{value}</span>}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex justify-center gap-6 mt-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-blue-500 rounded-full border-2 border-white"></div>
          <span className="text-gray-400">Entry Points</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-yellow-500 rounded-full border-2 border-white"></div>
          <span className="text-gray-400">Scale-ins</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-500 rounded-full border-2 border-white"></div>
          <span className="text-gray-400">Current Price</span>
        </div>
      </div>
    </div>
  );
}
