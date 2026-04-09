import { useState } from 'react';
import {
    Instagram,
    Palette,
    MessageSquare,
    Target,
    ChevronDown,
    ChevronUp,
    Crown,
    Layers,
    Sparkles,
    Megaphone,
    Eye,
    Users,
    Lightbulb
} from 'lucide-react';

interface InstagramBrandPresence {
    // Core identity
    brand_voice?: string | {
        tone?: string;
        primary_tone?: string;
        characteristics?: string[];
    };
    primary_tone?: string;
    secondary_tones?: string[];
    communication_style?: string;
    vocabulary_patterns?: string[];
    emoji_usage?: string;

    // Visual
    visual_aesthetic?: {
        color_palette?: string[];
        style?: string;
        mood?: string;
    };
    visual_mood?: string;
    color_palette_description?: string;
    content_style?: string;
    aesthetic_keywords?: string[];

    // Content
    content_pillars?: string[];
    content_mix?: Record<string, string | number>;
    post_types?: string[];
    storytelling_approach?: string;

    // Brand positioning
    core_message?: string;
    value_proposition?: string;
    differentiation?: string;
    brand_archetype?: string;
    brand_personality?: string;
    key_brand_attributes?: string[];

    // Engagement
    engagement_style?: string;
    engagement_tactics?: string[];
    cta_patterns?: string[];
    audience_persona?: string;
    community_building?: string;
    exclusivity_signals?: string;

    // Strategy
    hashtag_strategy?: string | string[];
    messaging_themes?: string[];
    recurring_themes?: string[];
    promotional_approach?: string;
    content_frequency_vibe?: string;

    // Post formats
    post_formats?: string[];
    caption_style?: string;

    // Ad recommendations
    recommendations_for_ad_creation?: Record<string, any>;

    // Meta
    analyzed_at?: string;
    posts_analyzed?: number;
    brand_name?: string;
    source?: string;

    // Catch-all for unknown fields
    [key: string]: any;
}

interface InstagramBrandViewProps {
    brandPresence: InstagramBrandPresence;
}

// Safe array helper — handles string, array, or null
function toStrArray(val: any): string[] {
    if (!val) return [];
    if (Array.isArray(val)) return val.map(v => String(v));
    if (typeof val === 'string') return [val];
    return [];
}

