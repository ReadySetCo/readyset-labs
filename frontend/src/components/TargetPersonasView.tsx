import { Target, AlertTriangle, Compass, Sparkles, ShoppingBag, Users2 } from 'lucide-react';

/**
 * Renders Target Personas — prospects (NOT existing customers).
 *
 * Each target persona maps to a Schwartz awareness level and includes the
 * specific reason this segment isn't yet a customer plus a ready-to-test
 * acquisition hook in category vocabulary (not brand vocabulary).
 */

type DemographicHypothesis = {
  age_range?: string;
  platform_affinity?: string[];
  lifestyle_markers?: string[];
};

type TargetPersona = {
  name?: string;
  awareness_level?: 'Unaware' | 'Problem Aware' | 'Solution Aware' | string;
  the_problem_they_have?: string;
  why_not_yet_a_customer?: string;
  current_solution_or_workaround?: string;
  what_would_unlock_them?: string;
  acquisition_hook?: string;
  evidence_indexes?: number[];
  evidence_quotes?: string[];
  estimated_acquisition_difficulty?: string;
  estimated_share_of_addressable_market?: number;
  demographic_hypothesis?: DemographicHypothesis;
  creative_format_recommendation?: string;
  anti_pattern?: string;
};

const awarenessColor = (level?: string): string => {
  switch (level) {
    case 'Unaware': return 'bg-red-500/15 text-red-300 border-red-500/30';
    case 'Problem Aware': return 'bg-orange-500/15 text-orange-300 border-orange-500/30';
    case 'Solution Aware': return 'bg-yellow-500/15 text-yellow-300 border-yellow-500/30';
    default: return 'bg-slate-500/15 text-slate-300 border-slate-500/30';
  }
};

const difficultyColor = (level?: string): string => {
  switch (level) {
    case 'low': return 'text-green-400';
    case 'medium': return 'text-yellow-400';
    case 'high': return 'text-red-400';
    default: return 'text-slate-400';
  }
};

