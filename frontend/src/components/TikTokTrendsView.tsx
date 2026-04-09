import { useState } from 'react';
import {
  Music,
  Hash,
  TrendingUp,
  Clock,
  BarChart3,
  Lightbulb,
  Play,
  ChevronDown,
  ChevronUp,
  Flame,
  Target
} from 'lucide-react';
import type { TikTokTrends, TrendingSound, TrendingHashtag } from '../api/client';

interface TikTokTrendsViewProps {
  trends: TikTokTrends;
}

export default function TikTokTrendsView({ trends }: TikTokTrendsViewProps) {
  const [expandedSection, setExpandedSection] = useState<string | null>('sounds');

  if (trends.status !== 'success' || trends.videos_analyzed < 5) {
    return (
      <div className="card p-8 text-center">
        <TrendingUp className="w-12 h-12 text-slate-500 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-white mb-2">Insufficient TikTok Data</h3>
        <p className="text-slate-400">
          Need at least 5 TikTok videos to analyze trends.
          Currently analyzed: {trends.videos_analyzed || 0} videos.
        </p>
      </div>
    );
  }

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={<Play className="w-5 h-5" />}
          label="Videos Analyzed"
          value={trends.videos_analyzed.toString()}
          color="purple"
        />
        <StatCard
          icon={<Music className="w-5 h-5" />}
          label="Trending Sounds"
          value={trends.trending_sounds?.length.toString() || '0'}
          color="pink"
        />
        <StatCard
          icon={<Hash className="w-5 h-5" />}
          label="Trending Hashtags"
          value={trends.trending_hashtags?.length.toString() || '0'}
          color="blue"
        />
        <StatCard
          icon={<Flame className="w-5 h-5" />}
          label="Avg Engagement"
          value={formatNumber(trends.engagement_benchmarks?.likes?.avg || 0)}
          color="orange"
        />
      </div>

      {/* Recommendations */}
      {trends.recommendations && trends.recommendations.length > 0 && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-yellow-400" />
            Actionable Recommendations
          </h3>
          <div className="grid gap-3">
            {trends.recommendations.map((rec, idx) => (
              <div key={idx} className="bg-slate-800/50 rounded-lg p-4 border-l-4 border-yellow-500">
                <div className="flex items-start gap-3">
                  <span className="tag-primary text-xs">{rec.type}</span>
                  <div>
                    <p className="text-white font-medium">{rec.action}</p>
                    <p className="text-slate-400 text-sm mt-1">{rec.rationale}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Trending Sounds */}
      <CollapsibleSection
        title="Trending Sounds"
        icon={<Music className="w-5 h-5 text-pink-400" />}
        count={trends.trending_sounds?.length || 0}
        expanded={expandedSection === 'sounds'}
        onToggle={() => toggleSection('sounds')}
      >
        <div className="grid gap-3">
          {trends.trending_sounds?.slice(0, 15).map((sound, idx) => (
            <SoundCard key={idx} sound={sound} rank={idx + 1} />
          ))}
        </div>
      </CollapsibleSection>

      {/* Trending Hashtags */}
      <CollapsibleSection
        title="Trending Hashtags"
        icon={<Hash className="w-5 h-5 text-blue-400" />}
        count={trends.trending_hashtags?.length || 0}
        expanded={expandedSection === 'hashtags'}
        onToggle={() => toggleSection('hashtags')}
      >
        <div className="flex flex-wrap gap-2">
          {trends.trending_hashtags?.slice(0, 30).map((tag, idx) => (
            <HashtagBadge key={idx} hashtag={tag} />
          ))}
        </div>
      </CollapsibleSection>

      {/* Content Patterns */}
      <CollapsibleSection
        title="Content Patterns"
        icon={<BarChart3 className="w-5 h-5 text-green-400" />}
        count={null}
        expanded={expandedSection === 'patterns'}
        onToggle={() => toggleSection('patterns')}
      >
        <div className="grid md:grid-cols-3 gap-6">
          {/* Duration Stats */}
          {trends.content_patterns?.duration_stats && (
            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
                <Clock className="w-4 h-4" /> Video Duration
              </h4>
              <p className="text-2xl font-bold text-white mb-1">
                {trends.content_patterns.duration_stats.most_common_range}
              </p>
              <p className="text-sm text-slate-400">
                Avg: {trends.content_patterns.duration_stats.avg_seconds}s |
                Median: {trends.content_patterns.duration_stats.median_seconds}s
              </p>
              {trends.content_patterns.duration_stats.distribution && (
                <div className="mt-3 space-y-1">
                  {Object.entries(trends.content_patterns.duration_stats.distribution).map(([range, count]) => (
                    <div key={range} className="flex items-center gap-2 text-xs">
                      <span className="text-slate-500 w-20">{formatDurationRange(range)}</span>
                      <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-green-500 rounded-full"
                          style={{ width: `${Math.min(100, (count as number) / trends.videos_analyzed * 100)}%` }}
                        />
                      </div>
                      <span className="text-slate-400 w-8">{count as number}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Popular Formats */}
          {trends.content_patterns?.popular_formats && trends.content_patterns.popular_formats.length > 0 && (
            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
                <Play className="w-4 h-4" /> Popular Formats
              </h4>
              <div className="space-y-2">
                {trends.content_patterns.popular_formats.map((fmt, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <span className="text-white">{fmt.format}</span>
                    <span className="tag-primary">{fmt.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Hook Styles */}
          {trends.content_patterns?.hook_styles && trends.content_patterns.hook_styles.length > 0 && (
            <div className="bg-slate-800/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
                <Target className="w-4 h-4" /> Hook Styles
              </h4>
              <div className="space-y-2">
                {trends.content_patterns.hook_styles.map((style, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <span className="text-white">{style.style}</span>
                    <span className="tag-primary">{style.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </CollapsibleSection>

      {/* Engagement Benchmarks */}
      {trends.engagement_benchmarks && (
        <CollapsibleSection
          title="Engagement Benchmarks"
          icon={<TrendingUp className="w-5 h-5 text-orange-400" />}
          count={null}
          expanded={expandedSection === 'benchmarks'}
          onToggle={() => toggleSection('benchmarks')}
        >
          <div className="grid md:grid-cols-3 gap-4">
            <BenchmarkCard
              title="Likes"
              data={trends.engagement_benchmarks.likes}
            />
            <BenchmarkCard
              title="Comments"
              data={trends.engagement_benchmarks.comments}
            />
            <BenchmarkCard
              title="Shares"
              data={trends.engagement_benchmarks.shares}
            />
          </div>
        </CollapsibleSection>
      )}

      {/* Segment Analysis - Deep insights from video content */}
      {trends.segment_analysis && (
        <CollapsibleSection
          title="Content Deep Dive (LLM Analysis)"
          icon={<Lightbulb className="w-5 h-5 text-cyan-400" />}
          count={null}
          expanded={expandedSection === 'segment'}
          onToggle={() => toggleSection('segment')}
        >
          <div className="grid md:grid-cols-2 gap-6">
            {/* Customer Language Patterns */}
            {trends.segment_analysis.aggregated?.customer_language_patterns && (
              <div className="bg-slate-800/50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
                  💬 Customer Language
                </h4>
                <div className="space-y-3">
                  {trends.segment_analysis.aggregated.customer_language_patterns.common_phrases && (
                    <div>
                      <p className="text-xs text-slate-500 mb-1">Common Phrases</p>
                      <div className="flex flex-wrap gap-1">
                        {(trends.segment_analysis.aggregated.customer_language_patterns.common_phrases as string[]).slice(0, 8).map((phrase: string, idx: number) => (
                          <span key={idx} className="text-xs bg-cyan-500/20 text-cyan-300 px-2 py-1 rounded">
                            "{phrase}"
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {trends.segment_analysis.aggregated.customer_language_patterns.slang && (
                    <div>
                      <p className="text-xs text-slate-500 mb-1">Slang / Informal</p>
                      <div className="flex flex-wrap gap-1">
                        {(trends.segment_analysis.aggregated.customer_language_patterns.slang as string[]).slice(0, 6).map((slang: string, idx: number) => (
                          <span key={idx} className="text-xs bg-pink-500/20 text-pink-300 px-2 py-1 rounded">
                            {slang}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Recommended Hooks */}
            {trends.segment_analysis.aggregated?.recommended_hook_types && (
              <div className="bg-slate-800/50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
                  🎯 Recommended Hooks
                </h4>
                <div className="space-y-2">
                  {(trends.segment_analysis.aggregated.recommended_hook_types as string[]).slice(0, 5).map((hook: string, idx: number) => (
                    <div key={idx} className="flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-yellow-500/20 flex items-center justify-center text-yellow-400 text-xs font-bold">
                        {idx + 1}
                      </span>
                      <span className="text-white text-sm">{hook}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Pain Points from Videos */}
            {trends.segment_analysis.aggregated?.top_pain_points && (
              <div className="bg-slate-800/50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
                  😤 Pain Points (from TikTok)
                </h4>
                <div className="space-y-2">
                  {(trends.segment_analysis.aggregated.top_pain_points as Array<{ pain_point?: string; frequency?: number }>).slice(0, 5).map((pain: { pain_point?: string; frequency?: number }, idx: number) => (
                    <div key={idx} className="flex items-start gap-2 text-sm">
                      <span className="text-red-400">•</span>
                      <span className="text-white">{typeof pain === 'string' ? pain : pain.pain_point}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Trending Formats */}
            {trends.segment_analysis.aggregated?.trending_formats && (
              <div className="bg-slate-800/50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
                  📹 Trending Formats
                </h4>
                <div className="flex flex-wrap gap-2">
                  {(trends.segment_analysis.aggregated.trending_formats as string[]).slice(0, 6).map((format: string, idx: number) => (
                    <span key={idx} className="tag-primary">
                      {format}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </CollapsibleSection>
      )}
    </div>
  );
}

// Sub-components

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string; color: string }) {
  const colors: Record<string, string> = {
    purple: 'bg-purple-500/20 text-purple-400',
    pink: 'bg-pink-500/20 text-pink-400',
    blue: 'bg-blue-500/20 text-blue-400',
    orange: 'bg-orange-500/20 text-orange-400',
    green: 'bg-green-500/20 text-green-400',
  };

  return (
    <div className="card p-4">
      <div className={`w-10 h-10 rounded-lg ${colors[color]} flex items-center justify-center mb-3`}>
        {icon}
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-sm text-slate-400">{label}</p>
    </div>
  );
}

function CollapsibleSection({
  title,
  icon,
  count,
  expanded,
  onToggle,
  children
}: {
  title: string;
  icon: React.ReactNode;
  count: number | null;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="card overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full p-4 flex items-center justify-between hover:bg-slate-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {icon}
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          {count !== null && <span className="tag-primary">{count}</span>}
        </div>
        {expanded ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
      </button>
      {expanded && <div className="p-4 pt-0 border-t border-slate-800">{children}</div>}
    </div>
  );
}

function SoundCard({ sound, rank }: { sound: TrendingSound; rank: number }) {
  return (
    <div className="bg-slate-800/50 rounded-lg p-4 flex items-center gap-4">
      <div className="w-8 h-8 rounded-full bg-pink-500/20 flex items-center justify-center text-pink-400 font-bold">
        {rank}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-white font-medium truncate">{sound.name}</p>
        <p className="text-sm text-slate-400">{sound.author || 'Unknown artist'}</p>
      </div>
      <div className="text-right">
        <p className="text-white font-medium">{sound.usage_count} uses</p>
        <p className="text-xs text-slate-400">{formatNumber(sound.avg_engagement)} avg eng.</p>
      </div>
      <div className="flex items-center gap-1">
        <Flame className="w-4 h-4 text-orange-400" />
        <span className="text-orange-400 font-medium">{sound.trend_score.toFixed(1)}</span>
      </div>
    </div>
  );
}

function HashtagBadge({ hashtag }: { hashtag: TrendingHashtag }) {
  const categoryColors: Record<string, string> = {
    discovery: 'bg-green-500/20 text-green-400 border-green-500/30',
    educational: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    review: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    transformation: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    lifestyle: 'bg-pink-500/20 text-pink-400 border-pink-500/30',
    entertainment: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    format: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    niche: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
  };

  const colorClass = categoryColors[hashtag.category] || categoryColors.niche;

  return (
    <div className={`px-3 py-2 rounded-lg border ${colorClass} flex items-center gap-2`}>
      <span className="font-medium">{hashtag.hashtag}</span>
      <span className="text-xs opacity-75">×{hashtag.usage_count}</span>
    </div>
  );
}

function BenchmarkCard({ title, data }: { title: string; data?: { avg: number; median: number; top_10_percent: number } }) {
  if (!data) return null;

  return (
    <div className="bg-slate-800/50 rounded-lg p-4">
      <h4 className="text-sm font-medium text-slate-400 mb-3">{title}</h4>
      <div className="space-y-2">
        <div className="flex justify-between">
          <span className="text-slate-400">Average</span>
          <span className="text-white font-medium">{formatNumber(data.avg)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Median</span>
          <span className="text-white font-medium">{formatNumber(data.median)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Top 10%</span>
          <span className="text-green-400 font-medium">{formatNumber(data.top_10_percent)}</span>
        </div>
      </div>
    </div>
  );
}

// Helpers

function formatNumber(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toString();
}

function formatDurationRange(range: string): string {
  const labels: Record<string, string> = {
    'under_15s': '<15s',
    '15_30s': '15-30s',
    '30_60s': '30-60s',
    'over_60s': '>60s',
  };
  return labels[range] || range;
}
