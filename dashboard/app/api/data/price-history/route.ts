import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Fetch from VPS API (which fetches from Binance)
    const response = await fetch('https://api.theunexpectedtrader.com/api/price/history', {
      cache: 'no-store'
    });

    if (!response.ok) {
      throw new Error('Failed to fetch price history from VPS');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching price history:', error);
    return NextResponse.json({ error: 'Failed to fetch price history' }, { status: 500 });
  }
}
