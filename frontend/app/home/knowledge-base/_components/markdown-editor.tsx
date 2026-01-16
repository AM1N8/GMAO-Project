
'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Textarea } from '@kit/ui/textarea';
import { Button } from '@kit/ui/button';
import { Label } from '@kit/ui/label';
import { Card, CardContent } from '@kit/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@kit/ui/tabs';
import { Eye, Edit, Save, X } from 'lucide-react';

interface MarkdownEditorProps {
    initialValue?: string;
    onSave: (content: string) => void;
    onCancel: () => void;
    isSaving?: boolean;
}

export function MarkdownEditor({
    initialValue = '',
    onSave,
    onCancel,
    isSaving = false
}: MarkdownEditorProps) {
    const [content, setContent] = useState(initialValue);
    const [activeTab, setActiveTab] = useState('write');

    return (
        <div className="space-y-4">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                <div className="flex items-center justify-between mb-2">
                    <TabsList>
                        <TabsTrigger value="write" className="flex items-center gap-2">
                            <Edit className="h-4 w-4" />
                            Write
                        </TabsTrigger>
                        <TabsTrigger value="preview" className="flex items-center gap-2">
                            <Eye className="h-4 w-4" />
                            Preview
                        </TabsTrigger>
                    </TabsList>
                    <div className="text-xs text-muted-foreground hidden sm:block">
                        Supports GitHub Flavored Markdown
                    </div>
                </div>

                <TabsContent value="write" className="mt-0">
                    <Textarea
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        placeholder="Type your markdown content here... # Headers, **bold**, - lists"
                        className="min-h-[500px] font-mono text-sm resize-y"
                    />
                </TabsContent>

                <TabsContent value="preview" className="mt-0">
                    <Card className="min-h-[500px] border-dashed">
                        <CardContent className="pt-6 prose dark:prose-invert max-w-none">
                            {content ? (
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {content}
                                </ReactMarkdown>
                            ) : (
                                <div className="text-muted-foreground text-center py-20 italic">
                                    Nothing to preview
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={onCancel} disabled={isSaving}>
                    <X className="h-4 w-4 mr-2" />
                    Cancel
                </Button>
                <Button onClick={() => onSave(content)} disabled={!content.trim() || isSaving}>
                    <Save className="h-4 w-4 mr-2" />
                    {isSaving ? 'Saving...' : 'Save Document'}
                </Button>
            </div>
        </div>
    );
}
