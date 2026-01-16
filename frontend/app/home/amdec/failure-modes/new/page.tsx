'use client';

import { useMutation } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { PageHeader } from '@kit/ui/page';
import { FailureModeForm } from '../../_components/failure-mode-form';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { toast } from 'sonner';
import { Card, CardContent } from '@kit/ui/card';

export default function NewFailureModePage() {
    const api = useGmaoApi();
    const router = useRouter();

    const mutation = useMutation({
        mutationFn: (values: any) => api.createFailureMode({
            ...values,
            equipment_id: parseInt(values.equipment_id)
        }),
        onSuccess: () => {
            toast.success('Failure mode created successfully');
            router.push('/home/amdec/failure-modes');
        },
        onError: (err: any) => {
            toast.error(`Creation failed: ${err.message}`);
        }
    });

    return (
        <div className="flex flex-col space-y-6 max-w-4xl mx-auto w-full">
            <PageHeader
                title="New Failure Mode"
                description="Define a new failure mode and its characteristics."
            />

            <Card>
                <CardContent className="pt-6">
                    <FailureModeForm
                        onSubmit={(values) => mutation.mutate(values)}
                        isLoading={mutation.isPending}
                    />
                </CardContent>
            </Card>
        </div>
    );
}
