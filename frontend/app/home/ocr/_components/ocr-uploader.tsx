'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@kit/ui/card';
import { Button } from '@kit/ui/button';
import { Input } from '@kit/ui/input';
import { Label } from '@kit/ui/label';
import { Badge } from '@kit/ui/badge';
import { Textarea } from '@kit/ui/textarea';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { Upload, FileText, Loader2, Copy, Check, Image, Edit, Eye, Save, Download, Trash2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { toast } from 'sonner';

type OutputFormat = 'markdown' | 'html' | 'json' | 'text';
type ViewMode = 'preview' | 'edit';

type SavedExtraction = {
    id: number;
    filename: string;
    content: string;
    format: OutputFormat;
    created_at: string;
};

export function OcrUploader() {
    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [result, setResult] = useState<string | null>(null);
    const [editedResult, setEditedResult] = useState<string>('');
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [outputFormat, setOutputFormat] = useState<OutputFormat>('markdown');
    const [copied, setCopied] = useState(false);
    const [viewMode, setViewMode] = useState<ViewMode>('preview');
    const [savedExtractions, setSavedExtractions] = useState<SavedExtraction[]>([]);
    const [loadingExtractions, setLoadingExtractions] = useState(false);
    const api = useGmaoApi();

    useEffect(() => {
        loadExtractions();
    }, []);

    const loadExtractions = async () => {
        setLoadingExtractions(true);
        try {
            const data = await api.listOcrExtractions();
            setSavedExtractions(data);
        } catch (err) {
            console.error('Failed to load extractions:', err);
        } finally {
            setLoadingExtractions(false);
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0];
            setFile(selectedFile);
            setResult(null);
            setEditedResult('');
            setError(null);

            if (selectedFile.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = (e) => setPreview(e.target?.result as string);
                reader.readAsDataURL(selectedFile);
            } else {
                setPreview(null);
            }
        }
    };

    const handleProcess = async () => {
        if (!file) return;

        setIsProcessing(true);
        setError(null);

        try {
            const response = await api.ocrProcess(file, outputFormat);
            const text = typeof response === 'string' ? response : JSON.stringify(response, null, 2);
            setResult(text);
            setEditedResult(text);
            toast.success('Text extracted successfully');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'OCR processing failed');
            toast.error('OCR processing failed');
        } finally {
            setIsProcessing(false);
        }
    };

    const handleCopy = async () => {
        const textToCopy = editedResult || result;
        if (textToCopy) {
            await navigator.clipboard.writeText(textToCopy);
            setCopied(true);
            toast.success('Copied to clipboard');
            setTimeout(() => setCopied(false), 2000);
        }
    };

    const handleSave = async () => {
        if (!editedResult || !file) return;

        try {
            await api.saveOcrExtraction({
                filename: file.name,
                content: editedResult,
                format: outputFormat
            });
            toast.success('Extraction saved permanently');
            loadExtractions();
        } catch (err) {
            toast.error('Failed to save extraction');
        }
    };

    const handleDownload = () => {
        if (!editedResult) return;

        const extension = outputFormat === 'json' ? 'json' : outputFormat === 'html' ? 'html' : 'md';
        const blob = new Blob([editedResult], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ocr-extraction.${extension}`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const handleDeleteSaved = async (id: number) => {
        if (!confirm('Are you sure you want to delete this saved extraction?')) return;

        try {
            await api.deleteOcrExtraction(id);
            toast.success('Extraction deleted');
            loadExtractions();
        } catch (err) {
            toast.error('Failed to delete extraction');
        }
    };

    const handleLoadSaved = (extraction: SavedExtraction) => {
        setResult(extraction.content);
        setEditedResult(extraction.content);
        setOutputFormat(extraction.format);
        toast.info(`Loaded: ${extraction.filename}`);
    };

    return (
        <div className="space-y-6">
            <div className="grid gap-6 lg:grid-cols-2">
                {/* Upload Section */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Upload className="h-5 w-5" />
                            Upload Document
                        </CardTitle>
                        <CardDescription>
                            Upload an image to extract text using Vision AI
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="file">Select Image</Label>
                            <Input
                                id="file"
                                type="file"
                                accept="image/jpeg,image/png,image/webp,image/bmp"
                                onChange={handleFileChange}
                            />
                            <p className="text-xs text-muted-foreground">
                                Supported: JPEG, PNG, WebP, BMP
                            </p>
                        </div>

                        <div className="space-y-2">
                            <Label>Output Format</Label>
                            <div className="flex flex-wrap gap-2">
                                {(['markdown', 'html', 'json', 'text'] as OutputFormat[]).map((format) => (
                                    <Button
                                        key={format}
                                        variant={outputFormat === format ? 'default' : 'outline'}
                                        size="sm"
                                        onClick={() => setOutputFormat(format)}
                                        className="min-w-[80px]"
                                    >
                                        {format.toUpperCase()}
                                    </Button>
                                ))}
                            </div>
                        </div>

                        {file && (
                            <div className="p-3 bg-muted rounded-lg">
                                <div className="flex items-center gap-2 text-sm">
                                    <FileText className="h-4 w-4" />
                                    <span className="font-medium truncate">{file.name}</span>
                                    <Badge variant="secondary" className="ml-auto">
                                        {(file.size / 1024).toFixed(1)} KB
                                    </Badge>
                                </div>
                            </div>
                        )}

                        {preview && (
                            <div className="border rounded-lg overflow-hidden">
                                <img
                                    src={preview}
                                    alt="Preview"
                                    className="max-h-48 w-full object-contain bg-muted"
                                />
                            </div>
                        )}

                        <Button
                            onClick={handleProcess}
                            disabled={!file || isProcessing}
                            className="w-full"
                        >
                            {isProcessing ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Processing with Vision AI...
                                </>
                            ) : (
                                <>
                                    <Image className="mr-2 h-4 w-4" />
                                    Extract Text ({outputFormat})
                                </>
                            )}
                        </Button>

                        {error && (
                            <div className="text-sm text-destructive p-3 bg-destructive/10 rounded-lg">
                                {error}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Results Section */}
                <Card className="flex flex-col">
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <CardTitle>Extracted Content</CardTitle>
                            <div className="flex gap-2">
                                <Button
                                    variant={viewMode === 'preview' ? 'default' : 'outline'}
                                    size="sm"
                                    onClick={() => setViewMode('preview')}
                                >
                                    <Eye className="h-4 w-4 mr-1" /> Preview
                                </Button>
                                <Button
                                    variant={viewMode === 'edit' ? 'default' : 'outline'}
                                    size="sm"
                                    onClick={() => setViewMode('edit')}
                                >
                                    <Edit className="h-4 w-4 mr-1" /> Edit
                                </Button>
                            </div>
                        </div>
                        {editedResult && (
                            <div className="flex gap-2 mt-2">
                                <Button variant="outline" size="sm" onClick={handleCopy}>
                                    {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                                </Button>
                                <Button variant="outline" size="sm" onClick={handleSave}>
                                    <Save className="h-4 w-4" />
                                </Button>
                                <Button variant="outline" size="sm" onClick={handleDownload}>
                                    <Download className="h-4 w-4" />
                                </Button>
                            </div>
                        )}
                    </CardHeader>
                    <CardContent className="flex-1 overflow-hidden">
                        {editedResult || result ? (
                            viewMode === 'preview' ? (
                                outputFormat === 'markdown' ? (
                                    <div className="prose prose-sm dark:prose-invert max-w-none overflow-auto max-h-[500px] p-4 bg-muted rounded-lg [&_table]:w-full [&_table]:border-collapse [&_th]:border [&_th]:border-muted-foreground/30 [&_th]:p-2 [&_th]:bg-muted-foreground/10 [&_td]:border [&_td]:border-muted-foreground/20 [&_td]:p-2">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {editedResult}
                                        </ReactMarkdown>
                                    </div>
                                ) : outputFormat === 'html' ? (
                                    <div
                                        className="prose prose-sm dark:prose-invert max-w-none overflow-auto max-h-[500px] p-4 bg-muted rounded-lg"
                                        dangerouslySetInnerHTML={{ __html: editedResult }}
                                    />
                                ) : (
                                    <pre className="whitespace-pre-wrap text-sm bg-muted p-4 rounded-lg max-h-[500px] overflow-auto font-mono">
                                        {editedResult}
                                    </pre>
                                )
                            ) : (
                                <Textarea
                                    value={editedResult}
                                    onChange={(e) => setEditedResult(e.target.value)}
                                    className="min-h-[400px] font-mono text-sm"
                                    placeholder="Edit extracted text here..."
                                />
                            )
                        ) : (
                            <div className="flex flex-col items-center justify-center text-muted-foreground py-12 h-full">
                                <FileText className="h-12 w-12 mb-4 opacity-50" />
                                <p>Upload an image to extract text</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Saved Extractions */}
            {(savedExtractions.length > 0 || loadingExtractions) && (
                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle>History</CardTitle>
                                <CardDescription>Permanently saved extractions available across sessions</CardDescription>
                            </div>
                            {loadingExtractions && <Loader2 className="h-4 w-4 animate-spin" />}
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {savedExtractions.map((extraction) => (
                                <div
                                    key={extraction.id}
                                    className="flex items-center justify-between p-3 bg-muted rounded-lg transition-colors hover:bg-muted/80"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-background rounded-full">
                                            <FileText className="h-4 w-4 text-orange-500" />
                                        </div>
                                        <div>
                                            <p className="font-medium text-sm">{extraction.filename}</p>
                                            <p className="text-xs text-muted-foreground">
                                                {new Date(extraction.created_at).toLocaleDateString()} {new Date(extraction.created_at).toLocaleTimeString()} · {extraction.format.toUpperCase()} · {extraction.content.length} chars
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => handleLoadSaved(extraction)}
                                        >
                                            Load
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => handleDeleteSaved(extraction.id)}
                                        >
                                            <Trash2 className="h-4 w-4 text-destructive" />
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
