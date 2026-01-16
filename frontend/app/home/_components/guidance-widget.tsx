'use client';

import { useState } from 'react';
import { MessageCircleQuestion, X, Send, Lightbulb } from 'lucide-react';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { type GuidanceAskRequest, type GuidanceAskResponse } from '~/lib/gmao-api';

export function GuidanceWidget() {
    const [isOpen, setIsOpen] = useState(false);
    const [question, setQuestion] = useState('');
    const [response, setResponse] = useState<GuidanceAskResponse | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const apiClient = useGmaoApi();

    const handleAsk = async () => {
        if (!question.trim()) return;

        setIsLoading(true);
        try {
            const request: GuidanceAskRequest = {
                question: question,
                context: {
                    current_page: window.location.pathname,
                    recent_actions: []
                }
            };

            const result = await apiClient.askGuidance(request);
            setResponse(result);
        } catch (error) {
            console.error('Error asking guidance:', error);
        } finally {
            setIsLoading(false);
        }
    };

    if (!isOpen) {
        return (
            <button
                onClick={() => setIsOpen(true)}
                className="fixed bottom-6 right-6 bg-primary text-primary-foreground rounded-full p-4 shadow-lg hover:shadow-xl transition-shadow z-50"
                aria-label="Open AI Guidance"
            >
                <MessageCircleQuestion className="h-6 w-6" />
            </button>
        );
    }

    return (
        <div className="fixed bottom-6 right-6 w-96 bg-background border rounded-lg shadow-2xl z-50 flex flex-col max-h-[600px]">
            {/* Header */}
            <div className="bg-primary text-primary-foreground px-4 py-3 rounded-t-lg flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Lightbulb className="h-5 w-5" />
                    <h3 className="font-semibold">AI Guidance</h3>
                </div>
                <button
                    onClick={() => setIsOpen(false)}
                    className="hover:bg-primary/90 rounded p-1"
                    aria-label="Close"
                >
                    <X className="h-5 w-5" />
                </button>
            </div>

            {/* Response Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {response ? (
                    <>
                        <div className="prose prose-sm dark:prose-invert">
                            <p className="text-sm">{response.answer}</p>
                        </div>

                        {response.suggested_actions.length > 0 && (
                            <div className="space-y-2">
                                <h4 className="text-sm font-semibold">Suggested Actions:</h4>
                                {response.suggested_actions.map((action, idx) => (
                                    <div
                                        key={idx}
                                        className="border rounded p-2 text-sm"
                                    >
                                        <div className="font-medium">{action.action_name}</div>
                                        <div className="text-muted-foreground text-xs">{action.description}</div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {response.related_links.length > 0 && (
                            <div className="space-y-2">
                                <h4 className="text-sm font-semibold">Related Pages:</h4>
                                {response.related_links.map((link, idx) => (
                                    <a
                                        key={idx}
                                        href={link.route}
                                        className="block border rounded p-2 text-sm hover:bg-accent"
                                    >
                                        <div className="font-medium text-primary">{link.title}</div>
                                        {link.description && (
                                            <div className="text-muted-foreground text-xs">{link.description}</div>
                                        )}
                                    </a>
                                ))}
                            </div>
                        )}
                    </>
                ) : (
                    <div className="text-center text-muted-foreground text-sm py-8">
                        Ask me anything about using the GMAO system!
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="border-t p-4">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleAsk()}
                        placeholder="How can I help you?"
                        className="flex-1 px-3 py-2 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                        disabled={isLoading}
                    />
                    <button
                        onClick={handleAsk}
                        disabled={isLoading || !question.trim()}
                        className="bg-primary text-primary-foreground px-4 py-2 rounded hover:bg-primary/90 disabled:opacity-50"
                        aria-label="Send question"
                    >
                        {isLoading ? (
                            <div className="h-4 w-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                        ) : (
                            <Send className="h-4 w-4" />
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
