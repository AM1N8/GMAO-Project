'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter, useParams } from 'next/navigation';
import { PageHeader } from '@kit/ui/page';
import { RpnForm } from '../../../_components/rpn-form';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { toast } from 'sonner';
import { Card, CardContent } from '@kit/ui/card';
import { Loader2 } from 'lucide-react';

export default function EditRpnAnalysisPage() {
    const api = useGmaoApi();
    const router = useRouter();
    const params = useParams();
    const queryClient = useQueryClient();
    const id = parseInt(params.id as string);

    const { data: analysis, isLoading } = useQuery({
        queryKey: ['rpn-analysis', id],
        queryFn: () => api.getRpnAnalysis(id),
    });

    const mutation = useMutation({
        mutationFn: (values: any) => api.updateRpnAnalysis(id, {
            ...values,
            failure_mode_id: parseInt(values.failure_mode_id)
        }),
        onSuccess: () => {
            toast.success('Analysis updated successfully');
            queryClient.invalidateQueries({ queryKey: ['rpn-analysis', id] });
            router.push('/home/amdec/rpn-analysis');
        },
        onError: (err: any) => {
            toast.error(`Update failed: ${err.message}`);
        }
    });

    if (isLoading) {
        return (
            <div className="flex items-center justify-center p-24">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="flex flex-col space-y-6 max-w-4xl mx-auto w-full">
            <PageHeader
                title="Edit RPN Analysis"
                description="Update the risk evaluation parameters."
            />

            <Card>
                <CardContent className="pt-6">
                    <RpnForm
                        initialValues={analysis}
                        onSubmit={(values) => mutation.mutate(values)}
                        isLoading={mutation.isPending}
                    />
                </CardContent>
            </Card>
        </div>
    );
}
