import { useState } from 'react';
import { Users, AlertCircle, Shield, Target, Zap, BarChart3, BookOpen, Lightbulb, Quote, RefreshCw, X, Brain } from 'lucide-react';

/**
 * Renders the Creative Target Personas (CTP) + their Hypothesis layer.
 *
 * CTP data flows from the research pipeline: scraped VoC snippets -> stance
 * classification -> cluster by stance -> LLM enrichment -> CTPs. The hypothesis
 * layer is a per-CTP ad-strategy suggestion (demographics, angles, framework,
 * tone, emotion arc).
 */

type KillSignals = {
  existence?: string[];
  engagement?: string[];
  conversion?: string[];
};

type CTP = {
  ctp_id?: string;
  ctp_name?: string;
  general_stance?: string;
  core_insight_general?: string;
  core_insight_product_anchored?: string;
  pain_points?: Array<{ pain_point?: string; frequency?: number; sources?: string[]; evidence_indexes?: number[] }>;
  desires?: Array<string | { desire?: string; evidence_indexes?: number[] }>;
  barriers_objections?: Array<{ prompt?: string; type?: string; evidence?: string }>;
  recommended_hooks?: Array<{ hook?: string; source?: string; rationale?: string }>;
  recommended_value_props?: Array<{ value_prop?: string; source?: string; rationale?: string }>;
  kill_signals?: KillSignals;
  weight?: number;
  review_percentage?: number;
  snippet_count?: number;
  top_language_cues?: string[];
  source_distribution?: Record<string, number>;
  representative_snippets?: Array<{ content?: string; source_type?: string }>;
  // Discovery-driven fields (v2)
  archetype_psychology?: string;
  behavioral_markers?: string[];
  decision_factors?: Array<{ factor?: string; priority?: string; evidence?: string }>;
  vocabulary?: string[];
  counter_segment?: string;
  what_makes_them_unique?: string;
  stance_tags?: string[];
  frameworks_that_resonate?: Array<{ framework?: string; rationale?: string }>;
  tone_and_emotion_arc?: { primary_tone?: string; emotion_arc?: string; rationale?: string };
  ad_creative_gap?: string;
  anti_patterns?: string[];
  evidence_quotes?: string[];
  source?: string;
};

type Hypothesis = {
  ctp_id?: string;
  demographic_variables?: {
    age_range?: string;
    gender_skew?: string;
    income_level?: string;
    education?: string;
    platform_affinity?: string[];
    geo_notes?: string;
  };
  angles?: Array<{
    angle_name?: string;
    angle_description?: string;
    awareness_level?: string;
    emotional_trigger?: string;
    validation_tag?: string;
    validation_evidence?: string;
  }>;
  funnel_stage?: { stage?: string; rationale?: string };
  framework_tactic?: { primary?: string; secondary?: string; rationale?: string };
  visual_style?: { style?: string; rationale?: string };
  narrative_driver?: { driver?: string; rationale?: string };
  tone?: { primary?: string; secondary?: string; rationale?: string };
  emotion?: { arc?: string; primary_emotion?: string; rationale?: string };
};

type Stats = {
  total_ctps?: number;
  total_snippets?: number;
  stance_distribution?: Record<string, number>;
};

