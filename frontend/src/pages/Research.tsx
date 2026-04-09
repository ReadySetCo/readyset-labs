import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Loader2,
  CheckCircle2,
  Circle,
  AlertCircle,
  Globe,
  MessageSquare,
  Twitter,
  Instagram,
  Star,
  Search,
  Palette,
  Type,
  Image,
  Sparkles,
  Heart,
  MessageCircle,
  Eye,
  PenTool,
  FileText,
  Clock,
  Zap,
  ChevronDown,
  ChevronUp,
  Terminal,
  AlertTriangle,
  Info,
  CheckCircle
} from 'lucide-react';
import { getSessionProgress, getSessionLogs } from '../api/client';
import type { LogEntry } from '../api/client';

// Brand DNA extraction steps (Pomelli-style)
const BRAND_DNA_STEPS = [
  { id: 'images', label: 'Pulling images from website...', icon: Image },
  { id: 'logo', label: 'Finding your logo...', icon: Sparkles },
  { id: 'colors', label: 'Gathering colors...', icon: Palette },
  { id: 'fonts', label: 'Picking brand fonts...', icon: Type },
  { id: 'values', label: 'Studying your brand values...', icon: Heart },
  { id: 'tone', label: 'Learning your tone of voice...', icon: MessageCircle },
  { id: 'aesthetic', label: 'Determining your visual aesthetic...', icon: Eye },
  { id: 'tagline', label: 'Writing your tagline...', icon: PenTool },
  { id: 'summary', label: 'Summarizing your business...', icon: FileText },
];

const SOURCE_ICONS: Record<string, React.ReactNode> = {
  website: <Globe className="w-4 h-4" />,
  reddit: <MessageSquare className="w-4 h-4" />,
  twitter: <Twitter className="w-4 h-4" />,
  tiktok: <span className="text-xs font-bold">TT</span>,
  instagram: <Instagram className="w-4 h-4" />,
  amazon: <Star className="w-4 h-4" />,
  google: <Search className="w-4 h-4" />,
  trustpilot: <Star className="w-4 h-4" />,
};

