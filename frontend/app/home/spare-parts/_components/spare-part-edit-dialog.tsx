'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';

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
import { Textarea } from '@kit/ui/textarea';

import { useGmaoApi } from '~/lib/hooks/use-gmao-api';

const sparePartSchema = z.object({
    designation: z.string().min(1, 'Designation is required').max(200),
    reference: z.string().min(1, 'Reference is required').max(100),
    description: z.string().optional(),
    cout_unitaire: z.coerce.number().min(0, 'Cost must be positive'),
    stock_actuel: z.coerce.number().int().min(0, 'Stock cannot be negative'),
    seuil_alerte: z.coerce.number().int().min(1, 'Alert threshold must be at least 1'),
    unite: z.string().min(1, 'Unit is required').max(20),
    fournisseur: z.string().optional().nullable(),
    delai_livraison: z.coerce.number().int().min(0).optional().nullable(),
});

type SparePartFormValues = z.infer<typeof sparePartSchema>;

interface SparePartEditDialogProps {
    sparePart: any;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function SparePartEditDialog({
    sparePart,
    open,
    onOpenChange,
}: SparePartEditDialogProps) {
    const api = useGmaoApi();
    const queryClient = useQueryClient();

    const form = useForm<SparePartFormValues>({
        resolver: zodResolver(sparePartSchema),
        defaultValues: {
            designation: '',
            reference: '',
            description: '',
            cout_unitaire: 0,
            stock_actuel: 0,
            seuil_alerte: 10,
            unite: 'pcs',
            fournisseur: '',
            delai_livraison: 0,
        },
    });

    useEffect(() => {
        if (sparePart && open) {
            form.reset({
                designation: sparePart.designation || '',
                reference: sparePart.reference || '',
                description: sparePart.description || '',
                cout_unitaire: sparePart.cout_unitaire || 0,
                stock_actuel: sparePart.stock_actuel || 0,
                seuil_alerte: sparePart.seuil_alerte || 10,
                unite: sparePart.unite || 'pcs',
                fournisseur: sparePart.fournisseur || '',
                delai_livraison: sparePart.delai_livraison || 0,
            });
        }
    }, [sparePart, open, form]);

    const updateMutation = useMutation({
        mutationFn: (values: SparePartFormValues) =>
            api.updateSparePart(sparePart.id, values),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['spare-parts'] });
            toast.success('Spare part updated successfully');
            onOpenChange(false);
        },
        onError: (error: any) => {
            toast.error(`Failed to update spare part: ${error.message}`);
        },
    });

    function onSubmit(values: SparePartFormValues) {
        updateMutation.mutate(values);
    }

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent className="sm:max-w-[500px] overflow-y-auto">
                <SheetHeader>
                    <SheetTitle>Edit Spare Part</SheetTitle>
                    <SheetDescription>
                        Modify inventory details and stock thresholds.
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
                                        <Input placeholder="e.g. Ball Bearing 6204-2RS" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <FormField
                            control={form.control}
                            name="reference"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Reference (SKU)</FormLabel>
                                    <FormControl>
                                        <Input placeholder="REF-001" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <FormField
                            control={form.control}
                            name="description"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Description</FormLabel>
                                    <FormControl>
                                        <Textarea
                                            placeholder="Technical details, usage, etc."
                                            className="min-h-[80px]"
                                            {...field}
                                        />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={form.control}
                                name="cout_unitaire"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Unit Cost (€)</FormLabel>
                                        <FormControl>
                                            <Input type="number" step="0.01" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="unite"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Unit</FormLabel>
                                        <FormControl>
                                            <Input placeholder="pcs, kg, m" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={form.control}
                                name="stock_actuel"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Current Stock</FormLabel>
                                        <FormControl>
                                            <Input type="number" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="seuil_alerte"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Alert Threshold</FormLabel>
                                        <FormControl>
                                            <Input type="number" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <FormField
                            control={form.control}
                            name="fournisseur"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Supplier</FormLabel>
                                    <FormControl>
                                        <Input placeholder="Supplier Name" {...field} value={field.value || ''} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <FormField
                            control={form.control}
                            name="delai_livraison"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Lead Time (Days)</FormLabel>
                                    <FormControl>
                                        <Input type="number" {...field} value={field.value || 0} />
                                    </FormControl>
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
                                        Saving...
                                    </>
                                ) : (
                                    'Save Part Details'
                                )}
                            </Button>
                        </SheetFooter>
                    </form>
                </Form>
            </SheetContent>
        </Sheet>
    );
}
