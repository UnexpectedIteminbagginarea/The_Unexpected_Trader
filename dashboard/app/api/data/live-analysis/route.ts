import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Fetch live analysis from VPS API
    const response = await fetch('https://api.theunexpectedtrader.com/api/analysis/current', {
      cache: 'no-store'
    });

    if (!response.ok) {
      // Return empty state if not available yet
      return NextResponse.json({
        timestamp: new Date().toISOString(),
        price: 0,
        sentiment: {},
        analysis: 'Waiting for data...'
      });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching live analysis:', error);
    return NextResponse.json({
      timestamp: new Date().toISOString(),
      price: 0,
      sentiment: {},
      analysis: 'Loading...'
    });
  }
}
