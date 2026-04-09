import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Loader2,
  Users,
  Heart,
  Video,
  Play,
  ExternalLink,
} from 'lucide-react';
import { getSessionData } from '../api/client';

export default function SocialMediaView({ sessionId, bySource }: { sessionId: number; bySource: Record<string, number> }) {
  const [selectedPlatform, setSelectedPlatform] = useState<string>('all');
  const [expandedVideo, setExpandedVideo] = useState<number | null>(null);

  // Only show social media platforms
  const socialPlatforms = ['tiktok', 'instagram', 'youtube'];
  const availablePlatforms = socialPlatforms.filter(p => bySource[p] && bySource[p] > 0);

  const { data: socialData, isLoading } = useQuery({
    queryKey: ['socialMedia', sessionId, selectedPlatform],
    queryFn: () => getSessionData(
      sessionId,
      selectedPlatform === 'all' ? undefined : selectedPlatform,
      undefined
    ),
  });

  // Filter to only social media items with videos
  const socialItems = (socialData || []).filter(
    item => socialPlatforms.includes(item.source_type)
  );

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case 'tiktok': return '📱';
      case 'instagram': return '📸';
      case 'youtube': return '🎬';
      default: return '🎥';
    }
  };

  const getPlatformColor = (platform: string) => {
    switch (platform) {
      case 'tiktok': return 'from-pink-500 to-cyan-500';
      case 'instagram': return 'from-purple-500 to-pink-500';
      case 'youtube': return 'from-red-500 to-red-700';
      default: return 'from-indigo-500 to-purple-500';
    }
  };

  return (
    <div className="space-y-6">
      {/* Platform Tabs */}
      <div className="glass-card p-4">
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => setSelectedPlatform('all')}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${selectedPlatform === 'all'
              ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white'
              : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
          >
            All Platforms ({socialPlatforms.reduce((sum, p) => sum + (bySource[p] || 0), 0)})
          </button>
          {availablePlatforms.map(platform => (
            <button
              key={platform}
              onClick={() => setSelectedPlatform(platform)}
              className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${selectedPlatform === platform
                ? `bg-gradient-to-r ${getPlatformColor(platform)} text-white`
                : 'bg-slate-800 text-slate-400 hover:text-white'
                }`}
            >
              <span>{getPlatformIcon(platform)}</span>
              <span className="capitalize">{platform}</span>
              <span className="text-xs opacity-75">({bySource[platform] || 0})</span>
            </button>
          ))}
        </div>
      </div>

      {/* Loading State */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
        </div>
      ) : socialItems.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <Video className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg text-slate-400 mb-2">No social media content found</h3>
          <p className="text-sm text-slate-500">Run an analysis to scrape TikTok, Instagram, and YouTube videos</p>
        </div>
      ) : (
        /* Video Grid by Platform */
        <div className="space-y-8">
          {(selectedPlatform === 'all' ? availablePlatforms : [selectedPlatform]).map(platform => {
            const platformItems = socialItems.filter(i => i.source_type === platform);
            if (platformItems.length === 0) return null;

            return (
              <div key={platform} className="glass-card p-6">
                <h3 className={`text-xl font-bold mb-4 flex items-center gap-3 bg-gradient-to-r ${getPlatformColor(platform)} bg-clip-text text-transparent`}>
                  <span className="text-2xl">{getPlatformIcon(platform)}</span>
                  <span className="capitalize">{platform}</span>
                  <span className="text-sm font-normal text-slate-400">({platformItems.length} videos)</span>
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {platformItems.slice(0, 12).map((item) => (
                    <div
                      key={item.id}
                      className="bg-slate-800/50 rounded-xl overflow-hidden hover:bg-slate-800 transition-all cursor-pointer group"
                      onClick={() => setExpandedVideo(expandedVideo === item.id ? null : item.id)}
                    >
                      {/* Video/Thumbnail */}
                      <div className="aspect-video bg-slate-900 relative flex items-center justify-center">
                        {item.video_file ? (
                          <video
                            src={`/api/research/videos/${item.video_file}`}
                            className="w-full h-full object-cover"
                            muted
                            loop
                            onMouseEnter={(e) => (e.target as HTMLVideoElement).play()}
                            onMouseLeave={(e) => (e.target as HTMLVideoElement).pause()}
                          />
                        ) : item.source_url ? (
                          <a
                            href={item.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex flex-col items-center text-slate-400 hover:text-white transition-colors"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <div className={`w-16 h-16 rounded-full bg-gradient-to-r ${getPlatformColor(platform)} flex items-center justify-center mb-2`}>
                              <Play className="w-8 h-8 text-white" />
                            </div>
                            <span className="text-xs">Watch on {platform}</span>
                          </a>
                        ) : (
                          <div className="flex flex-col items-center text-slate-600">
                            <Play className="w-12 h-12" />
                            <span className="text-xs mt-2">No preview</span>
                          </div>
                        )}
                        {/* Play overlay */}
                        {item.video_file && (
                          <div className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity">
                            <Play className="w-12 h-12 text-white" />
                          </div>
                        )}
                      </div>

                      {/* Info */}
                      <div className="p-3">
                        <p className="text-sm text-slate-300 line-clamp-2 mb-2">
                          {item.title || item.content?.slice(0, 100) || 'Untitled'}
                        </p>
                        <div className="flex items-center gap-3 text-xs text-slate-500">
                          {item.author && (
                            <span className="flex items-center gap-1">
                              <Users className="w-3 h-3" />
                              {item.author}
                            </span>
                          )}
                          {item.likes !== undefined && item.likes > 0 && (
                            <span className="flex items-center gap-1">
                              <Heart className="w-3 h-3" />
                              {item.likes.toLocaleString()}
                            </span>
                          )}
                        </div>

                        {/* Expanded Details */}
                        {expandedVideo === item.id && (
                          <div className="mt-3 pt-3 border-t border-slate-700 space-y-2">
                            {item.video_analysis?.hook && (
                              <div>
                                <span className="text-xs text-indigo-400 font-medium">Hook:</span>
                                <p className="text-sm text-slate-300">{item.video_analysis.hook}</p>
                              </div>
                            )}
                            {item.video_analysis?.key_message && (
                              <div>
                                <span className="text-xs text-green-400 font-medium">Key Message:</span>
                                <p className="text-sm text-slate-300">{item.video_analysis.key_message}</p>
                              </div>
                            )}
                            {item.source_url && (
                              <a
                                href={item.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:underline mt-2"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <ExternalLink className="w-3 h-3" />
                                View Original
                              </a>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {platformItems.length > 12 && (
                  <p className="text-center text-sm text-slate-500 mt-4">
                    Showing 12 of {platformItems.length} videos
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