export default function CTPView({
  ctps,
  hypothesis,
  stats,
  sessionId,
  onRegenerated,
}: {
  ctps: CTP[];
  hypothesis: Hypothesis[];
  stats: Stats;
  sessionId?: number;
  onRegenerated?: () => void;
}) {
  if (!ctps || ctps.length === 0) {
    return (
      <div className="card p-8 text-center">
        <Users className="w-12 h-12 text-slate-500 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-white mb-2">No Creative Target Personas</h3>
        <p className="text-slate-400">
          CTPs are generated from stance-classified VoC snippets. Run a new research session — the
          pipeline caps stance classification at 300 high-quality snippets now, so this should
          complete in ~1 minute.
        </p>
      </div>
    );
  }

  // Index hypothesis by ctp_id for side-by-side rendering
  const hypoByCtp: Record<string, Hypothesis> = {};
  for (const h of hypothesis || []) {
    if (h.ctp_id) hypoByCtp[h.ctp_id] = h;
  }

  return (
    <div className="space-y-6">
      {/* Summary bar */}
      <div className="grid md:grid-cols-3 gap-4">
        <StatCard
          icon={<Users className="w-5 h-5" />}
          label="Total CTPs"
          value={(stats?.total_ctps || ctps.length).toString()}
          color="indigo"
        />
        <StatCard
          icon={<BarChart3 className="w-5 h-5" />}
          label="VoC Snippets Analyzed"
          value={(stats?.total_snippets || 0).toString()}
          color="cyan"
        />
        <StatCard
          icon={<Zap className="w-5 h-5" />}
          label="Hypothesis Layers"
          value={(hypothesis?.length || 0).toString()}
          color="amber"
        />
      </div>

      {/* One card per CTP */}
      {ctps.map((ctp, i) => {
        const hypo = ctp.ctp_id ? hypoByCtp[ctp.ctp_id] : undefined;
        return (
          <CTPCard
            key={ctp.ctp_id || i}
            ctp={ctp}
            hypo={hypo}
            sessionId={sessionId}
            onRegenerated={onRegenerated}
          />
        );
      })}
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: 'indigo' | 'cyan' | 'amber';
}) {
  const colors: Record<string, string> = {
    indigo: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    cyan: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  };
  return (
    <div className={`glass-card p-4 ${colors[color]}`}>
      <div className="flex items-center gap-2 mb-2 opacity-80">
        {icon}
        <span className="text-sm">{label}</span>
      </div>
      <span className="text-2xl font-display font-bold">{value}</span>
    </div>
  );
}

