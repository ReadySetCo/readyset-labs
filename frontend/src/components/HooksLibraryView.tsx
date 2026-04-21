import { useState, useMemo } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Megaphone,
  Filter,
  Copy,
  Check,
  Star,
  Target,
  Heart,
  ChevronDown,
  Lightbulb,
  Bookmark,
  Search
} from 'lucide-react';
import type { HooksLibrary, Hook } from '../api/client';
import { createIdea } from '../api/client';

interface HooksLibraryViewProps {
  library: HooksLibrary;
  sessionId?: number;
  brandId?: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function textFromValue(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) return value.map(textFromValue).filter(Boolean).join(', ');
  if (isRecord(value)) {
    return Object.entries(value)
      .map(([key, nestedValue]) => {
        const text = textFromValue(nestedValue);
        return text ? `${formatType(key)}: ${text}` : '';
      })
      .filter(Boolean)
      .join(' | ');
  }
  return '';
}

function toStringArray(value: unknown, fallback: string[] = []): string[] {
  if (Array.isArray(value)) return value.map(textFromValue).filter(Boolean);
  const text = textFromValue(value);
  return text ? [text] : fallback;
}

function normalizeStrength(value: unknown): number {
  const numeric = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(numeric)) return 3;
  return Math.max(1, Math.min(5, Math.round(numeric)));
}

function normalizeHook(rawHook: unknown): Hook | null {
  if (!isRecord(rawHook)) return null;

  const hookText = textFromValue(rawHook.hook_text ?? rawHook.hook ?? rawHook.text ?? rawHook.headline);
  if (!hookText) return null;

  return {
    hook_text: hookText,
    hook_type: textFromValue(rawHook.hook_type ?? rawHook.type) || 'other',
    target_emotion: textFromValue(rawHook.target_emotion ?? rawHook.emotion) || 'other',
    target_persona: textFromValue(rawHook.target_persona ?? rawHook.persona) || undefined,
    platform_fit: toStringArray(rawHook.platform_fit ?? rawHook.platforms, ['General']),
    pain_point_addressed: textFromValue(rawHook.pain_point_addressed ?? rawHook.pain_point) || undefined,
    verbatim_source: textFromValue(rawHook.verbatim_source ?? rawHook.source) || undefined,
    strength_score: normalizeStrength(rawHook.strength_score ?? rawHook.score),
    why_it_works: textFromValue(rawHook.why_it_works ?? rawHook.rationale) || undefined,
  };
}

function collectHooks(library: HooksLibrary | null | undefined): Hook[] {
  if (!library) return [];

  const directHooks = Array.isArray((library as any).all_hooks) ? (library as any).all_hooks : [];
  const bucketHooks = directHooks.length === 0 && isRecord((library as any).by_type)
    ? Object.values((library as any).by_type).flatMap(value => Array.isArray(value) ? value : [])
    : [];

  return [...directHooks, ...bucketHooks]
    .map(normalizeHook)
    .filter((hook): hook is Hook => hook !== null);
}

function hasDistribution(data: unknown): data is Record<string, number> {
  return isRecord(data) && Object.keys(data).length > 0;
}

function buildDistribution(hooks: Hook[], key: 'hook_type' | 'target_emotion'): Record<string, number> {
  return hooks.reduce<Record<string, number>>((distribution, hook) => {
    const bucket = textFromValue(hook[key]) || 'other';
    distribution[bucket] = (distribution[bucket] || 0) + 1;
    return distribution;
  }, {});
}

function averageStrength(hooks: Hook[]): number {
  if (hooks.length === 0) return 0;
  const total = hooks.reduce((sum, hook) => sum + normalizeStrength(hook.strength_score), 0);
  return Math.round((total / hooks.length) * 10) / 10;
}

