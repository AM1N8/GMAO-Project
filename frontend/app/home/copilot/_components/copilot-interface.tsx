'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, Activity, AlertTriangle, FileText, CheckCircle2, MonitorCheck } from 'lucide-react';
import { Button } from '@kit/ui/button';
import { Input } from '@kit/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@kit/ui/card';
import { ScrollArea } from '@kit/ui/scroll-area';
import { Badge } from '@kit/ui/badge';
import { Separator } from '@kit/ui/separator';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { CopilotIntentEnum, CopilotQueryResponse, CopilotRecommendedAction } from '~/lib/gmao-api';

type Message = {
    id: string;
    role: 'user' | 'assistant';
    content: string; // Used for user messages or as fallback
    structuredResponse?: CopilotQueryResponse; // For assistant messages
    timestamp: Date;
    processingTime?: number;
};

export function CopilotInterface() {
    const [messages, setMessages] = useState<Message[]>([
        {
            id: 'welcome',
            role: 'assistant',
            content: 'Hello! I am your Maintenance Copilot. I can help with KPI analysis, equipment health summaries, and intervention reports.',
            timestamp: new Date(),
        },
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);
    const api = useGmaoApi();

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages]);

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
            // Check for simple context extraction (e.g. "equipment 123")
            // In a real app, we'd have a more robust context selector
            let context = {};
            const eqMatch = input.match(/equipment\s+(\d+|[a-zA-Z0-9-]+)/i);
            if (eqMatch) {
                context = { equipment_id: eqMatch[1] };
            }

            const response = await api.queryCopilot({
                message: userMessage.content,
                context: context
            });

            const botMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: response.summary,
                structuredResponse: response,
                timestamp: new Date(),
                processingTime: Date.now() - startTime,
            };

            setMessages((prev) => [...prev, botMessage]);
        } catch (error) {
            console.error(error);
            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: "Detailed analysis unavailable. Please try again or check connection.",
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    const renderIntentBadge = (intent: CopilotIntentEnum) => {
        switch (intent) {
            case CopilotIntentEnum.KPI_EXPLANATION:
                return <Badge variant="secondary" className="bg-blue-100 text-blue-800 hover:bg-blue-200"><Activity className="w-3 h-3 mr-1" /> KPI Analysis</Badge>;
            case CopilotIntentEnum.EQUIPMENT_HEALTH_SUMMARY:
                return <Badge variant="secondary" className="bg-green-100 text-green-800 hover:bg-green-200"><MonitorCheck className="w-3 h-3 mr-1" /> Health Summary</Badge>;
            case CopilotIntentEnum.INTERVENTION_REPORT:
                return <Badge variant="secondary" className="bg-purple-100 text-purple-800 hover:bg-purple-200"><FileText className="w-3 h-3 mr-1" /> Report</Badge>;
            default:
                return <Badge variant="outline">{intent}</Badge>;
        }
    };

    const renderActionPriority = (priority: string) => {
        switch (priority.toLowerCase()) {
            case 'high':
                return <Badge variant="destructive" className="h-5 text-[10px]">High</Badge>;
            case 'medium':
                return <Badge variant="default" className="h-5 text-[10px] bg-yellow-500 hover:bg-yellow-600">Med</Badge>;
            case 'low':
                return <Badge variant="secondary" className="h-5 text-[10px]">Low</Badge>;
            default:
                return null;
        }
    };

    return (
        <Card className="h-[750px] flex flex-col border-none shadow-md bg-background/50 backdrop-blur-sm">
            <CardHeader className="pb-4 border-b">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center ring-1 ring-primary/20">
                            <Sparkles className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                            <CardTitle className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-purple-600">
                                Maintenance Copilot
                            </CardTitle>
                            <CardDescription className="text-xs font-medium text-muted-foreground/80">
                                AI-Powered Engineering Assistant
                            </CardDescription>
                        </div>
                    </div>
                </div>
            </CardHeader>

            <CardContent className="flex-1 flex flex-col p-0 overflow-hidden relative">
                <div className="absolute inset-0 bg-grid-slate-50/[0.05] bg-[bottom_1px_center] opacity-40 pointer-events-none" />

                <ScrollArea className="flex-1 p-4">
                    <div className="flex flex-col gap-6 max-w-3xl mx-auto">
                        {messages.map((msg) => (
                            <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                                {/* Avatar */}
                                <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border shadow-sm ${msg.role === 'user'
                                        ? 'bg-primary text-primary-foreground'
                                        : 'bg-white dark:bg-zinc-800'
                                    }`}>
                                    {msg.role === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4 text-primary" />}
                                </div>

                                {/* Content */}
                                <div className={`flex flex-col gap-2 max-w-[80%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>

                                    {/* User Message Bubble */}
                                    {msg.role === 'user' && (
                                        <div className="rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm bg-primary text-primary-foreground shadow-sm">
                                            {msg.content}
                                        </div>
                                    )}

                                    {/* Assistant Structured Response */}
                                    {msg.role === 'assistant' && msg.structuredResponse && (
                                        <div className="flex flex-col w-full gap-3 animate-fade-in">

                                            {/* Header with Intent & Summary */}
                                            <div className=" bg-card border rounded-xl p-4 shadow-sm w-full space-y-3">
                                                <div className="flex items-center justify-between">
                                                    {renderIntentBadge(msg.structuredResponse.intent)}
                                                    <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold flex items-center gap-1">
                                                        Confidence:
                                                        <span className={`
                                                            ${msg.structuredResponse.confidence_level === 'high' ? 'text-green-600' :
                                                                msg.structuredResponse.confidence_level === 'medium' ? 'text-yellow-600' : 'text-red-600'}
                                                        `}>
                                                            {msg.structuredResponse.confidence_level.toUpperCase()}
                                                        </span>
                                                    </span>
                                                </div>

                                                <div className="font-medium text-lg text-foreground">
                                                    {msg.structuredResponse.summary}
                                                </div>

                                                <div className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line border-l-2 border-primary/20 pl-4">
                                                    {msg.structuredResponse.detailed_explanation}
                                                </div>
                                            </div>

                                            {/* Recommended Actions */}
                                            {msg.structuredResponse.recommended_actions.length > 0 && (
                                                <div className="space-y-2 w-full">
                                                    <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                                                        <CheckCircle2 className="w-3 h-3" /> Recommended Actions
                                                    </div>
                                                    <div className="grid gap-2">
                                                        {msg.structuredResponse.recommended_actions.map((action, idx) => (
                                                            <div key={idx} className="bg-muted/30 border rounded-lg p-3 text-sm hover:bg-muted/50 transition-colors">
                                                                <div className="flex items-start justify-between gap-2 mb-1">
                                                                    <span className="font-semibold text-foreground">{action.action}</span>
                                                                    {renderActionPriority(action.priority)}
                                                                </div>
                                                                <p className="text-xs text-muted-foreground">{action.rationale}</p>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            {/* Supporting Data */}
                                            {msg.structuredResponse.supporting_data_references.length > 0 && (
                                                <div className="flex flex-wrap gap-2 mt-1">
                                                    {msg.structuredResponse.supporting_data_references.map((data, idx) => (
                                                        <div key={idx} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-secondary/50 border border-border/50 text-xs text-secondary-foreground">
                                                            <Activity className="w-3 h-3 opacity-70" />
                                                            <span className="font-medium opacity-70">{data.description}:</span>
                                                            <span className="font-mono font-bold">{data.value || 'N/A'}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Fallback Assistant Message */}
                                    {msg.role === 'assistant' && !msg.structuredResponse && (
                                        <div className="rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm bg-muted text-foreground border shadow-sm">
                                            {msg.content}
                                        </div>
                                    )}

                                    {/* Timestamp */}
                                    <span className="text-[10px] text-muted-foreground px-1">
                                        {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        {msg.processingTime && ` • ${(msg.processingTime / 1000).toFixed(1)}s`}
                                    </span>
                                </div>
                            </div>
                        ))}

                        {isLoading && (
                            <div className="flex gap-4">
                                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border bg-white dark:bg-zinc-800 shadow-sm">
                                    <Bot className="h-4 w-4 text-primary" />
                                </div>
                                <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2 w-fit">
                                    <div className="flex gap-1">
                                        <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                        <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                        <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                    </div>
                                    <span className="text-xs font-medium text-muted-foreground">Analyzing system data...</span>
                                </div>
                            </div>
                        )}
                        <div ref={scrollRef} />
                    </div>
                </ScrollArea>

                <div className="p-4 bg-background border-t">
                    <div className="max-w-3xl mx-auto flex gap-3 relative">
                        <Input
                            placeholder="Ask Copilot about equipment health, KPIs, or specific interventions..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            disabled={isLoading}
                            className="flex-1 pr-12 h-12 rounded-xl border-muted-foreground/20 shadow-sm focus-visible:ring-offset-0 focus-visible:ring-1"
                        />
                        <Button
                            onClick={handleSend}
                            disabled={isLoading || !input.trim()}
                            className="absolute right-1.5 top-1.5 h-9 w-9 p-0 rounded-lg"
                        >
                            <Send className="h-4 w-4" />
                        </Button>
                    </div>
                    <div className="text-center mt-2">
                        <p className="text-[10px] text-muted-foreground">
                            AI-generated responses can be inaccurate. Always verify critical data in the main dashboard.
                        </p>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
