import { useState, useRef, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
    MessageCircle,
    Send,
    X,
    Loader2,
    Sparkles,
    User,
    Bot,
    Lightbulb
} from 'lucide-react';
import { sendChatMessage, getChatSuggestions } from '../api/client';
import type { ChatResponse } from '../api/client';

interface ChatSource {
    source_type: string;
    source_url?: string;
    content?: string;
    sentiment?: string;
    similarity?: number;
}

interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    sources?: ChatSource[];
}

interface ChatPanelProps {
    sessionId?: number;
    brandId?: number;
    brandName?: string;  // Optional - for display purposes
}

export default function ChatPanel({ sessionId, brandId }: ChatPanelProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Get suggestions
    const { data: suggestionsData } = useQuery({
        queryKey: ['chatSuggestions', sessionId],
        queryFn: () => getChatSuggestions(sessionId),
        enabled: isOpen && messages.length === 0,
    });

    // Send message mutation - using LOCAL RAG (ChromaDB) instead of AnythingLLM
    const sendMutation = useMutation({
        mutationFn: (message: string) => sendChatMessage({
            message,
            session_id: sessionId,
            brand_id: brandId
        }),
        onSuccess: (data: ChatResponse) => {
            const responseText = data.error
                ? `Error: ${data.error}`
                : data.response;
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: responseText,
                timestamp: new Date(),
                sources: data.sources as ChatSource[] | undefined
            }]);
        },
        onError: (error: Error) => {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: `Error: ${error.message}`,
                timestamp: new Date()
            }]);
        }
    });

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = () => {
        if (!input.trim() || sendMutation.isPending) return;

        // Add user message
        setMessages(prev => [...prev, {
            role: 'user',
            content: input,
            timestamp: new Date()
        }]);

        // Send to API
        sendMutation.mutate(input);
        setInput('');
    };

    const handleSuggestionClick = (suggestion: string) => {
        setInput(suggestion);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <>
            {/* Floating Button */}
            {!isOpen && (
                <button
                    onClick={() => setIsOpen(true)}
                    className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-lg hover:shadow-xl transition-all hover:scale-105 flex items-center justify-center z-50"
                >
                    <MessageCircle className="w-6 h-6" />
                </button>
            )}

            {/* Chat Panel */}
            {isOpen && (
                <div className="fixed bottom-6 right-6 w-96 h-[600px] bg-slate-900 rounded-2xl shadow-2xl border border-slate-800 flex flex-col z-50 overflow-hidden">
                    {/* Header */}
                    <div className="bg-gradient-to-r from-indigo-500 to-purple-500 p-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
                                <Sparkles className="w-5 h-5 text-white" />
                            </div>
                            <div>
                                <h3 className="font-semibold text-white">AI Research Assistant</h3>
                                <p className="text-xs text-white/70">Ask anything about your research</p>
                            </div>
                        </div>
                        <button
                            onClick={() => setIsOpen(false)}
                            className="text-white/70 hover:text-white transition-colors"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-4">
                        {messages.length === 0 ? (
                            <div className="text-center py-8">
                                <Bot className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                                <h4 className="text-slate-400 mb-2">How can I help you?</h4>
                                <p className="text-sm text-slate-500 mb-4">
                                    Ask me about pain points, verbatims, scripts, or anything in your research data.
                                </p>

                                {/* Suggestions */}
                                {suggestionsData?.suggestions && (
                                    <div className="space-y-2">
                                        <p className="text-xs text-slate-500 flex items-center justify-center gap-1">
                                            <Lightbulb className="w-3 h-3" />
                                            Try asking:
                                        </p>
                                        <div className="flex flex-wrap gap-2 justify-center">
                                            {suggestionsData.suggestions.slice(0, 4).map((suggestion, i) => (
                                                <button
                                                    key={i}
                                                    onClick={() => handleSuggestionClick(suggestion)}
                                                    className="text-xs px-3 py-1.5 rounded-full bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
                                                >
                                                    {suggestion.length > 40 ? suggestion.slice(0, 40) + '...' : suggestion}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ) : (
                            messages.map((msg, i) => (
                                <div
                                    key={i}
                                    className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                                >
                                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === 'user'
                                        ? 'bg-indigo-500'
                                        : 'bg-slate-700'
                                        }`}>
                                        {msg.role === 'user' ? (
                                            <User className="w-4 h-4 text-white" />
                                        ) : (
                                            <Bot className="w-4 h-4 text-slate-300" />
                                        )}
                                    </div>
                                    <div className={`max-w-[80%] rounded-2xl px-4 py-2 ${msg.role === 'user'
                                        ? 'bg-indigo-500 text-white rounded-tr-none'
                                        : 'bg-slate-800 text-slate-200 rounded-tl-none'
                                        }`}>
                                        <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                                        {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                                            <div className="mt-2 pt-2 border-t border-slate-700/50">
                                                <p className="text-xs text-slate-500 mb-1">Sources ({msg.sources.length}):</p>
                                                <div className="flex flex-wrap gap-1">
                                                    {msg.sources.slice(0, 8).map((src, si) => (
                                                        <span
                                                            key={si}
                                                            className={`text-xs px-1.5 py-0.5 rounded ${
                                                                src.sentiment === 'positive' ? 'bg-emerald-900/40 text-emerald-400' :
                                                                src.sentiment === 'negative' ? 'bg-red-900/40 text-red-400' :
                                                                'bg-slate-700/50 text-slate-400'
                                                            }`}
                                                            title={src.content || ''}
                                                        >
                                                            {src.source_type}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                        <span className="text-xs opacity-50 mt-1 block">
                                            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </span>
                                    </div>
                                </div>
                            ))
                        )}

                        {/* Loading indicator */}
                        {sendMutation.isPending && (
                            <div className="flex gap-3">
                                <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center">
                                    <Bot className="w-4 h-4 text-slate-300" />
                                </div>
                                <div className="bg-slate-800 rounded-2xl rounded-tl-none px-4 py-3">
                                    <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input */}
                    <div className="p-4 border-t border-slate-800">
                        <div className="flex items-center gap-2">
                            <input
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder="Ask about your research..."
                                className="flex-1 bg-slate-800 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder-slate-500"
                                disabled={sendMutation.isPending}
                            />
                            <button
                                onClick={handleSend}
                                disabled={!input.trim() || sendMutation.isPending}
                                className="w-10 h-10 rounded-xl bg-indigo-500 text-white flex items-center justify-center hover:bg-indigo-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <Send className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
