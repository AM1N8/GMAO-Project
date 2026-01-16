'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Settings2, FileText, ChevronDown, ChevronUp, Loader2, Sparkles } from 'lucide-react';
import { Button } from '@kit/ui/button';
import { Input } from '@kit/ui/input';
import { Label } from '@kit/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@kit/ui/card';
import { ScrollArea } from '@kit/ui/scroll-area';
import { Badge } from '@kit/ui/badge';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';

type Source = {
    text: string;
    document_name?: string;
    similarity?: number;
    chunk_id?: string;
    page_number?: number;
};

type Message = {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    sources?: Source[];
    processingTime?: number;
    kpiData?: any;
    routingInfo?: any;
    graphContext?: any;
};

export function RagChatInterface() {
    const [messages, setMessages] = useState<Message[]>([
        {
            id: 'welcome',
            role: 'assistant',
            content: 'Hello! I am your GMAO maintenance assistant. Ask me anything about equipment manuals, procedures, or past interventions.',
            timestamp: new Date(),
        },
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [showSettings, setShowSettings] = useState(false);
    const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());

    // RAG Settings
    const [topK, setTopK] = useState(5);
    const [similarityThreshold, setSimilarityThreshold] = useState(50); // 0-100 slider (maps to 0-0.05)
    const [includeSources, setIncludeSources] = useState(true);

    const scrollRef = useRef<HTMLDivElement>(null);
    const api = useGmaoApi();

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages]);

    const toggleSourceExpand = (messageId: string) => {
        setExpandedSources(prev => {
            const newSet = new Set(prev);
            if (newSet.has(messageId)) {
                newSet.delete(messageId);
            } else {
                newSet.add(messageId);
            }
            return newSet;
        });
    };

    // Convert slider value (0-100) to actual threshold (0-1.0)
    const getActualThreshold = () => similarityThreshold / 100;

    // ...
    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input,
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        const startTime = Date.now();

        try {
            const response = await api.queryRag(userMessage.content, {
                topK,
                similarityThreshold: getActualThreshold(),
                includeSources,
                useCache: true
            });

            // Handle V2 Response Structure with fallbacks for V1 compatibility
            const sources: Source[] = (response.citations || response.sources || []).map((c: any) => ({
                text: c.excerpt || c.text || '',
                document_name: c.document_name || c.metadata?.filename || c.metadata?.file_name || `Doc ${c.document_id}`,
                similarity: c.relevance_score || c.score || c.similarity,
                chunk_id: c.chunk_id || c.vector_id,
                page_number: c.page_number || c.metadata?.page_number
            }));

            const botMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: response.response_text || response.response || "I'm sorry, I couldn't find an answer to that.",
                timestamp: new Date(),
                sources: sources,
                processingTime: Date.now() - startTime,
                kpiData: response.kpi_data,
                routingInfo: response.routing_info,
                graphContext: response.graph_context
            };

            setMessages((prev) => [...prev, botMessage]);
        } catch (error) {
            console.error(error);
            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: "Sorry, I encountered an error connecting to the knowledge base. Please try again.",
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="space-y-4">
            {/* Settings Panel ... (Same as before) ... */}
            <Card className="border-dashed">
                <CardHeader
                    className="pb-2 cursor-pointer flex flex-row items-center justify-between"
                    onClick={() => setShowSettings(!showSettings)}
                >
                    <div className="flex items-center gap-2">
                        <Settings2 className="h-4 w-4" />
                        <CardTitle className="text-sm font-medium">RAG Settings</CardTitle>
                    </div>
                    {showSettings ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </CardHeader>
                {showSettings && (
                    <CardContent className="space-y-4">
                        <div className="grid md:grid-cols-3 gap-6">
                            {/* Top K */}
                            <div className="space-y-2">
                                <Label className="flex items-center justify-between">
                                    <span>Top K Results</span>
                                    <Badge variant="secondary">{topK}</Badge>
                                </Label>
                                <input
                                    type="range"
                                    min="1"
                                    max="10"
                                    value={topK}
                                    onChange={(e) => setTopK(Number(e.target.value))}
                                    className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
                                />
                                <p className="text-xs text-muted-foreground">Number of document chunks to retrieve</p>
                            </div>

                            {/* Similarity Threshold */}
                            <div className="space-y-2">
                                <Label className="flex items-center justify-between">
                                    <span>Similarity Threshold</span>
                                    <Badge variant="secondary">{similarityThreshold}%</Badge>
                                </Label>
                                <input
                                    type="range"
                                    min="0"
                                    max="100"
                                    value={similarityThreshold}
                                    onChange={(e) => setSimilarityThreshold(Number(e.target.value))}
                                    className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
                                />
                                <p className="text-xs text-muted-foreground">
                                    Higher = stricter matching (0-1.0 scale: {getActualThreshold().toFixed(2)})
                                </p>
                                <div className="flex items-center gap-2">
                                    <input
                                        type="checkbox"
                                        id="include-sources"
                                        checked={includeSources}
                                        onChange={(e) => setIncludeSources(e.target.checked)}
                                        className="h-4 w-4 rounded border-gray-300"
                                    />
                                    <label htmlFor="include-sources" className="text-sm cursor-pointer">
                                        Show source documents with answers
                                    </label>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                )}
            </Card>

            {/* Chat Interface */}
            <Card className="h-[550px] flex flex-col">
                <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                                <Sparkles className="h-4 w-4 text-primary" />
                            </div>
                            <div>
                                <CardTitle className="text-lg">Technical Assistant</CardTitle>
                                <CardDescription className="text-xs">Powered by RAG + SQL + Graph</CardDescription>
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <Badge variant="outline" className="text-xs">
                                Top K: {topK}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                                Threshold: {similarityThreshold}%
                            </Badge>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="flex-1 flex flex-col p-4 pt-0 gap-4 overflow-hidden">
                    <ScrollArea className="flex-1 pr-4">
                        <div className="flex flex-col gap-4">
                            {messages.map((msg) => (
                                <div key={msg.id} className="space-y-2">
                                    <div
                                        className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                                    >
                                        <div
                                            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border ${msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}
                                        >
                                            {msg.role === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                                        </div>
                                        <div className="flex flex-col gap-1 max-w-[85%]">
                                            {/* Metadata Badge (Tech Debug) */}
                                            {msg.role === 'assistant' && msg.routingInfo && (
                                                <div className="flex gap-2 mb-1">
                                                    <Badge variant="secondary" className="text-[10px] h-4 px-1">
                                                        {msg.routingInfo.intent?.toUpperCase()}
                                                    </Badge>
                                                    {msg.routingInfo.kpi_detected && (
                                                        <Badge variant="outline" className="text-[10px] h-4 px-1 text-blue-600 border-blue-200">
                                                            KPI: {msg.routingInfo.kpi_detected}
                                                        </Badge>
                                                    )}
                                                </div>
                                            )}

                                            <div
                                                className={`rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${msg.role === 'user'
                                                    ? 'bg-primary text-primary-foreground'
                                                    : 'bg-muted'}`}
                                            >
                                                {msg.content}
                                            </div>

                                            {/* KPI Data Card */}
                                            {msg.kpiData && (
                                                <div className="mt-2 text-xs border rounded-md p-3 bg-card shadow-sm">
                                                    <div className="font-semibold mb-2 flex items-center gap-2 text-foreground">
                                                        <Sparkles className="h-3.5 w-3.5 text-yellow-500 fill-yellow-500/20" />
                                                        Data Insight
                                                    </div>

                                                    {msg.kpiData.generated_sql ? (
                                                        // SQL Result
                                                        <div className="space-y-2">
                                                            <div className="text-muted-foreground font-mono bg-secondary/30 p-2 rounded border text-[10px] overflow-x-auto leading-relaxed">
                                                                {msg.kpiData.generated_sql}
                                                            </div>
                                                            <div className="font-semibold text-green-600 dark:text-green-400 flex items-center gap-1">
                                                                <div className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
                                                                {msg.kpiData.summary}
                                                            </div>
                                                        </div>
                                                    ) : (
                                                        // Standard KPI
                                                        <div className="grid grid-cols-2 gap-2">
                                                            {Object.entries(msg.kpiData).map(([k, v]) => (
                                                                k !== 'formatted_context' && typeof v !== 'object' && (
                                                                    <div key={k} className="bg-secondary/40 p-2 rounded-sm border border-border/40">
                                                                        <span className="block text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-0.5">{k.replace(/_/g, ' ')}</span>
                                                                        <span className="font-bold text-foreground text-sm">{String(v)}</span>
                                                                    </div>
                                                                )
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            )}

                                            {msg.processingTime && (
                                                <span className="text-xs text-muted-foreground">
                                                    {(msg.processingTime / 1000).toFixed(1)}s
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Sources Section */}
                                    {msg.sources && msg.sources.length > 0 && includeSources && (
                                        <div className="ml-11 space-y-2">
                                            <button
                                                onClick={() => toggleSourceExpand(msg.id)}
                                                className="flex items-center gap-1 text-xs text-primary hover:underline"
                                            >
                                                <FileText className="h-3 w-3" />
                                                {expandedSources.has(msg.id) ? 'Hide' : 'Show'} {msg.sources.length} source(s)
                                                {expandedSources.has(msg.id) ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                                            </button>

                                            {expandedSources.has(msg.id) && (
                                                <div className="space-y-2">
                                                    {msg.sources.map((source, idx) => (
                                                        <div key={idx} className="p-3 rounded-md bg-muted/50 border border-muted text-xs">
                                                            <div className="flex items-center justify-between mb-1">
                                                                <span className="font-medium text-muted-foreground flex items-center gap-2">
                                                                    {source.document_name || `Source ${idx + 1}`}
                                                                    {source.page_number && <Badge variant="outline" className="text-[10px] h-4">Pg {source.page_number}</Badge>}
                                                                </span>
                                                                {source.similarity !== undefined && (
                                                                    <Badge variant="outline" className="text-xs">
                                                                        {(source.similarity * 100).toFixed(1)}% match
                                                                    </Badge>
                                                                )}
                                                            </div>
                                                            <p className="text-muted-foreground line-clamp-3">
                                                                {source.text?.substring(0, 300)}{source.text?.length > 300 ? '...' : ''}
                                                            </p>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))}
                            {isLoading && (
                                <div className="flex gap-3 animate-fade-up">
                                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border bg-gradient-to-br from-blue-500/20 to-purple-500/20">
                                        <Bot className="h-4 w-4 text-primary" />
                                    </div>
                                    <div className="bg-muted rounded-2xl px-4 py-3 flex items-center gap-3">
                                        <div className="flex gap-1">
                                            <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                            <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                            <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                        </div>
                                        <span className="text-sm text-muted-foreground">Thinking...</span>
                                    </div>
                                </div>
                            )}
                            <div ref={scrollRef} />
                        </div>
                    </ScrollArea>

                    <div className="flex gap-2 mt-auto">
                        <Input
                            placeholder="Ask about maintenance procedures, equipement availability, or failures..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            disabled={isLoading}
                            className="flex-1"
                        />
                        <Button onClick={handleSend} disabled={isLoading || !input.trim()}>
                            <Send className="h-4 w-4" />
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div >
    );
}
