import { useQuery } from '@tanstack/react-query';
import {
  Loader2,
  BarChart3,
  ThumbsUp,
  ThumbsDown,
  Heart,
  Target,
  TrendingUp,
  Lightbulb,
  ShieldX,
  Megaphone,
  Zap,
  Check,
} from 'lucide-react';
import { getSentimentAnalysis } from '../api/client';
import type { Insight } from '../api/client';

export default function SentimentView({ sessionId, insights }: { sessionId: number; insights?: Insight }) {
  const { data: sentiment, isLoading } = useQuery({
    queryKey: ['sentiment', sessionId],
    queryFn: () => getSentimentAnalysis(sessionId),
  });

  const crossSource = insights?.cross_source_insights;

  return (
    <div className="space-y-8">
      {/* === Cross-Source Insights === */}
      {crossSource && (
        <>
          <div>
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <span className="text-emerald-400">🔗</span> Cross-Source Validated Insights
            </h2>
            <p className="text-sm text-slate-400 mb-4">Pain points and themes confirmed across multiple data sources. Higher confidence = appears in more platforms.</p>
          </div>

          {/* AI-Validated Pain Points */}
          {crossSource.ai_validated_pain_points && crossSource.ai_validated_pain_points.length > 0 && (
            <div className="glass-card p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Target className="w-5 h-5 text-red-400" /> Validated Pain Points
              </h3>
              <div className="space-y-3">
                {crossSource.ai_validated_pain_points.map((pp: any, i: number) => (
                  <div key={i} className="bg-slate-800/50 rounded-lg p-4">
                    <div className="flex items-start justify-between mb-2">
                      <p className="text-white font-medium flex-1">{pp.pain_point || pp}</p>
                      {pp.confidence && (
                        <span className={`text-xs px-2 py-1 rounded-full ml-2 shrink-0 ${pp.confidence > 0.8 ? 'bg-red-500/20 text-red-400' :
                            pp.confidence > 0.5 ? 'bg-yellow-500/20 text-yellow-400' :
                              'bg-slate-500/20 text-slate-400'
                          }`}>
                          {(pp.confidence * 100).toFixed(0)}% confidence
                        </span>
                      )}
                    </div>
                    {pp.sources && (
                      <div className="flex gap-1 flex-wrap">
                        {pp.sources.map((s: string, j: number) => (
                          <span key={j} className="text-xs bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded">{s}</span>
                        ))}
                      </div>
                    )}
                    {pp.evidence && <p className="text-xs text-slate-400 mt-2 italic">"{pp.evidence}"</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Universal Themes + Strategic Recs side by side */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {crossSource.universal_themes && crossSource.universal_themes.length > 0 && (
              <div className="glass-card p-6">
                <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-purple-400" /> Universal Themes
                </h3>
                <div className="space-y-2">
                  {crossSource.universal_themes.map((t: any, i: number) => (
                    <div key={i} className="flex items-center justify-between bg-slate-800/50 rounded p-3">
                      <span className="text-white">{t.theme || t}</span>
                      {t.sources && (
                        <span className="text-xs text-slate-400">{t.sources.length} sources</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {crossSource.strategic_recommendations && crossSource.strategic_recommendations.length > 0 && (
              <div className="glass-card p-6">
                <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                  <Lightbulb className="w-5 h-5 text-yellow-400" /> Strategic Recommendations
                </h3>
                <ol className="space-y-2 list-decimal list-inside">
                  {crossSource.strategic_recommendations.map((r: string, i: number) => (
                    <li key={i} className="text-slate-300 text-sm">{r}</li>
                  ))}
                </ol>
              </div>
            )}
          </div>

          {/* Messaging Gaps + Ad Angle Suggestions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {crossSource.messaging_gaps && crossSource.messaging_gaps.length > 0 && (
              <div className="glass-card p-6">
                <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                  <ShieldX className="w-5 h-5 text-orange-400" /> Messaging Gaps
                </h3>
                <div className="space-y-2">
                  {crossSource.messaging_gaps.map((g: any, i: number) => (
                    <div key={i} className="bg-orange-500/10 border border-orange-500/20 rounded p-3">
                      <p className="text-white text-sm font-medium">{g.gap || g}</p>
                      {g.evidence && <p className="text-xs text-slate-400 mt-1">{g.evidence}</p>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {crossSource.ad_angle_suggestions && crossSource.ad_angle_suggestions.length > 0 && (
              <div className="glass-card p-6">
                <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                  <Megaphone className="w-5 h-5 text-cyan-400" /> Suggested Ad Angles
                </h3>
                <div className="space-y-2">
                  {crossSource.ad_angle_suggestions.map((a: string, i: number) => (
                    <div key={i} className="bg-cyan-500/10 border border-cyan-500/20 rounded p-3">
                      <p className="text-white text-sm">{a}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Key Opportunities */}
          {crossSource.key_opportunities && crossSource.key_opportunities.length > 0 && (
            <div className="glass-card p-6">
              <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                <Zap className="w-5 h-5 text-green-400" /> Key Opportunities
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {crossSource.key_opportunities.map((o: string, i: number) => (
                  <div key={i} className="bg-green-500/10 border border-green-500/20 rounded p-3 flex items-start gap-2">
                    <Check className="w-4 h-4 text-green-400 mt-0.5 shrink-0" />
                    <p className="text-white text-sm">{o}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* === Sentiment Analysis === */}
      <div>
        <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <span className="text-blue-400">📊</span> Sentiment Analysis (RoBERTa ML)
        </h2>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
          <span className="ml-2 text-slate-400">Loading sentiment data...</span>
        </div>
      ) : sentiment && sentiment.total > 0 ? (
        <div className="space-y-6">
          {/* Overall Sentiment */}
          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Overall Sentiment Distribution</h3>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="text-center p-4 bg-green-500/10 border border-green-500/20 rounded-lg">
                <ThumbsUp className="w-6 h-6 text-green-400 mx-auto mb-2" />
                <p className="text-2xl font-bold text-green-400">{sentiment.overall_pct?.positive || 0}%</p>
                <p className="text-xs text-slate-400">Positive ({sentiment.overall?.positive || 0})</p>
              </div>
              <div className="text-center p-4 bg-slate-500/10 border border-slate-500/20 rounded-lg">
                <Heart className="w-6 h-6 text-slate-400 mx-auto mb-2" />
                <p className="text-2xl font-bold text-slate-300">{sentiment.overall_pct?.neutral || 0}%</p>
                <p className="text-xs text-slate-400">Neutral ({sentiment.overall?.neutral || 0})</p>
              </div>
              <div className="text-center p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                <ThumbsDown className="w-6 h-6 text-red-400 mx-auto mb-2" />
                <p className="text-2xl font-bold text-red-400">{sentiment.overall_pct?.negative || 0}%</p>
                <p className="text-xs text-slate-400">Negative ({sentiment.overall?.negative || 0})</p>
              </div>
            </div>
            {/* Visual bar */}
            <div className="w-full h-4 rounded-full overflow-hidden flex bg-slate-800">
              <div className="bg-green-500 h-full transition-all" style={{ width: `${sentiment.overall_pct?.positive || 0}%` }} />
              <div className="bg-slate-500 h-full transition-all" style={{ width: `${sentiment.overall_pct?.neutral || 0}%` }} />
              <div className="bg-red-500 h-full transition-all" style={{ width: `${sentiment.overall_pct?.negative || 0}%` }} />
            </div>
            <p className="text-xs text-slate-500 mt-2">Analyzed by {sentiment.model} • {sentiment.total} data points</p>
          </div>

          {/* By Source Breakdown */}
          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Sentiment by Source</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-2 text-slate-400 font-medium">Source</th>
                    <th className="text-right py-2 text-slate-400 font-medium">Total</th>
                    <th className="text-right py-2 text-green-400 font-medium">Positive</th>
                    <th className="text-right py-2 text-slate-400 font-medium">Neutral</th>
                    <th className="text-right py-2 text-red-400 font-medium">Negative</th>
                    <th className="text-right py-2 text-slate-400 font-medium">Avg Score</th>
                    <th className="py-2 text-slate-400 font-medium w-32">Distribution</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(sentiment.by_source)
                    .sort(([, a], [, b]) => b.total - a.total)
                    .map(([source, stats]) => {
                      const posPct = stats.total > 0 ? (stats.positive / stats.total * 100) : 0;
                      const neuPct = stats.total > 0 ? (stats.neutral / stats.total * 100) : 0;
                      const negPct = stats.total > 0 ? (stats.negative / stats.total * 100) : 0;
                      return (
                        <tr key={source} className="border-b border-slate-800 hover:bg-slate-800/50">
                          <td className="py-2 text-white capitalize">{source.replace(/_/g, ' ')}</td>
                          <td className="text-right py-2 text-slate-300">{stats.total}</td>
                          <td className="text-right py-2 text-green-400">{stats.positive}</td>
                          <td className="text-right py-2 text-slate-400">{stats.neutral}</td>
                          <td className="text-right py-2 text-red-400">{stats.negative}</td>
                          <td className={`text-right py-2 font-mono ${stats.avg_score > 0 ? 'text-green-400' : stats.avg_score < 0 ? 'text-red-400' : 'text-slate-400'}`}>
                            {stats.avg_score > 0 ? '+' : ''}{stats.avg_score.toFixed(3)}
                          </td>
                          <td className="py-2">
                            <div className="w-full h-2 rounded-full overflow-hidden flex bg-slate-800">
                              <div className="bg-green-500 h-full" style={{ width: `${posPct}%` }} />
                              <div className="bg-slate-500 h-full" style={{ width: `${neuPct}%` }} />
                              <div className="bg-red-500 h-full" style={{ width: `${negPct}%` }} />
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Top Verbatims */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Top Positive */}
            <div className="glass-card p-6">
              <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                <ThumbsUp className="w-5 h-5 text-green-400" /> Top Positive Verbatims
              </h3>
              <div className="space-y-3">
                {sentiment.top_positive?.slice(0, 5).map((v, i) => (
                  <div key={i} className="bg-green-500/5 border border-green-500/10 rounded p-3">
                    <p className="text-sm text-slate-200 italic">"{v.content}"</p>
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-xs text-slate-500 capitalize">{v.source.replace(/_/g, ' ')}</span>
                      <span className="text-xs text-green-400 font-mono">+{v.score.toFixed(3)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Top Negative */}
            <div className="glass-card p-6">
              <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                <ThumbsDown className="w-5 h-5 text-red-400" /> Top Negative Verbatims
              </h3>
              <div className="space-y-3">
                {sentiment.top_negative?.slice(0, 5).map((v, i) => (
                  <div key={i} className="bg-red-500/5 border border-red-500/10 rounded p-3">
                    <p className="text-sm text-slate-200 italic">"{v.content}"</p>
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-xs text-slate-500 capitalize">{v.source.replace(/_/g, ' ')}</span>
                      <span className="text-xs text-red-400 font-mono">{v.score.toFixed(3)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="card p-8 text-center">
          <BarChart3 className="w-12 h-12 text-slate-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">No Sentiment Data</h3>
          <p className="text-slate-400">Run a research session to generate sentiment analysis.</p>
        </div>
      )}
    </div>
  );
}