function CTPCard({
  ctp,
  hypo,
  sessionId,
  onRegenerated,
}: {
  ctp: CTP;
  hypo?: Hypothesis;
  sessionId?: number;
  onRegenerated?: () => void;
}) {
  const pain = ctp.pain_points || [];
  const desires = ctp.desires || [];
  const barriers = ctp.barriers_objections || [];
  const recommendedHooks = ctp.recommended_hooks || [];
  const recommendedVPs = ctp.recommended_value_props || [];
  const kill = ctp.kill_signals || {};
  const cues = ctp.top_language_cues || [];
  const sourceDist = ctp.source_distribution || {};
  const sampleSnippets = (ctp.representative_snippets || []).slice(0, 3);
  const angles = hypo?.angles || [];

  // Regenerate state
  const [regenerating, setRegenerating] = useState(false);
  const [regenError, setRegenError] = useState<string | null>(null);

  const handleRegenerate = async () => {
    if (!sessionId || !ctp.ctp_id) return;
    setRegenerating(true);
    setRegenError(null);
    try {
      const r = await fetch(`/api/research/session/${sessionId}/regenerate-ctp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ctp_id: ctp.ctp_id }),
      });
      if (!r.ok) {
        const err = await r.text();
        throw new Error(err || `HTTP ${r.status}`);
      }
      if (onRegenerated) onRegenerated();
    } catch (e: any) {
      setRegenError(e.message || 'Regeneration failed');
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <div className="glass-card p-6 border-l-4 border-indigo-500">
      {/* Header: name + stance + weight + regenerate */}
      <div className="flex items-start justify-between mb-4 gap-4">
        <div className="flex-1">
          <h3 className="text-xl font-semibold text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-indigo-400" />
            {ctp.ctp_name || 'Untitled CTP'}
          </h3>
          <div className="flex flex-wrap gap-2 mt-2 text-xs">
            {ctp.general_stance && (
              <span className="tag bg-indigo-500/20 text-indigo-300">
                {ctp.general_stance.replace(/_/g, ' ')}
              </span>
            )}
            {ctp.stance_tags && ctp.stance_tags.length > 1 && ctp.stance_tags.slice(1).map((t, i) => (
              <span key={i} className="tag bg-indigo-500/10 text-indigo-300/70">
                +{t.replace(/_/g, ' ')}
              </span>
            ))}
            {ctp.ctp_id && <span className="tag bg-slate-700 text-slate-300">{ctp.ctp_id}</span>}
            {typeof ctp.snippet_count === 'number' && (
              <span className="tag bg-slate-700 text-slate-300">{ctp.snippet_count} snippets</span>
            )}
            {typeof ctp.review_percentage === 'number' && (
              <span className="tag bg-slate-700 text-slate-300">{ctp.review_percentage}% of reviews</span>
            )}
            {ctp.source === 'discovery' && (
              <span className="tag bg-emerald-500/20 text-emerald-300">discovery</span>
            )}
          </div>
        </div>
        <div className="flex items-start gap-3 shrink-0">
          {typeof ctp.weight === 'number' && (
            <div className="flex flex-col items-center">
              <div className="text-3xl font-bold text-indigo-400">{ctp.weight}</div>
              <div className="text-xs text-slate-500">weight/10</div>
            </div>
          )}
          {sessionId && ctp.ctp_id && (
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="text-xs px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-slate-300 hover:text-white flex items-center gap-1.5"
              title="Re-run deep enrichment for this CTP only (uses the existing snippets, no re-discovery)"
            >
              <RefreshCw className={`w-3 h-3 ${regenerating ? 'animate-spin' : ''}`} />
              {regenerating ? 'Regenerating…' : 'Regenerate'}
            </button>
          )}
        </div>
      </div>
      {regenError && (
        <div className="mb-3 px-3 py-2 rounded bg-red-500/10 border border-red-500/30 text-red-300 text-xs flex items-center gap-2">
          <X className="w-4 h-4" /> {regenError}
        </div>
      )}

      {/* Archetype psychology + uniqueness + counter-segment (discovery v2) */}
      {(ctp.archetype_psychology || ctp.what_makes_them_unique || ctp.counter_segment) && (
        <div className="space-y-2 mb-4">
          {ctp.archetype_psychology && (
            <div className="bg-slate-800/40 rounded-lg p-3 border-l-2 border-indigo-500/40">
              <p className="text-xs text-indigo-400 mb-1 uppercase tracking-wider font-medium flex items-center gap-1">
                <Brain className="w-3 h-3" /> Psychology
              </p>
              <p className="text-sm text-slate-300">{ctp.archetype_psychology}</p>
            </div>
          )}
          {ctp.what_makes_them_unique && (
            <div className="bg-amber-500/5 rounded-lg p-3 border-l-2 border-amber-500/40">
              <p className="text-xs text-amber-400 mb-1 uppercase tracking-wider font-medium">
                What makes them unique
              </p>
              <p className="text-sm text-slate-300">{ctp.what_makes_them_unique}</p>
            </div>
          )}
          {ctp.counter_segment && (
            <div className="text-xs text-slate-500">
              <span className="text-slate-400">Not this segment:</span> {ctp.counter_segment}
            </div>
          )}
        </div>
      )}

      {/* Core insights */}
      {(ctp.core_insight_general || ctp.core_insight_product_anchored) && (
        <div className="grid md:grid-cols-2 gap-3 mb-4">
          {ctp.core_insight_general && (
            <div className="bg-indigo-500/10 rounded-xl p-3 border border-indigo-500/20">
              <p className="text-xs text-indigo-400 mb-1 uppercase tracking-wider font-medium">
                Core Insight (worldview)
              </p>
              <p className="text-sm text-slate-200 italic">"{ctp.core_insight_general}"</p>
            </div>
          )}
          {ctp.core_insight_product_anchored && (
            <div className="bg-cyan-500/10 rounded-xl p-3 border border-cyan-500/20">
              <p className="text-xs text-cyan-400 mb-1 uppercase tracking-wider font-medium">
                Product-Anchored (real quote)
              </p>
              <p className="text-sm text-slate-200 italic">
                "{ctp.core_insight_product_anchored}"
              </p>
            </div>
          )}
        </div>
      )}

      {/* Pain points + Barriers grid */}
      <div className="grid md:grid-cols-2 gap-4 mb-4">
        {pain.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-orange-400 mb-2 flex items-center gap-1">
              <AlertCircle className="w-4 h-4" /> Pain Points
            </h4>
            <ul className="space-y-1 text-sm text-slate-300">
              {pain.slice(0, 5).map((p, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-orange-400 mt-0.5">-</span>
                  <span>
                    {typeof p === 'string' ? p : p.pain_point}
                    {p.frequency ? (
                      <span className="text-xs text-slate-500 ml-1">({p.frequency})</span>
                    ) : null}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {barriers.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-red-400 mb-2 flex items-center gap-1">
              <Shield className="w-4 h-4" /> Barriers & Objections
            </h4>
            <ul className="space-y-2 text-sm text-slate-300">
              {barriers.slice(0, 4).map((b, i) => (
                <li key={i} className="bg-slate-800/50 p-2 rounded-lg">
                  {b.type && (
                    <span
                      className={`tag text-xs mr-1 ${
                        b.type === 'barrier'
                          ? 'bg-red-500/20 text-red-300'
                          : 'bg-amber-500/20 text-amber-300'
                      }`}
                    >
                      {b.type}
                    </span>
                  )}
                  <span>{b.prompt}</span>
                  {b.evidence && (
                    <p className="text-xs text-slate-500 mt-1">Evidence: {b.evidence}</p>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Desires + Behavioral Markers grid (discovery v2) */}
      {(desires.length > 0 || (ctp.behavioral_markers && ctp.behavioral_markers.length > 0)) && (
        <div className="grid md:grid-cols-2 gap-4 mb-4">
          {desires.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-emerald-400 mb-2 flex items-center gap-1">
                <Lightbulb className="w-4 h-4" /> Desires
              </h4>
              <ul className="space-y-1 text-sm text-slate-300">
                {desires.slice(0, 6).map((d, i) => {
                  const text = typeof d === 'string' ? d : d.desire || '';
                  return (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-emerald-400 mt-0.5">+</span>
                      <span>{text}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
          {ctp.behavioral_markers && ctp.behavioral_markers.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-purple-400 mb-2 flex items-center gap-1">
                <BookOpen className="w-4 h-4" /> Behavioral Markers
              </h4>
              <ul className="space-y-1 text-sm text-slate-300">
                {ctp.behavioral_markers.slice(0, 6).map((b, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-purple-400 mt-0.5">·</span>
                    <span>{b}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Decision factors (discovery v2) */}
      {ctp.decision_factors && ctp.decision_factors.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-cyan-400 mb-2">Decision Factors</h4>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {ctp.decision_factors.slice(0, 6).map((d, i) => (
              <div key={i} className="bg-slate-800/50 rounded-lg p-2 text-xs">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-slate-200 font-medium">{d.factor}</span>
                  {d.priority && (
                    <span
                      className={`tag text-[10px] ${
                        d.priority === 'high'
                          ? 'bg-red-500/20 text-red-300'
                          : d.priority === 'medium'
                          ? 'bg-amber-500/20 text-amber-300'
                          : 'bg-slate-600/30 text-slate-400'
                      }`}
                    >
                      {d.priority}
                    </span>
                  )}
                </div>
                {d.evidence && <p className="text-slate-500 text-[11px]">{d.evidence}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommended hooks + value props per-CTP (discovery v2) */}
      {(recommendedHooks.length > 0 || recommendedVPs.length > 0) && (
        <div className="grid md:grid-cols-2 gap-4 mb-4">
          {recommendedHooks.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-pink-400 mb-2">Recommended Hooks</h4>
              <ul className="space-y-2 text-sm text-slate-300">
                {recommendedHooks.slice(0, 5).map((h, i) => (
                  <li key={i} className="bg-slate-800/50 p-2 rounded-lg">
                    <p className="text-slate-200">"{h.hook}"</p>
                    <div className="flex items-center gap-2 mt-1">
                      {h.source && (
                        <span
                          className={`tag text-[10px] ${
                            h.source === 'from_brand_library'
                              ? 'bg-emerald-500/20 text-emerald-300'
                              : 'bg-pink-500/20 text-pink-300'
                          }`}
                        >
                          {h.source.replace(/_/g, ' ')}
                        </span>
                      )}
                      {h.rationale && <p className="text-[11px] text-slate-500">{h.rationale}</p>}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {recommendedVPs.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-blue-400 mb-2">Value Props</h4>
              <ul className="space-y-2 text-sm text-slate-300">
                {recommendedVPs.slice(0, 5).map((v, i) => (
                  <li key={i} className="bg-slate-800/50 p-2 rounded-lg">
                    <p className="text-slate-200">{v.value_prop}</p>
                    <div className="flex items-center gap-2 mt-1">
                      {v.source && (
                        <span
                          className={`tag text-[10px] ${
                            v.source === 'from_brand_library'
                              ? 'bg-emerald-500/20 text-emerald-300'
                              : 'bg-blue-500/20 text-blue-300'
                          }`}
                        >
                          {v.source.replace(/_/g, ' ')}
                        </span>
                      )}
                      {v.rationale && <p className="text-[11px] text-slate-500">{v.rationale}</p>}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Vocabulary tags (discovery v2) */}
      {ctp.vocabulary && ctp.vocabulary.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Their Vocabulary (verbatim)</h4>
          <div className="flex flex-wrap gap-1">
            {ctp.vocabulary.slice(0, 14).map((v, i) => (
              <span key={i} className="tag bg-violet-500/15 text-violet-300 italic">
                "{v}"
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Evidence quotes (discovery v2) — collapsible */}
      {ctp.evidence_quotes && ctp.evidence_quotes.length > 0 && (
        <details className="mb-4">
          <summary className="text-sm font-semibold text-cyan-400 cursor-pointer flex items-center gap-1">
            <Quote className="w-4 h-4" /> Evidence Quotes ({ctp.evidence_quotes.length})
          </summary>
          <div className="space-y-2 mt-2 pl-2">
            {ctp.evidence_quotes.map((q, i) => (
              <blockquote
                key={i}
                className="text-sm text-slate-300 italic border-l-2 border-cyan-500/40 pl-3"
              >
                "{q}"
              </blockquote>
            ))}
          </div>
        </details>
      )}

      {/* Frameworks that resonate (discovery v2) */}
      {ctp.frameworks_that_resonate && ctp.frameworks_that_resonate.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Frameworks that resonate</h4>
          <div className="space-y-1">
            {ctp.frameworks_that_resonate.map((f, i) => (
              <div key={i} className="text-sm">
                <span className="text-amber-300 font-medium">{f.framework}</span>
                {f.rationale && <span className="text-slate-500"> — {f.rationale}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tone / emotion arc (discovery v2) */}
      {ctp.tone_and_emotion_arc && (ctp.tone_and_emotion_arc.primary_tone || ctp.tone_and_emotion_arc.emotion_arc) && (
        <div className="mb-4 grid sm:grid-cols-2 gap-2 text-xs">
          {ctp.tone_and_emotion_arc.primary_tone && (
            <div className="bg-slate-800/50 p-2 rounded">
              <p className="text-slate-500">Tone</p>
              <p className="text-slate-200 font-medium">{ctp.tone_and_emotion_arc.primary_tone}</p>
            </div>
          )}
          {ctp.tone_and_emotion_arc.emotion_arc && (
            <div className="bg-slate-800/50 p-2 rounded">
              <p className="text-slate-500">Emotion Arc</p>
              <p className="text-slate-200 font-medium">{ctp.tone_and_emotion_arc.emotion_arc}</p>
            </div>
          )}
        </div>
      )}

      {/* Ad creative gap + anti-patterns (discovery v2) */}
      {(ctp.ad_creative_gap || (ctp.anti_patterns && ctp.anti_patterns.length > 0)) && (
        <div className="mb-4 space-y-2">
          {ctp.ad_creative_gap && (
            <div className="bg-rose-500/5 border-l-2 border-rose-500/40 pl-3 py-2 text-sm">
              <span className="text-rose-400 font-medium text-xs uppercase">Creative gap: </span>
              <span className="text-slate-300">{ctp.ad_creative_gap}</span>
            </div>
          )}
          {ctp.anti_patterns && ctp.anti_patterns.length > 0 && (
            <div className="text-xs text-slate-500 space-y-1">
              <p className="text-slate-400 font-medium">Avoid:</p>
              <ul className="pl-3 space-y-0.5">
                {ctp.anti_patterns.map((a, i) => (
                  <li key={i}>· {a}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Kill signals */}
      {(kill.existence?.length || kill.engagement?.length || kill.conversion?.length) ? (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-emerald-400 mb-2 flex items-center gap-1">
            <Target className="w-4 h-4" /> Kill Signals
          </h4>
          <div className="grid md:grid-cols-3 gap-3">
            <SignalColumn title="Existence" items={kill.existence || []} color="emerald" />
            <SignalColumn title="Engagement" items={kill.engagement || []} color="cyan" />
            <SignalColumn title="Conversion" items={kill.conversion || []} color="indigo" />
          </div>
        </div>
      ) : null}

      {/* Language cues + source distribution */}
      {(cues.length > 0 || Object.keys(sourceDist).length > 0) && (
        <div className="grid md:grid-cols-2 gap-4 mb-4 text-xs">
          {cues.length > 0 && (
            <div>
              <p className="text-slate-500 mb-1">Language cues:</p>
              <div className="flex flex-wrap gap-1">
                {cues.slice(0, 8).map((c, i) => (
                  <span key={i} className="tag bg-slate-700 text-slate-300">
                    "{c}"
                  </span>
                ))}
              </div>
            </div>
          )}
          {Object.keys(sourceDist).length > 0 && (
            <div>
              <p className="text-slate-500 mb-1">Source distribution:</p>
              <div className="flex flex-wrap gap-1">
                {Object.entries(sourceDist)
                  .sort((a, b) => (b[1] || 0) - (a[1] || 0))
                  .slice(0, 5)
                  .map(([src, n]) => (
                    <span key={src} className="tag bg-slate-700 text-slate-300">
                      {src}: {n}
                    </span>
                  ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Sample representative snippets */}
      {sampleSnippets.length > 0 && (
        <details className="mb-4">
          <summary className="text-sm text-slate-400 cursor-pointer hover:text-slate-200">
            Show {sampleSnippets.length} representative snippets
          </summary>
          <div className="space-y-2 mt-2">
            {sampleSnippets.map((s, i) => (
              <blockquote
                key={i}
                className="text-xs text-slate-400 italic border-l-2 border-indigo-500/30 pl-2"
              >
                "{s.content}"
                {s.source_type && (
                  <span className="not-italic text-slate-500 block">— {s.source_type}</span>
                )}
              </blockquote>
            ))}
          </div>
        </details>
      )}

      {/* Hypothesis layer (ad strategy) */}
      {hypo && (
        <div className="mt-4 pt-4 border-t border-slate-700/50">
          <h4 className="text-sm font-semibold text-amber-400 mb-3 flex items-center gap-1">
            <Zap className="w-4 h-4" /> Hypothesis Layer (Ad Strategy)
          </h4>

          {/* Demographics */}
          {hypo.demographic_variables && (
            <div className="grid md:grid-cols-4 gap-2 mb-3 text-xs">
              {hypo.demographic_variables.age_range && (
                <div className="bg-slate-800/50 p-2 rounded">
                  <p className="text-slate-500">Age</p>
                  <p className="text-slate-200">{hypo.demographic_variables.age_range}</p>
                </div>
              )}
              {hypo.demographic_variables.gender_skew && (
                <div className="bg-slate-800/50 p-2 rounded">
                  <p className="text-slate-500">Gender</p>
                  <p className="text-slate-200">{hypo.demographic_variables.gender_skew}</p>
                </div>
              )}
              {hypo.demographic_variables.income_level && (
                <div className="bg-slate-800/50 p-2 rounded">
                  <p className="text-slate-500">Income</p>
                  <p className="text-slate-200">{hypo.demographic_variables.income_level}</p>
                </div>
              )}
              {hypo.demographic_variables.education && (
                <div className="bg-slate-800/50 p-2 rounded">
                  <p className="text-slate-500">Education</p>
                  <p className="text-slate-200">{hypo.demographic_variables.education}</p>
                </div>
              )}
            </div>
          )}

          {/* Angles */}
          {angles.length > 0 && (
            <div className="mb-3">
              <p className="text-xs text-slate-500 mb-2">Angle suggestions:</p>
              <div className="space-y-2">
                {angles.map((a, i) => (
                  <div
                    key={i}
                    className="bg-amber-500/10 rounded-lg p-3 border border-amber-500/20"
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <p className="font-semibold text-amber-300 text-sm">{a.angle_name}</p>
                      <div className="flex gap-1 flex-shrink-0">
                        {a.validation_tag && (
                          <span
                            className={`tag text-xs ${
                              a.validation_tag === 'data_backed'
                                ? 'bg-green-500/20 text-green-400'
                                : 'bg-slate-700 text-slate-300'
                            }`}
                          >
                            {a.validation_tag}
                          </span>
                        )}
                        {a.awareness_level && (
                          <span className="tag text-xs bg-blue-500/20 text-blue-400">
                            {a.awareness_level}
                          </span>
                        )}
                      </div>
                    </div>
                    <p className="text-xs text-slate-300">{a.angle_description}</p>
                    {a.emotional_trigger && (
                      <p className="text-xs text-pink-400 mt-1">
                        Emotion: {a.emotional_trigger}
                      </p>
                    )}
                    {a.validation_evidence && (
                      <p className="text-xs text-slate-500 mt-1 italic">
                        {a.validation_evidence}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Strategy blocks grid */}
          <div className="grid md:grid-cols-2 gap-2 text-xs">
            {hypo.funnel_stage?.stage && (
              <HypoTile label="Funnel Stage" value={hypo.funnel_stage.stage} rationale={hypo.funnel_stage.rationale} />
            )}
            {hypo.framework_tactic?.primary && (
              <HypoTile
                label="Framework"
                value={`${hypo.framework_tactic.primary}${hypo.framework_tactic.secondary ? ` + ${hypo.framework_tactic.secondary}` : ''}`}
                rationale={hypo.framework_tactic.rationale}
              />
            )}
            {hypo.visual_style?.style && (
              <HypoTile label="Visual Style" value={hypo.visual_style.style} rationale={hypo.visual_style.rationale} />
            )}
            {hypo.narrative_driver?.driver && (
              <HypoTile
                label="Narrative Driver"
                value={hypo.narrative_driver.driver}
                rationale={hypo.narrative_driver.rationale}
              />
            )}
            {hypo.tone?.primary && (
              <HypoTile
                label="Tone"
                value={`${hypo.tone.primary}${hypo.tone.secondary ? ` / ${hypo.tone.secondary}` : ''}`}
                rationale={hypo.tone.rationale}
              />
            )}
            {hypo.emotion?.arc && (
              <HypoTile
                label="Emotion Arc"
                value={hypo.emotion.arc}
                rationale={hypo.emotion.rationale}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function SignalColumn({
  title,
  items,
  color,
}: {
  title: string;
  items: string[];
  color: 'emerald' | 'cyan' | 'indigo';
}) {
  const colorMap: Record<string, string> = {
    emerald: 'text-emerald-400',
    cyan: 'text-cyan-400',
    indigo: 'text-indigo-400',
  };
  return (
    <div className="bg-slate-800/50 rounded-lg p-3">
      <p className={`text-xs font-semibold mb-1 ${colorMap[color]}`}>{title}</p>
      {items.length === 0 ? (
        <p className="text-xs text-slate-500">—</p>
      ) : (
        <ul className="space-y-0.5 text-xs text-slate-300">
          {items.slice(0, 4).map((s, i) => (
            <li key={i}>• {s}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function HypoTile({
  label,
  value,
  rationale,
}: {
  label: string;
  value: string;
  rationale?: string;
}) {
  return (
    <div className="bg-slate-800/50 rounded-lg p-2">
      <p className="text-slate-500">{label}</p>
      <p className="text-slate-200 font-medium">{value}</p>
      {rationale && <p className="text-slate-500 text-[11px] mt-1">{rationale}</p>}
    </div>
  );
}
