import { useState } from 'react';
import {
  Loader2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  PenTool,
  Image,
  TestTube,
  Sparkles,
  Lightbulb,
  Quote,
  Users,
  ClipboardList,
  MessageCircle,
  Brain,
} from 'lucide-react';
import type { Insight } from '../api/client';

function toStringArray(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String).filter(Boolean);
  if (typeof value === 'string' && value.trim()) return [value.trim()];
  return [];
}

function normalizeScript(script: any) {
  return {
    ...script,
    based_on_verbatims: toStringArray(script?.based_on_verbatims ?? script?.verbatims_used),
  };
}

function normalizeThumbnail(thumb: any) {
  const visualElements = toStringArray(thumb?.visual_elements);
  return {
    ...thumb,
    thumbnail_type: thumb?.thumbnail_type ?? thumb?.visual_style ?? thumb?.first_frame_element,
    visual_description: thumb?.visual_description ?? thumb?.description ?? visualElements.join(', '),
    emotion_evoked: thumb?.emotion_evoked ?? thumb?.emotion_target ?? thumb?.target_emotion,
    why_it_works: thumb?.why_it_works ?? thumb?.why_effective,
    platform_fit: toStringArray(thumb?.platform_fit ?? thumb?.platforms),
  };
}

function normalizeABTest(test: any) {
  const expectedImpact = typeof test?.expected_impact === 'string' ? test.expected_impact.toLowerCase() : undefined;
  return {
    ...test,
    priority: test?.priority ?? expectedImpact ?? 'medium',
    test_type: test?.test_type ?? test?.element_being_tested,
    control: test?.control ?? test?.variant_a,
    variant: test?.variant ?? test?.variant_b,
    rationale: test?.rationale ?? test?.data_supporting_test,
  };
}

