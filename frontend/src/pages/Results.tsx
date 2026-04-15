import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import {
  Loader2,
  Users,
  AlertTriangle,
  Zap,
  MessageSquare,
  TrendingUp,
  Download,
  Star,
  Globe,
  ArrowLeft,
  FileText,
  Megaphone,
  Video,
  PenTool,
  BarChart3,
  Play,
  Sparkles,
  Flame,
} from 'lucide-react';
import { getFullResearchResult } from '../api/client';
import ChatPanel from '../components/ChatPanel';
import TikTokTrendsView from '../components/TikTokTrendsView';
import HooksLibraryView from '../components/HooksLibraryView';
import InstagramBrandView from '../components/InstagramBrandView';
import BrandDNAView from '../components/BrandDNAView';
import InsightsView from '../components/InsightsView';
import AdIntelligenceView from '../components/AdIntelligenceView';
import GeneratedContentView from '../components/GeneratedContentView';
import SocialMediaView from '../components/SocialMediaView';
import DataView from '../components/DataView';
import SentimentView from '../components/SentimentView';

type Tab = 'dna' | 'insights' | 'ads' | 'social' | 'generated' | 'trends' | 'hooks' | 'sentiment' | 'data' | 'report';


export default function Results() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [activeTab, setActiveTab] = useState<Tab>('dna');
  const [exportFormat, setExportFormat] = useState('full');

  const { data: result, isLoading, error } = useQuery({
    queryKey: ['result', sessionId],
    queryFn: () => getFullResearchResult(Number(sessionId)),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <h2 className="text-xl text-white mb-2">Error loading results</h2>
        <p className="text-slate-400">{(error as Error)?.message || 'Unknown error'}</p>
      </div>
    );
  }

  const { brand, insights, scraped_data_count, scraped_data_by_source } = result;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link to="/" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-white mb-2">
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>
          <h1 className="text-3xl font-display font-bold text-white mb-1">
            {brand.name}
          </h1>
          <div className="flex items-center gap-3">
            {brand.sector && <span className="tag-primary">{brand.sector}</span>}
            {brand.vertical && <span className="tag-primary">{brand.vertical}</span>}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={exportFormat}
            onChange={(e) => setExportFormat(e.target.value)}
            className="bg-gray-800 border border-gray-600 text-gray-200 text-sm rounded px-2 py-2 focus:outline-none focus:border-blue-500"
          >
            <option value="full">Full Report</option>
            <option value="raw_reviews">Raw Reviews</option>
            <option value="ctp">CTP Personas</option>
            <option value="hypothesis">Hypothesis Layer</option>
          </select>
          <button
            onClick={() => {
              const safeName = brand.name.toLowerCase().replace(/\s+/g, '-');
              const filenames: Record<string, string> = {
                full: `${safeName}-research-export.md`,
                raw_reviews: `${safeName}-raw-reviews.md`,
                ctp: `${safeName}-ctp-personas.md`,
                hypothesis: `${safeName}-hypothesis-layer.md`,
              };
              const link = document.createElement('a');
              link.href = `/api/research/session/${sessionId}/export?format=${exportFormat}`;
              link.download = filenames[exportFormat] || `${safeName}-export.md`;
              link.click();
            }}
            className="btn-secondary flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={<Star className="w-5 h-5" />}
          label="Sentiment Score"
          value={insights?.sentiment_score ? `${insights.sentiment_score.toFixed(1)}/5` : 'N/A'}
          color="yellow"
        />
        <StatCard
          icon={<MessageSquare className="w-5 h-5" />}
          label="Data Points"
          value={scraped_data_count.toString()}
          color="blue"
        />
        <StatCard
          icon={<Users className="w-5 h-5" />}
          label="ICPs Found"
          value={(insights?.icps?.length || 0).toString()}
          color="purple"
        />
        <StatCard
          icon={<Zap className="w-5 h-5" />}
          label="Angles"
          value={(insights?.messaging_angles?.length || 0).toString()}
          color="green"
        />
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-800">
        <div className="flex gap-4 overflow-x-auto">
          <TabButton
            active={activeTab === 'dna'}
            onClick={() => setActiveTab('dna')}
            icon={<Sparkles className="w-4 h-4" />}
          >
            Brand DNA
          </TabButton>
          <TabButton
            active={activeTab === 'insights'}
            onClick={() => setActiveTab('insights')}
            icon={<TrendingUp className="w-4 h-4" />}
          >
            Creative Dimensions
          </TabButton>
          <TabButton
            active={activeTab === 'ads'}
            onClick={() => setActiveTab('ads')}
            icon={<Video className="w-4 h-4" />}
          >
            Ad Intelligence
          </TabButton>
          <TabButton
            active={activeTab === 'generated'}
            onClick={() => setActiveTab('generated')}
            icon={<PenTool className="w-4 h-4" />}
          >
            Generated Content
          </TabButton>
          <TabButton
            active={activeTab === 'social'}
            onClick={() => setActiveTab('social')}
            icon={<Play className="w-4 h-4" />}
          >
            Social Media
          </TabButton>
          <TabButton
            active={activeTab === 'trends'}
            onClick={() => setActiveTab('trends')}
            icon={<Flame className="w-4 h-4" />}
          >
            TikTok Trends
          </TabButton>
          <TabButton
            active={activeTab === 'hooks'}
            onClick={() => setActiveTab('hooks')}
            icon={<Megaphone className="w-4 h-4" />}
          >
            Hooks Library
          </TabButton>
          <TabButton
            active={activeTab === 'sentiment'}
            onClick={() => setActiveTab('sentiment')}
            icon={<BarChart3 className="w-4 h-4" />}
          >
            Sentiment Analysis
          </TabButton>
          <TabButton
            active={activeTab === 'data'}
            onClick={() => setActiveTab('data')}
            icon={<Globe className="w-4 h-4" />}
          >
            Raw Data ({scraped_data_count})
          </TabButton>
          <TabButton
            active={activeTab === 'report'}
            onClick={() => setActiveTab('report')}
            icon={<FileText className="w-4 h-4" />}
          >
            Full Report
          </TabButton>
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'dna' && (
        <BrandDNAView brand={brand} />
      )}

      {activeTab === 'insights' && insights && (
        <InsightsView insights={insights} />
      )}

      {activeTab === 'ads' && insights && (
        <AdIntelligenceView insights={insights} />
      )}

      {activeTab === 'generated' && insights && (
        <GeneratedContentView insights={insights} sessionId={Number(sessionId)} />
      )}

      {activeTab === 'social' && (
        <SocialMediaView sessionId={Number(sessionId)} bySource={scraped_data_by_source} />
      )}

      {activeTab === 'trends' && (
        <div className="space-y-8">
          {/* TikTok Trends Section */}
          {insights?.tiktok_trends ? (
            <div>
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <span className="text-pink-400">📱</span> TikTok Trends & Analysis
              </h2>
              <TikTokTrendsView trends={insights.tiktok_trends} />
            </div>
          ) : (
            <div className="card p-8 text-center">
              <Flame className="w-12 h-12 text-slate-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-white mb-2">No TikTok Trends Data</h3>
              <p className="text-slate-400">Run a new research session to generate TikTok trends analysis.</p>
            </div>
          )}

          {/* Instagram Brand Presence Section */}
          <div>
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <span className="text-purple-400">📸</span> Instagram Brand Presence
            </h2>
            {insights?.instagram_brand_presence ? (
              <InstagramBrandView brandPresence={insights.instagram_brand_presence} />
            ) : (
              <div className="card p-8 text-center">
                <Flame className="w-12 h-12 text-slate-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">No Instagram Brand Data</h3>
                <p className="text-slate-400">Run a new research session to generate Instagram brand presence analysis.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'hooks' && insights?.hooks_library && (
        <HooksLibraryView
          library={insights.hooks_library}
          sessionId={Number(sessionId)}
          brandId={brand.id}
        />
      )}

      {activeTab === 'hooks' && !insights?.hooks_library && (
        <div className="card p-8 text-center">
          <Megaphone className="w-12 h-12 text-slate-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">No Hooks Library</h3>
          <p className="text-slate-400">
            Run a new research session to generate hooks library.
          </p>
        </div>
      )}

      {activeTab === 'sentiment' && (
        <SentimentView sessionId={Number(sessionId)} insights={insights} />
      )}

      {activeTab === 'data' && (
        <DataView sessionId={Number(sessionId)} bySource={scraped_data_by_source} />
      )}

      {activeTab === 'report' && insights?.full_report && (
        <div className="glass-card p-8 prose prose-invert max-w-none">
          <ReactMarkdown>{insights.full_report}</ReactMarkdown>
        </div>
      )}

      {/* AI Chat Assistant */}
      <ChatPanel sessionId={Number(sessionId)} />
    </div>
  );
}

function StatCard({ icon, label, value, color }: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: 'yellow' | 'blue' | 'purple' | 'green';
}) {
  const colors = {
    yellow: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    green: 'bg-green-500/10 text-green-400 border-green-500/20',
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

function TabButton({
  children,
  active,
  onClick,
  icon
}: {
  children: React.ReactNode;
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-all border-b-2 -mb-px ${active
        ? 'text-indigo-400 border-indigo-400'
        : 'text-slate-400 border-transparent hover:text-white'
        }`}
    >
      {icon}
      {children}
    </button>
  );
}