function formatTime(seconds: number): string {
  if (seconds <= 0) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export default function Research() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [dnaStepIndex, setDnaStepIndex] = useState(0);
  const [elapsedTime, setElapsedTime] = useState(0);

  // Poll for progress with error handling
  const { data: progress, isLoading, error: progressError } = useQuery({
    queryKey: ['progress', sessionId],
    queryFn: () => getSessionProgress(Number(sessionId)),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false;
      }
      return 2000; // Poll every 2 seconds
    },
    staleTime: 1000, // Don't refetch if data is less than 1 second old
    retry: 3, // Retry failed requests up to 3 times
    retryDelay: 1000, // Wait 1 second between retries
  });

  // Elapsed time counter
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedTime(prev => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Animate DNA steps
  useEffect(() => {
    if (progress?.current_phase === 'brand_dna') {
      const interval = setInterval(() => {
        setDnaStepIndex(prev => (prev + 1) % BRAND_DNA_STEPS.length);
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [progress?.current_phase]);

  // Redirect when complete
  useEffect(() => {
    if (progress?.status === 'completed') {
      setTimeout(() => {
        navigate(`/results/${sessionId}`);
      }, 1500);
    }
  }, [progress?.status, sessionId, navigate]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
      </div>
    );
  }

  // Show error state if polling fails
  if (progressError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <AlertCircle className="w-12 h-12 text-red-400" />
        <h2 className="text-xl font-semibold text-white">Connection Error</h2>
        <p className="text-slate-400">Unable to connect to the research backend.</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-white transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  // Updated to match actual sources from backend
  const allSources = [
    'website', 'reddit', 'twitter', 'tiktok',
    'instagram', 'amazon', 'google', 'trustpilot'
  ];

  const isBrandDNAPhase = progress?.current_phase === 'brand_dna';
  const estimatedRemaining = progress?.estimated_time_remaining || 600;

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <div className="inline-flex items-center gap-2 mb-4 px-4 py-2 rounded-full bg-indigo-500/10 border border-indigo-500/30">
          <Zap className="w-4 h-4 text-indigo-400" />
          <span className="text-sm text-indigo-300">Building Your Brand Intelligence</span>
        </div>
        <h1 className="text-4xl font-display font-bold text-white mb-2">
          Research in Progress
        </h1>
        <p className="text-slate-400 text-lg">
          Analyzing your brand and gathering market intelligence...
        </p>
      </div>

      {/* Timer */}
      <div className="flex justify-center gap-8">
        <div className="text-center">
          <div className="flex items-center gap-2 text-slate-400 text-sm mb-1">
            <Clock className="w-4 h-4" />
            <span>Elapsed</span>
          </div>
          <span className="text-2xl font-mono text-white">{formatTime(elapsedTime)}</span>
        </div>
        <div className="text-center">
          <div className="flex items-center gap-2 text-slate-400 text-sm mb-1">
            <Clock className="w-4 h-4" />
            <span>Estimated Remaining</span>
          </div>
          <span className="text-2xl font-mono text-indigo-400">~{Math.ceil(estimatedRemaining / 60)} min</span>
        </div>
      </div>

      {/* Progress Card */}
      <div className="glass-card p-8 animate-fade-in">
        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-slate-400">
              {progress?.current_step || 'Starting...'}
            </span>
            <span className="text-sm font-medium text-indigo-400">
              {progress?.progress_percent || 0}%
            </span>
          </div>
          <div className="h-3 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full gradient-accent transition-all duration-700 ease-out rounded-full"
              style={{ width: `${progress?.progress_percent || 0}%` }}
            />
          </div>
        </div>

        {/* Status */}
        <div className="flex flex-col items-center justify-center gap-2 mb-8">
          {progress?.status === 'completed' ? (
            <>
              <CheckCircle2 className="w-8 h-8 text-green-400" />
              <span className="text-xl text-green-400 font-medium">Research Complete!</span>
            </>
          ) : progress?.status === 'failed' ? (
            <>
              <AlertCircle className="w-8 h-8 text-red-400" />
              <span className="text-xl text-red-400 font-medium">Research Failed</span>
            </>
          ) : (
            <>
              <div className="flex items-center gap-3">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
                <span className="text-xl text-white font-medium">
                  {progress?.current_step || 'Processing...'}
                </span>
              </div>
              {/* Phase Badge */}
              <div className="flex items-center gap-2 mt-2">
                <span className="px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 text-sm font-medium uppercase tracking-wide">
                  {progress?.current_phase?.replace('_', ' ') || 'Starting'}
                </span>
              </div>
            </>
          )}
        </div>

        {/* Brand DNA Steps (Pomelli-style) */}
        {isBrandDNAPhase && (
          <div className="mb-8 p-6 bg-gradient-to-br from-indigo-500/10 to-purple-500/10 rounded-xl border border-indigo-500/20">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              Building Your Brand DNA
            </h3>
            <div className="space-y-3">
              {BRAND_DNA_STEPS.map((step, index) => {
                const Icon = step.icon;
                const isActive = index === dnaStepIndex;
                const isCompleted = index < dnaStepIndex;

                return (
                  <div
                    key={step.id}
                    className={`flex items-center gap-3 p-3 rounded-lg transition-all duration-500 ${isActive
                      ? 'bg-indigo-500/20 border border-indigo-500/40'
                      : isCompleted
                        ? 'opacity-60'
                        : 'opacity-30'
                      }`}
                  >
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${isCompleted
                      ? 'bg-green-500/20 text-green-400'
                      : isActive
                        ? 'bg-indigo-500/20 text-indigo-400'
                        : 'bg-slate-700/50 text-slate-500'
                      }`}>
                      {isCompleted ? (
                        <CheckCircle2 className="w-4 h-4" />
                      ) : isActive ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Icon className="w-4 h-4" />
                      )}
                    </div>
                    <span className={`text-sm font-medium ${isActive ? 'text-white' : isCompleted ? 'text-slate-400' : 'text-slate-500'
                      }`}>
                      {step.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Sources Grid */}
        {!isBrandDNAPhase && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {allSources.map((source) => {
              const isCompleted = progress?.sources_completed?.includes(source);
              const isPending = progress?.sources_pending?.includes(source);
              const isCurrent = !isCompleted && !isPending && progress?.status === 'in_progress';

              return (
                <div
                  key={source}
                  className={`p-4 rounded-xl border transition-all ${isCompleted
                    ? 'bg-green-500/10 border-green-500/30'
                    : isCurrent
                      ? 'bg-indigo-500/10 border-indigo-500/30 animate-pulse'
                      : 'bg-slate-800/30 border-slate-700/30'
                    }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className={`${isCompleted ? 'text-green-400' : 'text-slate-400'}`}>
                      {SOURCE_ICONS[source]}
                    </span>
                    {isCompleted ? (
                      <CheckCircle2 className="w-4 h-4 text-green-400" />
                    ) : isCurrent ? (
                      <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                    ) : (
                      <Circle className="w-4 h-4 text-slate-600" />
                    )}
                  </div>
                  <span className={`text-sm font-medium capitalize ${isCompleted ? 'text-green-300' : 'text-slate-400'
                    }`}>
                    {source}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Phase Indicator */}
      <div className="flex justify-center">
        <div className="flex items-center gap-2">
          {['brand_dna', 'discovery', 'keywords', 'scraping', 'ad_library', 'competitors', 'insights'].map((phase, index) => {
            const currentPhaseIndex = ['brand_dna', 'discovery', 'keywords', 'scraping', 'ad_library', 'competitors', 'insights'].indexOf(progress?.current_phase || 'brand_dna');
            const isCompleted = index < currentPhaseIndex;
            const isCurrent = index === currentPhaseIndex;

            return (
              <div
                key={phase}
                className={`w-3 h-3 rounded-full transition-all ${isCompleted
                  ? 'bg-green-400'
                  : isCurrent
                    ? 'bg-indigo-400 animate-pulse'
                    : 'bg-slate-700'
                  }`}
                title={phase.replace('_', ' ')}
              />
            );
          })}
        </div>
      </div>

      {/* Tips */}
      <div className="glass-card p-6 bg-indigo-500/5 border-indigo-500/20">
        <h3 className="text-sm font-semibold text-indigo-300 mb-3">What's happening?</h3>
        <ul className="text-sm text-slate-400 space-y-2">
          <li className="flex items-start gap-2">
            <span className="text-indigo-400 mt-0.5">•</span>
            <span><strong className="text-slate-300">Brand DNA:</strong> Extracting colors, fonts, logo, and brand identity</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-indigo-400 mt-0.5">•</span>
            <span><strong className="text-slate-300">Track 1:</strong> Finding mentions of your brand across platforms</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-indigo-400 mt-0.5">•</span>
            <span><strong className="text-slate-300">Track 2:</strong> Researching the market segment and customer conversations</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-indigo-400 mt-0.5">•</span>
            <span><strong className="text-slate-300">Ad Library:</strong> Analyzing active Facebook/Instagram ads</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-indigo-400 mt-0.5">•</span>
            <span><strong className="text-slate-300">Analysis:</strong> AI extracts insights, patterns, and Creative Dimensions</span>
          </li>
        </ul>
      </div>

      {/* Real-time Logs Panel */}
      <LogsPanel sessionId={Number(sessionId)} isActive={progress?.status === 'in_progress'} />
    </div>
  );
}

// LogsPanel - Shows real-time scraping logs
function LogsPanel({ sessionId, isActive }: { sessionId: number; isActive: boolean }) {
  const [isExpanded, setIsExpanded] = useState(true); // Auto-expanded
  const logsContainerRef = useRef<HTMLDivElement>(null);

  // Poll for logs when active
  const { data: logsData } = useQuery({
    queryKey: ['logs', sessionId],
    queryFn: () => getSessionLogs(sessionId),
    refetchInterval: isActive ? 1500 : false, // Faster polling
    enabled: true, // Always fetch
  });

  const logs = logsData?.logs || [];

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (logsContainerRef.current && isExpanded) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [logs.length, isExpanded]);

  const getLogIcon = (level: string) => {
    switch (level) {
      case 'success':
        return <CheckCircle className="w-3 h-3 text-green-400" />;
      case 'warning':
        return <AlertTriangle className="w-3 h-3 text-yellow-400" />;
      case 'error':
        return <AlertCircle className="w-3 h-3 text-red-400" />;
      default:
        return <Info className="w-3 h-3 text-blue-400" />;
    }
  };

  const getLogColor = (level: string) => {
    switch (level) {
      case 'success':
        return 'text-green-300';
      case 'warning':
        return 'text-yellow-300';
      case 'error':
        return 'text-red-300';
      default:
        return 'text-slate-300';
    }
  };

  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-slate-800/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-slate-400" />
          <span className="font-medium text-white">Live Logs</span>
          {logs.length > 0 && (
            <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">
              {logs.length}
            </span>
          )}
          {isActive && (
            <span className="flex items-center gap-1 text-xs text-green-400">
              <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
              Live
            </span>
          )}
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-slate-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-400" />
        )}
      </button>

      {isExpanded && (
        <div
          ref={logsContainerRef}
          className="max-h-64 overflow-y-auto bg-slate-900/50 border-t border-slate-700/50"
        >
          {logs.length > 0 ? (
            <div className="p-3 space-y-1 font-mono text-xs">
              {logs.map((log: LogEntry, i: number) => (
                <div
                  key={i}
                  className={`flex items-start gap-2 py-1 ${getLogColor(log.level)}`}
                >
                  <span className="text-slate-500 shrink-0">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  {getLogIcon(log.level)}
                  {log.source && (
                    <span className="tag text-xs bg-slate-700 text-slate-400 shrink-0">
                      {log.source}
                    </span>
                  )}
                  <span className="flex-1">{log.message}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-6 text-center text-slate-500">
              <Terminal className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No logs yet</p>
              <p className="text-xs">Logs will appear here once scraping starts</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
