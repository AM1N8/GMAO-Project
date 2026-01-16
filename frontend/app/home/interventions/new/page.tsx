'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Wrench } from 'lucide-react';

import { PageBody, PageHeader } from '@kit/ui/page';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@kit/ui/card';

import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { InterventionForm, type InterventionFormValues } from '../_components/intervention-form';
import { TechnicianOnly } from '~/components/auth/role-guard';

export default function NewInterventionPage() {
    const api = useGmaoApi();
    const router = useRouter();
    const queryClient = useQueryClient();

    const createMutation = useMutation({
        mutationFn: (values: InterventionFormValues) => api.createIntervention(values),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['interventions'] });
            toast.success('Intervention logged successfully');
            router.push('/home/interventions');
        },
        onError: (error: any) => {
            toast.error(`Failed to log intervention: ${error.message}`);
        },
    });

    return (
        <TechnicianOnly>
            <PageHeader
                title="Log Intervention"
                description="Submit a new maintenance report."
            />

            <PageBody>
                <div className="max-w-2xl mx-auto py-6">
                    <Card className="border-t-4 border-t-primary">
                        <CardHeader className="pb-2">
                            <div className="flex items-center gap-3">
                                <div className="p-2 rounded-lg bg-primary/10 text-primary">
                                    <Wrench className="h-5 w-5" />
                                </div>
                                <div>
                                    <CardTitle className="text-xl">Intervention Details</CardTitle>
                                    <CardDescription>
                                        Please fill in all required operational information.
                                    </CardDescription>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <InterventionForm
                                onSubmit={(values) => createMutation.mutate(values)}
                                isLoading={createMutation.isPending}
                                submitLabel="Submit Report"
                            />
                        </CardContent>
                    </Card>
                </div>
            </PageBody>
        </TechnicianOnly>
    );
}
