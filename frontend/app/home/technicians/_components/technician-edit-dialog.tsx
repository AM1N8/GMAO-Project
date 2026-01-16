'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Loader2, Calendar as CalendarIcon } from 'lucide-react';
import { format } from 'date-fns';

import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
    SheetFooter,
} from '@kit/ui/sheet';
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

const technicianSchema = z.object({
    nom: z.string().min(1, 'Last name is required').max(100),
    prenom: z.string().min(1, 'First name is required').max(100),
    email: z.string().email('Invalid email address'),
    telephone: z.string().optional(),
    specialite: z.string().optional(),
    taux_horaire: z.coerce.number().min(0),
    status: z.enum(['active', 'inactive', 'on_leave']),
    date_embauche: z.string().optional(),
    matricule: z.string().optional(),
});

type TechnicianFormValues = z.infer<typeof technicianSchema>;

interface TechnicianEditDialogProps {
    technician: any;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function TechnicianEditDialog({
    technician,
    open,
    onOpenChange,
}: TechnicianEditDialogProps) {
    const api = useGmaoApi();
    const queryClient = useQueryClient();

    const form = useForm<TechnicianFormValues>({
        resolver: zodResolver(technicianSchema),
        defaultValues: {
            nom: '',
            prenom: '',
            email: '',
            telephone: '',
            specialite: '',
            taux_horaire: 0,
            status: 'active',
            date_embauche: '',
            matricule: '',
        },
    });

    useEffect(() => {
        if (technician && open) {
            form.reset({
                nom: technician.nom || '',
                prenom: technician.prenom || '',
                email: technician.email || '',
                telephone: technician.telephone || '',
                specialite: technician.specialite || '',
                taux_horaire: technician.taux_horaire || 0,
                status: technician.status || 'active',
                date_embauche: technician.date_embauche || '',
                matricule: technician.matricule || '',
            });
        }
    }, [technician, open, form]);

    const updateMutation = useMutation({
        mutationFn: (values: TechnicianFormValues) =>
            api.updateTechnician(technician.id, values),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['technicians'] });
            toast.success('Technician profile updated');
            onOpenChange(false);
        },
        onError: (error: any) => {
            toast.error(`Failed to update technician: ${error.message}`);
        },
    });

    function onSubmit(values: TechnicianFormValues) {
        updateMutation.mutate(values);
    }

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent className="sm:max-w-[500px] overflow-y-auto">
                <SheetHeader>
                    <SheetTitle>Edit Technician Profile</SheetTitle>
                    <SheetDescription>
                        Update personnel information and specialties.
                    </SheetDescription>
                </SheetHeader>

                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4 py-4">
                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={form.control}
                                name="prenom"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>First Name</FormLabel>
                                        <FormControl>
                                            <Input placeholder="Jane" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="nom"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Last Name</FormLabel>
                                        <FormControl>
                                            <Input placeholder="Doe" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <FormField
                            control={form.control}
                            name="email"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Email</FormLabel>
                                    <FormControl>
                                        <Input type="email" placeholder="jane.doe@example.com" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={form.control}
                                name="telephone"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Phone</FormLabel>
                                        <FormControl>
                                            <Input placeholder="+33 6 12 34 56 78" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="matricule"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Employee ID (Matricule)</FormLabel>
                                        <FormControl>
                                            <Input placeholder="TEC-2024-001" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <FormField
                            control={form.control}
                            name="specialite"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Specialty</FormLabel>
                                    <FormControl>
                                        <Input placeholder="e.g. Electrical, Hydraulic" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={form.control}
                                name="taux_horaire"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Hourly Rate (€)</FormLabel>
                                        <FormControl>
                                            <Input type="number" step="0.5" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="status"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Status</FormLabel>
                                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                                            <FormControl>
                                                <SelectTrigger>
                                                    <SelectValue placeholder="Select status" />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent>
                                                <SelectItem value="active">Active</SelectItem>
                                                <SelectItem value="on_leave">On Leave</SelectItem>
                                                <SelectItem value="inactive">Inactive</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <FormField
                            control={form.control}
                            name="date_embauche"
                            render={({ field }) => (
                                <FormItem className="flex flex-col">
                                    <FormLabel>Hire Date</FormLabel>
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

                        <SheetFooter className="pt-4">
                            <Button
                                type="submit"
                                className="w-full"
                                disabled={updateMutation.isPending}
                            >
                                {updateMutation.isPending ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Saving Profile...
                                    </>
                                ) : (
                                    'Save Profile'
                                )}
                            </Button>
                        </SheetFooter>
                    </form>
                </Form>
            </SheetContent>
        </Sheet>
    );
}
