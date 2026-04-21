import { Target, TrendingUp, Calendar, FileText, Layers, Users, ArrowRight } from 'lucide-react';

function asArray<T = any>(value: unknown): T[] {
  if (Array.isArray(value)) return value as T[];
  if (value === null || value === undefined || value === '') return [];
  return [value as T];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function formatLabel(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, char => char.toUpperCase());
}

function valueToText(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) {
    return value.map(valueToText).filter(Boolean).join(', ');
  }
  if (isRecord(value)) {
    const preferredKeys = [
      'headline',
      'body',
      'description',
      'image_description',
      'cta_button',
      'goal',
      'action',
      'rationale',
      'text',
      'hook',
      'name',
      'question',
    ];
    const preferred = preferredKeys
      .map(key => valueToText(value[key]))
      .filter(Boolean);

    if (preferred.length > 0) return preferred.join(' ');

    return Object.entries(value)
      .map(([key, nestedValue]) => {
        const text = valueToText(nestedValue);
        return text ? `${formatLabel(key)}: ${text}` : '';
      })
      .filter(Boolean)
      .join(' | ');
  }

  return '';
}

function hasDisplayValue(value: unknown): boolean {
  return valueToText(value).length > 0;
}

function StructuredValue({ value }: { value: unknown }) {
  if (isRecord(value)) {
    const entries = Object.entries(value).filter(([, nestedValue]) => hasDisplayValue(nestedValue));

    return (
      <div className="space-y-2">
        {entries.map(([key, nestedValue]) => (
          <div key={key}>
            <p className="text-xs text-slate-500">{formatLabel(key)}:</p>
            <p className={`text-sm ${key === 'headline' ? 'text-white font-medium' : 'text-slate-300'}`}>
              {valueToText(nestedValue)}
            </p>
          </div>
        ))}
      </div>
    );
  }

  return <p className="text-sm text-white italic">"{valueToText(value)}"</p>;
}

