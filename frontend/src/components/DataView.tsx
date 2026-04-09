import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Loader2,
  Star,
  Play,
  ExternalLink,
} from 'lucide-react';
import { getSessionData } from '../api/client';
import type { ScrapedData } from '../api/client';

export default function DataView({ sessionId, bySource }: { sessionId: number; bySource: Record<string, number> }) {
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [selectedTrack, setSelectedTrack] = useState<number | null>(null);

  const { data: scrapedData, isLoading } = useQuery({
    queryKey: ['data', sessionId, selectedSource, selectedTrack],
    queryFn: () => getSessionData(sessionId, selectedSource || undefined, selectedTrack || undefined),
  });

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => { setSelectedSource(null); setSelectedTrack(null); }}
          className={`tag ${!selectedSource && !selectedTrack ? 'tag-primary' : 'bg-slate-800 text-slate-400'}`}
        >
          All
        </button>
        <span className="text-slate-600">|</span>
        <button
          onClick={() => setSelectedTrack(selectedTrack === 1 ? null : 1)}
          className={`tag ${selectedTrack === 1 ? 'tag-success' : 'bg-slate-800 text-slate-400'}`}
        >
          Track 1: Brand
        </button>
        <button
          onClick={() => setSelectedTrack(selectedTrack === 2 ? null : 2)}
          className={`tag ${selectedTrack === 2 ? 'tag-warning' : 'bg-slate-800 text-slate-400'}`}
        >
          Track 2: Segment
        </button>
        <span className="text-slate-600">|</span>
        {Object.entries(bySource).map(([source, count]) => (
          <button
            key={source}
            onClick={() => setSelectedSource(selectedSource === source ? null : source)}
            className={`tag ${selectedSource === source ? 'tag-primary' : 'bg-slate-800 text-slate-400'}`}
          >
            {source} ({count})
          </button>
        ))}
      </div>

      {/* Data List */}
      {isLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
        </div>
      ) : (
        <div className="space-y-3">
          {scrapedData?.map((item) => (
            <DataCard key={item.id} data={item} />
          ))}
          {scrapedData?.length === 0 && (
            <p className="text-center text-slate-500 py-8">No data found</p>
          )}
        </div>
      )}
    </div>
  );
}

