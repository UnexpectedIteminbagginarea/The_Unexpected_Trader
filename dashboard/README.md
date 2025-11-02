# 🚀 Fibonacci Golden Pocket Trader - Dashboard

Live trading dashboard for the Aster Vibe Trading Arena competition.

## Features

- ✨ Animated star background (React Three Fiber)
- 🔮 Glass-morphism design with semi-transparent boxes
- 📊 Real-time position tracking
- 📝 Live decision feed
- 🎯 Performance metrics
- 🔄 Auto-refresh every 30 seconds

## Setup

1. **Install dependencies**:
```bash
npm install
```

2. **Run development server**:
```bash
npm run dev
```

3. **Open browser**:
```
http://localhost:3000
```

## Data Sources

The dashboard reads data from the bot's log files:
- `../logs/position_state.json` - Current position
- `../logs/trading_decisions.json` - Trade history
- Binance API - Live BTC price

## Build for Production

```bash
npm run build
npm start
```

## Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

## Design Credits

- Star background: Adapted from Starshield project
- Glass-morphism styling: Custom CSS with backdrop-filter
- Color scheme: Orange spectral gradient

## Stack

- Next.js 15
- React 19
- React Three Fiber (3D stars)
- TailwindCSS
- TypeScript
