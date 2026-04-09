import { useState } from 'react';
import {
  Target,
  ThumbsUp,
  ThumbsDown,
  Users,
  AlertTriangle,
  MessageSquare,
  Heart,
  Zap,
  TrendingUp,
  Star,
  Quote,
  ShieldX,
  Lightbulb,
  DollarSign,
  Megaphone,
  ChevronUp,
  ChevronDown,
} from 'lucide-react';
import type { Insight } from '../api/client';

function CollapsibleCard({
  title,
  icon,
  items,
  isQuote = false
}: {
  title: string;
  icon: React.ReactNode;
  items?: string[];
  isQuote?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(true);

  if (!items || items.length === 0) return null;

  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 hover:bg-slate-800/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="font-medium text-white">{title}</span>
          <span className="text-xs text-slate-500">({items.length})</span>
        </div>
        {isOpen ? (
          <ChevronUp className="w-4 h-4 text-slate-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-400" />
        )}
      </button>

      {isOpen && (
        <div className="px-4 pb-4">
          <ul className="space-y-2">
            {items.map((item, i) => (
              <li key={i} className={`text-sm ${isQuote ? 'text-slate-400 italic' : 'text-slate-300'}`}>
                {isQuote ? `"${item}"` : `• ${item}`}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function InsightsView({ insights }: { insights: Insight }) {
  return (
    <div className="grid gap-6">
      {/* Brand Summary */}
      {insights.brand_summary && (
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-3">Brand Summary</h3>
          <p className="text-slate-300">{insights.brand_summary}</p>
        </div>
      )}

      {/* Proto-ICPs - Recommended Customer Segments */}
      {(insights as any).proto_icp_recommendations && (insights as any).proto_icp_recommendations.length > 0 && (
        <div className="glass-card p-6 border-l-4 border-yellow-500">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-yellow-400" />
            🎯 Recommended Proto-ICPs
            <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded-full ml-2">
              {(insights as any).proto_icp_stats?.total_clusters || 0} clusters found
            </span>
          </h3>
          <div className="grid gap-4">
            {(insights as any).proto_icp_recommendations.slice(0, 3).map((rec: any, i: number) => {
              const cluster = rec.cluster;
              return (
                <div key={i} className="bg-slate-800/50 p-4 rounded-lg border border-slate-700 hover:border-yellow-500/50 transition-colors">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-yellow-400 font-bold">{cluster.cluster_id}</span>
                        <span className="text-slate-400 text-sm">Score: {rec.score}</span>
                      </div>
                      <div className="flex gap-2 mt-1">
                        <span className="tag bg-indigo-500/20 text-indigo-300">{cluster.trigger_label}</span>
                        <span className="text-slate-500">×</span>
                        <span className="tag bg-red-500/20 text-red-300">{cluster.blocker_label}</span>
                      </div>
                    </div>
                    <span className="text-xs text-slate-500">{cluster.snippet_count} snippets</span>
                  </div>

                  {/* Language Cues */}
                  {cluster.top_phrases && cluster.top_phrases.length > 0 && (
                    <div className="mb-3">
                      <span className="text-xs text-slate-500 uppercase">Language Cues:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {cluster.top_phrases.slice(0, 5).map((phrase: string, j: number) => (
                          <span key={j} className="text-xs bg-slate-700/50 text-slate-300 px-2 py-0.5 rounded">
                            "{phrase}"
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Representative Snippet */}
                  {cluster.representative_snippets && cluster.representative_snippets.length > 0 && (
                    <div className="bg-slate-900/50 p-3 rounded border-l-2 border-indigo-500">
                      <p className="text-slate-300 text-sm italic">
                        "{cluster.representative_snippets[0].content?.slice(0, 150)}..."
                      </p>
                      {cluster.representative_snippets[0].source_url && (
                        <a
                          href={cluster.representative_snippets[0].source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-indigo-400 hover:text-indigo-300 mt-1 inline-block"
                        >
                          View source →
                        </a>
                      )}
                    </div>
                  )}

                  <p className="text-xs text-slate-500 mt-2">{rec.rationale}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Two Column Layout */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Track 1: Brand Mentions */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-indigo-400 uppercase tracking-wider">
            Track 1: Brand Mentions
          </h3>

          <CollapsibleCard
            title="What People Love"
            icon={<ThumbsUp className="w-4 h-4 text-green-400" />}
            items={insights.top_positives}
          />

          <CollapsibleCard
            title="Common Concerns"
            icon={<ThumbsDown className="w-4 h-4 text-red-400" />}
            items={insights.top_negatives}
          />

          <CollapsibleCard
            title="Competitors Mentioned"
            icon={<Users className="w-4 h-4 text-slate-400" />}
            items={insights.competitors_mentioned}
          />
        </div>

        {/* Track 2: Segment Research */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-purple-400 uppercase tracking-wider">
            Track 2: Segment Research
          </h3>

          <CollapsibleCard
            title="Market Pain Points"
            icon={<AlertTriangle className="w-4 h-4 text-orange-400" />}
            items={insights.market_pain_points}
          />

          <CollapsibleCard
            title="Customer Language"
            icon={<MessageSquare className="w-4 h-4 text-blue-400" />}
            items={insights.customer_language}
            isQuote
          />

          <CollapsibleCard
            title="What Customers Want"
            icon={<Heart className="w-4 h-4 text-pink-400" />}
            items={insights.customer_desires}
          />
        </div>
      </div>

      {/* Verbatim Quotes - Real Customer Voice */}
      {(insights as any).verbatim_quotes && (insights as any).verbatim_quotes.length > 0 && (
        <div className="glass-card p-6 border-l-4 border-indigo-500">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-indigo-400" />
            Real Customer Voice - Verbatim Quotes
          </h3>
          <div className="space-y-4">
            {(insights as any).verbatim_quotes.slice(0, 8).map((quote: any, i: number) => (
              <div key={i} className="bg-slate-800/30 p-4 rounded-lg border-l-2 border-slate-600 hover:border-indigo-400 transition-colors">
                <p className="text-slate-300 italic mb-2">
                  "{typeof quote === 'string' ? quote : quote.text || quote.quote}"
                </p>
                {typeof quote === 'object' && (quote.source || quote.platform) && (
                  <div className="flex items-center gap-2 text-xs">
                    <span className="tag bg-slate-700/50 text-slate-400">
                      {quote.platform || quote.source_type || 'User'}
                    </span>
                    {quote.author && (
                      <span className="text-slate-500">— {quote.author}</span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Creative Dimensions */}
      <div className="space-y-6">
        <h3 className="text-xl font-display font-semibold text-white">Creative Dimensions</h3>

        {/* ICPs */}
        {insights.icps && insights.icps.length > 0 && (
          <div className="glass-card p-6">
            <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Users className="w-5 h-5 text-purple-400" />
              Ideal Customer Profiles
            </h4>
            <div className="grid md:grid-cols-2 gap-4">
              {insights.icps.map((icp, i) => (
                <div key={i} className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                  <h5 className="font-semibold text-purple-300 mb-2">{icp.name}</h5>
                  <p className="text-sm text-slate-400 mb-2">{icp.description}</p>
                  {icp.age_range && (
                    <span className="text-xs text-slate-500">Age: {icp.age_range}</span>
                  )}
                  {icp.characteristics && icp.characteristics.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {icp.characteristics.map((c, j) => (
                        <span key={j} className="tag-primary text-xs">{c}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Pain Points & Value Props */}
        <div className="grid md:grid-cols-2 gap-6">
          <div className="glass-card p-6">
            <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-orange-400" />
              Pain Points (for Ads)
            </h4>
            <ul className="space-y-2">
              {insights.pain_points?.map((p, i) => (
                <li key={i} className="flex items-start gap-2 text-slate-300">
                  <span className="text-orange-400 mt-1">•</span>
                  {p}
                </li>
              ))}
            </ul>
          </div>

          <div className="glass-card p-6">
            <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Zap className="w-5 h-5 text-green-400" />
              Value Props (to Highlight)
            </h4>
            <ul className="space-y-2">
              {insights.value_props?.map((v, i) => (
                <li key={i} className="flex items-start gap-2 text-slate-300">
                  <span className="text-green-400 mt-1">•</span>
                  {v}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Messaging Angles */}
        {insights.messaging_angles && insights.messaging_angles.length > 0 && (
          <div className="glass-card p-6">
            <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-indigo-400" />
              Messaging Angles
            </h4>
            <div className="grid gap-4">
              {insights.messaging_angles.map((angle, i) => (
                <div key={i} className="bg-indigo-500/10 rounded-xl p-4 border border-indigo-500/20">
                  <h5 className="font-semibold text-indigo-300 mb-1">{angle.name}</h5>
                  <p className="text-white font-medium mb-2">"{angle.hook}"</p>
                  <p className="text-sm text-slate-400">{angle.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tone & Content Insights */}
        <div className="grid md:grid-cols-2 gap-6">
          {insights.tone_emotions && insights.tone_emotions.length > 0 && (
            <div className="glass-card p-6">
              <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Heart className="w-5 h-5 text-pink-400" />
                Tone / Emotion Journey
              </h4>
              <div className="flex flex-wrap gap-2">
                {insights.tone_emotions.map((t, i) => (
                  <span key={i} className="tag bg-pink-500/20 text-pink-300">{t}</span>
                ))}
              </div>
            </div>
          )}

          {insights.content_insights && insights.content_insights.length > 0 && (
            <div className="glass-card p-6">
              <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Star className="w-5 h-5 text-yellow-400" />
                Content Insights (TikTok/IG)
              </h4>
              <ul className="space-y-2">
                {insights.content_insights.map((c, i) => (
                  <li key={i} className="flex items-start gap-2 text-slate-300">
                    <span className="text-yellow-400 mt-1">•</span>
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* NEW: Enhanced Insights Section */}
        <h3 className="text-xl font-display font-semibold text-white mt-8">Deep Insights</h3>

        {/* Competitor Analysis */}
        {insights.competitor_analysis && Object.keys(insights.competitor_analysis).length > 0 && (
          <div className="glass-card p-6 border-l-4 border-cyan-500">
            <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-cyan-400" />
              Competitor Analysis
            </h4>
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <h5 className="text-sm font-medium text-cyan-400 mb-2">Our Advantages</h5>
                <ul className="space-y-1">
                  {(insights.competitor_analysis as any)?.our_advantages?.map((item: string, i: number) => (
                    <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                      <span className="text-green-400">+</span> {item}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h5 className="text-sm font-medium text-cyan-400 mb-2">Their Advantages</h5>
                <ul className="space-y-1">
                  {(insights.competitor_analysis as any)?.their_advantages?.map((item: string, i: number) => (
                    <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                      <span className="text-red-400">-</span> {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            {(insights.competitor_analysis as any)?.positioning_opportunity && (
              <div className="mt-4 p-3 bg-cyan-500/10 rounded-lg border border-cyan-500/20">
                <p className="text-sm text-cyan-300">
                  <strong>Positioning Opportunity:</strong> {(insights.competitor_analysis as any).positioning_opportunity}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Purchase Triggers & Objections */}
        <div className="grid md:grid-cols-2 gap-6">
          {insights.purchase_triggers && insights.purchase_triggers.length > 0 && (
            <div className="glass-card p-6">
              <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Lightbulb className="w-5 h-5 text-amber-400" />
                Purchase Triggers
              </h4>
              <ul className="space-y-2">
                {insights.purchase_triggers.map((trigger, i) => (
                  <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                    <span className="text-amber-400 mt-1">*</span> {trigger}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {insights.objections && insights.objections.length > 0 && (
            <div className="glass-card p-6">
              <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <ShieldX className="w-5 h-5 text-red-400" />
                Objections to Address
              </h4>
              <div className="space-y-3">
                {insights.objections.map((obj, i) => (
                  <div key={i} className="bg-red-500/10 rounded-lg p-3 border border-red-500/20">
                    <p className="text-sm font-medium text-red-300">
                      {typeof obj === 'string' ? obj : (obj as any).objection}
                    </p>
                    {typeof obj !== 'string' && (obj as any).counter_messaging && (
                      <p className="text-xs text-slate-400 mt-1">
                        Counter: {(obj as any).counter_messaging}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Verbatim Quotes */}
        {insights.verbatim_quotes && insights.verbatim_quotes.length > 0 && (
          <div className="glass-card p-6 bg-gradient-to-br from-slate-900/80 to-indigo-900/20">
            <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Quote className="w-5 h-5 text-indigo-400" />
              Verbatim Quotes (for Ads)
            </h4>
            <div className="grid gap-4">
              {insights.verbatim_quotes.map((q, i) => (
                <blockquote key={i} className="border-l-2 border-indigo-500 pl-4 py-2">
                  <p className="text-white italic">
                    "{typeof q === 'string' ? q : (q as any).quote}"
                  </p>
                  {typeof q !== 'string' && (
                    <>
                      {(q as any).context && (
                        <p className="text-xs text-slate-500 mt-1">Context: {(q as any).context}</p>
                      )}
                      {(q as any).use_case && (
                        <p className="text-xs text-indigo-400 mt-1">Use: {(q as any).use_case}</p>
                      )}
                    </>
                  )}
                </blockquote>
              ))}
            </div>
          </div>
        )}

        {/* Recommended Hooks */}
        {insights.recommended_hooks && insights.recommended_hooks.length > 0 && (
          <div className="glass-card p-6 border-l-4 border-green-500">
            <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Megaphone className="w-5 h-5 text-green-400" />
              Recommended Hooks
            </h4>
            <div className="grid md:grid-cols-2 gap-4">
              {insights.recommended_hooks.map((hook, i) => (
                <div key={i} className="bg-green-500/10 rounded-xl p-4 border border-green-500/20">
                  <p className="font-medium text-green-300 text-lg mb-2">
                    "{typeof hook === 'string' ? hook : (hook as any).hook}"
                  </p>
                  {typeof hook !== 'string' && (
                    <>
                      <span className="tag bg-green-500/20 text-green-400 text-xs">
                        {(hook as any).type}
                      </span>
                      {(hook as any).reasoning && (
                        <p className="text-xs text-slate-400 mt-2">{(hook as any).reasoning}</p>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Price Sensitivity & Content Opportunities */}
        <div className="grid md:grid-cols-2 gap-6">
          {insights.price_sensitivity && Object.keys(insights.price_sensitivity).length > 0 && (
            <div className="glass-card p-6">
              <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-emerald-400" />
                Price Sensitivity
              </h4>
              <div className="space-y-2">
                <p className="text-sm text-slate-300">
                  <strong>Overall:</strong>{' '}
                  <span className={`${(insights.price_sensitivity as any)?.overall_sensitivity === 'high'
                    ? 'text-red-400'
                    : (insights.price_sensitivity as any)?.overall_sensitivity === 'low'
                      ? 'text-green-400'
                      : 'text-yellow-400'
                    }`}>
                    {(insights.price_sensitivity as any)?.overall_sensitivity || 'Unknown'}
                  </span>
                </p>
                {(insights.price_sensitivity as any)?.value_perception && (
                  <p className="text-sm text-slate-400">
                    Value Perception: {(insights.price_sensitivity as any).value_perception}
                  </p>
                )}
              </div>
            </div>
          )}

          {insights.content_opportunities && insights.content_opportunities.length > 0 && (
            <div className="glass-card p-6">
              <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Lightbulb className="w-5 h-5 text-yellow-400" />
                Content Opportunities
              </h4>
              <ul className="space-y-2">
                {insights.content_opportunities.map((opp, i) => (
                  <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                    <span className="text-yellow-400 mt-1">*</span> {opp}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Feature Requests */}
        {insights.feature_requests && insights.feature_requests.length > 0 && (
          <div className="glass-card p-6">
            <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-blue-400" />
              Feature Requests (What Users Want)
            </h4>
            <div className="flex flex-wrap gap-2">
              {insights.feature_requests.map((req, i) => (
                <span key={i} className="tag bg-blue-500/20 text-blue-300">{req}</span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