function DataCard({ data }: { data: ScrapedData }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const rawVideoAnalysis = (data as any).video_analysis;

  // Parse video analysis if it's a string
  const videoAnalysis = typeof rawVideoAnalysis === 'string'
    ? JSON.parse(rawVideoAnalysis)
    : rawVideoAnalysis;

  // Extract nested structures (handle both old and new formats)
  const contentAnalysis = videoAnalysis?.['Content Analysis'] || videoAnalysis;
  const formatStyle = videoAnalysis?.['Format & Style'] || videoAnalysis;
  const insightsForAds = videoAnalysis?.['Insights for Ads'] || videoAnalysis;
  const engagementFactors = videoAnalysis?.['Engagement Factors'] || videoAnalysis;

  // New IMA-style dimensions (flat structure from updated prompt)
  const viralFormat = videoAnalysis?.creative_format || contentAnalysis?.creative_format;
  const trendDetected = videoAnalysis?.trend_detected || contentAnalysis?.trend_detected;
  const trendName = videoAnalysis?.trend_name || contentAnalysis?.trend_name;
  const soundName = videoAnalysis?.sound_name;
  const soundViralPotential = videoAnalysis?.sound_viral_potential;
  const hookStrength = videoAnalysis?.hook_strength || contentAnalysis?.hook_strength_1to5;
  const hookTechnique = videoAnalysis?.hook_technique;
  const firstFrame = videoAnalysis?.first_frame_element;
  const effectivenessScore = videoAnalysis?.effectiveness_score;
  const sceneBreakdown = videoAnalysis?.scene_breakdown || [];
  const replicationDifficulty = videoAnalysis?.replication_difficulty;

  return (
    <div className="glass-card p-4 hover:border-slate-600/50 transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className={`tag text-xs ${data.track === 1 ? 'tag-success' : 'tag-warning'}`}>
              Track {data.track}
            </span>
            <span className="tag bg-slate-700 text-slate-300 text-xs capitalize">
              {data.source_type.replace(/_/g, ' ')}
            </span>
            {(data as any).validation_level === 2 && (
              <span className="tag text-xs bg-emerald-500/20 text-emerald-400">
                📋 Client Provided
              </span>
            )}
            {data.rating && (
              <span className="flex items-center gap-1 text-yellow-400 text-sm">
                <Star className="w-3 h-3" />
                {data.rating}
              </span>
            )}
            {videoAnalysis && (
              <>
                <span className="tag text-xs bg-purple-500/20 text-purple-400">
                  🎬 Video Analyzed
                </span>
                {/* Viral Format Badge (NEW) */}
                {viralFormat && (
                  <span className="tag text-xs bg-pink-500/20 text-pink-400">
                    📱 {viralFormat}
                  </span>
                )}
                {/* Trend Badge (NEW) */}
                {trendDetected && trendName && (
                  <span className="tag text-xs bg-fuchsia-500/20 text-fuchsia-400">
                    🔥 {trendName}
                  </span>
                )}
                {/* Hook Strength (enhanced) */}
                {hookStrength && (
                  <span className={`tag text-xs ${hookStrength >= 4
                    ? 'bg-green-500/20 text-green-400'
                    : hookStrength >= 3
                      ? 'bg-yellow-500/20 text-yellow-400'
                      : 'bg-red-500/20 text-red-400'
                    }`}>
                    Hook: {hookStrength}/5
                  </span>
                )}
                {/* Effectiveness Score (NEW) */}
                {effectivenessScore && (
                  <span className="tag text-xs bg-amber-500/20 text-amber-400">
                    ⭐ {effectivenessScore}/5
                  </span>
                )}
                {/* Trending Sound (NEW) */}
                {soundName && (
                  <span className="tag text-xs bg-violet-500/20 text-violet-400" title={`Viral Potential: ${soundViralPotential || '?'}/5`}>
                    🎵 {soundName.length > 20 ? soundName.slice(0, 20) + '...' : soundName}
                  </span>
                )}
                {formatStyle?.duration_seconds && (
                  <span className="tag text-xs bg-slate-600/50 text-slate-300">
                    {Math.round(formatStyle.duration_seconds)}s
                  </span>
                )}
              </>
            )}
          </div>

          {data.title && (
            <h4 className="font-medium text-white mb-1 truncate">{data.title}</h4>
          )}

          <p className={`text-sm text-slate-400 ${isExpanded ? '' : 'line-clamp-2'}`}>
            {data.content}
          </p>

          {((data.content && data.content.length > 200) || videoAnalysis) && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-xs text-indigo-400 hover:text-indigo-300 mt-1"
            >
              {isExpanded ? 'Show less' : 'Show more'}
            </button>
          )}

          {/* Enhanced Video Analysis Section */}
          {videoAnalysis && isExpanded && (
            <div className="mt-3 space-y-3">
              {/* Inline Video Player */}
              {((data as any).video_file || (data as any).source_url) && (
                <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-600/30">
                  <p className="text-xs text-slate-400 font-medium mb-2 flex items-center gap-2">
                    <Play className="w-3 h-3" />
                    Video Preview
                  </p>
                  {(data as any).video_file ? (
                    <video
                      controls
                      className="w-full max-h-64 rounded-lg"
                      preload="metadata"
                    >
                      <source src={`/api/videos/${encodeURIComponent((data as any).video_file)}`} type="video/mp4" />
                      Your browser does not support video playback.
                    </video>
                  ) : (data as any).source_url && (
                    <a
                      href={(data as any).source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-sm text-indigo-400 hover:text-indigo-300"
                    >
                      <ExternalLink className="w-4 h-4" />
                      Watch on {data.source_type}
                    </a>
                  )}
                </div>
              )}

              {/* Transcription */}
              {contentAnalysis?.transcription && (
                <div className="p-3 bg-purple-500/10 rounded-lg border border-purple-500/20">
                  <p className="text-xs text-purple-400 font-medium mb-2">📝 Transcription</p>
                  <p className="text-xs text-slate-300 italic leading-relaxed">
                    "{contentAnalysis.transcription}"
                  </p>
                </div>
              )}

              {/* Hook Analysis */}
              {(contentAnalysis?.hook || contentAnalysis?.key_message) && (
                <div className="p-3 bg-green-500/10 rounded-lg border border-green-500/20">
                  <p className="text-xs text-green-400 font-medium mb-2">🎣 Hook Analysis</p>
                  {contentAnalysis?.hook && (
                    <div className="mb-2">
                      <span className="text-xs text-slate-500">Opening: </span>
                      <span className="text-xs text-green-300 font-medium">"{contentAnalysis.hook}"</span>
                    </div>
                  )}
                  <div className="flex flex-wrap gap-2 mb-2">
                    {contentAnalysis?.hook_type && (
                      <span className="tag text-xs bg-green-500/20 text-green-400">
                        Type: {contentAnalysis.hook_type}
                      </span>
                    )}
                    {firstFrame && (
                      <span className="tag text-xs bg-cyan-500/20 text-cyan-400">
                        First Frame: {firstFrame}
                      </span>
                    )}
                    {replicationDifficulty && (
                      <span className={`tag text-xs ${replicationDifficulty === 'Easy' ? 'bg-green-500/20 text-green-400' :
                        replicationDifficulty === 'Medium' ? 'bg-yellow-500/20 text-yellow-400' :
                          'bg-red-500/20 text-red-400'
                        }`}>
                        Replication: {replicationDifficulty}
                      </span>
                    )}
                  </div>
                  {hookTechnique && (
                    <p className="text-xs text-slate-400 italic border-l-2 border-green-500/30 pl-2">
                      💡 {hookTechnique}
                    </p>
                  )}
                  {contentAnalysis?.key_message && (
                    <p className="text-xs text-slate-400 mt-2">{contentAnalysis.key_message}</p>
                  )}
                </div>
              )}

              {/* Format & Style */}
              {Object.keys(formatStyle).length > 0 && (
                <div className="p-3 bg-blue-500/10 rounded-lg border border-blue-500/20">
                  <p className="text-xs text-blue-400 font-medium mb-2">🎨 Format & Style</p>
                  <div className="flex flex-wrap gap-2">
                    {formatStyle.content_type && (
                      <span className="tag text-xs bg-blue-500/20 text-blue-300">{formatStyle.content_type}</span>
                    )}
                    {formatStyle.pacing && (
                      <span className="tag text-xs bg-blue-500/20 text-blue-300">Pacing: {formatStyle.pacing}</span>
                    )}
                    {formatStyle.visual_style && (
                      <span className="tag text-xs bg-blue-500/20 text-blue-300">{formatStyle.visual_style}</span>
                    )}
                    {formatStyle.audio_type && (
                      <span className="tag text-xs bg-blue-500/20 text-blue-300">Audio: {formatStyle.audio_type}</span>
                    )}
                  </div>
                </div>
              )}

              {/* Insights for Ads */}
              {Object.keys(insightsForAds).length > 0 && (
                <div className="p-3 bg-amber-500/10 rounded-lg border border-amber-500/20">
                  <p className="text-xs text-amber-400 font-medium mb-2">💡 Insights for Ads</p>
                  <div className="space-y-2 text-xs">
                    {insightsForAds.pain_points_mentioned && (
                      <div>
                        <span className="text-slate-500">Pain Points: </span>
                        <span className="text-orange-300">{insightsForAds.pain_points_mentioned}</span>
                      </div>
                    )}
                    {insightsForAds.solutions_shown && (
                      <div>
                        <span className="text-slate-500">Solutions: </span>
                        <span className="text-green-300">{insightsForAds.solutions_shown}</span>
                      </div>
                    )}
                    {insightsForAds.emotional_triggers && (
                      <div>
                        <span className="text-slate-500">Emotional Triggers: </span>
                        <span className="text-pink-300">{insightsForAds.emotional_triggers}</span>
                      </div>
                    )}
                    {insightsForAds.audience_indicators && (
                      <div>
                        <span className="text-slate-500">Target Audience: </span>
                        <span className="text-cyan-300">{insightsForAds.audience_indicators}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Engagement Factors */}
              {engagementFactors.what_makes_it_work && (
                <div className="p-3 bg-indigo-500/10 rounded-lg border border-indigo-500/20">
                  <p className="text-xs text-indigo-400 font-medium mb-2">✨ Why It Works</p>
                  <p className="text-xs text-slate-300">{engagementFactors.what_makes_it_work}</p>
                </div>
              )}

              {/* Scene Breakdown (NEW) */}
              {sceneBreakdown && sceneBreakdown.length > 0 && (
                <div className="p-3 bg-teal-500/10 rounded-lg border border-teal-500/20">
                  <p className="text-xs text-teal-400 font-medium mb-2">🎬 Scene Breakdown ({sceneBreakdown.length} scenes)</p>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {sceneBreakdown.slice(0, 8).map((scene: any, idx: number) => (
                      <div key={idx} className="flex items-start gap-2 text-xs">
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-teal-500/20 text-teal-400 text-[10px] font-medium flex-shrink-0">
                          {scene.scene_number || idx + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            {scene.timestamp_start && (
                              <span className="text-slate-500">{scene.timestamp_start}</span>
                            )}
                            {scene.scene_type && (
                              <span className="tag text-[10px] bg-teal-500/20 text-teal-400">{scene.scene_type}</span>
                            )}
                          </div>
                          <p className="text-slate-300 truncate">{scene.visual_description || scene.audio_transcript || '-'}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* IMA Creative Dimensions (NEW) */}
              {(videoAnalysis?.target_persona || videoAnalysis?.pain_points || videoAnalysis?.value_props || videoAnalysis?.messaging_angle) && (
                <div className="p-3 bg-orange-500/10 rounded-lg border border-orange-500/20">
                  <p className="text-xs text-orange-400 font-medium mb-2">🎯 IMA Creative Dimensions</p>
                  <div className="space-y-2 text-xs">
                    {videoAnalysis?.target_persona && (
                      <div>
                        <span className="text-slate-500">Target Persona: </span>
                        <span className="text-orange-300 font-medium">{videoAnalysis.target_persona}</span>
                      </div>
                    )}
                    {videoAnalysis?.messaging_angle && (
                      <div>
                        <span className="text-slate-500">Messaging Angle: </span>
                        <span className="text-orange-300">{videoAnalysis.messaging_angle}</span>
                      </div>
                    )}
                    {videoAnalysis?.pain_points && (
                      <div>
                        <span className="text-slate-500">Pain Points: </span>
                        <span className="text-red-300">{videoAnalysis.pain_points}</span>
                      </div>
                    )}
                    {videoAnalysis?.value_props && (
                      <div>
                        <span className="text-slate-500">Value Props: </span>
                        <span className="text-green-300">{videoAnalysis.value_props}</span>
                      </div>
                    )}
                    {videoAnalysis?.concept && (
                      <div className="mt-2 p-2 bg-slate-700/30 rounded border-l-2 border-orange-500/50">
                        <span className="text-slate-400 italic">💡 {videoAnalysis.concept}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="text-right text-xs text-slate-500 shrink-0">
          {data.author && <p>@{data.author}</p>}
          {data.likes && <p>{data.likes} likes</p>}
          {(data as any).source_url && (
            <a
              href={(data as any).source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 mt-1 justify-end"
            >
              <ExternalLink className="w-3 h-3" /> View
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
