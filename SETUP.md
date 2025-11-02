# 🚀 Setup Guide for Unexpected Vibe Trader

## Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd Unexpected_vibe_trader
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
# Get your Aster API keys from Aster DEX
ASTER_API_KEY=your_actual_key_here
ASTER_API_SECRET=your_actual_secret_here

# Get CoinGlass API key ($49/month): https://www.coinglass.com/pricing
COINGLASS_API_KEY=your_actual_key_here

# Get Claude API key: https://console.anthropic.com/
ANTHROPIC_API_KEY=your_actual_key_here
```

### 4. Test Connections

```bash
# Test Aster API connection
python data/aster_client.py

# Test CoinGlass API connection
python data/coinglass_client.py
```

### 5. Run the Trader

```bash
# Paper trading mode (safe, no real money)
python core/trader.py

# Live trading (real money - be careful!)
# Edit config/config.py and set PAPER_TRADING = False
```

### 6. View Dashboard

```bash
cd dashboard
python app.py
```

Visit: http://localhost:8000

## 📝 Important Notes

- **Always test in paper trading mode first**
- Start with small position sizes
- Monitor the bot continuously
- Set appropriate stop losses
- Review the AI's reasoning before going live

## 🔒 Security

- Never commit your `.env` file
- Keep API keys private
- Use read-only API keys for testing
- Enable 2FA on your exchange accounts

## 📚 Documentation

See [README.md](README.md) for full documentation.
