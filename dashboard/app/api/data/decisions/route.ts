import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get('limit') || '10';

    // Fetch from VPS API
    const response = await fetch(`https://api.theunexpectedtrader.com/api/logs/decisions?limit=${limit}`, {
      cache: 'no-store'
    });

    if (!response.ok) {
      throw new Error('Failed to fetch decisions');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching decisions:', error);
    return NextResponse.json({ error: 'Failed to load decisions' }, { status: 500 });
  }
}
