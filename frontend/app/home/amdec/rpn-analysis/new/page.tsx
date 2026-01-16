'use client';

import { useMutation } from '@tanstack/react-query';
import { useRouter, useSearchParams } from 'next/navigation';
import { PageHeader } from '@kit/ui/page';
import { RpnForm } from '../../_components/rpn-form';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { toast } from 'sonner';
import { Card, CardContent } from '@kit/ui/card';

export default function NewRpnAnalysisPage() {
    const api = useGmaoApi();
    const router = useRouter();
    const searchParams = useSearchParams();
    const failureModeId = searchParams.get('failure_mode_id');

    const mutation = useMutation({
        mutationFn: (values: any) => api.createRpnAnalysis({
            ...values,
            failure_mode_id: parseInt(values.failure_mode_id)
        }),
        onSuccess: () => {
            toast.success('RPN analysis saved successfully');
            router.push('/home/amdec/rpn-analysis');
        },
        onError: (err: any) => {
            toast.error(`Analysis failed: ${err.message}`);
        }
    });

    return (
        <div className="flex flex-col space-y-6 max-w-4xl mx-auto w-full">
            <PageHeader
                title="New RPN Analysis"
                description="Evaluate risk parameters to calculate the Risk Priority Number."
            />

            <Card>
                <CardContent className="pt-6">
                    <RpnForm
                        initialValues={{ failure_mode_id: failureModeId || '' }}
                        onSubmit={(values) => mutation.mutate(values)}
                        isLoading={mutation.isPending}
                    />
                </CardContent>
            </Card>
        </div>
    );
}
