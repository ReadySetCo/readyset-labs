import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Lightbulb,
  Megaphone,
  FileText,
  Quote,
  Image,
  Search,
  Star,
  Trash2,
  Copy,
  Check,
  Plus,
  ChevronDown,
  ArrowLeft,
  Loader2,
  AlertTriangle,
  Heart
} from 'lucide-react';
import {
  listIdeas,
  deleteIdea,
  toggleIdeaFavorite,
  getIdeaBankStats,
  type SavedIdea
} from '../api/client';

type IdeaType = 'all' | 'hook' | 'script' | 'thumbnail' | 'angle' | 'quote';

export default function IdeaBank() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState({
    type: 'all' as IdeaType,
    search: '',
    favoritesOnly: false
  });
  const [copiedId, setCopiedId] = useState<number | null>(null);

  // Fetch ideas
  const { data: ideas, isLoading, error } = useQuery({
    queryKey: ['ideas', filter],
    queryFn: () => listIdeas({
      idea_type: filter.type === 'all' ? undefined : filter.type,
      is_favorite: filter.favoritesOnly ? true : undefined,
      search: filter.search || undefined,
      limit: 100
    })
  });

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['ideaStats'],
    queryFn: getIdeaBankStats
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: deleteIdea,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ideas'] });
      queryClient.invalidateQueries({ queryKey: ['ideaStats'] });
    }
  });

  // Toggle favorite mutation
  const favoriteMutation = useMutation({
    mutationFn: toggleIdeaFavorite,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ideas'] });
      queryClient.invalidateQueries({ queryKey: ['ideaStats'] });
    }
  });

  const copyIdea = async (idea: SavedIdea) => {
    await navigator.clipboard.writeText(idea.content);
    setCopiedId(idea.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const typeIcons: Record<string, React.ReactNode> = {
    hook: <Megaphone className="w-4 h-4" />,
    script: <FileText className="w-4 h-4" />,
    thumbnail: <Image className="w-4 h-4" />,
    angle: <Lightbulb className="w-4 h-4" />,
    quote: <Quote className="w-4 h-4" />
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <h2 className="text-xl text-white mb-2">Error loading Idea Bank</h2>
        <p className="text-slate-400">{(error as Error)?.message || 'Unknown error'}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link to="/" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-white mb-2">
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>
          <h1 className="text-3xl font-display font-bold text-white mb-1 flex items-center gap-3">
            <Lightbulb className="w-8 h-8 text-yellow-400" />
            Idea Bank
          </h1>
          <p className="text-slate-400">Save and organize your best creative ideas</p>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatCard
            icon={<Lightbulb className="w-5 h-5" />}
            label="Total Ideas"
            value={stats.total_ideas.toString()}
            color="yellow"
          />
          <StatCard
            icon={<Heart className="w-5 h-5" />}
            label="Favorites"
            value={stats.favorites.toString()}
            color="pink"
          />
          <StatCard
            icon={<Megaphone className="w-5 h-5" />}
            label="Hooks"
            value={(stats.by_type?.hook || 0).toString()}
            color="purple"
          />
          <StatCard
            icon={<FileText className="w-5 h-5" />}
            label="Scripts"
            value={(stats.by_type?.script || 0).toString()}
            color="blue"
          />
          <StatCard
            icon={<Quote className="w-5 h-5" />}
            label="Quotes"
            value={(stats.by_type?.quote || 0).toString()}
            color="green"
          />
        </div>
      )}

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap items-center gap-4">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search ideas..."
              value={filter.search}
              onChange={(e) => setFilter({ ...filter, search: e.target.value })}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* Type Filter */}
          <div className="relative">
            <select
              value={filter.type}
              onChange={(e) => setFilter({ ...filter, type: e.target.value as IdeaType })}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white appearance-none pr-8 focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Types</option>
              <option value="hook">Hooks</option>
              <option value="script">Scripts</option>
              <option value="thumbnail">Thumbnails</option>
              <option value="angle">Angles</option>
              <option value="quote">Quotes</option>
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
          </div>

          {/* Favorites Toggle */}
          <button
            onClick={() => setFilter({ ...filter, favoritesOnly: !filter.favoritesOnly })}
            className={`px-3 py-2 rounded-lg border flex items-center gap-2 transition-colors ${
              filter.favoritesOnly
                ? 'bg-yellow-500/20 border-yellow-500/50 text-yellow-400'
                : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-white'
            }`}
          >
            <Star className={`w-4 h-4 ${filter.favoritesOnly ? 'fill-yellow-400' : ''}`} />
            Favorites
          </button>
        </div>
      </div>

      {/* Ideas Grid */}
      {ideas && ideas.length > 0 ? (
        <div className="grid gap-4">
          {ideas.map((idea) => (
            <IdeaCard
              key={idea.id}
              idea={idea}
              icon={typeIcons[idea.idea_type]}
              onCopy={() => copyIdea(idea)}
              onToggleFavorite={() => favoriteMutation.mutate(idea.id)}
              onDelete={() => {
                if (confirm('Delete this idea?')) {
                  deleteMutation.mutate(idea.id);
                }
              }}
              copied={copiedId === idea.id}
            />
          ))}
        </div>
      ) : (
        <div className="card p-12 text-center">
          <Lightbulb className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No Ideas Yet</h3>
          <p className="text-slate-400 mb-6">
            {filter.search || filter.type !== 'all' || filter.favoritesOnly
              ? 'No ideas match your filters. Try adjusting them.'
              : 'Start saving hooks, scripts, and quotes from your research sessions.'}
          </p>
          <Link to="/" className="btn-primary inline-flex items-center gap-2">
            <Plus className="w-4 h-4" />
            Start Research
          </Link>
        </div>
      )}
    </div>
  );
}

