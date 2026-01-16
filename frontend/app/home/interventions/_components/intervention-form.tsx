'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useQuery } from '@tanstack/react-query';
import { Loader2, Calendar as CalendarIcon } from 'lucide-react';
import { format } from 'date-fns';

import {
    Form,
    FormControl,
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
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from '@kit/ui/popover';
import { Calendar } from '@kit/ui/calendar';
import { cn } from '@kit/ui/utils';

import { useGmaoApi } from '~/lib/hooks/use-gmao-api';

export const interventionSchema = z.object({
    equipment_id: z.coerce.number().min(1, 'Equipment is required'),
    type_panne: z.string().min(1, 'Type is required').max(100),
    status: z.enum(['open', 'in_progress', 'completed', 'closed', 'cancelled']),
    date_intervention: z.string().min(1, 'Date is required'),
    resume_intervention: z.string().optional(),
    cause: z.string().optional(),
    resultat: z.string().optional(),
    duree_arret: z.coerce.number().min(0),
    cout_materiel: z.coerce.number().min(0),
    nombre_heures_mo: z.coerce.number().min(0),
});

export type InterventionFormValues = z.infer<typeof interventionSchema>;

interface InterventionFormProps {
    onSubmit: (values: InterventionFormValues) => void;
    initialValues?: Partial<InterventionFormValues>;
    isLoading?: boolean;
    submitLabel?: string;
}

export function InterventionForm({
    onSubmit,
    initialValues,
    isLoading,
    submitLabel = 'Save Intervention',
}: InterventionFormProps) {
    const api = useGmaoApi();

    const form = useForm<InterventionFormValues>({
        resolver: zodResolver(interventionSchema),
        defaultValues: {
            equipment_id: initialValues?.equipment_id || 0,
            type_panne: initialValues?.type_panne || '',
            status: initialValues?.status || 'open',
            date_intervention: initialValues?.date_intervention || new Date().toISOString().split('T')[0],
            resume_intervention: initialValues?.resume_intervention || '',
            cause: initialValues?.cause || '',
            resultat: initialValues?.resultat || '',
            duree_arret: initialValues?.duree_arret || 0,
            cout_materiel: initialValues?.cout_materiel || 0,
            nombre_heures_mo: initialValues?.nombre_heures_mo || 0,
        },
    });

    const { data: equipment, isLoading: equipmentLoading } = useQuery({
        queryKey: ['equipment-list'],
        queryFn: () => api.listEquipment(),
    });

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4 py-4">
                <FormField
                    control={form.control}
                    name="equipment_id"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Equipment</FormLabel>
                            <Select
                                onValueChange={field.onChange}
                                defaultValue={field.value?.toString()}
                                value={field.value?.toString()}
                            >
                                <FormControl>
                                    <SelectTrigger disabled={equipmentLoading}>
                                        <SelectValue placeholder="Select equipment" />
                                    </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                    {equipment?.map((eq: any) => (
                                        <SelectItem key={eq.id} value={eq.id.toString()}>
                                            {eq.designation || eq.code || `Equipment #${eq.id}`}
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
                    name="type_panne"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Failure Type</FormLabel>
                            <FormControl>
                                <Input placeholder="e.g. Mechanical, Electrical" {...field} />
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField
                        control={form.control}
                        name="status"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Status</FormLabel>
                                <Select onValueChange={field.onChange} defaultValue={field.value} value={field.value}>
                                    <FormControl>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select status" />
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        <SelectItem value="open">Open</SelectItem>
                                        <SelectItem value="in_progress">In Progress</SelectItem>
                                        <SelectItem value="completed">Completed</SelectItem>
                                        <SelectItem value="closed">Closed</SelectItem>
                                        <SelectItem value="cancelled">Cancelled</SelectItem>
                                    </SelectContent>
                                </Select>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="date_intervention"
                        render={({ field }) => (
                            <FormItem className="flex flex-col">
                                <FormLabel>Date</FormLabel>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <FormControl>
                                            <Button
                                                variant={"outline"}
                                                className={cn(
                                                    "w-full pl-3 text-left font-normal",
                                                    !field.value && "text-muted-foreground"
                                                )}
                                            >
                                                {field.value ? (
                                                    format(new Date(field.value), "PPP")
                                                ) : (
                                                    <span>Pick a date</span>
                                                )}
                                                <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                                            </Button>
                                        </FormControl>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-auto p-0" align="start">
                                        <Calendar
                                            mode="single"
                                            selected={field.value ? new Date(field.value) : undefined}
                                            onSelect={(date) =>
                                                field.onChange(date?.toISOString().split('T')[0])
                                            }
                                            disabled={(date) =>
                                                date > new Date() || date < new Date("1900-01-01")
                                            }
                                            initialFocus
                                        />
                                    </PopoverContent>
                                </Popover>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                <FormField
                    control={form.control}
                    name="resume_intervention"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Summary</FormLabel>
                            <FormControl>
                                <Textarea
                                    placeholder="Brief description of the work done"
                                    className="min-h-[80px]"
                                    {...field}
                                />
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="cause"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Root Cause</FormLabel>
                            <FormControl>
                                <Textarea
                                    placeholder="What caused the failure?"
                                    className="min-h-[80px]"
                                    {...field}
                                />
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="resultat"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Result/Outcome</FormLabel>
                            <FormControl>
                                <Textarea
                                    placeholder="Final status of the machine"
                                    className="min-h-[80px]"
                                    {...field}
                                />
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <FormField
                        control={form.control}
                        name="duree_arret"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Downtime (h)</FormLabel>
                                <FormControl>
                                    <Input type="number" step="0.5" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="nombre_heures_mo"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Labor (h)</FormLabel>
                                <FormControl>
                                    <Input type="number" step="0.5" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="cout_materiel"
                        render={({ field }) => (
                            <FormItem className="col-span-2 md:col-span-1">
                                <FormLabel>Material Cost (€)</FormLabel>
                                <FormControl>
                                    <Input type="number" step="0.1" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                <Button
                    type="submit"
                    className="w-full"
                    disabled={isLoading}
                >
                    {isLoading ? (
                        <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Processing...
                        </>
                    ) : (
                        submitLabel
                    )}
                </Button>
            </form>
        </Form>
    );
}
