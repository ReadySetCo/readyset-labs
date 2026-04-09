import {
  Sparkles,
  Palette,
  Type,
  Heart,
  MessageSquare,
  Globe,
  ExternalLink,
  FileText,
  Target,
  Image,
} from 'lucide-react';

export default function BrandDNAView({ brand }: {
  brand: {
    name: string;
    description?: string;
    brand_colors?: string[];
    tagline?: string;
    brand_values?: string[];
    brand_aesthetic?: string[];
    tone_of_voice?: string[];
    logo_url?: string;
    fonts?: string[];
    brand_images?: string[];
    social_media_urls?: Record<string, string>;
    product_descriptions?: Array<{ name: string; description?: string }>;
  }
}) {
  const hasDNA = brand.brand_colors?.length || brand.tagline || brand.brand_values?.length;

  if (!hasDNA) {
    return (
      <div className="glass-card p-8 text-center">
        <Sparkles className="w-12 h-12 text-slate-600 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-white mb-2">No Brand DNA Available</h3>
        <p className="text-slate-400">Brand DNA extraction requires a valid website URL.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Logo */}
      <div className="glass-card p-6 flex items-center gap-6">
        {brand.logo_url && (
          <div className="w-20 h-20 rounded-xl bg-white/10 flex items-center justify-center overflow-hidden">
            <img
              src={brand.logo_url}
              alt={`${brand.name} logo`}
              className="w-full h-full object-contain"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          </div>
        )}
        <div className="flex-1">
          <h2 className="text-2xl font-display font-bold text-white mb-1">{brand.name}</h2>
          {brand.tagline && (
            <p className="text-xl italic text-amber-400">{brand.tagline}</p>
          )}
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Colors */}
        {brand.brand_colors && brand.brand_colors.length > 0 && (
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <Palette className="w-5 h-5 text-indigo-400" />
              <h3 className="text-lg font-semibold text-white">Colors</h3>
            </div>
            <div className="flex flex-wrap gap-4">
              {brand.brand_colors.map((color, i) => (
                <div key={i} className="flex flex-col items-center gap-2">
                  <div
                    className="w-14 h-14 rounded-full border-2 border-white/20 shadow-lg"
                    style={{ backgroundColor: color }}
                  />
                  <span className="text-xs text-slate-400 font-mono">{color}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Fonts */}
        {brand.fonts && brand.fonts.length > 0 && (
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <Type className="w-5 h-5 text-indigo-400" />
              <h3 className="text-lg font-semibold text-white">Typography</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {brand.fonts.map((font, i) => (
                <span
                  key={i}
                  className="px-3 py-1.5 bg-slate-700/50 rounded-lg text-slate-300 text-sm"
                  style={{ fontFamily: font }}
                >
                  {font}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Brand Values */}
        {brand.brand_values && brand.brand_values.length > 0 && (
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <Heart className="w-5 h-5 text-pink-400" />
              <h3 className="text-lg font-semibold text-white">Brand Values</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {brand.brand_values.map((value, i) => (
                <span
                  key={i}
                  className="px-3 py-1.5 bg-pink-500/20 text-pink-300 rounded-full text-sm font-medium border border-pink-500/30"
                >
                  {value}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Brand Aesthetic */}
        {brand.brand_aesthetic && brand.brand_aesthetic.length > 0 && (
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="w-5 h-5 text-purple-400" />
              <h3 className="text-lg font-semibold text-white">Brand Aesthetic</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {brand.brand_aesthetic.map((item, i) => (
                <span
                  key={i}
                  className="px-3 py-1.5 bg-purple-500/20 text-purple-300 rounded-full text-sm font-medium border border-purple-500/30"
                >
                  {item}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Tone of Voice */}
        {brand.tone_of_voice && brand.tone_of_voice.length > 0 && (
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <MessageSquare className="w-5 h-5 text-blue-400" />
              <h3 className="text-lg font-semibold text-white">Tone of Voice</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {brand.tone_of_voice.map((tone, i) => (
                <span
                  key={i}
                  className="px-3 py-1.5 bg-blue-500/20 text-blue-300 rounded-full text-sm font-medium border border-blue-500/30"
                >
                  {tone}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Social Media */}
        {brand.social_media_urls && Object.keys(brand.social_media_urls).length > 0 && (
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <Globe className="w-5 h-5 text-green-400" />
              <h3 className="text-lg font-semibold text-white">Social Media</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(brand.social_media_urls).map(([platform, url]) => (
                <a
                  key={platform}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-green-500/20 text-green-300 rounded-lg text-sm font-medium border border-green-500/30 hover:bg-green-500/30 transition-colors"
                >
                  {platform.charAt(0).toUpperCase() + platform.slice(1)}
                  <ExternalLink className="w-3 h-3" />
                </a>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Business Overview */}
      {brand.description && (
        <div className="glass-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <FileText className="w-5 h-5 text-indigo-400" />
            <h3 className="text-lg font-semibold text-white">Business Overview</h3>
          </div>
          <p className="text-slate-300 leading-relaxed">{brand.description}</p>
        </div>
      )}

      {/* Products */}
      {brand.product_descriptions && brand.product_descriptions.length > 0 && (
        <div className="glass-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Target className="w-5 h-5 text-indigo-400" />
            <h3 className="text-lg font-semibold text-white">Products & Services</h3>
          </div>
          <div className="grid gap-3">
            {brand.product_descriptions.map((product, i) => (
              <div key={i} className="p-4 bg-slate-800/50 rounded-lg">
                <h4 className="font-medium text-white mb-1">{product.name}</h4>
                {product.description && (
                  <p className="text-sm text-slate-400">{product.description}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Brand Images Grid */}
      {brand.brand_images && brand.brand_images.length > 0 && (
        <div className="glass-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Image className="w-5 h-5 text-indigo-400" />
            <h3 className="text-lg font-semibold text-white">Brand Images</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {brand.brand_images.slice(0, 8).map((url, i) => (
              <div key={i} className="aspect-square rounded-lg overflow-hidden bg-slate-800">
                <img
                  src={url}
                  alt={`Brand image ${i + 1}`}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none';
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