export default function FunnelStrategyView({ strategy }: { strategy: any }) {
  if (!strategy || strategy._fallback) {
    return (
      <div className="card p-8 text-center">
        <Layers className="w-12 h-12 text-slate-500 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-white mb-2">No Funnel Strategy Generated</h3>
        <p className="text-slate-400">Run a full research session to generate a funnel strategy.</p>
      </div>
    );
  }

  const diagnosis = strategy.account_diagnosis || {};
  const personas = asArray(strategy.persona_architecture);
  const funnel = strategy.funnel_map || {};
  const roadmap = strategy.ninety_day_roadmap || {};
  const tracker = strategy.creative_tracker_setup || {};
  const briefs = asArray(strategy.first_three_briefs);
  const identifiedGaps = asArray(diagnosis.identified_gaps).map(valueToText).filter(Boolean);

  return (
    <div className="space-y-6">

      {/* Account Diagnosis */}
      {diagnosis && Object.keys(diagnosis).length > 0 && (
        <div className="glass-card p-6 border-l-4 border-red-500">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-red-400" />
            Account Diagnosis
          </h3>
          <div className="grid md:grid-cols-2 gap-4">
            {hasDisplayValue(diagnosis.current_awareness_distribution) && (
              <div className="bg-slate-800/50 p-4 rounded-xl">
                <p className="text-xs text-slate-500 mb-1">Current Awareness Distribution</p>
                <p className="text-sm text-slate-300">{valueToText(diagnosis.current_awareness_distribution)}</p>
              </div>
            )}
            {hasDisplayValue(diagnosis.frequency_assessment) && (
              <div className="bg-slate-800/50 p-4 rounded-xl">
                <p className="text-xs text-slate-500 mb-1">Frequency Assessment</p>
                <p className="text-sm text-slate-300">{valueToText(diagnosis.frequency_assessment)}</p>
              </div>
            )}
          </div>
          {hasDisplayValue(diagnosis.biggest_creative_bottleneck) && (
            <div className="mt-4 p-3 bg-red-500/10 rounded-lg border border-red-500/20">
              <p className="text-sm text-red-300">
                <strong>Biggest Bottleneck:</strong> {valueToText(diagnosis.biggest_creative_bottleneck)}
              </p>
            </div>
          )}
          {identifiedGaps.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {identifiedGaps.map((gap, i) => (
                <span key={i} className="tag text-xs bg-red-500/20 text-red-300">{gap}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Persona Architecture */}
      {personas.length > 0 && (
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-purple-400" />
            Persona Architecture ({personas.length})
          </h3>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {personas.map((p: any, i: number) => (
              <div key={i} className="bg-purple-500/10 rounded-xl p-4 border border-purple-500/20">
                <h4 className="font-semibold text-purple-300 mb-2">{valueToText(p.persona_name) || `Persona ${i + 1}`}</h4>
                <p className="text-sm text-slate-400 mb-3">{valueToText(p.description)}</p>
                <div className="space-y-1 text-xs">
                  <p><span className="text-purple-400">Awareness:</span> <span className="text-slate-300">{valueToText(p.awareness_level)}</span></p>
                  <p><span className="text-purple-400">Primary Driver:</span> <span className="text-slate-300">{valueToText(p.primary_pain_or_desire)}</span></p>
                  <p><span className="text-purple-400">Trigger:</span> <span className="text-slate-300">{valueToText(p.emotional_trigger)}</span></p>
                </div>
                {hasDisplayValue(p.hook_direction) && (
                  <div className="mt-3 p-2 bg-slate-900/50 rounded">
                    <p className="text-xs text-purple-400 mb-1">Hook Direction:</p>
                    <StructuredValue value={p.hook_direction} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Full Funnel Map */}
      {funnel && Object.keys(funnel).length > 0 && (
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            Full Funnel Map
          </h3>
          <div className="grid md:grid-cols-3 gap-4">
            {[
              { key: 'top_of_funnel', label: 'Top of Funnel', color: 'blue', emoji: '🔵' },
              { key: 'middle_of_funnel', label: 'Middle of Funnel', color: 'yellow', emoji: '🟡' },
              { key: 'bottom_of_funnel', label: 'Bottom of Funnel', color: 'green', emoji: '🟢' },
            ].map(({ key, label, color, emoji }) => {
              const stage = funnel[key];
              if (!stage) return null;
              const recommendedFormats = asArray(stage.recommended_formats).map(valueToText).filter(Boolean);
              const example = stage.example_hook || stage.example_static_concept;

              return (
                <div key={key} className={`bg-${color}-500/10 rounded-xl p-4 border border-${color}-500/20`}>
                  <h4 className={`font-semibold text-${color}-300 mb-2`}>{emoji} {label}</h4>
                  {hasDisplayValue(stage.goal) && <p className="text-sm text-slate-300 mb-2">{valueToText(stage.goal)}</p>}
                  {hasDisplayValue(stage.awareness_levels) && <p className="text-xs text-slate-500 mb-2">{valueToText(stage.awareness_levels)}</p>}
                  {recommendedFormats.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {recommendedFormats.map((format, j) => (
                        <span key={j} className="tag text-xs bg-slate-700 text-slate-300">{format}</span>
                      ))}
                    </div>
                  )}
                  {hasDisplayValue(example) && (
                    <div className="mt-2 p-2 bg-slate-900/50 rounded">
                      <p className="text-xs text-slate-500 mb-1">Example:</p>
                      <StructuredValue value={example} />
                    </div>
                  )}
                  {hasDisplayValue(stage.budget_allocation) && (
                    <p className="text-xs text-slate-500 mt-2">Budget: {valueToText(stage.budget_allocation)}</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 90-Day Roadmap */}
      {roadmap && Object.keys(roadmap).length > 0 && (
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Calendar className="w-5 h-5 text-amber-400" />
            90-Day Creative Roadmap
          </h3>
          <div className="space-y-4">
            {[
              { key: 'phase_1_foundation', label: 'Phase 1: Foundation', weeks: 'Weeks 1-4', color: 'amber' },
              { key: 'phase_2_validation', label: 'Phase 2: Validation', weeks: 'Weeks 5-8', color: 'blue' },
              { key: 'phase_3_compounding', label: 'Phase 3: Compounding', weeks: 'Weeks 9-12', color: 'green' },
            ].map(({ key, label, weeks, color }) => {
              const phase = roadmap[key];
              if (!phase) return null;
              const priorityAngles = asArray(phase.priority_angles).map(valueToText).filter(Boolean);

              return (
                <div key={key} className={`bg-slate-800/50 p-4 rounded-xl border-l-4 border-${color}-500`}>
                  <div className="flex items-center gap-2 mb-2">
                    <h4 className={`font-semibold text-${color}-300`}>{label}</h4>
                    <span className="tag text-xs bg-slate-700 text-slate-400">{valueToText(phase.weeks) || weeks}</span>
                  </div>
                  <div className="space-y-2 text-sm text-slate-400">
                    {priorityAngles.length > 0 && (
                      <div>
                        <p className="text-xs text-slate-500">Priority Angles:</p>
                        <ul className="list-disc list-inside">
                          {priorityAngles.map((angle, j) => <li key={j}>{angle}</li>)}
                        </ul>
                      </div>
                    )}
                    {hasDisplayValue(phase.minimum_creative_volume) && <p><span className="text-amber-400">Volume:</span> {valueToText(phase.minimum_creative_volume)}</p>}
                    {hasDisplayValue(phase.signal_to_watch) && <p><span className="text-amber-400">Signal:</span> {valueToText(phase.signal_to_watch)}</p>}
                    {hasDisplayValue(phase.how_to_read_data) && <p><span className="text-blue-400">Read Data:</span> {valueToText(phase.how_to_read_data)}</p>}
                    {hasDisplayValue(phase.scale_kill_iterate) && <p><span className="text-blue-400">Decision:</span> {valueToText(phase.scale_kill_iterate)}</p>}
                    {hasDisplayValue(phase.winner_iteration) && <p><span className="text-green-400">Iterate:</span> {valueToText(phase.winner_iteration)}</p>}
                    {hasDisplayValue(phase.healthy_account_indicators) && <p><span className="text-green-400">Health:</span> {valueToText(phase.healthy_account_indicators)}</p>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* First 3 Priority Briefs */}
      {briefs.length > 0 && (
        <div className="glass-card p-6 border-l-4 border-green-500">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-green-400" />
            First 3 Priority Briefs
          </h3>
          <div className="space-y-4">
            {briefs.map((brief: any, i: number) => (
              <div key={i} className="bg-green-500/10 rounded-xl p-4 border border-green-500/20">
                <div className="flex items-center gap-3 mb-2">
                  <span className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center text-green-400 font-bold text-sm">
                    {valueToText(brief.priority) || i + 1}
                  </span>
                  <h4 className="font-semibold text-green-300">{valueToText(brief.angle)}</h4>
                </div>
                <div className="grid md:grid-cols-2 gap-2 text-sm mb-2">
                  <p><span className="text-slate-500">Persona:</span> <span className="text-slate-300">{valueToText(brief.target_persona)}</span></p>
                  <p><span className="text-slate-500">Awareness:</span> <span className="text-slate-300">{valueToText(brief.awareness_level)}</span></p>
                  <p><span className="text-slate-500">Format:</span> <span className="text-slate-300">{valueToText(brief.format)}</span></p>
                  <p><span className="text-slate-500">Hook:</span> <span className="text-white italic">"{valueToText(brief.hook_direction)}"</span></p>
                </div>
                {hasDisplayValue(brief.why_first) && (
                  <p className="text-xs text-green-400 mt-2 flex items-center gap-1">
                    <ArrowRight className="w-3 h-3" /> {valueToText(brief.why_first)}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Creative Tracker Setup */}
      {tracker && tracker.naming_convention && (
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-cyan-400" />
            Creative Tracker Setup
          </h3>
          <div className="space-y-3">
            <div className="bg-slate-800/50 p-3 rounded-xl">
              <p className="text-xs text-slate-500 mb-1">Naming Convention:</p>
              <p className="text-sm text-slate-300">{valueToText(tracker.naming_convention)}</p>
            </div>
            {hasDisplayValue(tracker.example_ad_name) && (
              <div className="bg-cyan-500/10 p-3 rounded-lg border border-cyan-500/20">
                <p className="text-xs text-cyan-400 mb-1">Example:</p>
                <code className="text-sm text-white">{valueToText(tracker.example_ad_name)}</code>
              </div>
            )}
            {hasDisplayValue(tracker.how_to_rank_by_angle) && (
              <p className="text-sm text-slate-400">{valueToText(tracker.how_to_rank_by_angle)}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
