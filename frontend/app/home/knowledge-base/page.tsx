
'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageBody, PageHeader } from '@kit/ui/page';
import { Card, CardContent } from '@kit/ui/card';
import { Button } from '@kit/ui/button';
import { Input } from '@kit/ui/input';
import { Badge } from '@kit/ui/badge';
import { ScrollArea } from '@kit/ui/scroll-area';
import { Separator } from '@kit/ui/separator';
import { Alert, AlertDescription, AlertTitle } from '@kit/ui/alert';
import { Label } from '@kit/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@kit/ui/select";
import {
    Book, Search, Plus, FileText, AlertTriangle, ShieldCheck,
    MoreVertical, Trash2, Globe, Clock, RefreshCw, Edit
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { toast } from 'sonner';

import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { MarkdownEditor } from './_components/markdown-editor';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@kit/ui/dropdown-menu";
import { SupervisorOrAbove } from '~/components/auth/role-guard';

export default function KnowledgeBasePage() {
    const api = useGmaoApi();
    const queryClient = useQueryClient();

    // UI State
    const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
    const [isEditing, setIsEditing] = useState(false);
    const [isCreating, setIsCreating] = useState(false);
    const [filters, setFilters] = useState({
        search: '',
        category: 'all' as string,
    });

    // Queries
    const { data: documents, isLoading: isLoadingList } = useQuery({
        queryKey: ['kb-documents', filters],
        queryFn: () => api.listDocuments({ ...filters, size: 50 }),
    });

    const { data: selectedDoc, isLoading: isLoadingDoc, error: docError } = useQuery({
        queryKey: ['kb-document', selectedDocId],
        queryFn: async () => {
            if (!selectedDocId) return null;
            console.log("Fetching doc:", selectedDocId);
            try {
                const res = await api.getDocument(selectedDocId);
                console.log("Doc fetch result:", res);
                return res;
            } catch (err) {
                console.error("Doc fetch error:", err);
                throw err;
            }
        },
        enabled: !!selectedDocId,
    });

    if (docError) {
        toast.error("Error loading document");
    }

    // Mutations
    const createMutation = useMutation({
        mutationFn: (data: any) => api.createDocument(data),
        onSuccess: (newDoc) => {
            queryClient.invalidateQueries({ queryKey: ['kb-documents'] });
            toast.success('Document created');
            setIsCreating(false);
            setSelectedDocId(newDoc.id);
        },
        onError: () => toast.error('Failed to create document'),
    });

    const updateMutation = useMutation({
        mutationFn: async ({ id, data }: { id: number; data: any }) => {
            console.log("Updating doc", id, data);
            return await api.updateDocument(id, data);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['kb-documents'] });
            queryClient.invalidateQueries({ queryKey: ['kb-document', selectedDocId] });
            toast.success('Document updated');
            setIsEditing(false);
        },
        onError: (err) => {
            console.error("Update failed:", err);
            toast.error('Failed to update document');
        }
    });

    const deleteMutation = useMutation({
        mutationFn: async (id: number) => {
            console.log("Deleting doc", id);
            return await api.deleteDocument(id);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['kb-documents'] });
            toast.success('Document deleted');
            setSelectedDocId(null);
        },
        onError: (err) => {
            console.error("Delete failed:", err);
            toast.error('Failed to delete document');
        }
    });

    const reindexMutation = useMutation({
        mutationFn: (id: number) => api.reindexDocument(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['kb-documents'] }); // Update indexed status
            toast.success('Re-indexing triggered');
        },
    });

    // Form State
    const [formData, setFormData] = useState({
        title: '',
        category: 'Enterprise',
        type_panne: '',
        safety_level: 'Low'
    });

    // Initialize form when editing or creating
    const startCreating = () => {
        setFormData({
            title: '',
            category: 'Enterprise',
            type_panne: '',
            safety_level: 'Low'
        });
        setIsCreating(true);
    };

    const startEditing = () => {
        if (selectedDoc) {
            setFormData({
                title: selectedDoc.title,
                category: selectedDoc.category,
                type_panne: selectedDoc.type_panne || '',
                safety_level: selectedDoc.safety_level
            });
            setIsEditing(true);
        }
    };

    // Handlers
    const handleSave = (content: string) => {
        if (isCreating) {
            createMutation.mutate({
                ...formData,
                content
            });
        } else if (selectedDocId) {
            updateMutation.mutate({
                id: selectedDocId,
                data: {
                    ...formData,
                    content
                }
            });
        }
    };

    const handleDelete = (id: number) => {
        if (confirm('Are you sure you want to delete this document?')) {
            deleteMutation.mutate(id);
        }
    };

    return (
        <div className="flex flex-col h-full">
            <PageHeader
                title="Maintenance Knowledge Base"
                description="Centralized repository for maintenance procedures, safety guidelines, and training materials."
            >
                <div className="flex items-center gap-2">
                    <SupervisorOrAbove>
                        <Button onClick={startCreating}>
                            <Plus className="h-4 w-4 mr-2" />
                            New Document
                        </Button>
                    </SupervisorOrAbove>
                </div>
            </PageHeader>

            <PageBody className="flex-1 p-0 overflow-hidden">
                <div className="flex h-[calc(100vh-140px)]">
                    {/* Sidebar List */}
                    <div className="w-1/3 min-w-[300px] border-r bg-muted/10 p-4 flex flex-col gap-4">
                        <div className="relative">
                            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Search documents..."
                                className="pl-8"
                                value={filters.search}
                                onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                            />
                        </div>

                        <div className="flex gap-2 overflow-x-auto pb-2">
                            {['all', 'Formation', 'Safety', 'Enterprise', 'AMDEC'].map(cat => (
                                <Badge
                                    key={cat}
                                    variant={filters.category === cat ? "default" : "outline"}
                                    className="cursor-pointer whitespace-nowrap"
                                    onClick={() => setFilters(prev => ({ ...prev, category: cat }))}
                                >
                                    {cat === 'all' ? 'All' : cat}
                                </Badge>
                            ))}
                        </div>

                        <ScrollArea className="flex-1">
                            <div className="space-y-2 pr-4">
                                {isLoadingList ? (
                                    <div className="text-center py-4 text-muted-foreground">Loading...</div>
                                ) : documents?.items?.length === 0 ? (
                                    <div className="text-center py-10 text-muted-foreground">No documents found</div>
                                ) : (
                                    documents?.items.map((doc: any) => (
                                        <div
                                            key={doc.id}
                                            className={`
                                                p-3 rounded-lg border cursor-pointer hover:bg-accent transition-colors
                                                ${selectedDocId === doc.id ? 'bg-accent border-primary' : 'bg-card'}
                                            `}
                                            onClick={() => {
                                                console.log("Clicked doc ID:", doc.id);
                                                setSelectedDocId(doc.id);
                                                setIsCreating(false);
                                                setIsEditing(false);
                                            }}
                                        >
                                            <div className="flex justify-between items-start mb-1">
                                                <h4 className="font-medium text-sm line-clamp-2">{doc.title}</h4>
                                                <Badge variant="secondary" className="text-[10px] h-5">{doc.category}</Badge>
                                            </div>
                                            <div className="flex items-center gap-2 text-xs text-muted-foreground mt-2">
                                                <span className="flex items-center">
                                                    <Clock className="h-3 w-3 mr-1" />
                                                    {new Date(doc.updated_at).toLocaleDateString()}
                                                </span>
                                                {doc.safety_level === 'High' && (
                                                    <Badge variant="destructive" className="h-4 text-[10px] px-1">Safety Critical</Badge>
                                                )}
                                                {doc.indexed && (
                                                    <span className="ml-auto text-green-600 flex items-center" title="Indexed for AI">
                                                        <ShieldCheck className="h-3 w-3" />
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </ScrollArea>
                    </div>

                    {/* Main Content Area */}
                    <div className="flex-1 p-6 overflow-y-auto bg-background">
                        {isCreating ? (
                            <div className="max-w-4xl mx-auto space-y-4">
                                <h2 className="text-2xl font-bold">Create New Document</h2>

                                <div className="grid grid-cols-2 gap-4">
                                    <div className="col-span-2">
                                        <Label>Document Title</Label>
                                        <Input
                                            value={formData.title}
                                            onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                                            placeholder="e.g. Hydraulic Pump Maintenance Protocol"
                                        />
                                    </div>

                                    <div>
                                        <Label>Category</Label>
                                        <Select
                                            value={formData.category}
                                            onValueChange={(val) => setFormData(prev => ({ ...prev, category: val }))}
                                        >
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select Category" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="Formation">Formation</SelectItem>
                                                <SelectItem value="Safety">Safety</SelectItem>
                                                <SelectItem value="Enterprise">Enterprise</SelectItem>
                                                <SelectItem value="AMDEC">AMDEC</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    <div>
                                        <Label>Safety Level</Label>
                                        <Select
                                            value={formData.safety_level}
                                            onValueChange={(val) => setFormData(prev => ({ ...prev, safety_level: val }))}
                                        >
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select Level" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="Low">Low</SelectItem>
                                                <SelectItem value="Medium">Medium</SelectItem>
                                                <SelectItem value="High">High</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    <div className="col-span-2">
                                        <Label>Failure Type (Optional)</Label>
                                        <Input
                                            value={formData.type_panne}
                                            onChange={(e) => setFormData(prev => ({ ...prev, type_panne: e.target.value }))}
                                            placeholder="e.g. Mechanical, Electrical"
                                        />
                                    </div>
                                </div>

                                <Separator />

                                <MarkdownEditor
                                    onSave={handleSave}
                                    onCancel={() => setIsCreating(false)}
                                    isSaving={createMutation.isPending}
                                />
                            </div>
                        ) : selectedDoc ? (
                            isEditing ? (
                                <div className="max-w-4xl mx-auto space-y-4">
                                    <div className="flex items-center justify-between mb-4">
                                        <h2 className="text-2xl font-bold">{isCreating ? 'Create Document' : `Editing: ${selectedDoc.title}`}</h2>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="col-span-2">
                                            <Label>Document Title</Label>
                                            <Input
                                                value={formData.title}
                                                onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                                                placeholder="e.g. Hydraulic Pump Maintenance Protocol"
                                            />
                                        </div>

                                        <div>
                                            <Label>Category</Label>
                                            <Select
                                                value={formData.category}
                                                onValueChange={(val) => setFormData(prev => ({ ...prev, category: val }))}
                                            >
                                                <SelectTrigger>
                                                    <SelectValue placeholder="Select Category" />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="Formation">Formation</SelectItem>
                                                    <SelectItem value="Safety">Safety</SelectItem>
                                                    <SelectItem value="Enterprise">Enterprise</SelectItem>
                                                    <SelectItem value="AMDEC">AMDEC</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>

                                        <div>
                                            <Label>Safety Level</Label>
                                            <Select
                                                value={formData.safety_level}
                                                onValueChange={(val) => setFormData(prev => ({ ...prev, safety_level: val }))}
                                            >
                                                <SelectTrigger>
                                                    <SelectValue placeholder="Select Level" />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="Low">Low</SelectItem>
                                                    <SelectItem value="Medium">Medium</SelectItem>
                                                    <SelectItem value="High">High</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>

                                        <div className="col-span-2">
                                            <Label>Failure Type (Optional)</Label>
                                            <Input
                                                value={formData.type_panne}
                                                onChange={(e) => setFormData(prev => ({ ...prev, type_panne: e.target.value }))}
                                                placeholder="e.g. Mechanical, Electrical"
                                            />
                                        </div>
                                    </div>

                                    <Separator />

                                    <MarkdownEditor
                                        initialValue={selectedDoc.content}
                                        onSave={handleSave}
                                        onCancel={() => setIsEditing(false)}
                                        isSaving={updateMutation.isPending}
                                    />
                                </div>
                            ) : (
                                <div className="max-w-4xl mx-auto space-y-6">
                                    {/* Document Header */}
                                    <div className="border-b pb-4">
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <div className="flex items-center gap-2 mb-2">
                                                    <Badge>{selectedDoc.category}</Badge>
                                                    {selectedDoc.type_panne && (
                                                        <Badge variant="outline">{selectedDoc.type_panne}</Badge>
                                                    )}
                                                    {selectedDoc.safety_level === 'High' && (
                                                        <Badge variant="destructive" className="animate-pulse">
                                                            <AlertTriangle className="h-3 w-3 mr-1" />
                                                            Critical Safety
                                                        </Badge>
                                                    )}
                                                </div>
                                                <h1 className="text-3xl font-bold tracking-tight">{selectedDoc.title}</h1>
                                                <div className="text-sm text-muted-foreground mt-2 flex items-center gap-4">
                                                    <span>Version {selectedDoc.version}</span>
                                                    <span>Last updated: {new Date(selectedDoc.updated_at).toLocaleString()}</span>
                                                </div>
                                            </div>
                                            <div className="flex gap-2">
                                                <SupervisorOrAbove>
                                                    <Button variant="outline" size="sm" onClick={startEditing}>
                                                        <Edit className="h-4 w-4 mr-2" />
                                                        Edit
                                                    </Button>
                                                </SupervisorOrAbove>

                                                <SupervisorOrAbove>
                                                    <DropdownMenu>
                                                        <DropdownMenuTrigger asChild>
                                                            <Button variant="ghost" size="icon">
                                                                <MoreVertical className="h-4 w-4" />
                                                            </Button>
                                                        </DropdownMenuTrigger>
                                                        <DropdownMenuContent align="end">
                                                            <DropdownMenuItem onClick={() => reindexMutation.mutate(selectedDoc.id)}>
                                                                <RefreshCw className="h-4 w-4 mr-2" />
                                                                Re-index for AI
                                                            </DropdownMenuItem>
                                                            <DropdownMenuItem className="text-red-600" onClick={() => handleDelete(selectedDoc.id)}>
                                                                <Trash2 className="h-4 w-4 mr-2" />
                                                                Delete
                                                            </DropdownMenuItem>
                                                        </DropdownMenuContent>
                                                    </DropdownMenu>
                                                </SupervisorOrAbove>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Document Content */}
                                    <article className="prose dark:prose-invert max-w-none prose-headings:font-bold prose-h1:text-2xl prose-a:text-primary">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {selectedDoc.content}
                                        </ReactMarkdown>
                                    </article>

                                    {!selectedDoc.indexed && (
                                        <Alert variant="warning" className="mt-8">
                                            <AlertTriangle className="h-4 w-4" />
                                            <AlertTitle>Not Indexed</AlertTitle>
                                            <AlertDescription>
                                                This version has not been indexed yet. It may not appear in AI search results.
                                            </AlertDescription>
                                        </Alert>
                                    )}
                                </div>
                            )
                        ) : (
                            <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
                                <Book className="h-16 w-16 mb-4 opacity-20" />
                                <h3 className="text-lg font-medium">Select a document</h3>
                                <p>Choose a document from the sidebar or create a new one.</p>
                            </div>
                        )}
                    </div>
                </div>
            </PageBody>
        </div>
    );
}
