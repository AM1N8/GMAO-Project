'use client';

import { useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
    MoreHorizontal,
    Search,
    Filter,
    ChevronDown,
    Package,
    Edit,
    Trash,
    AlertTriangle
} from 'lucide-react';
import { toast } from 'sonner';

import { DataTableColumnHeader } from '~/components/data-table-column-header';
import { AdminOnly, SupervisorOrAbove } from '~/components/auth/role-guard';
import { useUserRole } from '~/lib/hooks/use-user-role';

import { Badge } from '@kit/ui/badge';
import { DataTable } from '@kit/ui/enhanced-data-table';
import { Button } from '@kit/ui/button';
import { Input } from '@kit/ui/input';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@kit/ui/dropdown-menu';

import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { SparePartEditDialog } from './spare-part-edit-dialog';

type SparePart = {
    id: number;
    designation: string;
    reference: string;
    cout_unitaire: number;
    stock_actuel: number;
    seuil_alerte: number;
    fournisseur: string;
    unite: string;
    description?: string;
    delai_livraison?: number;
};

export function SparePartsTable() {
    const api = useGmaoApi();
    const { role } = useUserRole();
    const queryClient = useQueryClient();
    const [search, setSearch] = useState('');
    const [stockFilter, setStockFilter] = useState<'all' | 'low'>('all');

    // State for Edit Dialog
    const [editingPart, setEditingPart] = useState<SparePart | null>(null);
    const [editDialogOpen, setEditDialogOpenOpen] = useState(false);

    const { data, isLoading } = useQuery({
        queryKey: ['spare-parts'],
        queryFn: () => api.listSpareParts(),
    });

    // Delete Mutation
    const deleteMutation = useMutation({
        mutationFn: (id: number) => api.deleteSparePart(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['spare-parts'] });
            toast.success('Spare part removed from inventory');
        },
        onError: (error: any) => {
            toast.error(`Operation failed: ${error.message}`);
        }
    });

    const baseColumns = useMemo<ColumnDef<SparePart>[]>(() => [
        {
            accessorKey: 'designation',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Designation" />
            ),
            cell: ({ row }) => (
                <div className="flex items-center gap-2">
                    <div className="p-2 rounded-full bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400">
                        <Package className="h-4 w-4" />
                    </div>
                    <div className="flex flex-col">
                        <span className="font-semibold">{row.original.designation}</span>
                        <span className="text-xs text-muted-foreground">{row.original.reference}</span>
                    </div>
                </div>
            )
        },
        {
            accessorKey: 'reference',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Reference" />
            ),
            cell: ({ row }) => (
                <span className="font-mono text-xs">{row.original.reference}</span>
            )
        },
        {
            accessorKey: 'stock_actuel',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Stock" />
            ),
            cell: ({ row }) => {
                const stock = row.original.stock_actuel;
                const threshold = row.original.seuil_alerte;
                const isLow = stock <= threshold;
                return (
                    <div className="flex items-center gap-2">
                        <Badge
                            variant={isLow ? 'destructive' : 'outline'}
                            className={!isLow ? "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400" : ""}
                        >
                            {stock} {row.original.unite}
                        </Badge>
                        {isLow && (
                            <AlertTriangle className="h-4 w-4 text-destructive animate-pulse" />
                        )}
                    </div>
                );
            }
        },
        {
            accessorKey: 'cout_unitaire',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Unit Cost" />
            ),
            cell: ({ row }) => (
                <span className="font-medium">
                    €{row.original.cout_unitaire.toFixed(2)}
                </span>
            )
        },
        {
            accessorKey: 'fournisseur',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Supplier" />
            ),
            cell: ({ row }) => (
                <span className="text-muted-foreground">
                    {row.original.fournisseur || '-'}
                </span>
            )
        },
        {
            id: 'actions',
            cell: ({ row }) => {
                const item = row.original;
                return (
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" className="h-8 w-8 p-0">
                                <span className="sr-only">Open menu</span>
                                <MoreHorizontal className="h-4 w-4" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-[160px]">
                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                            <SupervisorOrAbove>
                                <DropdownMenuItem
                                    onClick={() => {
                                        setEditingPart(item);
                                        setEditDialogOpenOpen(true);
                                    }}
                                    className="flex items-center cursor-pointer"
                                >
                                    <Edit className="mr-2 h-4 w-4" />
                                    Edit Details
                                </DropdownMenuItem>
                            </SupervisorOrAbove>

                            <AdminOnly>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                    onClick={() => {
                                        if (confirm('Are you sure you want to remove this part from inventory?')) {
                                            deleteMutation.mutate(item.id);
                                        }
                                    }}
                                    className="text-destructive flex items-center cursor-pointer"
                                >
                                    <Trash className="mr-2 h-4 w-4" />
                                    Delete
                                </DropdownMenuItem>
                            </AdminOnly>
                        </DropdownMenuContent>
                    </DropdownMenu>
                );
            },
        },
    ], [deleteMutation]);

    const columns = useMemo<ColumnDef<SparePart>[]>(() => {
        // Hide actions for non-management roles (Technician, Viewer)
        if (role !== 'admin' && role !== 'supervisor') {
            return baseColumns.filter(col => col.id !== 'actions');
        }
        return baseColumns;
    }, [role, baseColumns]);

    const filteredData = useMemo(() => {
        if (!data) return [];
        return data.filter(item => {
            const matchesSearch =
                item.designation.toLowerCase().includes(search.toLowerCase()) ||
                item.reference.toLowerCase().includes(search.toLowerCase()) ||
                (item.fournisseur || '').toLowerCase().includes(search.toLowerCase());

            const isLow = item.stock_actuel <= item.seuil_alerte;
            const matchesStock = stockFilter === 'all' || (stockFilter === 'low' && isLow);

            return matchesSearch && matchesStock;
        });
    }, [data, search, stockFilter]);

    if (isLoading) {
        return (
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <div className="h-10 w-[250px] bg-muted animate-pulse rounded-md" />
                    <div className="h-10 w-[150px] bg-muted animate-pulse rounded-md" />
                </div>
                <div className="h-[400px] w-full bg-muted animate-pulse rounded-md" />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="relative w-full sm:max-w-sm">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search spare parts..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="pl-9 bg-background shadow-sm"
                    />
                </div>
                <div className="flex items-center gap-2 w-full sm:w-auto">
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="outline" className="ml-auto flex gap-2 shadow-sm">
                                <Filter className="h-4 w-4" />
                                {stockFilter === 'low' ? "Low Stock Only" : "All Parts"}
                                <ChevronDown className="h-4 w-4 opacity-50" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => setStockFilter('all')}>
                                All Parts
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setStockFilter('low')} className="text-destructive">
                                Low Stock Alert
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </div>

            <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
                <DataTable
                    columns={columns}
                    data={filteredData}
                    pageSize={10}
                />
            </div>

            {editingPart && (
                <SparePartEditDialog
                    sparePart={editingPart}
                    open={editDialogOpen}
                    onOpenChange={setEditDialogOpenOpen}
                />
            )}
        </div>
    );
}
