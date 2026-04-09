import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Loader2,
  Globe,
  TrendingUp,
  Clock,
  ChevronRight,
  Sparkles,
  Trash2
} from 'lucide-react';
import { listBrands, createBrand, startResearch, getBrandSessions, deleteBrand } from '../api/client';
import type { Brand } from '../api/client';

export default function Dashboard() {
  const [brandName, setBrandName] = useState('');
  const [websiteUrl, setWebsiteUrl] = useState('');
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Fetch brands
  const { data: brands, isLoading: brandsLoading } = useQuery({
    queryKey: ['brands'],
    queryFn: listBrands,
  });

  // Create brand mutation
  const createMutation = useMutation({
    mutationFn: ({ name, url }: { name: string; url?: string }) =>
      createBrand(name, url || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brands'] });
      setBrandName('');
      setWebsiteUrl('');
    },
  });

  // Start research mutation
  const startResearchMutation = useMutation({
    mutationFn: (brandId: number) => startResearch(brandId),
    onSuccess: (session) => {
      navigate(`/research/${session.id}`);
    },
  });

  // Delete brand mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteBrand(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brands'] });
    },
  });

  const handleCreateAndStart = async () => {
    if (!brandName.trim()) return;

    const brand = await createMutation.mutateAsync({
      name: brandName.trim(),
      url: websiteUrl.trim() || undefined
    });

    startResearchMutation.mutate(brand.id);
  };

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="text-center py-12">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-500/10 border border-indigo-500/20 mb-6">
          <Sparkles className="w-4 h-4 text-indigo-400" />
          <span className="text-sm text-indigo-300">Powered by GPT-5.1</span>
        </div>
        <h1 className="text-4xl md:text-5xl font-display font-bold text-white mb-4">
          Brand Intelligence <span className="text-indigo-400">Scraper</span>
        </h1>
        <p className="text-lg text-slate-400 max-w-2xl mx-auto">
          Discover customer insights, pain points, and messaging angles by scraping
          Reddit, Twitter, TikTok, Instagram, and reviews.
        </p>
      </div>

      {/* New Research Card */}
      <div className="glass-card p-8 animate-fade-in">
        <h2 className="text-xl font-display font-semibold text-white mb-6 flex items-center gap-2">
          <Search className="w-5 h-5 text-indigo-400" />
          Start New Research
        </h2>

        <div className="grid md:grid-cols-2 gap-4 mb-6">
          <div>
            <label className="block text-sm text-slate-400 mb-2">Brand Name *</label>
            <input
              type="text"
              placeholder="e.g., Happy Head"
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
              className="input-field"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-2">Website URL (optional)</label>
            <input
              type="text"
              placeholder="e.g., https://happyhead.com"
              value={websiteUrl}
              onChange={(e) => setWebsiteUrl(e.target.value)}
              className="input-field"
            />
          </div>
        </div>

        <button
          onClick={handleCreateAndStart}
          disabled={!brandName.trim() || createMutation.isPending || startResearchMutation.isPending}
          className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {(createMutation.isPending || startResearchMutation.isPending) ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Sparkles className="w-5 h-5" />
          )}
          Start Research
        </button>
      </div>

      {/* Recent Brands */}
      <div className="space-y-4">
        <h2 className="text-xl font-display font-semibold text-white flex items-center gap-2">
          <Clock className="w-5 h-5 text-slate-400" />
          Recent Brands
        </h2>

        {brandsLoading ? (
          <div className="glass-card p-8 flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
          </div>
        ) : brands && brands.length > 0 ? (
          <div className="grid gap-4">
            {brands.map((brand, index) => (
              <BrandCard
                key={brand.id}
                brand={brand}
                index={index}
                onStartResearch={() => startResearchMutation.mutate(brand.id)}
                onDelete={() => deleteMutation.mutate(brand.id)}
                isStarting={startResearchMutation.isPending}
              />
            ))}
          </div>
        ) : (
          <div className="glass-card p-8 text-center">
            <Globe className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400">No brands yet. Start your first research above!</p>
          </div>
        )}
      </div>
    </div>
  );
}

function BrandCard({
  brand,
  index,
  onStartResearch,
  onDelete,
  isStarting
}: {
  brand: Brand;
  index: number;
  onStartResearch: () => void;
  onDelete: () => void;
  isStarting: boolean;
}) {
  const { data: sessions } = useQuery({
    queryKey: ['sessions', brand.id],
    queryFn: () => getBrandSessions(brand.id),
  });

  // Find the first COMPLETED session, not just the first session
  const latestCompletedSession = sessions?.find(s => s.status === 'completed');
  const latestSession = sessions?.[0];
  const navigate = useNavigate();

  return (
    <div
      className="glass-card p-6 animate-fade-in hover:border-indigo-500/30 transition-all cursor-pointer group"
      style={{ animationDelay: `${index * 100}ms` }}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h3 className="text-lg font-semibold text-white">{brand.name}</h3>
            {brand.sector && (
              <span className="tag-primary text-xs">{brand.sector}</span>
            )}
          </div>

          {brand.description && (
            <p className="text-sm text-slate-400 mb-3 line-clamp-2">{brand.description}</p>
          )}

          <div className="flex items-center gap-4 text-sm text-slate-500">
            {brand.website_url && (
              <span className="flex items-center gap-1">
                <Globe className="w-3 h-3" />
                {(() => {
                  try {
                    const url = brand.website_url.startsWith('http')
                      ? brand.website_url
                      : `https://${brand.website_url}`;
                    return new URL(url).hostname;
                  } catch {
                    return brand.website_url;
                  }
                })()}
              </span>
            )}
            {latestSession && (
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                Last: {new Date(latestSession.started_at).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {latestCompletedSession && (
            <button
              onClick={() => navigate(`/results/${latestCompletedSession.id}`)}
              className="btn-secondary text-sm py-2 px-4 flex items-center gap-1"
            >
              View Results
              <ChevronRight className="w-4 h-4" />
            </button>
          )}

          <button
            onClick={onStartResearch}
            disabled={isStarting}
            className="btn-primary text-sm py-2 px-4 flex items-center gap-1"
          >
            {isStarting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <TrendingUp className="w-4 h-4" />
            )}
            New Research
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              if (confirm('Delete this brand?')) onDelete();
            }}
            className="p-2 text-slate-500 hover:text-red-400 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

