import { useState } from 'react';
import {
  BarChart3,
  Play,
  Shield,
  Users,
  Video,
  X,
  Eye,
  Zap,
  AlertTriangle,
  MessageSquare,
  FileText,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import type { Insight } from '../api/client';

// Helper to proxy external images to avoid CORS issues
// Handles both string URLs and objects with original_url property
const getProxiedImageUrl = (url: string | { original_url?: string } | undefined): string | undefined => {
  if (!url) return undefined;
  // Extract URL from object if needed
  const urlString = typeof url === 'string' ? url : url.original_url;
  if (!urlString) return undefined;
  // Skip if already proxied or is local/data URL
  if (urlString.startsWith('/api/') || urlString.startsWith('data:') || urlString.startsWith('blob:')) return urlString;
  return `/api/research/proxy-image?url=${encodeURIComponent(urlString)}`;
};

export default function AdIntelligenceView({ insights }: { insights: Insight }) {
  const patterns = (insights as any).ad_creative_patterns || {};
  const brandAds = (insights as any).ad_library_data || {};
  const competitorAds = (insights as any).competitor_ads_data || [];
  const swot = (insights as any).swot_analysis || {};
  const competitorProfiles = (insights as any).competitor_profiles || [];

  return (
    <div className="space-y-6">
      {/* Ad Creative Patterns */}
      {patterns && Object.keys(patterns).length > 0 && (
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-indigo-400" />
            Ad Creative Patterns
          </h3>

          <div className="grid md:grid-cols-4 gap-4 mb-6">
            <div className="bg-slate-800/50 p-4 rounded-xl text-center">
              <p className="text-3xl font-bold text-indigo-400">{patterns.total_analyzed || 0}</p>
              <p className="text-sm text-slate-400">Ads Analyzed</p>
            </div>
            <div className="bg-slate-800/50 p-4 rounded-xl text-center">
              <p className="text-3xl font-bold text-green-400">{(patterns.avg_hook_strength || 0).toFixed(1)}/5</p>
              <p className="text-sm text-slate-400">Avg Hook Strength</p>
            </div>
            <div className="bg-slate-800/50 p-4 rounded-xl text-center">
              <p className="text-3xl font-bold text-yellow-400">{(patterns.avg_effectiveness || 0).toFixed(1)}/5</p>
              <p className="text-sm text-slate-400">Avg Effectiveness</p>
            </div>
            <div className="bg-slate-800/50 p-4 rounded-xl text-center">
              <p className="text-3xl font-bold text-purple-400">{Object.keys(patterns.frameworks || {}).length}</p>
              <p className="text-sm text-slate-400">Frameworks Found</p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {/* Top Frameworks */}
            {patterns.frameworks && Object.keys(patterns.frameworks).length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-slate-400 mb-3">Top Frameworks</h4>
                <div className="space-y-2">
                  {Object.entries(patterns.frameworks).slice(0, 5).map(([fw, count], i) => (
                    <div key={i} className="flex items-center justify-between bg-slate-800/30 p-2 rounded">
                      <span className="text-slate-300">{fw}</span>
                      <span className="text-indigo-400 font-medium">{count as number} ads</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Top Hook Types */}
            {patterns.hook_types && Object.keys(patterns.hook_types).length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-slate-400 mb-3">Top Hook Types</h4>
                <div className="space-y-2">
                  {Object.entries(patterns.hook_types).slice(0, 5).map(([hook, count], i) => (
                    <div key={i} className="flex items-center justify-between bg-slate-800/30 p-2 rounded">
                      <span className="text-slate-300">{hook}</span>
                      <span className="text-green-400 font-medium">{count as number} ads</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Top Transcriptions */}
          {patterns.top_transcriptions && patterns.top_transcriptions.length > 0 && (
            <div className="mt-6">
              <h4 className="text-sm font-medium text-slate-400 mb-3">Top Performing Transcriptions</h4>
              <div className="space-y-4">
                {patterns.top_transcriptions.slice(0, 3).map((trans: any, i: number) => (
                  <div key={i} className="bg-slate-800/30 p-4 rounded-xl border-l-2 border-indigo-500">
                    <div className="flex items-center gap-2 mb-2">
                      <Play className="w-4 h-4 text-indigo-400" />
                      <span className="text-xs text-slate-500">Ad {trans.library_id}</span>
                      {trans.effectiveness && (
                        <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded">
                          Effectiveness: {trans.effectiveness}/5
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-300 italic">"{trans.text?.slice(0, 300)}..."</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* SWOT Analysis */}
      {swot && Object.keys(swot).length > 0 && (
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-cyan-400" />
            SWOT Analysis
          </h3>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="bg-green-500/10 p-4 rounded-xl border border-green-500/20">
              <h4 className="text-green-400 font-medium mb-2">Strengths</h4>
              <ul className="space-y-1">
                {(swot.strengths || []).slice(0, 4).map((s: any, i: number) => (
                  <li key={i} className="text-sm text-slate-300">
                    • {typeof s === 'string' ? s : s.point}
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-red-500/10 p-4 rounded-xl border border-red-500/20">
              <h4 className="text-red-400 font-medium mb-2">Weaknesses</h4>
              <ul className="space-y-1">
                {(swot.weaknesses || []).slice(0, 4).map((w: any, i: number) => (
                  <li key={i} className="text-sm text-slate-300">
                    • {typeof w === 'string' ? w : w.point}
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-blue-500/10 p-4 rounded-xl border border-blue-500/20">
              <h4 className="text-blue-400 font-medium mb-2">Opportunities</h4>
              <ul className="space-y-1">
                {(swot.opportunities || []).slice(0, 4).map((o: any, i: number) => (
                  <li key={i} className="text-sm text-slate-300">
                    • {typeof o === 'string' ? o : o.point}
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-yellow-500/10 p-4 rounded-xl border border-yellow-500/20">
              <h4 className="text-yellow-400 font-medium mb-2">Threats</h4>
              <ul className="space-y-1">
                {(swot.threats || []).slice(0, 4).map((t: any, i: number) => (
                  <li key={i} className="text-sm text-slate-300">
                    • {typeof t === 'string' ? t : t.point}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Competitor Profiles */}
      {competitorProfiles && competitorProfiles.length > 0 && (
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-purple-400" />
            Competitor Profiles
          </h3>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {competitorProfiles.slice(0, 6).map((comp: any, i: number) => (
              <div key={i} className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
                <h4 className="font-semibold text-purple-300 mb-2">{comp.name}</h4>
                <p className="text-sm text-slate-400 mb-2">{comp.positioning?.slice(0, 100)}</p>
                {comp.key_differentiator && (
                  <p className="text-xs text-slate-500">
                    <strong>Differentiator:</strong> {comp.key_differentiator}
                  </p>
                )}
                {comp.estimated_size && (
                  <span className="tag text-xs bg-slate-700 text-slate-300 mt-2 inline-block">
                    {comp.estimated_size}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Brand Ads Summary with Transcriptions */}
      {brandAds && brandAds.total_ads > 0 && (
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Video className="w-5 h-5 text-green-400" />
            Brand Ad Library ({brandAds.total_ads} ads)
          </h3>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="text-center p-3 bg-slate-800/30 rounded-lg">
              <p className="text-2xl font-bold text-green-400">{brandAds.video_ads_count || 0}</p>
              <p className="text-xs text-slate-500">Video Ads</p>
            </div>
            <div className="text-center p-3 bg-slate-800/30 rounded-lg">
              <p className="text-2xl font-bold text-blue-400">{brandAds.image_ads_count || 0}</p>
              <p className="text-xs text-slate-500">Static Ads</p>
            </div>
            <div className="text-center p-3 bg-slate-800/30 rounded-lg">
              <p className="text-2xl font-bold text-purple-400">{competitorAds.length}</p>
              <p className="text-xs text-slate-500">Competitors Scraped</p>
            </div>
          </div>

          {/* Thumbnail Grid View */}
          {brandAds.ads && brandAds.ads.length > 0 && (
            <div className="mb-6">
              <h4 className="text-sm font-medium text-slate-400 mb-3">Quick View - Click to expand</h4>
              <div className="grid grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2">
                {brandAds.ads.slice(0, 16).map((ad: any, idx: number) => (
                  <div
                    key={idx}
                    className="aspect-square bg-slate-800 rounded-lg overflow-hidden cursor-pointer group relative border border-slate-700 hover:border-indigo-500 transition-all"
                    title={ad.primary_text || ad.headline || `Ad ${idx + 1}`}
                  >
                    {(ad.thumbnail_url || ad.media_url) ? (
                      <img
                        src={getProxiedImageUrl(ad.thumbnail_url || ad.media_url)}
                        alt={`Ad ${idx + 1}`}
                        className="w-full h-full object-cover group-hover:scale-110 transition-transform"
                        onError={(e) => { (e.target as HTMLImageElement).src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect fill="%23334155"/><text x="50%" y="50%" fill="%23666" font-size="12" text-anchor="middle" dy=".3em">Ad</text></svg>'; }}
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-slate-600 text-xs">
                        {ad.media_type === 'video' ? '\uD83C\uDFAC' : '\uD83D\uDDBC\uFE0F'}
                      </div>
                    )}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                      <div className="absolute bottom-1 left-1 right-1 flex gap-1 flex-wrap">
                        {ad.media_type === 'video' && (
                          <span className="text-[10px] bg-green-500/80 text-white px-1 rounded">Video</span>
                        )}
                        {ad.creative_analysis?.hook_strength && (
                          <span className="text-[10px] bg-amber-500/80 text-white px-1 rounded">
                            H:{ad.creative_analysis.hook_strength}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Brand Ads with Transcriptions */}
          <AdListSection
            title="Brand Ads with Transcriptions"
            ads={brandAds.ads || []}
            maxShow={5}
          />
        </div>
      )}

      {/* Competitor Ads with Transcriptions - Enhanced View */}
      {competitorAds && competitorAds.length > 0 && (
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <Users className="w-5 h-5 text-purple-400" />
            Competitor Ads Analysis
            <span className="ml-auto text-sm bg-purple-500/20 text-purple-400 px-3 py-1 rounded-full">
              {competitorAds.length} competitor{competitorAds.length > 1 ? 's' : ''}
            </span>
          </h3>

          {/* Competitor Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
            {competitorAds.map((compData: any, idx: number) => {
              const videoCount = compData.ads?.filter((ad: any) => ad.media_type === 'video').length || 0;
              const staticCount = compData.ads?.filter((ad: any) => ad.media_type === 'image').length || 0;
              const avgEffectiveness = compData.ads?.reduce((acc: number, ad: any) =>
                acc + (ad.creative_analysis?.effectiveness || 0), 0) / (compData.ads?.length || 1);

              return (
                <div key={idx} className="bg-gradient-to-br from-purple-500/10 to-slate-800/50 p-4 rounded-xl border border-purple-500/20">
                  <h5 className="font-semibold text-purple-300 text-sm mb-2 truncate">
                    {compData.competitor_name || `Competitor ${idx + 1}`}
                  </h5>
                  <div className="space-y-1 text-xs text-slate-400">
                    <p className="flex justify-between">
                      <span>Total Ads:</span>
                      <span className="text-white font-medium">{compData.ads?.length || 0}</span>
                    </p>
                    <p className="flex justify-between">
                      <span>Videos:</span>
                      <span className="text-green-400">{videoCount}</span>
                    </p>
                    <p className="flex justify-between">
                      <span>Static:</span>
                      <span className="text-blue-400">{staticCount}</span>
                    </p>
                    {avgEffectiveness > 0 && (
                      <p className="flex justify-between">
                        <span>Avg Score:</span>
                        <span className="text-amber-400">{avgEffectiveness.toFixed(1)}/5</span>
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Detailed Competitor Ads */}
          {competitorAds.map((compData: any, idx: number) => {
            const frameworks = new Set(compData.ads?.map((ad: any) => ad.creative_analysis?.framework).filter(Boolean));

            return (
              <div key={idx} className="mb-8 last:mb-0">
                <div className="flex items-center gap-3 mb-4 pb-3 border-b border-slate-700/50">
                  <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center">
                    <span className="text-purple-300 font-bold text-sm">{idx + 1}</span>
                  </div>
                  <div className="flex-1">
                    <h4 className="text-lg font-semibold text-white">
                      {compData.competitor_name || `Competitor ${idx + 1}`}
                    </h4>
                    <p className="text-xs text-slate-400">
                      {compData.ads?.length || 0} ads analyzed •
                      Frameworks: {frameworks.size > 0 ? Array.from(frameworks).slice(0, 3).join(', ') : 'N/A'}
                    </p>
                  </div>
                  <span className="tag text-xs bg-purple-500/20 text-purple-400">
                    {compData.ads?.length || 0} ads
                  </span>
                </div>
                <AdListSection
                  title=""
                  ads={compData.ads || []}
                  maxShow={3}
                />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// Ad Detail Modal - Shows full ad details with complete analysis
function AdDetailModal({ ad, onClose }: { ad: any; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  const [activeSection, setActiveSection] = useState<'overview' | 'scenes' | 'copy'>('overview');

  const copyText = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const analysis = ad.creative_analysis || {};
  const scenes = analysis.scene_breakdown || [];
  const hookAnalysis = analysis.hook_analysis || {};
  const dimensions = analysis.creative_dimensions || {};
  const disclaimers = analysis.disclaimers || [];

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-slate-900 rounded-2xl max-w-5xl w-full max-h-[90vh] overflow-hidden shadow-2xl border border-slate-700"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <span className={`tag ${ad.media_type === 'video'
              ? 'bg-green-500/20 text-green-400'
              : 'bg-blue-500/20 text-blue-400'
              }`}>
              {ad.media_type === 'video' ? '\uD83C\uDFAC Video Ad' : '\uD83D\uDDBC\uFE0F Static Ad'}
            </span>
            {ad.library_id && (
              <span className="text-sm text-slate-400">ID: {ad.library_id}</span>
            )}
            {analysis.effectiveness && (
              <span className="tag bg-amber-500/20 text-amber-400">
                Effectiveness: {analysis.effectiveness}/5
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-700">
          {[
            { id: 'overview', label: 'Overview', icon: Eye },
            { id: 'scenes', label: `Scenes (${scenes.length})`, icon: Video },
            { id: 'copy', label: 'Copy & Script', icon: FileText },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveSection(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-all border-b-2 -mb-px ${activeSection === tab.id
                ? 'text-indigo-400 border-indigo-400'
                : 'text-slate-400 border-transparent hover:text-white'
                }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-140px)] p-6">
          {activeSection === 'overview' && (
            <div className="grid md:grid-cols-2 gap-6">
              {/* Left Column - Media & Scores */}
              <div className="space-y-4">
                {/* Media Preview */}
                {(ad.media_url || ad.thumbnail_url) && (
                  <div className="rounded-xl overflow-hidden bg-slate-800 aspect-video flex items-center justify-center">
                    {ad.media_type === 'video' && ad.media_url ? (
                      <video
                        controls
                        src={ad.media_url}
                        poster={getProxiedImageUrl(ad.thumbnail_url)}
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <img
                        src={getProxiedImageUrl(ad.media_url || ad.thumbnail_url)}
                        alt="Ad creative"
                        className="w-full h-full object-contain"
                        onError={(e) => { (e.target as HTMLImageElement).src = '/placeholder-ad.png'; }}
                      />
                    )}
                  </div>
                )}

                {/* Scores Grid */}
                <div className="grid grid-cols-2 gap-3">
                  {analysis.hook_strength && (
                    <div className="bg-slate-800/50 p-3 rounded-lg text-center">
                      <p className="text-2xl font-bold text-green-400">{analysis.hook_strength}/5</p>
                      <p className="text-xs text-slate-400">Hook Strength</p>
                    </div>
                  )}
                  {analysis.effectiveness && (
                    <div className="bg-slate-800/50 p-3 rounded-lg text-center">
                      <p className="text-2xl font-bold text-amber-400">{analysis.effectiveness}/5</p>
                      <p className="text-xs text-slate-400">Effectiveness</p>
                    </div>
                  )}
                </div>

                {/* Hook Analysis Card */}
                {(analysis.hook || hookAnalysis.hook_text) && (
                  <div className="bg-gradient-to-br from-green-500/10 to-slate-800/50 p-4 rounded-xl border border-green-500/20">
                    <h4 className="text-sm font-medium text-green-400 mb-3 flex items-center gap-2">
                      <Zap className="w-4 h-4" />
                      Hook Analysis
                    </h4>
                    <p className="text-white font-medium italic mb-3">
                      "{analysis.hook || hookAnalysis.hook_text}"
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      {(analysis.hook_type || hookAnalysis.hook_type) && (
                        <div>
                          <span className="text-xs text-slate-500">Type:</span>
                          <p className="text-sm text-slate-300">{analysis.hook_type || hookAnalysis.hook_type}</p>
                        </div>
                      )}
                      {hookAnalysis.hook_technique && (
                        <div>
                          <span className="text-xs text-slate-500">Technique:</span>
                          <p className="text-sm text-slate-300">{hookAnalysis.hook_technique}</p>
                        </div>
                      )}
                      {hookAnalysis.attention_device && (
                        <div className="col-span-2">
                          <span className="text-xs text-slate-500">Attention Device:</span>
                          <p className="text-sm text-slate-300">{hookAnalysis.attention_device}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Right Column - Analysis Details */}
              <div className="space-y-4">
                {/* Creative Dimensions - Expanded with all IMA v46 taxonomies */}
                <div className="bg-slate-800/50 p-4 rounded-xl">
                  <h4 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-purple-400" />
                    Creative Dimensions (IMA v46)
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                    {/* Row 1: Core */}
                    {(analysis.framework || dimensions.framework) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-purple-400 font-medium">Framework</span>
                        <p className="text-slate-300 mt-0.5">{analysis.framework || dimensions.framework}</p>
                      </div>
                    )}
                    {(dimensions.tone || analysis.tone) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-blue-400 font-medium">Tone</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.tone || analysis.tone}</p>
                      </div>
                    )}
                    {(dimensions.visual_type || analysis.visual_type) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-cyan-400 font-medium">Visual Type</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.visual_type || analysis.visual_type}</p>
                      </div>
                    )}
                    {/* Row 2: Narration & Format */}
                    {(dimensions.narration_driver || analysis.narration_driver) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-green-400 font-medium">Narration Driver</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.narration_driver || analysis.narration_driver}</p>
                      </div>
                    )}
                    {(dimensions.creative_format || analysis.creative_format) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-indigo-400 font-medium">Creative Format</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.creative_format || analysis.creative_format}</p>
                      </div>
                    )}
                    {dimensions.pacing && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-yellow-400 font-medium">Pacing</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.pacing}</p>
                      </div>
                    )}
                    {/* Row 3: Talent & Setting */}
                    {(dimensions.talent_type || analysis.talent_type) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-pink-400 font-medium">Talent Type</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.talent_type || analysis.talent_type}</p>
                      </div>
                    )}
                    {(dimensions.talent_count || analysis.talent_count) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-pink-400 font-medium">Talent Count</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.talent_count || analysis.talent_count}</p>
                      </div>
                    )}
                    {(dimensions.setting_type || analysis.setting) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-emerald-400 font-medium">Setting</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.setting_type || analysis.setting}</p>
                      </div>
                    )}
                    {/* Row 4: Audio & Visual */}
                    {(dimensions.audio_mix || analysis.audio_mix) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-orange-400 font-medium">Audio Mix</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.audio_mix || analysis.audio_mix}</p>
                      </div>
                    )}
                    {(dimensions.music_energy || analysis.music_energy) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-orange-400 font-medium">Music Energy</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.music_energy || analysis.music_energy}</p>
                      </div>
                    )}
                    {(dimensions.text_style || analysis.text_style) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-teal-400 font-medium">Text Style</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.text_style || analysis.text_style}</p>
                      </div>
                    )}
                    {/* Row 5: Hook & CTA */}
                    {(dimensions.hook_type || analysis.hook_type) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-green-400 font-medium">Hook Type</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.hook_type || analysis.hook_type}</p>
                      </div>
                    )}
                    {(dimensions.first_frame_element || analysis.first_frame) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-green-400 font-medium">First Frame</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.first_frame_element || analysis.first_frame}</p>
                      </div>
                    )}
                    {(dimensions.cta_type || dimensions.cta_placement) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-amber-400 font-medium">CTA</span>
                        <p className="text-slate-300 mt-0.5">
                          {[dimensions.cta_type, dimensions.cta_placement].filter(Boolean).join(' · ')}
                        </p>
                      </div>
                    )}
                    {/* Row 6: Proof & Urgency */}
                    {dimensions.proof_type && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-cyan-400 font-medium">Proof Type</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.proof_type}</p>
                      </div>
                    )}
                    {(dimensions.urgency_element || analysis.urgency) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-red-400 font-medium">Urgency</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.urgency_element || analysis.urgency}</p>
                      </div>
                    )}
                    {/* Row 7: Funnel & Offer */}
                    {(dimensions.funnel_stage || analysis.funnel_stage) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-violet-400 font-medium">Funnel Stage</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.funnel_stage || analysis.funnel_stage}</p>
                      </div>
                    )}
                    {(dimensions.offer_type || analysis.offer) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-lime-400 font-medium">Offer Type</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.offer_type || analysis.offer}</p>
                      </div>
                    )}
                    {(dimensions.ad_intent || analysis.intent) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-sky-400 font-medium">Ad Intent</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.ad_intent || analysis.intent}</p>
                      </div>
                    )}
                    {/* Row 8: Additional */}
                    {dimensions.production_quality && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-purple-400 font-medium">Production</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.production_quality}</p>
                      </div>
                    )}
                    {(dimensions.product_display || analysis.product_display) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-blue-400 font-medium">Product Display</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.product_display || analysis.product_display}</p>
                      </div>
                    )}
                    {(dimensions.length || analysis.length) && (
                      <div className="bg-slate-900/50 p-2 rounded">
                        <span className="text-slate-400 font-medium">Length</span>
                        <p className="text-slate-300 mt-0.5">{dimensions.length || analysis.length}</p>
                      </div>
                    )}
                  </div>

                  {/* Emotions as tags */}
                  {(analysis.target_emotion || (dimensions.emotions && dimensions.emotions.length > 0)) && (
                    <div className="mt-3 pt-3 border-t border-slate-700">
                      <span className="text-xs text-pink-400 font-medium">Emotions:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {dimensions.emotions ? dimensions.emotions.map((e: string, i: number) => (
                          <span key={i} className="tag text-xs bg-pink-500/20 text-pink-300">{e}</span>
                        )) : (
                          <span className="tag text-xs bg-pink-500/20 text-pink-300">{analysis.target_emotion}</span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* NFC Tags */}
                  {(dimensions.nfc || dimensions.opener_visual) && (
                    <div className="mt-3 pt-3 border-t border-slate-700">
                      <span className="text-xs text-cyan-400 font-medium">NFC (Narrative Footage):</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {(dimensions.nfc || dimensions.opener_visual || []).map((n: string, i: number) => (
                          <span key={i} className="tag text-xs bg-cyan-500/20 text-cyan-300">{n}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Visual Elements as tags */}
                  {(dimensions.visual_elements || analysis.visual_elements) && (
                    <div className="mt-3 pt-3 border-t border-slate-700">
                      <span className="text-xs text-teal-400 font-medium">Visual Elements:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {(dimensions.visual_elements || analysis.visual_elements || []).map((v: string, i: number) => (
                          <span key={i} className="tag text-xs bg-teal-500/20 text-teal-300">{v}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Disclaimers */}
                {disclaimers.length > 0 && (
                  <div className="bg-yellow-500/10 p-4 rounded-xl border border-yellow-500/20">
                    <h4 className="text-sm font-medium text-yellow-400 mb-2 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4" />
                      Disclaimers Detected ({disclaimers.length})
                    </h4>
                    <ul className="space-y-1">
                      {disclaimers.map((d: string, i: number) => (
                        <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                          <span className="text-yellow-500 mt-0.5">•</span>
                          {d}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Key Messages */}
                {analysis.key_messages && analysis.key_messages.length > 0 && (
                  <div className="bg-slate-800/50 p-4 rounded-xl">
                    <h4 className="text-sm font-medium text-white mb-2">Key Messages</h4>
                    <ul className="space-y-1">
                      {analysis.key_messages.map((msg: string, i: number) => (
                        <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                          <span className="text-indigo-400">•</span> {msg}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Visual Elements */}
                {analysis.visual_elements && analysis.visual_elements.length > 0 && (
                  <div className="bg-slate-800/50 p-4 rounded-xl">
                    <h4 className="text-sm font-medium text-white mb-2">Visual Elements</h4>
                    <div className="flex flex-wrap gap-2">
                      {analysis.visual_elements.map((elem: string, i: number) => (
                        <span key={i} className="tag text-xs bg-slate-700 text-slate-300">{elem}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Scenes Tab */}
          {activeSection === 'scenes' && (
            <div className="space-y-4">
              {scenes.length > 0 ? (
                <>
                  <p className="text-sm text-slate-400 mb-4">
                    Scene-by-scene breakdown of the ad creative
                  </p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-700">
                          <th className="text-left py-3 px-4 text-slate-400 font-medium">Scene</th>
                          <th className="text-left py-3 px-4 text-slate-400 font-medium">Duration</th>
                          <th className="text-left py-3 px-4 text-slate-400 font-medium">Visual</th>
                          <th className="text-left py-3 px-4 text-slate-400 font-medium">Audio/Text</th>
                        </tr>
                      </thead>
                      <tbody>
                        {scenes.map((scene: any, i: number) => (
                          <tr key={i} className="border-b border-slate-800 hover:bg-slate-800/30">
                            <td className="py-3 px-4">
                              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 text-xs font-medium">
                                {scene.scene_number || i + 1}
                              </span>
                              {scene.scene_type && (
                                <span className="ml-2 tag text-xs bg-slate-700">{scene.scene_type}</span>
                              )}
                            </td>
                            <td className="py-3 px-4 text-slate-300">
                              {scene.duration_seconds ? `${scene.duration_seconds}s` : '-'}
                              {scene.timestamp_start && (
                                <span className="text-xs text-slate-500 block">
                                  {scene.timestamp_start} - {scene.timestamp_end || '?'}
                                </span>
                              )}
                            </td>
                            <td className="py-3 px-4 text-slate-300 max-w-xs">
                              {scene.visual_description || '-'}
                            </td>
                            <td className="py-3 px-4 text-slate-400 italic max-w-xs">
                              {scene.audio_transcript || scene.on_screen_text || '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : analysis.scene_by_scene_breakdown ? (
                /* Fallback: Show scene_by_scene_breakdown as text if no structured scenes */
                <div className="space-y-4">
                  <p className="text-sm text-slate-400 mb-4">
                    Scene breakdown from video analysis
                  </p>
                  <div className="bg-slate-800/50 p-4 rounded-xl">
                    <h4 className="text-sm font-medium text-indigo-400 mb-3 flex items-center gap-2">
                      <Video className="w-4 h-4" />
                      Scene by Scene Breakdown
                    </h4>
                    <pre className="text-sm text-slate-300 whitespace-pre-wrap font-sans leading-relaxed">
                      {analysis.scene_by_scene_breakdown}
                    </pre>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12">
                  <Video className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                  <h3 className="text-lg text-slate-400">No scene breakdown available</h3>
                  <p className="text-sm text-slate-500">Scene analysis may not be available for this ad</p>
                </div>
              )}
            </div>
          )}

          {/* Copy Tab */}
          {activeSection === 'copy' && (
            <div className="space-y-6">
              {/* Full Transcription */}
              {(analysis.transcription || analysis.audio_transcript) && (
                <div className="bg-gradient-to-br from-slate-800/80 to-indigo-900/20 p-4 rounded-xl border border-indigo-500/20">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-medium text-white flex items-center gap-2">
                      <MessageSquare className="w-4 h-4 text-indigo-400" />
                      Full Transcription
                    </h4>
                    <button
                      onClick={() => copyText(analysis.transcription || analysis.audio_transcript)}
                      className="flex items-center gap-1 px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded transition-colors"
                    >
                      {copied ? (
                        <>
                          <Check className="w-3 h-3 text-green-400" />
                          <span className="text-green-400">Copied!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  </div>
                  <div className="max-h-[300px] overflow-y-auto">
                    <p className="text-sm text-slate-300 italic whitespace-pre-wrap leading-relaxed">
                      "{analysis.transcription || analysis.audio_transcript}"
                    </p>
                  </div>
                </div>
              )}

              {/* Full Copy */}
              {analysis.full_copy && (
                <div className="bg-slate-800/50 p-4 rounded-xl">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-medium text-white flex items-center gap-2">
                      <FileText className="w-4 h-4 text-blue-400" />
                      Full Ad Copy
                    </h4>
                    <button
                      onClick={() => copyText(analysis.full_copy)}
                      className="flex items-center gap-1 px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded transition-colors"
                    >
                      <Copy className="w-3 h-3" />
                      <span>Copy</span>
                    </button>
                  </div>
                  <p className="text-sm text-slate-300 whitespace-pre-wrap">
                    {analysis.full_copy}
                  </p>
                </div>
              )}

              {/* Primary Text */}
              {(ad.primary_text || ad.headline) && (
                <div className="bg-slate-800/50 p-4 rounded-xl">
                  <h4 className="text-sm font-medium text-white mb-2">Primary Text / Headline</h4>
                  <p className="text-slate-300">{ad.primary_text || ad.headline}</p>
                </div>
              )}

              {/* Empty State */}
              {!analysis.transcription && !analysis.audio_transcript && !analysis.full_copy && !ad.primary_text && !ad.headline && (
                <div className="text-center py-12">
                  <FileText className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                  <h3 className="text-lg text-slate-400">No copy or script available</h3>
                  <p className="text-sm text-slate-500">Text content may not be available for this ad</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Component to display ads with transcriptions
function AdListSection({ title, ads, maxShow = 5 }: { title: string; ads: any[]; maxShow?: number }) {
  const [expanded, setExpanded] = useState(false);
  const [selectedAd, setSelectedAd] = useState<any>(null);
  const [expandedTranscriptions, setExpandedTranscriptions] = useState<Set<number>>(new Set());
  const displayAds = expanded ? ads : ads.slice(0, maxShow);

  const toggleTranscription = (index: number) => {
    const newSet = new Set(expandedTranscriptions);
    if (newSet.has(index)) {
      newSet.delete(index);
    } else {
      newSet.add(index);
    }
    setExpandedTranscriptions(newSet);
  };

  if (!ads || ads.length === 0) return null;

  return (
    <div className="space-y-4">
      {title && <h4 className="text-sm font-medium text-slate-400">{title}</h4>}

      {displayAds.map((ad: any, i: number) => (
        <div key={i} className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50 hover:border-slate-600/50 transition-colors">
          <div className="flex items-start gap-4">
            {/* Thumbnail - Clickable */}
            {(ad.thumbnail_url || ad.media_url) && (
              <div
                className="w-28 h-28 rounded-lg overflow-hidden bg-slate-900 flex-shrink-0 cursor-pointer group relative"
                onClick={() => setSelectedAd(ad)}
              >
                <img
                  src={getProxiedImageUrl(ad.thumbnail_url || ad.media_url)}
                  alt="Ad thumbnail"
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                />
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <Eye className="w-6 h-6 text-white" />
                </div>
              </div>
            )}

            <div className="flex-1 min-w-0">
              {/* Ad Type Badge */}
              <div className="flex items-center gap-2 mb-2 flex-wrap">
                <span className={`tag text-xs ${ad.media_type === 'video'
                  ? 'bg-green-500/20 text-green-400'
                  : 'bg-blue-500/20 text-blue-400'
                  }`}>
                  {ad.media_type === 'video' ? '\uD83C\uDFAC Video' : '\uD83D\uDDBC\uFE0F Static'}
                </span>
                {ad.library_id && (
                  <span className="text-xs text-slate-500">ID: {ad.library_id}</span>
                )}
                {ad.creative_analysis?.effectiveness && (
                  <span className="tag text-xs bg-amber-500/20 text-amber-400">
                    Effectiveness: {ad.creative_analysis.effectiveness}/5
                  </span>
                )}
                {ad.creative_analysis?.hook_strength && (
                  <span className="tag text-xs bg-green-500/20 text-green-400">
                    Hook: {ad.creative_analysis.hook_strength}/5
                  </span>
                )}
              </div>

              {/* Primary Text / Headline */}
              {(ad.primary_text || ad.headline) && (
                <p className="text-sm text-slate-300 mb-2 line-clamp-2">
                  {ad.primary_text || ad.headline}
                </p>
              )}

              {/* Transcription (expandable) */}
              {ad.creative_analysis?.transcription && (
                <div className="mt-2 p-3 bg-slate-900/50 rounded border border-slate-700/30">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-xs text-indigo-400 flex items-center gap-1">
                      <MessageSquare className="w-3 h-3" /> Transcription:
                    </p>
                    <button
                      onClick={() => toggleTranscription(i)}
                      className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                    >
                      {expandedTranscriptions.has(i) ? (
                        <>
                          <ChevronUp className="w-3 h-3" /> Collapse
                        </>
                      ) : (
                        <>
                          <ChevronDown className="w-3 h-3" /> Expand
                        </>
                      )}
                    </button>
                  </div>
                  <p className={`text-xs text-slate-400 italic ${expandedTranscriptions.has(i) ? '' : 'line-clamp-3'}`}>
                    "{ad.creative_analysis.transcription}"
                  </p>
                </div>
              )}

              {/* Hook Analysis */}
              {ad.creative_analysis?.hook && (
                <div className="mt-2 flex items-center gap-2">
                  <span className="text-xs text-green-400">Hook:</span>
                  <span className="text-xs text-slate-300">"{ad.creative_analysis.hook}"</span>
                </div>
              )}

              {/* Framework */}
              {ad.creative_analysis?.framework && (
                <div className="mt-1 flex items-center gap-2">
                  <span className="text-xs text-purple-400">Framework:</span>
                  <span className="text-xs text-slate-300">{ad.creative_analysis.framework}</span>
                </div>
              )}

              {/* View Details Button */}
              <button
                onClick={() => setSelectedAd(ad)}
                className="mt-3 text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
              >
                <Eye className="w-3 h-3" /> View Full Details
              </button>
            </div>
          </div>
        </div>
      ))}

      {ads.length > maxShow && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-sm text-indigo-400 hover:text-indigo-300"
        >
          {expanded ? 'Show less' : `Show ${ads.length - maxShow} more ads`}
        </button>
      )}

      {/* Modal */}
      {selectedAd && (
        <AdDetailModal ad={selectedAd} onClose={() => setSelectedAd(null)} />
      )}
    </div>
  );
}
