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

const equipmentSchema = z.object({
    designation: z.string().min(1, 'Designation is required').max(200),
    type: z.string().min(1, 'Type is required').max(100),
    location: z.string().optional(),
    status: z.enum(['active', 'inactive', 'maintenance', 'decommissioned']),
    acquisition_date: z.string().optional(),
    manufacturer: z.string().optional(),
    model: z.string().optional(),
    serial_number: z.string().optional(),
});

type EquipmentFormValues = z.infer<typeof equipmentSchema>;

interface EquipmentEditDialogProps {
    equipment: any;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function EquipmentEditDialog({
    equipment,
    open,
    onOpenChange,
}: EquipmentEditDialogProps) {
    const api = useGmaoApi();
    const queryClient = useQueryClient();

    const form = useForm<EquipmentFormValues>({
        resolver: zodResolver(equipmentSchema),
        defaultValues: {
            designation: '',
            type: '',
            location: '',
            status: 'active',
            acquisition_date: '',
            manufacturer: '',
            model: '',
            serial_number: '',
        },
    });

    useEffect(() => {
        if (equipment && open) {
            form.reset({
                designation: equipment.designation || '',
                type: equipment.type || '',
                location: equipment.location || '',
                status: equipment.status || 'active',
                acquisition_date: equipment.acquisition_date || '',
                manufacturer: equipment.manufacturer || '',
                model: equipment.model || '',
                serial_number: equipment.serial_number || '',
            });
        }
    }, [equipment, open, form]);

    const updateMutation = useMutation({
        mutationFn: (values: EquipmentFormValues) =>
            api.updateEquipment(equipment.id, values),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['equipment-list'] });
            toast.success('Equipment updated successfully');
            onOpenChange(false);
        },
        onError: (error: any) => {
            toast.error(`Failed to update equipment: ${error.message}`);
        },
    });

    function onSubmit(values: EquipmentFormValues) {
        updateMutation.mutate(values);
    }

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent className="sm:max-w-[500px] overflow-y-auto">
                <SheetHeader>
                    <SheetTitle>Edit Equipment</SheetTitle>
                    <SheetDescription>
                        Update the details of the asset.
                    </SheetDescription>
                </SheetHeader>

                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4 py-4">
                        <FormField
                            control={form.control}
                            name="designation"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Designation</FormLabel>
                                    <FormControl>
                                        <Input placeholder="e.g. CNC Machine, Air Compressor" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={form.control}
                                name="type"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Type</FormLabel>
                                        <FormControl>
                                            <Input placeholder="e.g. Mechanical" {...field} />
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
                                                <SelectItem value="maintenance">Maintenance</SelectItem>
                                                <SelectItem value="inactive">Inactive</SelectItem>
                                                <SelectItem value="decommissioned">Decommissioned</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <FormField
                            control={form.control}
                            name="location"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Location</FormLabel>
                                    <FormControl>
                                        <Input placeholder="e.g. Workshop A, Production Line 2" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={form.control}
                                name="manufacturer"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Manufacturer</FormLabel>
                                        <FormControl>
                                            <Input placeholder="e.g. Siemens, Bosch" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="model"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Model</FormLabel>
                                        <FormControl>
                                            <Input placeholder="e.g. X100, V2" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={form.control}
                                name="serial_number"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Serial Number</FormLabel>
                                        <FormControl>
                                            <Input placeholder="e.g. SN-12345" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="acquisition_date"
                                render={({ field }) => (
                                    <FormItem className="flex flex-col">
                                        <FormLabel>Acquisition Date</FormLabel>
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

                        <SheetFooter className="pt-4">
                            <Button
                                type="submit"
                                className="w-full"
                                disabled={updateMutation.isPending}
                            >
                                {updateMutation.isPending ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Saving Changes...
                                    </>
                                ) : (
                                    'Save Changes'
                                )}
                            </Button>
                        </SheetFooter>
                    </form>
                </Form>
            </SheetContent>
        </Sheet>
    );
}
