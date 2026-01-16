'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '@kit/ui/page';
import { FailureModesTable } from '../_components/failure-modes-table';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { Loader2, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

export default function FailureModesPage() {
    const api = useGmaoApi();
    const queryClient = useQueryClient();

    const { data: failureModes, isLoading } = useQuery({
        queryKey: ['failure-modes'],
        queryFn: () => api.listFailureModes({ include_rpn: true }),
    });

    const deleteMutation = useMutation({
        mutationFn: (id: number) => api.deleteFailureMode(id),
        onSuccess: () => {
            toast.success('Failure mode deleted successfully');
            queryClient.invalidateQueries({ queryKey: ['failure-modes'] });
        },
        onError: (err: any) => {
            toast.error(`Delete failed: ${err.message}`);
        }
    });

    const handleDelete = (id: number) => {
        if (confirm('Are you sure you want to delete this failure mode? This will also delete all associated RPN analyses.')) {
            deleteMutation.mutate(id);
        }
    };

    return (
        <div className="flex flex-col space-y-6">
            <PageHeader
                title="Failure Modes"
                description="Catalogue of all possible failure modes for tracked equipment."
            />

            {isLoading ? (
                <div className="flex items-center justify-center py-24">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
            ) : failureModes ? (
                <FailureModesTable
                    data={failureModes}
                    onDelete={handleDelete}
                />
            ) : (
                <div className="flex flex-col items-center justify-center py-24 text-muted-foreground border rounded-lg border-dashed">
                    <AlertTriangle className="h-12 w-12 mb-4 opacity-20" />
                    <p>Failed to load failure modes.</p>
                </div>
            )}
        </div>
    );
}
