import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Fetch Claude reviews from VPS API
    const response = await fetch('https://api.theunexpectedtrader.com/api/claude/decisions', {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error('Failed to fetch Claude reviews');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching Claude reviews:', error);
    return NextResponse.json({ error: 'Failed to load Claude reviews' }, { status: 500 });
  }
}