export default function InstagramBrandView({ brandPresence }: InstagramBrandViewProps) {
    const [expandedSection, setExpandedSection] = useState<string | null>('voice');

    if (!brandPresence || Object.keys(brandPresence).length === 0) {
        return (
            <div className="card p-8 text-center">
                <Instagram className="w-12 h-12 text-slate-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">No Instagram Brand Data</h3>
                <p className="text-slate-400">
                    Run a new research session to generate Instagram brand presence analysis.
                </p>
            </div>
        );
    }

    const toggleSection = (section: string) => {
        setExpandedSection(expandedSection === section ? null : section);
    };

    // Extract voice tone safely
    const voiceTone = typeof brandPresence.brand_voice === 'string'
        ? brandPresence.brand_voice
        : brandPresence.brand_voice?.tone || brandPresence.brand_voice?.primary_tone
        || brandPresence.primary_tone || 'N/A';

    const hashtagArr = toStrArray(brandPresence.hashtag_strategy);
    const contentPillars = toStrArray(brandPresence.content_pillars);
    const secondaryTones = toStrArray(brandPresence.secondary_tones);
    const postFormats = toStrArray(brandPresence.post_formats || brandPresence.post_types);
    const aestheticKeywords = toStrArray(brandPresence.aesthetic_keywords);
    const ctaPatterns = toStrArray(brandPresence.cta_patterns);
    const engagementTactics = toStrArray(brandPresence.engagement_tactics);
    const recurringThemes = toStrArray(brandPresence.recurring_themes || brandPresence.messaging_themes);
    const keyAttributes = toStrArray(brandPresence.key_brand_attributes);
    const vocabPatterns = toStrArray(brandPresence.vocabulary_patterns);

    return (
        <div className="space-y-6">
            {/* Header Summary */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                    icon={<MessageSquare className="w-5 h-5" />}
                    label="Primary Tone"
                    value={brandPresence.primary_tone || (typeof voiceTone === 'string' ? voiceTone.slice(0, 20) : 'Analyzed')}
                    color="purple"
                />
                <StatCard
                    icon={<Crown className="w-5 h-5" />}
                    label="Archetype"
                    value={brandPresence.brand_archetype?.slice(0, 15) || 'Unknown'}
                    color="yellow"
                />
                <StatCard
                    icon={<Layers className="w-5 h-5" />}
                    label="Content Pillars"
                    value={contentPillars.length.toString()}
                    color="pink"
                />
                <StatCard
                    icon={<Eye className="w-5 h-5" />}
                    label="Posts Analyzed"
                    value={brandPresence.posts_analyzed?.toString() || '0'}
                    color="cyan"
                />
            </div>

            {/* Brand Voice & Tone */}
            <CollapsibleSection
                title="Brand Voice & Tone"
                icon={<MessageSquare className="w-5 h-5 text-purple-400" />}
                expanded={expandedSection === 'voice'}
                onToggle={() => toggleSection('voice')}
            >
                <div className="space-y-4">
                    <div className="grid md:grid-cols-2 gap-6">
                        <div className="bg-slate-800/50 rounded-lg p-4">
                            <h4 className="text-sm font-medium text-slate-400 mb-3">Brand Voice</h4>
                            <p className="text-white leading-relaxed">
                                {typeof brandPresence.brand_voice === 'string'
                                    ? brandPresence.brand_voice
                                    : voiceTone}
                            </p>
                        </div>
                        {brandPresence.communication_style && (
                            <div className="bg-slate-800/50 rounded-lg p-4">
                                <h4 className="text-sm font-medium text-slate-400 mb-3">Communication Style</h4>
                                <p className="text-white leading-relaxed">{brandPresence.communication_style}</p>
                            </div>
                        )}
                    </div>

                    {secondaryTones.length > 0 && (
                        <div className="bg-slate-800/50 rounded-lg p-4">
                            <h4 className="text-sm font-medium text-slate-400 mb-3">Tone Attributes</h4>
                            <div className="flex flex-wrap gap-2">
                                {secondaryTones.map((tone, idx) => (
                                    <span key={idx} className="text-xs bg-purple-500/20 text-purple-300 px-3 py-1.5 rounded-full">
                                        {tone}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {vocabPatterns.length > 0 && (
                        <div className="bg-slate-800/50 rounded-lg p-4">
                            <h4 className="text-sm font-medium text-slate-400 mb-3">Vocabulary Patterns</h4>
                            <div className="flex flex-wrap gap-2">
                                {vocabPatterns.map((v, idx) => (
                                    <span key={idx} className="text-xs bg-indigo-500/20 text-indigo-300 px-3 py-1.5 rounded-full">
                                        {v}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {brandPresence.emoji_usage && (
                        <div className="bg-slate-800/50 rounded-lg p-4">
                            <h4 className="text-sm font-medium text-slate-400 mb-2">Emoji Usage</h4>
                            <p className="text-white">{brandPresence.emoji_usage}</p>
                        </div>
                    )}
                </div>
            </CollapsibleSection>

            {/* Content Strategy */}
            {(contentPillars.length > 0 || brandPresence.content_mix || brandPresence.storytelling_approach) && (
                <CollapsibleSection
                    title="Content Strategy"
                    icon={<Layers className="w-5 h-5 text-pink-400" />}
                    expanded={expandedSection === 'content'}
                    onToggle={() => toggleSection('content')}
                >
                    <div className="space-y-4">
                        {contentPillars.length > 0 && (
                            <div>
                                <h4 className="text-sm font-medium text-slate-400 mb-3">Content Pillars</h4>
                                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
                                    {contentPillars.map((pillar, idx) => (
                                        <div key={idx} className="bg-slate-800/50 rounded-lg p-3 border-l-4 border-pink-500">
                                            <div className="flex items-center gap-2">
                                                <span className="w-6 h-6 rounded-full bg-pink-500/20 flex items-center justify-center text-pink-400 text-sm font-bold">
                                                    {idx + 1}
                                                </span>
                                                <span className="text-white font-medium">{pillar}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {brandPresence.content_mix && typeof brandPresence.content_mix === 'object' && (
                            <div className="bg-slate-800/50 rounded-lg p-4">
                                <h4 className="text-sm font-medium text-slate-400 mb-3">Content Mix</h4>
                                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                    {Object.entries(brandPresence.content_mix).map(([key, val], idx) => (
                                        <div key={idx} className="bg-slate-700/50 rounded-lg p-3 text-center">
                                            <p className="text-sm text-slate-400 capitalize">{key.replace(/_/g, ' ')}</p>
                                            <p className="text-white font-semibold mt-1">{String(val)}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {brandPresence.storytelling_approach && (
                            <div className="bg-slate-800/50 rounded-lg p-4">
                                <h4 className="text-sm font-medium text-slate-400 mb-2">Storytelling Approach</h4>
                                <p className="text-white leading-relaxed">{brandPresence.storytelling_approach}</p>
                            </div>
                        )}
                    </div>
                </CollapsibleSection>
            )}

            {/* Visual Aesthetic */}
            {(brandPresence.visual_aesthetic || brandPresence.visual_mood || brandPresence.content_style) && (
                <CollapsibleSection
                    title="Visual Aesthetic"
                    icon={<Palette className="w-5 h-5 text-cyan-400" />}
                    expanded={expandedSection === 'visual'}
                    onToggle={() => toggleSection('visual')}
                >
                    <div className="space-y-4">
                        <div className="grid md:grid-cols-2 gap-4">
                            {(brandPresence.visual_mood || brandPresence.visual_aesthetic?.mood) && (
                                <div className="bg-slate-800/50 rounded-lg p-4">
                                    <h4 className="text-sm font-medium text-slate-400 mb-2">Visual Mood</h4>
                                    <p className="text-white">{brandPresence.visual_mood || brandPresence.visual_aesthetic?.mood}</p>
                                </div>
                            )}
                            {(brandPresence.content_style || brandPresence.visual_aesthetic?.style) && (
                                <div className="bg-slate-800/50 rounded-lg p-4">
                                    <h4 className="text-sm font-medium text-slate-400 mb-2">Content Style</h4>
                                    <p className="text-white">{brandPresence.content_style || brandPresence.visual_aesthetic?.style}</p>
                                </div>
                            )}
                        </div>

                        {brandPresence.color_palette_description && (
                            <div className="bg-slate-800/50 rounded-lg p-4">
                                <h4 className="text-sm font-medium text-slate-400 mb-2">Color Palette</h4>
                                <p className="text-white">{brandPresence.color_palette_description}</p>
                            </div>
                        )}

                        {aestheticKeywords.length > 0 && (
                            <div className="flex flex-wrap gap-2">
                                {aestheticKeywords.map((kw, idx) => (
                                    <span key={idx} className="text-xs bg-cyan-500/20 text-cyan-300 px-3 py-1.5 rounded-full">
                                        {kw}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>
                </CollapsibleSection>
            )}

            {/* Brand Positioning */}
            {(brandPresence.core_message || brandPresence.value_proposition || brandPresence.differentiation) && (
                <CollapsibleSection
                    title="Brand Positioning"
                    icon={<Target className="w-5 h-5 text-orange-400" />}
                    expanded={expandedSection === 'positioning'}
                    onToggle={() => toggleSection('positioning')}
                >
                    <div className="space-y-4">
                        {brandPresence.core_message && (
                            <div className="bg-gradient-to-r from-orange-500/10 to-yellow-500/10 rounded-lg p-4 border border-orange-500/20">
                                <h4 className="text-sm font-medium text-orange-400 mb-2">Core Message</h4>
                                <p className="text-white leading-relaxed">{brandPresence.core_message}</p>
                            </div>
                        )}
                        <div className="grid md:grid-cols-2 gap-4">
                            {brandPresence.value_proposition && (
                                <div className="bg-slate-800/50 rounded-lg p-4">
                                    <h4 className="text-sm font-medium text-slate-400 mb-2">Value Proposition</h4>
                                    <p className="text-white leading-relaxed">{brandPresence.value_proposition}</p>
                                </div>
                            )}
                            {brandPresence.differentiation && (
                                <div className="bg-slate-800/50 rounded-lg p-4">
                                    <h4 className="text-sm font-medium text-slate-400 mb-2">Differentiation</h4>
                                    <p className="text-white leading-relaxed">{brandPresence.differentiation}</p>
                                </div>
                            )}
                        </div>
                    </div>
                </CollapsibleSection>
            )}

            {/* Brand Archetype & Personality */}
            {(brandPresence.brand_archetype || brandPresence.brand_personality) && (
                <div className="card p-6 bg-gradient-to-r from-yellow-500/10 to-orange-500/10 border-yellow-500/20">
                    <div className="flex items-start gap-4">
                        <div className="w-12 h-12 rounded-xl bg-yellow-500/20 flex items-center justify-center flex-shrink-0">
                            <Crown className="w-6 h-6 text-yellow-400" />
                        </div>
                        <div className="flex-1">
                            {brandPresence.brand_archetype && (
                                <div className="mb-2">
                                    <p className="text-sm text-slate-400">Brand Archetype</p>
                                    <p className="text-2xl font-bold text-white">{brandPresence.brand_archetype}</p>
                                </div>
                            )}
                            {brandPresence.brand_personality && (
                                <p className="text-slate-300 leading-relaxed">{brandPresence.brand_personality}</p>
                            )}
                            {keyAttributes.length > 0 && (
                                <div className="flex flex-wrap gap-2 mt-3">
                                    {keyAttributes.map((attr, idx) => (
                                        <span key={idx} className="text-xs bg-yellow-500/20 text-yellow-300 px-2 py-1 rounded">
                                            {attr}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Engagement Strategy */}
            {(engagementTactics.length > 0 || brandPresence.audience_persona || brandPresence.community_building) && (
                <CollapsibleSection
                    title="Engagement & Community"
                    icon={<Users className="w-5 h-5 text-green-400" />}
                    expanded={expandedSection === 'engagement'}
                    onToggle={() => toggleSection('engagement')}
                >
                    <div className="space-y-4">
                        {brandPresence.audience_persona && (
                            <div className="bg-slate-800/50 rounded-lg p-4">
                                <h4 className="text-sm font-medium text-slate-400 mb-2">Audience Persona</h4>
                                <p className="text-white leading-relaxed">{brandPresence.audience_persona}</p>
                            </div>
                        )}
                        <div className="grid md:grid-cols-2 gap-4">
                            {brandPresence.community_building && (
                                <div className="bg-slate-800/50 rounded-lg p-4">
                                    <h4 className="text-sm font-medium text-slate-400 mb-2">Community Building</h4>
                                    <p className="text-white leading-relaxed">{brandPresence.community_building}</p>
                                </div>
                            )}
                            {brandPresence.exclusivity_signals && (
                                <div className="bg-slate-800/50 rounded-lg p-4">
                                    <h4 className="text-sm font-medium text-slate-400 mb-2">Exclusivity Signals</h4>
                                    <p className="text-white leading-relaxed">{brandPresence.exclusivity_signals}</p>
                                </div>
                            )}
                        </div>
                        {engagementTactics.length > 0 && (
                            <div className="bg-slate-800/50 rounded-lg p-4">
                                <h4 className="text-sm font-medium text-slate-400 mb-3">Engagement Tactics</h4>
                                <div className="flex flex-wrap gap-2">
                                    {engagementTactics.map((t, idx) => (
                                        <span key={idx} className="text-xs bg-green-500/20 text-green-300 px-3 py-1.5 rounded-full">
                                            {t}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                        {ctaPatterns.length > 0 && (
                            <div className="bg-slate-800/50 rounded-lg p-4">
                                <h4 className="text-sm font-medium text-slate-400 mb-3">CTA Patterns</h4>
                                <div className="flex flex-wrap gap-2">
                                    {ctaPatterns.map((cta, idx) => (
                                        <span key={idx} className="text-xs bg-emerald-500/20 text-emerald-300 px-3 py-1.5 rounded-full">
                                            {cta}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </CollapsibleSection>
            )}

            {/* Recurring Themes & Hashtags */}
            {(recurringThemes.length > 0 || hashtagArr.length > 0) && (
                <CollapsibleSection
                    title="Themes & Hashtags"
                    icon={<Sparkles className="w-5 h-5 text-blue-400" />}
                    expanded={expandedSection === 'themes'}
                    onToggle={() => toggleSection('themes')}
                >
                    <div className="space-y-4">
                        {recurringThemes.length > 0 && (
                            <div>
                                <h4 className="text-sm font-medium text-slate-400 mb-3">Recurring Themes</h4>
                                <div className="flex flex-wrap gap-3">
                                    {recurringThemes.map((theme, idx) => (
                                        <div key={idx} className="bg-orange-500/10 border border-orange-500/30 rounded-lg px-4 py-2">
                                            <span className="text-orange-300">{theme}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        {hashtagArr.length > 0 && (
                            <div>
                                <h4 className="text-sm font-medium text-slate-400 mb-3">Hashtag Strategy</h4>
                                {typeof brandPresence.hashtag_strategy === 'string' ? (
                                    <p className="text-white leading-relaxed">{brandPresence.hashtag_strategy}</p>
                                ) : (
                                    <div className="flex flex-wrap gap-2">
                                        {hashtagArr.slice(0, 10).map((tag, idx) => (
                                            <span key={idx} className="text-sm bg-blue-500/20 text-blue-300 px-2 py-1 rounded">
                                                {tag}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </CollapsibleSection>
            )}

            {/* Post Formats */}
            {postFormats.length > 0 && (
                <div className="card p-6">
                    <h4 className="text-sm font-medium text-slate-400 mb-4 flex items-center gap-2">
                        <Sparkles className="w-4 h-4" /> Post Formats
                    </h4>
                    <div className="flex flex-wrap gap-2">
                        {postFormats.map((format, idx) => (
                            <span key={idx} className="tag-primary">{format}</span>
                        ))}
                    </div>
                </div>
            )}

            {/* Ad Creation Recommendations */}
            {brandPresence.recommendations_for_ad_creation && typeof brandPresence.recommendations_for_ad_creation === 'object' && (
                <CollapsibleSection
                    title="Ad Creation Recommendations"
                    icon={<Lightbulb className="w-5 h-5 text-amber-400" />}
                    expanded={expandedSection === 'adrecs'}
                    onToggle={() => toggleSection('adrecs')}
                >
                    <div className="grid md:grid-cols-2 gap-4">
                        {Object.entries(brandPresence.recommendations_for_ad_creation).map(([key, val], idx) => (
                            <div key={idx} className="bg-slate-800/50 rounded-lg p-4">
                                <h4 className="text-sm font-medium text-amber-400 mb-2 capitalize">{key.replace(/_/g, ' ')}</h4>
                                <p className="text-white leading-relaxed text-sm">
                                    {typeof val === 'string' ? val : JSON.stringify(val, null, 2)}
                                </p>
                            </div>
                        ))}
                    </div>
                </CollapsibleSection>
            )}

            {/* Promotional Approach */}
            {brandPresence.promotional_approach && (
                <div className="bg-slate-800/50 rounded-lg p-4">
                    <h4 className="text-sm font-medium text-slate-400 mb-2 flex items-center gap-2">
                        <Megaphone className="w-4 h-4" /> Promotional Approach
                    </h4>
                    <p className="text-white leading-relaxed">{brandPresence.promotional_approach}</p>
                </div>
            )}
        </div>
    );
}

// Sub-components

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string; color: string }) {
    const colors: Record<string, string> = {
        purple: 'bg-purple-500/20 text-purple-400',
        pink: 'bg-pink-500/20 text-pink-400',
        yellow: 'bg-yellow-500/20 text-yellow-400',
        red: 'bg-red-500/20 text-red-400',
        cyan: 'bg-cyan-500/20 text-cyan-400',
        green: 'bg-green-500/20 text-green-400',
    };

    return (
        <div className="card p-4">
            <div className={`w-10 h-10 rounded-lg ${colors[color] || colors.purple} flex items-center justify-center mb-3`}>
                {icon}
            </div>
            <p className="text-lg font-bold text-white truncate">{value}</p>
            <p className="text-sm text-slate-400">{label}</p>
        </div>
    );
}

function CollapsibleSection({
    title,
    icon,
    expanded,
    onToggle,
    children
}: {
    title: string;
    icon: React.ReactNode;
    expanded: boolean;
    onToggle: () => void;
    children: React.ReactNode;
}) {
    return (
        <div className="card overflow-hidden">
            <button
                onClick={onToggle}
                className="w-full p-4 flex items-center justify-between hover:bg-slate-800/50 transition-colors"
            >
                <div className="flex items-center gap-3">
                    {icon}
                    <h3 className="text-lg font-semibold text-white">{title}</h3>
                </div>
                {expanded ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
            </button>
            {expanded && <div className="p-4 pt-0 border-t border-slate-800">{children}</div>}
        </div>
    );
}