export default function GeneratedContentView({ insights, sessionId }: { insights: Insight; sessionId: number }) {
  const scripts = ((insights as any).generated_scripts || []).map(normalizeScript);
  const thumbnails = ((insights as any).thumbnail_suggestions || []).map(normalizeThumbnail);
  const abTests = ((insights as any).ab_test_suggestions || []).map(normalizeABTest);
  const ugcBriefs = (insights as any).ugc_briefs || [];
  const survey = (insights as any).post_purchase_survey || {};
  const verbatimQuotes = (insights as any).verbatim_quotes || [];
  const painPoints = (insights as any).pain_points || [];
  const [expandedSources, setExpandedSources] = useState<Set<number>>(new Set());
  const [isGenerating, setIsGenerating] = useState(false);
  const [localScripts, setLocalScripts] = useState(scripts);

  const handleGenerateMore = async () => {
    setIsGenerating(true);
    try {
      const response = await fetch(`/api/research/session/${sessionId}/generate-scripts?count=3`, {
        method: 'POST'
      });
      if (response.ok) {
        const data = await response.json();
        setLocalScripts([...localScripts, ...((data.new_scripts || []).map(normalizeScript))]);
      }
    } catch (error) {
      console.error('Failed to generate scripts:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  const toggleSources = (index: number) => {
    const newSet = new Set(expandedSources);
    if (newSet.has(index)) {
      newSet.delete(index);
    } else {
      newSet.add(index);
    }
    setExpandedSources(newSet);
  };

  return (
    <div className="space-y-6">
      {(localScripts && localScripts.length > 0) || scripts.length === 0 ? (
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <PenTool className="w-5 h-5 text-indigo-400" />
              Generated Ad Scripts ({(localScripts || scripts).length})
            </h3>
            <button
              onClick={handleGenerateMore}
              disabled={isGenerating}
              className="btn-primary text-sm py-2 px-4 flex items-center gap-2 disabled:opacity-50"
            >
              {isGenerating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              Generate More Scripts
            </button>
          </div>
          <div className="space-y-6">
            {(localScripts || scripts).map((script: any, i: number) => (
              <div key={i} className="bg-slate-800/50 p-5 rounded-xl border border-slate-700/50">
                <div className="flex items-start justify-between mb-3">
                  <h4 className="font-semibold text-indigo-300">{script.script_name}</h4>
                  <div className="flex gap-2">
                    <span className="tag text-xs bg-indigo-500/20 text-indigo-400">{script.framework}</span>
                    <span className="tag text-xs bg-green-500/20 text-green-400">{script.hook_type}</span>
                    <span className="tag text-xs bg-slate-700 text-slate-300">~{script.estimated_length_seconds}s</span>
                  </div>
                </div>

                <div className="mb-3">
                  <p className="text-xs text-slate-500 mb-1">Hook:</p>
                  <p className="text-white font-medium bg-slate-900/50 p-2 rounded">{script.hook}</p>
                </div>

                <div className="mb-3">
                  <p className="text-xs text-slate-500 mb-1">Full Script:</p>
                  <pre className="text-sm text-slate-300 bg-slate-900/50 p-3 rounded whitespace-pre-wrap font-sans">
                    {script.full_script || script.body}
                  </pre>
                </div>

                {script.why_it_works && (
                  <div className="bg-green-500/10 p-3 rounded border border-green-500/20 mb-3">
                    <p className="text-xs text-green-400">
                      <strong>Why it works:</strong> {script.why_it_works}
                    </p>
                  </div>
                )}

                {/* Data Sources Section */}
                <div className="mt-4 border-t border-slate-700/50 pt-4">
                  <button
                    onClick={() => toggleSources(i)}
                    className="flex items-center gap-2 text-sm text-amber-400 hover:text-amber-300 transition-colors"
                  >
                    <Lightbulb className="w-4 h-4" />
                    <span className="font-medium">Data Sources</span>
                    {expandedSources.has(i) ? (
                      <ChevronUp className="w-4 h-4" />
                    ) : (
                      <ChevronDown className="w-4 h-4" />
                    )}
                  </button>

                  {expandedSources.has(i) && (
                    <div className="mt-3 space-y-4">
                      {/* Script-specific sources (if available from backend) */}
                      {script.based_on_verbatims && script.based_on_verbatims.length > 0 && (
                        <div className="bg-slate-900/50 p-3 rounded-lg">
                          <h5 className="text-xs font-medium text-indigo-400 mb-2 flex items-center gap-1">
                            <Quote className="w-3 h-3" />
                            Verbatim Quotes Used
                          </h5>
                          <div className="space-y-2">
                            {script.based_on_verbatims.map((q: string, j: number) => (
                              <blockquote key={j} className="text-xs text-slate-400 italic border-l-2 border-indigo-500/50 pl-2">
                                "{q}"
                              </blockquote>
                            ))}
                          </div>
                        </div>
                      )}

                      {script.pain_points_addressed && script.pain_points_addressed.length > 0 && (
                        <div className="bg-slate-900/50 p-3 rounded-lg">
                          <h5 className="text-xs font-medium text-orange-400 mb-2 flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" />
                            Pain Points Addressed
                          </h5>
                          <div className="flex flex-wrap gap-1">
                            {script.pain_points_addressed.map((p: string, j: number) => (
                              <span key={j} className="tag text-xs bg-orange-500/20 text-orange-300">{p}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Fallback: Show general insights if no script-specific sources */}
                      {(!script.based_on_verbatims || script.based_on_verbatims.length === 0) && verbatimQuotes.length > 0 && (
                        <div className="bg-slate-900/50 p-3 rounded-lg">
                          <h5 className="text-xs font-medium text-indigo-400 mb-2 flex items-center gap-1">
                            <Quote className="w-3 h-3" />
                            Sample Verbatim Quotes (from research)
                          </h5>
                          <div className="space-y-2">
                            {verbatimQuotes.slice(0, 3).map((q: any, j: number) => (
                              <blockquote key={j} className="text-xs text-slate-400 italic border-l-2 border-indigo-500/50 pl-2">
                                "{typeof q === 'string' ? q : q.quote}"
                                {typeof q !== 'string' && q.use_case && (
                                  <span className="text-indigo-500 not-italic block mt-1">→ {q.use_case}</span>
                                )}
                              </blockquote>
                            ))}
                          </div>
                        </div>
                      )}

                      {(!script.pain_points_addressed || script.pain_points_addressed.length === 0) && painPoints.length > 0 && (
                        <div className="bg-slate-900/50 p-3 rounded-lg">
                          <h5 className="text-xs font-medium text-orange-400 mb-2 flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" />
                            Research Pain Points
                          </h5>
                          <div className="flex flex-wrap gap-1">
                            {painPoints.slice(0, 5).map((p: string, j: number) => (
                              <span key={j} className="tag text-xs bg-orange-500/20 text-orange-300">{p}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Target emotion / best for */}
                      <div className="flex flex-wrap gap-4 text-xs text-slate-500">
                        {script.target_emotion && (
                          <span>
                            <span className="text-pink-400">Target Emotion:</span> {script.target_emotion}
                          </span>
                        )}
                        {script.best_for && (
                          <span>
                            <span className="text-cyan-400">Best For:</span> {script.best_for}
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Thumbnail Suggestions */}
      {thumbnails && thumbnails.length > 0 && (
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Image className="w-5 h-5 text-pink-400" />
            Thumbnail / First Frame Suggestions
          </h3>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {thumbnails.map((thumb: any, i: number) => (
              <div key={i} className="bg-gradient-to-br from-slate-800/80 to-pink-900/20 p-4 rounded-xl border border-pink-500/20">
                <h4 className="font-semibold text-pink-300 mb-2">{thumb.concept_name}</h4>
                <div className="space-y-2 text-sm">
                  <p className="text-slate-400">
                    <span className="text-pink-400">Type:</span> {thumb.thumbnail_type}
                  </p>
                  <p className="text-slate-400">
                    <span className="text-pink-400">Visual:</span> {thumb.visual_description?.slice(0, 100)}
                  </p>
                  {thumb.text_overlay && (
                    <p className="text-white font-medium bg-slate-900/50 p-2 rounded">
                      "{thumb.text_overlay}"
                    </p>
                  )}
                  <p className="text-slate-400">
                    <span className="text-pink-400">Emotion:</span> {thumb.emotion_evoked}
                  </p>
                </div>
                {thumb.platform_fit && (
                  <div className="flex gap-1 mt-3">
                    {thumb.platform_fit.map((p: string, j: number) => (
                      <span key={j} className="tag text-xs bg-slate-700 text-slate-300">{p}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* A/B Test Suggestions */}
      {abTests && abTests.length > 0 && (
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <TestTube className="w-5 h-5 text-cyan-400" />
            A/B Test Suggestions
          </h3>
          <div className="space-y-4">
            {abTests.map((test: any, i: number) => (
              <div key={i} className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
                <div className="flex items-start justify-between mb-3">
                  <h4 className="font-semibold text-cyan-300">{test.test_name}</h4>
                  <div className="flex gap-2">
                    <span className={`tag text-xs ${test.priority === 'high' ? 'bg-red-500/20 text-red-400' :
                      test.priority === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-slate-700 text-slate-400'
                      }`}>
                      {test.priority} priority
                    </span>
                    <span className="tag text-xs bg-cyan-500/20 text-cyan-400">{test.test_type}</span>
                  </div>
                </div>

                <p className="text-sm text-slate-400 mb-3">
                  <strong>Hypothesis:</strong> {test.hypothesis}
                </p>

                <div className="grid md:grid-cols-2 gap-3">
                  <div className="bg-slate-900/50 p-3 rounded">
                    <p className="text-xs text-slate-500 mb-1">Control (A)</p>
                    <p className="text-sm text-slate-300">{test.control?.description || test.control}</p>
                  </div>
                  <div className="bg-cyan-500/10 p-3 rounded border border-cyan-500/20">
                    <p className="text-xs text-cyan-400 mb-1">Variant (B)</p>
                    <p className="text-sm text-slate-300">{test.variant?.description || test.variant}</p>
                  </div>
                </div>

                {test.expected_impact && (
                  <p className="text-xs text-slate-500 mt-3">
                    <strong>Expected Impact:</strong> {test.expected_impact}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* UGC Creator Briefs */}
      {ugcBriefs && ugcBriefs.length > 0 && (
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-orange-400" />
            UGC Creator Briefs ({ugcBriefs.length})
          </h3>
          <div className="space-y-6">
            {ugcBriefs.map((brief: any, i: number) => (
              <div key={i} className="bg-slate-800/50 p-5 rounded-xl border border-orange-500/20">
                <div className="flex items-start justify-between mb-3">
                  <h4 className="font-semibold text-orange-300">{brief.brief_name}</h4>
                  <div className="flex gap-2">
                    <span className="tag text-xs bg-orange-500/20 text-orange-400">{brief.angle_type}</span>
                    <span className="tag text-xs bg-slate-700 text-slate-300">{brief.awareness_level}</span>
                  </div>
                </div>

                {brief.target_persona && (
                  <p className="text-sm text-slate-400 mb-3">
                    <span className="text-orange-400">Target:</span> {brief.target_persona}
                  </p>
                )}

                {brief.overview && (
                  <p className="text-sm text-slate-300 mb-4">{brief.overview}</p>
                )}

                {/* Hook Non-Negotiable */}
                {brief.hook_non_negotiable && (
                  <div className="mb-4 p-4 bg-red-500/10 rounded-lg border border-red-500/20">
                    <h5 className="text-xs font-bold text-red-400 mb-2 uppercase tracking-wider">Hook — Non-Negotiable</h5>
                    <p className="text-white font-medium text-lg mb-2">"{brief.hook_non_negotiable.exact_line}"</p>
                    <div className="space-y-1 text-xs text-slate-400">
                      {brief.hook_non_negotiable.visual_direction && <p><span className="text-red-400">Visual:</span> {brief.hook_non_negotiable.visual_direction}</p>}
                      {brief.hook_non_negotiable.energy && <p><span className="text-red-400">Energy:</span> {brief.hook_non_negotiable.energy}</p>}
                      {brief.hook_non_negotiable.what_not_to_do && <p><span className="text-red-400">Do NOT:</span> {brief.hook_non_negotiable.what_not_to_do}</p>}
                    </div>
                  </div>
                )}

                {/* Talking Points */}
                {brief.body_talking_points && brief.body_talking_points.length > 0 && (
                  <div className="mb-4">
                    <h5 className="text-xs font-medium text-orange-400 mb-2">Talking Points:</h5>
                    <ol className="space-y-2">
                      {brief.body_talking_points.map((point: string, j: number) => (
                        <li key={j} className="text-sm text-slate-300 flex items-start gap-2">
                          <span className="bg-orange-500/20 text-orange-400 rounded-full w-5 h-5 flex items-center justify-center text-xs flex-shrink-0 mt-0.5">{j + 1}</span>
                          {point}
                        </li>
                      ))}
                    </ol>
                  </div>
                )}

                {/* Must Say Verbatim */}
                {brief.must_say_verbatim && brief.must_say_verbatim.length > 0 && (
                  <div className="mb-3 flex flex-wrap gap-2">
                    <span className="text-xs text-slate-500">Must say:</span>
                    {brief.must_say_verbatim.map((phrase: string, j: number) => (
                      <span key={j} className="tag text-xs bg-amber-500/20 text-amber-300">"{phrase}"</span>
                    ))}
                  </div>
                )}

                {/* Emotional Journey */}
                {brief.emotional_journey && (
                  <div className="mb-3 p-2 bg-slate-900/50 rounded flex items-center gap-2">
                    <Brain className="w-4 h-4 text-pink-400 flex-shrink-0" />
                    <p className="text-xs text-slate-400"><span className="text-pink-400">Emotional Arc:</span> {brief.emotional_journey}</p>
                  </div>
                )}

                {/* Close */}
                {brief.close && (
                  <div className="mb-3 p-3 bg-green-500/10 rounded-lg border border-green-500/20">
                    <p className="text-xs text-green-400 mb-1">Close:</p>
                    <p className="text-sm text-slate-300">{brief.close.how_it_ends}</p>
                    {brief.close.cta_language && <p className="text-sm text-white font-medium mt-1">CTA: "{brief.close.cta_language}"</p>}
                  </div>
                )}

                {/* Production Notes */}
                {brief.production_notes && (
                  <div className="text-xs text-slate-500 space-y-1 mt-3 border-t border-slate-700/50 pt-3">
                    {brief.production_notes.setting && <p><span className="text-slate-400">Setting:</span> {brief.production_notes.setting}</p>}
                    {brief.production_notes.wardrobe && <p><span className="text-slate-400">Wardrobe:</span> {brief.production_notes.wardrobe}</p>}
                    {brief.production_notes.what_to_avoid && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        <span className="text-red-400">Avoid:</span>
                        {brief.production_notes.what_to_avoid.map((item: string, j: number) => (
                          <span key={j} className="tag text-xs bg-red-500/10 text-red-300">{item}</span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Post-Purchase Survey */}
      {survey && (survey.core_five?.length > 0 || survey.single_best_question) && (
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <ClipboardList className="w-5 h-5 text-teal-400" />
            Post-Purchase Survey (Creative Intelligence)
          </h3>

          {/* Single Best Question */}
          {survey.single_best_question && (
            <div className="mb-6 p-4 bg-teal-500/10 rounded-xl border border-teal-500/20">
              <p className="text-xs text-teal-400 font-bold uppercase tracking-wider mb-2">The Single Best Question</p>
              <p className="text-white font-medium text-lg mb-2">"{survey.single_best_question.question}"</p>
              {survey.single_best_question.why_its_the_best && (
                <p className="text-sm text-slate-400">{survey.single_best_question.why_its_the_best}</p>
              )}
            </div>
          )}

          {/* Core Five */}
          {survey.core_five && survey.core_five.length > 0 && (
            <div className="mb-6">
              <h4 className="text-sm font-medium text-teal-400 mb-3">Core Questions ({survey.core_five.length})</h4>
              <div className="space-y-3">
                {survey.core_five.map((q: any, i: number) => (
                  <div key={i} className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
                    <p className="text-white font-medium mb-2 flex items-start gap-2">
                      <MessageCircle className="w-4 h-4 text-teal-400 mt-0.5 flex-shrink-0" />
                      "{q.question}"
                    </p>
                    <div className="grid md:grid-cols-2 gap-2 text-xs text-slate-400">
                      {q.creative_output_designed_for && <p><span className="text-teal-400">Designed to produce:</span> {q.creative_output_designed_for}</p>}
                      {q.awareness_level_surfaced && <p><span className="text-teal-400">Surfaces:</span> {q.awareness_level_surfaced} language</p>}
                    </div>
                    {q.example_winning_response && (
                      <p className="text-xs text-slate-500 mt-2 italic">Example response: "{q.example_winning_response}"</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Category-Specific Questions */}
          {survey.category_specific_questions && survey.category_specific_questions.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-medium text-teal-400 mb-3">Category-Specific Questions</h4>
              <div className="space-y-2">
                {survey.category_specific_questions.map((q: any, i: number) => (
                  <div key={i} className="bg-slate-800/50 p-3 rounded-lg">
                    <p className="text-sm text-white mb-1">"{q.question}"</p>
                    {q.angle_it_surfaces && <p className="text-xs text-slate-500">Surfaces: {q.angle_it_surfaces}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Survey Design Notes */}
          {survey.survey_design_notes && (
            <div className="p-3 bg-slate-800/50 rounded-lg text-xs text-slate-400 space-y-1">
              {survey.survey_design_notes.recommended_timing && <p><span className="text-teal-400">Timing:</span> {survey.survey_design_notes.recommended_timing}</p>}
              {survey.survey_design_notes.recommended_format && <p><span className="text-teal-400">Format:</span> {survey.survey_design_notes.recommended_format}</p>}
              {survey.survey_design_notes.framing_mistake_to_avoid && <p><span className="text-red-400">Avoid:</span> {survey.survey_design_notes.framing_mistake_to_avoid}</p>}
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {scripts.length === 0 && thumbnails.length === 0 && abTests.length === 0 && ugcBriefs.length === 0 && (
        <div className="text-center py-12">
          <PenTool className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg text-slate-400">No generated content yet</h3>
          <p className="text-sm text-slate-500">Content will be generated after Ad Library analysis</p>
        </div>
      )}
    </div>
  );
}
