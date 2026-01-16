'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '@kit/ui/page';
import { RpnTable } from '../_components/rpn-table';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { Loader2, AlertTriangle, TrendingUp } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@kit/ui/card';

export default function RpnAnalysisPage() {
    const api = useGmaoApi();
    const queryClient = useQueryClient();

    const { data: analyses, isLoading } = useQuery({
        queryKey: ['rpn-analyses'],
        queryFn: () => api.listRpnAnalyses({ limit: 1000 }),
    });

    const deleteMutation = useMutation({
        mutationFn: (id: number) => api.deleteRpnAnalysis(id),
        onSuccess: () => {
            toast.success('RPN analysis deleted successfully');
            queryClient.invalidateQueries({ queryKey: ['rpn-analyses'] });
        },
        onError: (err: any) => {
            toast.error(`Delete failed: ${err.message}`);
        }
    });

    const handleDelete = (id: number) => {
        if (confirm('Are you sure you want to delete this RPN analysis?')) {
            deleteMutation.mutate(id);
        }
    };

    return (
        <div className="flex flex-col space-y-6">
            <PageHeader
                title="RPN Analyses"
                description="Assess risks by evaluating Severity, Occurrence, and Detection for each failure mode."
            />

            <div className="grid gap-6 md:grid-cols-3">
                <Card className="md:col-span-1">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium uppercase text-muted-foreground">Analyses Performed</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center gap-3">
                            <TrendingUp className="h-8 w-8 text-primary" />
                            <span className="text-3xl font-bold">{analyses?.length || 0}</span>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {isLoading ? (
                <div className="flex items-center justify-center py-24">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
            ) : analyses ? (
                <RpnTable
                    data={analyses}
                    onDelete={handleDelete}
                />
            ) : (
                <div className="flex flex-col items-center justify-center py-24 text-muted-foreground border rounded-lg border-dashed">
                    <AlertTriangle className="h-12 w-12 mb-4 opacity-20" />
                    <p>Failed to load RPN analyses.</p>
                </div>
            )}
        </div>
    );
}