export default function HooksLibraryView({ library, sessionId, brandId }: HooksLibraryViewProps) {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState({
    type: 'all',
    emotion: 'all',
    platform: 'all',
    minStrength: 1,
    search: ''
  });
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [savedId, setSavedId] = useState<number | null>(null);
  const allHooks = useMemo(() => collectHooks(library), [library]);
  const typeDistribution = useMemo(
    () => hasDistribution(library?.type_distribution) ? library.type_distribution : buildDistribution(allHooks, 'hook_type'),
    [library, allHooks]
  );
  const emotionDistribution = useMemo(
    () => hasDistribution(library?.emotion_distribution) ? library.emotion_distribution : buildDistribution(allHooks, 'target_emotion'),
    [library, allHooks]
  );
  const totalHooks = typeof library?.total_hooks === 'number' && library.total_hooks > 0
    ? library.total_hooks
    : allHooks.length;
  const avgStrength = typeof library?.avg_strength === 'number' && library.avg_strength > 0
    ? library.avg_strength
    : averageStrength(allHooks);
  const recommendations = Array.isArray(library?.recommendations) ? library.recommendations : [];

  // Save hook mutation
  const saveMutation = useMutation({
    mutationFn: (hook: Hook) => createIdea({
      brand_id: brandId,
      session_id: sessionId,
      idea_type: 'hook',
      content: hook.hook_text,
      hook_type: hook.hook_type,
      target_emotion: hook.target_emotion,
      target_persona: hook.target_persona,
      platform_fit: hook.platform_fit,
      strength_score: hook.strength_score,
      source: 'generated',
      source_detail: hook.why_it_works
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ideas'] });
      queryClient.invalidateQueries({ queryKey: ['ideaStats'] });
    }
  });

  const saveHook = (hook: Hook, idx: number) => {
    saveMutation.mutate(hook);
    setSavedId(idx);
    setTimeout(() => setSavedId(null), 2000);
  };

  // Filter hooks
  const filteredHooks = useMemo(() => {
    return allHooks.filter(hook => {
      if (filter.type !== 'all' && hook.hook_type !== filter.type) return false;
      if (filter.emotion !== 'all' && hook.target_emotion !== filter.emotion) return false;
      if (filter.platform !== 'all' && !hook.platform_fit.some(p => p.toLowerCase().includes(filter.platform))) return false;
      if (hook.strength_score < filter.minStrength) return false;
      if (filter.search && !hook.hook_text.toLowerCase().includes(filter.search.toLowerCase())) return false;
      return true;
    }).sort((a, b) => b.strength_score - a.strength_score);
  }, [allHooks, filter]);

  const copyHook = async (hook: Hook, idx: number) => {
    await navigator.clipboard.writeText(hook.hook_text);
    setCopiedId(idx);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (!library || totalHooks === 0 || allHooks.length === 0) {
    return (
      <div className="card p-8 text-center">
        <Megaphone className="w-12 h-12 text-slate-500 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-white mb-2">No Hooks Generated</h3>
        <p className="text-slate-400">
          Hooks library will be generated with your next research session.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={<Megaphone className="w-5 h-5" />}
          label="Total Hooks"
          value={totalHooks.toString()}
          color="purple"
        />
        <StatCard
          icon={<Star className="w-5 h-5" />}
          label="Avg Strength"
          value={`${avgStrength}/5`}
          color="yellow"
        />
        <StatCard
          icon={<Target className="w-5 h-5" />}
          label="Hook Types"
          value={Object.keys(typeDistribution).length.toString()}
          color="blue"
        />
        <StatCard
          icon={<Heart className="w-5 h-5" />}
          label="Emotions"
          value={Object.keys(emotionDistribution).length.toString()}
          color="pink"
        />
      </div>

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-yellow-400" />
            Quick Recommendations
          </h3>
          <div className="grid md:grid-cols-2 gap-3">
            {recommendations.slice(0, 4).map((rec: any, idx) => (
              <div key={idx} className="bg-slate-800/50 rounded-lg p-3 border-l-4 border-yellow-500">
                <span className="tag-primary text-xs mb-1">{textFromValue(rec.type) || 'Recommendation'}</span>
                <p className="text-white text-sm">{textFromValue(rec.action)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-sm text-slate-400">Filter Hooks</span>
          <span className="ml-auto text-sm text-slate-500">{filteredHooks.length} results</span>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {/* Search */}
          <div className="col-span-2 md:col-span-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search hooks..."
              value={filter.search}
              onChange={(e) => setFilter({ ...filter, search: e.target.value })}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* Type Filter */}
          <FilterSelect
            label="Type"
            value={filter.type}
            onChange={(v) => setFilter({ ...filter, type: v })}
            options={[
              { value: 'all', label: 'All Types' },
              ...Object.keys(typeDistribution).map(t => ({ value: t, label: formatType(t) }))
            ]}
          />

          {/* Emotion Filter */}
          <FilterSelect
            label="Emotion"
            value={filter.emotion}
            onChange={(v) => setFilter({ ...filter, emotion: v })}
            options={[
              { value: 'all', label: 'All Emotions' },
              ...Object.keys(emotionDistribution).map(e => ({ value: e, label: formatType(e) }))
            ]}
          />

          {/* Platform Filter */}
          <FilterSelect
            label="Platform"
            value={filter.platform}
            onChange={(v) => setFilter({ ...filter, platform: v })}
            options={[
              { value: 'all', label: 'All Platforms' },
              { value: 'tiktok', label: 'TikTok' },
              { value: 'instagram', label: 'Instagram' },
              { value: 'facebook', label: 'Facebook' },
              { value: 'youtube', label: 'YouTube' },
            ]}
          />

          {/* Strength Filter */}
          <FilterSelect
            label="Min Strength"
            value={filter.minStrength.toString()}
            onChange={(v) => setFilter({ ...filter, minStrength: parseInt(v) })}
            options={[
              { value: '1', label: 'Any Strength' },
              { value: '3', label: '3+ Stars' },
              { value: '4', label: '4+ Stars' },
              { value: '5', label: '5 Stars Only' },
            ]}
          />
        </div>
      </div>

      {/* Hooks Grid */}
      <div className="grid gap-4">
        {filteredHooks.map((hook, idx) => (
          <HookCard
            key={idx}
            hook={hook}
            onCopy={() => copyHook(hook, idx)}
            onSave={() => saveHook(hook, idx)}
            copied={copiedId === idx}
            saved={savedId === idx}
          />
        ))}

        {filteredHooks.length === 0 && (
          <div className="card p-8 text-center">
            <p className="text-slate-400">No hooks match your filters. Try adjusting them.</p>
          </div>
        )}
      </div>

      {/* Distribution Charts */}
      <div className="grid md:grid-cols-2 gap-6">
        <DistributionCard
          title="By Hook Type"
          data={typeDistribution}
          colorClass="bg-purple-500"
        />
        <DistributionCard
          title="By Emotion"
          data={emotionDistribution}
          colorClass="bg-pink-500"
        />
      </div>
    </div>
  );
}

// Sub-components

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string; color: string }) {
  const colors: Record<string, string> = {
    purple: 'bg-purple-500/20 text-purple-400',
    yellow: 'bg-yellow-500/20 text-yellow-400',
    blue: 'bg-blue-500/20 text-blue-400',
    pink: 'bg-pink-500/20 text-pink-400',
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

function FilterSelect({
  label: _label,
  value,
  onChange,
  options
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white appearance-none focus:outline-none focus:border-indigo-500"
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
    </div>
  );
}

function HookCard({
  hook,
  onCopy,
  onSave,
  copied,
  saved
}: {
  hook: Hook;
  onCopy: () => void;
  onSave: () => void;
  copied: boolean;
  saved?: boolean;
}) {
  const typeColors: Record<string, string> = {
    question: 'bg-blue-500/20 text-blue-400',
    statement: 'bg-purple-500/20 text-purple-400',
    story: 'bg-green-500/20 text-green-400',
    pattern_interrupt: 'bg-orange-500/20 text-orange-400',
    curiosity_gap: 'bg-pink-500/20 text-pink-400',
    testimonial: 'bg-cyan-500/20 text-cyan-400',
    problem_call_out: 'bg-red-500/20 text-red-400',
    transformation: 'bg-yellow-500/20 text-yellow-400',
  };

  return (
    <div className="card p-4 hover:bg-slate-800/70 transition-colors">
      <div className="flex items-start gap-4">
        {/* Strength Score */}
        <div className="flex flex-col items-center">
          <div className="text-2xl font-bold text-white">{hook.strength_score}</div>
          <div className="flex gap-0.5">
            {[1, 2, 3, 4, 5].map(i => (
              <Star
                key={i}
                className={`w-3 h-3 ${i <= hook.strength_score ? 'text-yellow-400 fill-yellow-400' : 'text-slate-600'}`}
              />
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <p className="text-white text-lg leading-relaxed mb-3">"{hook.hook_text}"</p>
          
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className={`px-2 py-1 rounded text-xs font-medium ${typeColors[hook.hook_type] || 'bg-slate-700 text-slate-300'}`}>
              {formatType(hook.hook_type)}
            </span>
            <span className="px-2 py-1 rounded text-xs font-medium bg-slate-700 text-slate-300">
              {formatType(hook.target_emotion)}
            </span>
            {toStringArray(hook.platform_fit, ['General']).map(p => (
              <span key={p} className="px-2 py-1 rounded text-xs bg-slate-800 text-slate-400">
                {p}
              </span>
            ))}
            {(hook as any).awareness_level && (
              <span className="px-2 py-1 rounded text-xs font-medium bg-blue-500/20 text-blue-400">
                {(hook as any).awareness_level}
              </span>
            )}
            {(hook as any).recommended_format && (
              <span className="px-2 py-1 rounded text-xs font-medium bg-purple-500/20 text-purple-400">
                {(hook as any).recommended_format}
              </span>
            )}
          </div>

          {hook.target_persona && (
            <p className="text-sm text-slate-400 flex items-center gap-1">
              <Target className="w-3 h-3" /> {hook.target_persona}
            </p>
          )}

          {hook.why_it_works && (
            <p className="text-sm text-slate-500 mt-2 italic">💡 {hook.why_it_works}</p>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2">
          <button
            onClick={onCopy}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors"
            title="Copy hook"
          >
            {copied ? (
              <Check className="w-4 h-4 text-green-400" />
            ) : (
              <Copy className="w-4 h-4 text-slate-400" />
            )}
          </button>
          <button
            onClick={onSave}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors"
            title="Save to Idea Bank"
          >
            {saved ? (
              <Check className="w-4 h-4 text-green-400" />
            ) : (
              <Bookmark className="w-4 h-4 text-slate-400" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

function DistributionCard({
  title,
  data,
  colorClass
}: {
  title: string;
  data: Record<string, number>;
  colorClass: string;
}) {
  const sorted = Object.entries(data || {})
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1]);
  const total = sorted.reduce((sum, [, count]) => sum + count, 0);

  if (total === 0) {
    return (
      <div className="card p-4">
        <h4 className="text-sm font-medium text-slate-400 mb-4">{title}</h4>
        <p className="text-sm text-slate-500">No distribution data available.</p>
      </div>
    );
  }

  return (
    <div className="card p-4">
      <h4 className="text-sm font-medium text-slate-400 mb-4">{title}</h4>
      <div className="space-y-3">
        {sorted.map(([key, count]) => (
          <div key={key}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-white">{formatType(key)}</span>
              <span className="text-slate-400">{count} ({Math.round(count / total * 100)}%)</span>
            </div>
            <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className={`h-full ${colorClass} rounded-full transition-all`}
                style={{ width: `${count / total * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Helpers

function formatType(type: unknown): string {
  const text = textFromValue(type) || 'other';
  return text
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
