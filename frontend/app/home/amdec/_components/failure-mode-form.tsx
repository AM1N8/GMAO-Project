'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { useQuery } from '@tanstack/react-query';
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from '@kit/ui/form';
import { Input } from '@kit/ui/input';
import { Button } from '@kit/ui/button';
import { Textarea } from '@kit/ui/textarea';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@kit/ui/select';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { Loader2 } from 'lucide-react';

const formSchema = z.object({
    equipment_id: z.string().min(1, 'Equipment is required'),
    mode_name: z.string().min(3, 'Mode name must be at least 3 characters').max(200),
    description: z.string().optional(),
    failure_cause: z.string().optional(),
    failure_effect: z.string().optional(),
    detection_method: z.string().max(200).optional(),
    prevention_action: z.string().optional(),
    is_active: z.boolean(),
});

type FormValues = z.infer<typeof formSchema>;

interface FailureModeFormProps {
    initialValues?: Partial<FormValues>;
    onSubmit: (values: FormValues) => void;
    isLoading?: boolean;
}

export function FailureModeForm({ initialValues, onSubmit, isLoading }: FailureModeFormProps) {
    const api = useGmaoApi();
    // Sanitize initialValues: convert nulls to empty strings for controlled inputs
    const sanitizedInitialValues = initialValues ? Object.entries(initialValues).reduce((acc, [key, value]) => {
        acc[key as keyof FormValues] = (value === null && typeof value !== 'boolean') ? '' : value;
        return acc;
    }, {} as any) : {};

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            mode_name: '',
            description: '',
            failure_cause: '',
            failure_effect: '',
            detection_method: '',
            prevention_action: '',
            is_active: true,
            ...sanitizedInitialValues,
        } as FormValues,
    });

    const { data: equipments, isLoading: isLoadingEquipments } = useQuery({
        queryKey: ['equipment-list'],
        queryFn: () => api.listEquipment({ limit: 1000 }),
    });

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                <div className="grid gap-6 md:grid-cols-2">
                    <FormField
                        control={form.control}
                        name="equipment_id"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Equipment</FormLabel>
                                <Select
                                    onValueChange={field.onChange}
                                    defaultValue={field.value}
                                    disabled={isLoadingEquipments}
                                >
                                    <FormControl>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select equipment" />
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        {equipments?.map((eq: any) => (
                                            <SelectItem key={eq.id} value={eq.id.toString()}>
                                                {eq.designation} ({eq.code})
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="mode_name"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Failure Mode Name</FormLabel>
                                <FormControl>
                                    <Input placeholder="e.g., Bearing Seizure, Oil Leak" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                <FormField
                    control={form.control}
                    name="description"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Detailed Description</FormLabel>
                            <FormControl>
                                <Textarea
                                    placeholder="Describe how the failure happens..."
                                    className="min-h-[100px]"
                                    {...field}
                                />
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <div className="grid gap-6 md:grid-cols-2">
                    <FormField
                        control={form.control}
                        name="failure_cause"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Potential Cause</FormLabel>
                                <FormControl>
                                    <Textarea placeholder="What causes this failure?" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="failure_effect"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Failure Effect</FormLabel>
                                <FormControl>
                                    <Textarea placeholder="What is the impact of this failure?" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                <div className="grid gap-6 md:grid-cols-2">
                    <FormField
                        control={form.control}
                        name="detection_method"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Detection Method</FormLabel>
                                <FormControl>
                                    <Input placeholder="Visual inspection, vibration analysis, etc." {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="prevention_action"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Prevention Action</FormLabel>
                                <FormControl>
                                    <Textarea placeholder="What actions prevent this?" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                <div className="flex justify-end gap-3">
                    <Button type="button" variant="outline" onClick={() => window.history.back()}>
                        Cancel
                    </Button>
                    <Button type="submit" disabled={isLoading}>
                        {isLoading ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Saving...
                            </>
                        ) : (
                            'Save Failure Mode'
                        )}
                    </Button>
                </div>
            </form>
        </Form>
    );
}
