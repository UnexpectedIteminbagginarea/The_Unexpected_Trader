"use client";

import { useState, useEffect } from 'react';
import { formatDistance } from 'date-fns';
import PriceChart from '@/components/PriceChart';

interface PositionData {
  position: {
    entry_price: number;
    average_price: number;
    size: number;
    leverage: number;
    entry_time: string;
  };
  last_entry_price: number;
  scale_in_count: number;
}

interface DecisionData {
  timestamp: string;
  action: string;
  price?: number;
  size?: number;
  reasoning?: string;
  details?: string;
}

interface LiveAnalysis {
  fear_greed: number;
  funding_rate: number;
  ls_ratio: number;
  bot_decision: string;
  upper_exit: number;
}

interface ClaudeDecision {
  timestamp: string;
  decision: string;
  reasoning: string;
  confidence: number;
}

export default function DashboardPage() {
  const [mounted, setMounted] = useState(false);
  const [position, setPosition] = useState<PositionData | null>(null);
  const [decisions, setDecisions] = useState<DecisionData[]>([]);
  const [claudeReviews, setClaudeReviews] = useState<ClaudeDecision[]>([]);
  const [currentPrice, setCurrentPrice] = useState<number>(0);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [liveAnalysis, setLiveAnalysis] = useState<LiveAnalysis>({
    fear_greed: 30,
    funding_rate: 0.0001,
    ls_ratio: 1.0,
    bot_decision: "Analyzing...",
    upper_exit: 112246
  });

  useEffect(() => {
    setMounted(true);
    loadData();

    // Auto-refresh every 30 seconds
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      let decData: any = null;

      // Fetch position data
      const posRes = await fetch('/api/data/position');
      if (posRes.ok) {
        const posData = await posRes.json();
        setPosition(posData);
      }

      // Fetch recent decisions
      const decRes = await fetch('/api/data/decisions?limit=100');
      if (decRes.ok) {
        decData = await decRes.json();
        setDecisions(decData);

        // Extract sentiment from latest decision
        if (decData && decData.length > 0) {
          const latestWithSentiment = decData.find((d: any) => d.sentiment_scores);
          if (latestWithSentiment && latestWithSentiment.sentiment_scores) {
            const sentiment = latestWithSentiment.sentiment_scores;
            const fg = sentiment.fear_greed || 30;
            const fr = sentiment.funding_rate || 0.0001;

            // Determine bot decision based on sentiment
            let decision = "Monitoring position";
            if (fg < 25 && fr < -0.01) {
              decision = "Extreme fear + neg funding → Strong buy conditions (1.3x sizing)";
            } else if (fg < 40) {
              decision = "Fear sentiment → Letting winners run (1.2x targets)";
            } else if (fg > 75 && fr > 0.05) {
              decision = "Extreme greed → Taking profits early (0.6x targets)";
            }

            setLiveAnalysis({
              fear_greed: fg,
              funding_rate: fr,
              ls_ratio: sentiment.ls_ratio || 1.0,
              bot_decision: decision,
              upper_exit: 112246
            });
          }
        }
      }

      // Fetch current price
      const priceRes = await fetch('/api/data/price');
      if (priceRes.ok) {
        const priceData = await priceRes.json();
        setCurrentPrice(priceData.price);
      }

      // Fetch Claude reviews from LIVE API via Next.js route
      try {
        const claudeRes = await fetch('/api/data/claude-reviews');
        if (claudeRes.ok) {
          const claudeData = await claudeRes.json();
          // Get last 6 reviews and reverse for newest first
          const recentReviews = claudeData.slice(-6).reverse();
          setClaudeReviews(recentReviews.map((r: any) => ({
            timestamp: r.timestamp,
            decision: r.decision,
            reasoning: r.reasoning,
            confidence: r.confidence
          })));
        }
      } catch (e) {
        console.log('Claude reviews API error:', e);
      }

      setLastUpdate(new Date());
    } catch (error) {
      console.error('Error loading data:', error);
    }
  };

  const calculatePnL = () => {
    if (!position || !currentPrice) return { pnl: 0, pnlPercent: 0, leveragedPnl: 0, leveragedPnlPercent: 0 };

    // Calculate base P&L (price change)
    const basePnlPercent = ((currentPrice - position.position.average_price) / position.position.average_price) * 100;

    // Dollar P&L = position size × price change (NOT multiplied by leverage)
    const pnlUsd = position.position.size * (currentPrice - position.position.average_price);

    // Calculate LEVERAGED P&L percentage (percentage gets multiplied by leverage)
    const leverage = position.position.leverage || 4;
    const leveragedPnlPercent = basePnlPercent * leverage;

    return {
      pnl: pnlUsd,
      pnlPercent: basePnlPercent,
      leveragedPnl: pnlUsd,  // Same dollar amount
      leveragedPnlPercent    // Leveraged percentage
    };
  };

  const { pnl, pnlPercent, leveragedPnl, leveragedPnlPercent } = calculatePnL();

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-black animated-space-gradient">
      <div className="starfield" />

      {/* Header */}
      <header className="relative z-10 py-2 px-4 md:py-0 md:px-6 border-b border-white/10">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4 md:gap-0">
          <div className="flex items-center gap-2 md:gap-4">
            <img
              src="/unexpected-trader.png"
              alt="Unexpected Trader"
              className="w-32 h-32 md:w-56 md:h-56 object-contain"
            />
            <div>
              <h1 className="text-xl md:text-3xl font-bold text-white">The Unexpected Trader</h1>
              <p className="text-xs md:text-sm text-gray-400 mt-1">Powered by Aster API and Coinglass Data</p>
            </div>
          </div>
          <button
            onClick={loadData}
            className="px-4 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded-lg transition-colors text-sm md:text-base"
          >
            Refresh Data
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 max-w-7xl mx-auto p-4 md:p-6 space-y-4 md:space-y-6">

        {/* Top Row - Price & Position */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

          {/* Live BTC Price */}
          <div className="glass-advanced rounded-xl p-6">
            <h2 className="text-xl font-semibold text-orange-400 mb-4">💰 Live BTC Price</h2>
            {currentPrice > 0 ? (
              <>
                <div className="text-5xl font-bold text-white mb-2">
                  ${currentPrice.toLocaleString()}
                </div>
                <p className="text-gray-400 text-sm">
                  Last updated: {formatDistance(lastUpdate, new Date(), { addSuffix: true })}
                </p>
              </>
            ) : (
              <div className="text-gray-500">Loading price...</div>
            )}
          </div>

          {/* Position Status */}
          <div className="glass-advanced rounded-xl p-6">
            <h2 className="text-xl font-semibold text-orange-400 mb-4">📊 Position Status</h2>
            {position ? (
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">Size:</span>
                  <span className="text-white font-semibold">{position.position.size} BTC</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Average Entry:</span>
                  <span className="text-white font-semibold">${position.position.average_price.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Leverage:</span>
                  <span className="text-white font-semibold">{position.position.leverage}x</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Scale-ins:</span>
                  <span className="text-white font-semibold">{position.scale_in_count}/4</span>
                </div>
                <div className="pt-3 mt-3 border-t border-white/10">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400">Unrealized P&L (Leveraged):</span>
                    <div className="text-right">
                      <div className={`text-xl font-bold ${leveragedPnlPercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {leveragedPnlPercent >= 0 ? '+' : ''}{leveragedPnlPercent.toFixed(2)}%
                      </div>
                      <div className={`text-sm ${leveragedPnlPercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        ${leveragedPnl.toFixed(2)}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-gray-500">No active position</div>
            )}
          </div>
        </div>

        {/* Price Chart with Trade Markers */}
        <div className="glass-advanced rounded-xl p-6">
          <h2 className="text-xl font-semibold text-orange-400 mb-4">📈 BTC Price & Trade History</h2>
          {decisions.length > 0 && currentPrice > 0 ? (
            <PriceChart
              trades={decisions
                .filter(d => (d.action === 'ENTRY' || d.action === 'SCALE_IN') && d.timestamp >= '2025-10-29T17:48:00')
                .map((d, idx) => ({
                  timestamp: d.timestamp,
                  price: d.price || 0,
                  action: d.action,
                  size: d.size,
                  index: idx
                }))}
              currentPrice={currentPrice}
            />
          ) : (
            <div className="h-96 flex items-center justify-center text-gray-500">
              Loading chart data...
            </div>
          )}

          {/* Target levels */}
          {position && (
            <div className="grid grid-cols-3 gap-3 text-center text-sm mt-4">
              <div className="bg-green-900/20 border border-green-500/30 rounded p-2">
                <div className="text-green-400">Target +5%</div>
                <div className="text-white">${(position.position.average_price * 1.05).toLocaleString()}</div>
              </div>
              <div className="bg-green-900/20 border border-green-500/30 rounded p-2">
                <div className="text-green-400">Target +10%</div>
                <div className="text-white">${(position.position.average_price * 1.10).toLocaleString()}</div>
              </div>
              <div className="bg-red-900/20 border border-red-500/30 rounded p-2">
                <div className="text-red-400">Invalidation -10%</div>
                <div className="text-white">${(position.position.average_price * 0.90).toLocaleString()}</div>
              </div>
            </div>
          )}
        </div>

        {/* Bottom Row - Feed & Stats (3 columns now) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

          {/* Live Feed - Split into Trade History and Claude Reviews */}
          <div className="glass-advanced rounded-xl p-6 md:col-span-2">
            <h2 className="text-xl font-semibold text-orange-400 mb-4">📝 Trading Activity</h2>
            <div className="grid grid-cols-2 gap-4">

              {/* Left: Trade History */}
              <div>
                <h3 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wide">Trade History</h3>
                <div className="space-y-2 max-h-80 overflow-y-auto">
              {decisions.length > 0 ? (
                decisions
                  .filter(d => d.timestamp >= '2025-10-29T17:48:00' && d.action !== 'RECOVERY')
                  .map((decision, idx) => (
                  <div key={idx} className="bg-black/30 rounded p-3 border-l-2 border-orange-500/50">
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-semibold text-orange-300">{decision.action}</span>
                      <span className="text-xs text-gray-500">
                        {new Date(decision.timestamp).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric'
                        })} {new Date(decision.timestamp).toLocaleTimeString('en-US', {
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </span>
                    </div>
                    {decision.details && (
                      <div className="text-sm text-gray-300 mb-2">{decision.details}</div>
                    )}
                    {decision.reasoning && (
                      <div className="text-xs text-gray-500 italic mt-1 pt-2 border-t border-gray-700">
                        💡 {decision.reasoning}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-gray-500 text-center py-8">No decisions yet</div>
              )}
                </div>
              </div>

              {/* Right: Claude AI Strategic Reviews */}
              <div>
                <h3 className="text-sm font-semibold text-purple-400 mb-3 uppercase tracking-wide">🤖 AI Strategic Reviews</h3>
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {claudeReviews.length > 0 ? (
                    claudeReviews.map((review, idx) => (
                      <div key={idx} className="bg-black/30 rounded p-3 border-l-2 border-purple-500/50">
                        <div className="flex justify-between items-start mb-2">
                          <span className="font-semibold text-purple-300 text-sm">{review.decision}</span>
                          <span className="text-xs text-gray-600">
                            {new Date(review.timestamp).toLocaleTimeString('en-US', {
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </span>
                        </div>
                        <div className="text-xs text-gray-300 leading-relaxed">
                          {review.reasoning}
                        </div>
                        <div className="text-xs text-purple-400 mt-2 font-semibold">
                          Confidence: {(review.confidence * 100).toFixed(0)}%
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-gray-500 text-center py-4 text-xs">No AI reviews yet</div>
                  )}
                </div>
              </div>

            </div>
          </div>

          {/* Right Column: Performance + Live Analysis */}
          <div className="space-y-6">
            {/* Performance Metrics - Compact */}
            <div className="glass-advanced rounded-xl p-4">
              <h2 className="text-lg font-semibold text-orange-400 mb-3">🏆 Performance</h2>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Trades:</span>
                  <span className="font-bold text-white">
                    {decisions.filter(d => (d.action === 'ENTRY' || d.action === 'SCALE_IN') && d.timestamp >= '2025-10-29T17:48:00').length}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">P&L:</span>
                  <span className={`font-bold ${leveragedPnlPercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {leveragedPnlPercent >= 0 ? '+' : ''}{leveragedPnlPercent.toFixed(2)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Status:</span>
                  <span className="text-green-400 text-xs">🟢 Running</span>
                </div>
              </div>
            </div>

            {/* Live Analysis - Real-time bot thinking */}
            <div className="glass-advanced rounded-xl p-4">
              <h2 className="text-lg font-semibold text-orange-400 mb-3">🧠 Live Analysis</h2>
              <div className="space-y-3 text-xs">
                <div>
                  <div className="text-gray-500 uppercase tracking-wide mb-1">Market Sentiment</div>
                  <div className="space-y-1">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Fear & Greed:</span>
                      <span className={`font-semibold ${liveAnalysis.fear_greed < 25 ? 'text-red-400' : liveAnalysis.fear_greed < 40 ? 'text-yellow-400' : 'text-green-400'}`}>
                        {liveAnalysis.fear_greed} {liveAnalysis.fear_greed < 40 ? '(Fear)' : '(Greed)'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Funding Rate:</span>
                      <span className={`font-semibold ${liveAnalysis.funding_rate < 0 ? 'text-blue-400' : 'text-orange-400'}`}>
                        {liveAnalysis.funding_rate.toFixed(4)} {liveAnalysis.funding_rate < 0 ? '(Neg)' : '(Pos)'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">L/S Ratio:</span>
                      <span className="text-white font-semibold">
                        {liveAnalysis.ls_ratio.toFixed(2)} {liveAnalysis.ls_ratio > 1.5 ? '(Bullish)' : '(Neutral)'}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="pt-2 border-t border-white/10">
                  <div className="text-gray-500 uppercase tracking-wide mb-1">Bot Decision</div>
                  <div className="text-gray-300 italic text-xs">
                    {liveAnalysis.bot_decision}
                  </div>
                </div>

                <div className="pt-2 border-t border-white/10">
                  <div className="text-gray-500 uppercase tracking-wide mb-1">Next Action</div>
                  <div className="space-y-1">
                    <div className="text-blue-400">↗ ${liveAnalysis.upper_exit.toLocaleString()}: Take 50% (Fib)</div>
                    {position && (
                      <>
                        <div className="text-green-400">↗ ${(position.position.average_price * 1.06).toLocaleString()}: Take 25% (+6%)</div>
                        <div className="text-yellow-400">↘ $106,647: Scale-in #3</div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* About Section */}
        <div className="glass-advanced rounded-xl p-4 md:p-6">
          <h2 className="text-xl md:text-2xl font-semibold text-orange-400 mb-4 md:mb-6">📖 About The Unexpected Trader</h2>

          {/* Vision */}
          <div className="prose prose-invert max-w-none mb-4 md:mb-6">
            <h3 className="text-lg md:text-xl text-orange-300 font-semibold mb-2 md:mb-3">Project Vision</h3>
            <p className="text-sm md:text-base text-gray-300 leading-relaxed mb-3">
              My goal creating this bot is to demonstrate what can be done without writing a single line of code by hand. I acted as
              project manager and creative director, while Claude executed the vision. The trade strategy and algorithm was designed
              and tested through natural language collaboration with AI.
            </p>
            <p className="text-sm md:text-base text-gray-300 leading-relaxed mb-3">
              I wanted a "less is more" approach. Rather than battling it out with the market through scalping, I modeled the strategy
              after my own manual trading methodology—targeting high-conviction, mid-to-long term plays with patience and discipline.
            </p>
            <p className="text-sm md:text-base text-gray-300 leading-relaxed">
              I decided to focus only on BTC as it is the most liquid and most traded asset on the market. Staying highly focused on one
              currency allows easier tracking, monitoring and specialization of the trade strategy rather than a scattergun approach.
            </p>
          </div>

          {/* The Hybrid Approach */}
          <div className="prose prose-invert max-w-none mb-4 md:mb-6">
            <h3 className="text-lg md:text-xl text-orange-300 font-semibold mb-2 md:mb-3">How It Works: Algorithm + AI Supervision</h3>
            <p className="text-sm md:text-base text-gray-300 leading-relaxed mb-4">
              The system combines algorithmic precision with AI judgment through a two-layer architecture. The core algorithm continuously
              monitors Bitcoin price action, specifically targeting the Fibonacci "golden pocket" (61.8%-65% retracement zone), a historically
              significant support level where institutional buying often occurs. When technical setups emerge, Claude AI evaluates market
              conditions using real-time sentiment data from CoinGlass (Fear & Greed Index, funding rates, long/short ratios) and order
              book dynamics from Aster API.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6 mt-4">
              {/* Trading Framework */}
              <div className="bg-black/30 rounded-lg p-4 md:p-5 border border-orange-500/20">
                <h4 className="text-base md:text-lg text-orange-300 font-semibold mb-2 md:mb-3 flex items-center gap-2">
                  <span>⚙️</span> Trading Framework
                </h4>
                <div className="space-y-2 md:space-y-3 text-xs md:text-sm text-gray-300">
                  <div>
                    <span className="text-orange-400 font-semibold">Entry:</span> Fibonacci golden pocket (61.8-65%) with 2+ confluence
                    factors—sentiment extremes, negative funding, bounce confirmation.
                  </div>
                  <div>
                    <span className="text-orange-400 font-semibold">Scaling:</span> Conviction-based accumulation at -1%, -2%, -4%, -6%
                    with increasing leverage (3x→5x), lowering average entry instead of panic exits.
                  </div>
                  <div>
                    <span className="text-orange-400 font-semibold">Exits:</span> Systematic profit-taking at +5%, +10%, +15% from
                    average entry, with full exit on structural invalidation.
                  </div>
                </div>
              </div>

              {/* AI Authority & Boundaries */}
              <div className="bg-black/30 rounded-lg p-4 md:p-5 border border-purple-500/20">
                <h4 className="text-base md:text-lg text-purple-300 font-semibold mb-2 md:mb-3 flex items-center gap-2">
                  <span>🤖</span> Claude's Authority & Boundaries
                </h4>
                <div className="space-y-2 md:space-y-3 text-xs md:text-sm text-gray-300">
                  <div>
                    <span className="text-purple-400 font-semibold">Full Authority:</span> Entry approval (25-75% sizing based on conviction),
                    exit decisions at Fibonacci resistance levels, emergency exits on fundamental invalidation.
                  </div>
                  <div>
                    <span className="text-purple-400 font-semibold">Strategic Reviews:</span> Every 20 minutes, Claude can add up to 5%
                    more capital if at key Fibonacci levels (max 3 adjustments/day).
                  </div>
                  <div>
                    <span className="text-purple-400 font-semibold">Hard Limits:</span> 8 safety rules enforced—5x max leverage, 30%
                    liquidation buffer, cannot reduce while in loss except for invalidation of the trade, 6% liquid reserve always maintained.
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* What Makes It Unique */}
          <div className="prose prose-invert max-w-none">
            <h3 className="text-lg md:text-xl text-orange-300 font-semibold mb-2 md:mb-3">What Makes This Unique</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-4">
              <div className="bg-gradient-to-br from-orange-900/20 to-black/30 rounded-lg p-4 border border-orange-500/30">
                <div className="text-2xl mb-2">💭</div>
                <h4 className="text-orange-300 font-semibold mb-2">No-Code Development</h4>
                <p className="text-xs text-gray-400">
                  Entire system built through conversation with Claude Code—strategy design through natural language collaboration.
                </p>
              </div>
              <div className="bg-gradient-to-br from-purple-900/20 to-black/30 rounded-lg p-4 border border-purple-500/30">
                <div className="text-2xl mb-2">🧠</div>
                <h4 className="text-purple-300 font-semibold mb-2">True AI Autonomy</h4>
                <p className="text-xs text-gray-400">
                  Claude makes strategic decisions 24/7 using live market sentiment, not just executing pre-programmed rules.
                </p>
              </div>
              <div className="bg-gradient-to-br from-blue-900/20 to-black/30 rounded-lg p-4 border border-blue-500/30">
                <div className="text-2xl mb-2">🔍</div>
                <h4 className="text-blue-300 font-semibold mb-2">Complete Transparency</h4>
                <p className="text-xs text-gray-400">
                  Every decision logged with full reasoning—see exactly why the AI chose to enter, hold, or exit.
                </p>
              </div>
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}
