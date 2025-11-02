import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Fetch from VPS API (which proxies Binance)
    const response = await fetch('https://api.theunexpectedtrader.com/api/price/current', {
      cache: 'no-store'
    });

    if (!response.ok) {
      throw new Error('Failed to fetch price');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching price:', error);
    return NextResponse.json({ error: 'Failed to fetch price' }, { status: 500 });
  }
}
