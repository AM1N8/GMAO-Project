'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter, useParams } from 'next/navigation';
import { PageHeader } from '@kit/ui/page';
import { FailureModeForm } from '../../../_components/failure-mode-form';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { toast } from 'sonner';
import { Card, CardContent } from '@kit/ui/card';
import { Loader2 } from 'lucide-react';

export default function EditFailureModePage() {
    const api = useGmaoApi();
    const router = useRouter();
    const params = useParams();
    const queryClient = useQueryClient();
    const id = parseInt(params.id as string);

    const { data: failureMode, isLoading } = useQuery({
        queryKey: ['failure-mode', id],
        queryFn: () => api.getFailureMode(id),
    });

    const mutation = useMutation({
        mutationFn: (values: any) => api.updateFailureMode(id, {
            ...values,
            equipment_id: parseInt(values.equipment_id)
        }),
        onSuccess: () => {
            toast.success('Failure mode updated successfully');
            queryClient.invalidateQueries({ queryKey: ['failure-mode', id] });
            router.push('/home/amdec/failure-modes');
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
                title="Edit Failure Mode"
                description={`Updating details for ${failureMode?.mode_name}`}
            />

            <Card>
                <CardContent className="pt-6">
                    <FailureModeForm
                        initialValues={failureMode}
                        onSubmit={(values) => mutation.mutate(values)}
                        isLoading={mutation.isPending}
                    />
                </CardContent>
            </Card>
        </div>
    );
}
