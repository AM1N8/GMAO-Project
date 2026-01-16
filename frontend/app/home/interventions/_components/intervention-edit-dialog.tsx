'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
} from '@kit/ui/sheet';

import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { InterventionForm, type InterventionFormValues } from './intervention-form';

interface InterventionEditDialogProps {
    intervention: any;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function InterventionEditDialog({
    intervention,
    open,
    onOpenChange,
}: InterventionEditDialogProps) {
    const api = useGmaoApi();
    const queryClient = useQueryClient();

    const updateMutation = useMutation({
        mutationFn: (values: InterventionFormValues) =>
            api.updateIntervention(intervention.id, values),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['interventions'] });
            toast.success('Intervention updated successfully');
            onOpenChange(false);
        },
        onError: (error: any) => {
            toast.error(`Failed to update intervention: ${error.message}`);
        },
    });

    function onSubmit(values: InterventionFormValues) {
        updateMutation.mutate(values);
    }

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent className="sm:max-w-[500px] overflow-y-auto">
                <SheetHeader>
                    <SheetTitle>Edit Intervention</SheetTitle>
                    <SheetDescription>
                        Update the details of the maintenance intervention.
                    </SheetDescription>
                </SheetHeader>

                {intervention && (
                    <InterventionForm
                        onSubmit={onSubmit}
                        initialValues={intervention}
                        isLoading={updateMutation.isPending}
                        submitLabel="Save Changes"
                    />
                )}
            </SheetContent>
        </Sheet>
    );
}