// Sub-components

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string; color: string }) {
  const colors: Record<string, string> = {
    yellow: 'bg-yellow-500/20 text-yellow-400',
    pink: 'bg-pink-500/20 text-pink-400',
    purple: 'bg-purple-500/20 text-purple-400',
    blue: 'bg-blue-500/20 text-blue-400',
    green: 'bg-green-500/20 text-green-400',
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

function IdeaCard({
  idea,
  icon,
  onCopy,
  onToggleFavorite,
  onDelete,
  copied
}: {
  idea: SavedIdea;
  icon?: React.ReactNode;
  onCopy: () => void;
  onToggleFavorite: () => void;
  onDelete: () => void;
  copied: boolean;
}) {
  const typeColors: Record<string, string> = {
    hook: 'bg-purple-500/20 text-purple-400',
    script: 'bg-blue-500/20 text-blue-400',
    thumbnail: 'bg-green-500/20 text-green-400',
    angle: 'bg-orange-500/20 text-orange-400',
    quote: 'bg-cyan-500/20 text-cyan-400',
  };

  return (
    <div className="card p-4 hover:bg-slate-800/70 transition-colors">
      <div className="flex items-start gap-4">
        {/* Type Icon */}
        <div className={`w-10 h-10 rounded-lg ${typeColors[idea.idea_type] || 'bg-slate-700 text-slate-400'} flex items-center justify-center shrink-0`}>
          {icon || <Lightbulb className="w-5 h-5" />}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {idea.title && (
            <h4 className="text-white font-medium mb-1">{idea.title}</h4>
          )}
          <p className="text-slate-300 whitespace-pre-wrap">
            {idea.idea_type === 'script' && idea.content.length > 300
              ? idea.content.slice(0, 300) + '...'
              : idea.content}
          </p>
          
          <div className="flex flex-wrap items-center gap-2 mt-3">
            <span className={`px-2 py-1 rounded text-xs font-medium ${typeColors[idea.idea_type] || 'bg-slate-700 text-slate-300'}`}>
              {idea.idea_type}
            </span>
            {idea.hook_type && (
              <span className="px-2 py-1 rounded text-xs bg-slate-800 text-slate-400">
                {idea.hook_type}
              </span>
            )}
            {idea.target_emotion && (
              <span className="px-2 py-1 rounded text-xs bg-slate-800 text-slate-400">
                {idea.target_emotion}
              </span>
            )}
            {idea.strength_score && (
              <span className="px-2 py-1 rounded text-xs bg-yellow-500/20 text-yellow-400 flex items-center gap-1">
                <Star className="w-3 h-3" /> {idea.strength_score}/5
              </span>
            )}
            {idea.platform_fit?.map(p => (
              <span key={p} className="px-2 py-1 rounded text-xs bg-slate-800 text-slate-500">
                {p}
              </span>
            ))}
          </div>

          {idea.notes && (
            <p className="text-sm text-slate-500 mt-2 italic">📝 {idea.notes}</p>
          )}

          <p className="text-xs text-slate-600 mt-2">
            Saved {new Date(idea.created_at).toLocaleDateString()}
          </p>
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2 shrink-0">
          <button
            onClick={onToggleFavorite}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors"
            title={idea.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
          >
            <Star className={`w-4 h-4 ${idea.is_favorite ? 'text-yellow-400 fill-yellow-400' : 'text-slate-400'}`} />
          </button>
          <button
            onClick={onCopy}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors"
            title="Copy content"
          >
            {copied ? (
              <Check className="w-4 h-4 text-green-400" />
            ) : (
              <Copy className="w-4 h-4 text-slate-400" />
            )}
          </button>
          <button
            onClick={onDelete}
            className="p-2 rounded-lg bg-slate-800 hover:bg-red-900/50 transition-colors"
            title="Delete"
          >
            <Trash2 className="w-4 h-4 text-slate-400 hover:text-red-400" />
          </button>
        </div>
      </div>
    </div>
  );
}
