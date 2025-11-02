import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Fetch from VPS API via HTTPS
    const response = await fetch('https://api.theunexpectedtrader.com/api/logs/position', {
      cache: 'no-store'
    });

    if (!response.ok) {
      throw new Error('Failed to fetch position data');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching position data:', error);
    return NextResponse.json({ error: 'Failed to load position data' }, { status: 500 });
  }
}