export default function TargetPersonasView({
  targetPersonas,
}: {
  targetPersonas: TargetPersona[];
}) {
  if (!targetPersonas || targetPersonas.length === 0) {
    return (
      <div className="card p-8 text-center">
        <Target className="w-12 h-12 text-slate-500 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-white mb-2">No Target Personas Yet</h3>
        <p className="text-slate-400">
          Target Personas are <strong>prospects, not customers</strong> — segments who experience
          the category problem but aren't yet buying from this brand. They're discovered from the
          same data corpus as CTPs but through a Schwartz-awareness lens (Unaware / Problem Aware /
          Solution Aware). Run a new session or reprocess an existing one to populate them.
        </p>
      </div>
    );
  }

  // Sort by awareness level (Unaware first — TOFU priority)
  const order: Record<string, number> = {
    'Unaware': 0, 'Problem Aware': 1, 'Solution Aware': 2,
  };
  const sorted = [...targetPersonas].sort(
    (a, b) => (order[a.awareness_level || ''] ?? 99) - (order[b.awareness_level || ''] ?? 99)
  );

  return (
    <div className="space-y-6">
      {/* Intro banner */}
      <div className="card p-5 border-l-4 border-l-cyan-500">
        <div className="flex items-start gap-3">
          <Compass className="w-5 h-5 text-cyan-400 mt-1 shrink-0" />
          <div>
            <h2 className="text-lg font-semibold text-white mb-1">
              Target Personas — TOFU Acquisition Map
            </h2>
            <p className="text-slate-400 text-sm">
              These are <strong className="text-white">people who aren't customers yet</strong> but
              should be. Mapped to Eugene Schwartz's awareness framework. Each persona includes a
              ready-to-test acquisition hook in <em>category vocabulary</em> — written for someone
              who has never heard of the brand.
            </p>
          </div>
        </div>
      </div>

      {/* Persona cards */}
      <div className="space-y-5">
        {sorted.map((tp, idx) => (
          <div key={idx} className="card p-6 space-y-4">
            {/* Header */}
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`text-xs px-2 py-0.5 rounded border ${awarenessColor(tp.awareness_level)}`}
                  >
                    {tp.awareness_level || 'Unspecified'}
                  </span>
                  {tp.estimated_share_of_addressable_market !== undefined && (
                    <span className="text-xs text-slate-400">
                      ~{tp.estimated_share_of_addressable_market}% TAM
                    </span>
                  )}
                  {tp.estimated_acquisition_difficulty && (
                    <span className={`text-xs ${difficultyColor(tp.estimated_acquisition_difficulty)}`}>
                      acquisition: {tp.estimated_acquisition_difficulty}
                    </span>
                  )}
                </div>
                <h3 className="text-xl font-bold text-white">{tp.name || `Target Persona ${idx + 1}`}</h3>
              </div>
            </div>

            {/* The problem */}
            {tp.the_problem_they_have && (
              <Section icon={<AlertTriangle className="w-4 h-4 text-orange-400" />} label="The problem they have">
                {tp.the_problem_they_have}
              </Section>
            )}

            {/* Why not yet customer */}
            {tp.why_not_yet_a_customer && (
              <Section icon={<Users2 className="w-4 h-4 text-rose-400" />} label="Why not a customer yet">
                {tp.why_not_yet_a_customer}
              </Section>
            )}

            {/* Current workaround */}
            {tp.current_solution_or_workaround && (
              <Section icon={<ShoppingBag className="w-4 h-4 text-amber-400" />} label="Current workaround">
                {tp.current_solution_or_workaround}
              </Section>
            )}

            {/* What would unlock them */}
            {tp.what_would_unlock_them && (
              <Section icon={<Sparkles className="w-4 h-4 text-emerald-400" />} label="What would unlock them">
                {tp.what_would_unlock_them}
              </Section>
            )}

            {/* Acquisition hook — highlighted */}
            {tp.acquisition_hook && (
              <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Target className="w-4 h-4 text-cyan-400" />
                  <span className="text-sm font-semibold text-cyan-300 uppercase tracking-wide">
                    Acquisition Hook
                  </span>
                </div>
                <blockquote className="text-white text-base italic">
                  "{tp.acquisition_hook}"
                </blockquote>
                {tp.creative_format_recommendation && (
                  <p className="text-xs text-slate-400 mt-2">
                    Format: <span className="text-slate-300">{tp.creative_format_recommendation}</span>
                  </p>
                )}
              </div>
            )}

            {/* Anti-pattern */}
            {tp.anti_pattern && (
              <div className="text-sm text-slate-400 border-l-2 border-rose-500/40 pl-3">
                <span className="text-rose-400 font-medium">Avoid:</span> {tp.anti_pattern}
              </div>
            )}

            {/* Demographic hypothesis */}
            {tp.demographic_hypothesis && (
              <div className="grid sm:grid-cols-3 gap-3 pt-3 border-t border-slate-800 text-sm">
                {tp.demographic_hypothesis.age_range && (
                  <div>
                    <div className="text-xs text-slate-500 uppercase mb-1">Age</div>
                    <div className="text-slate-300">{tp.demographic_hypothesis.age_range}</div>
                  </div>
                )}
                {tp.demographic_hypothesis.platform_affinity && tp.demographic_hypothesis.platform_affinity.length > 0 && (
                  <div>
                    <div className="text-xs text-slate-500 uppercase mb-1">Platforms</div>
                    <div className="text-slate-300">{tp.demographic_hypothesis.platform_affinity.join(', ')}</div>
                  </div>
                )}
                {tp.demographic_hypothesis.lifestyle_markers && tp.demographic_hypothesis.lifestyle_markers.length > 0 && (
                  <div>
                    <div className="text-xs text-slate-500 uppercase mb-1">Lifestyle</div>
                    <div className="text-slate-300">{tp.demographic_hypothesis.lifestyle_markers.join(' · ')}</div>
                  </div>
                )}
              </div>
            )}

            {/* Evidence quotes */}
            {tp.evidence_quotes && tp.evidence_quotes.length > 0 && (
              <details className="text-sm pt-3 border-t border-slate-800">
                <summary className="text-slate-400 cursor-pointer hover:text-slate-300">
                  Evidence ({tp.evidence_quotes.length} verbatim quotes
                  {tp.evidence_indexes ? `, snippets: ${tp.evidence_indexes.slice(0, 8).join(', ')}${tp.evidence_indexes.length > 8 ? '...' : ''}` : ''}
                  )
                </summary>
                <ul className="mt-2 space-y-1 text-slate-400">
                  {tp.evidence_quotes.slice(0, 5).map((q, i) => (
                    <li key={i} className="italic">"{q}"</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function Section({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-slate-300 text-sm">{children}</p>
    </div>
  );
}
