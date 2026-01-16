'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
    MoreHorizontal,
    Search,
    Settings2,
    Edit,
    Trash,
    ChevronDown,
    Filter
} from 'lucide-react';
import Link from 'next/link';

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
import { EquipmentEditDialog } from './equipment-edit-dialog';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { useUserRole } from '~/lib/hooks/use-user-role';
import { DataTableColumnHeader } from '~/components/data-table-column-header';

type Equipment = {
    id: number;
    designation: string;
    type: string;
    location: string;
    status: 'active' | 'inactive' | 'maintenance' | 'decommissioned';
    manufacturer: string;
    model: string;
    acquisition_date?: string;
    serial_number?: string;
};

export function EquipmentTable() {
    const api = useGmaoApi();
    const { role } = useUserRole();
    const queryClient = useQueryClient();
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState<string | null>(null);

    // State for Edit Dialog
    const [editingEquipment, setEditingEquipment] = useState<Equipment | null>(null);
    const [editDialogOpen, setEditDialogOpenOpen] = useState(false);

    const { data: equipment, isLoading } = useQuery({
        queryKey: ['equipment-list'],
        queryFn: () => api.listEquipment(),
    });

    // Delete Mutation (Decommission)
    const deleteMutation = useMutation({
        mutationFn: (id: number) => api.deleteEquipment(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['equipment-list'] });
            toast.success('Equipment decommissioned successfully');
        },
        onError: (error: any) => {
            toast.error(`Operation failed: ${error.message}`);
        }
    });

    const baseColumns = useMemo<ColumnDef<Equipment>[]>(() => [
        {
            accessorKey: 'designation',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Designation" />
            ),
            cell: ({ row }) => {
                const canViewHistory = role === 'admin' || role === 'supervisor';
                return (
                    <div className="flex flex-col">
                        {canViewHistory ? (
                            <Link
                                href={`/home/equipment/${row.original.id}`}
                                className="font-semibold hover:underline text-primary"
                            >
                                {row.original.designation}
                            </Link>
                        ) : (
                            <span className="font-semibold">
                                {row.original.designation}
                            </span>
                        )}
                        <span className="text-xs text-muted-foreground">{row.original.model}</span>
                    </div>
                );
            },
        },
        {
            accessorKey: 'type',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Type" />
            ),
            cell: ({ row }) => <Badge variant="outline">{row.original.type}</Badge>
        },
        {
            accessorKey: 'location',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Location" />
            ),
        },
        {
            accessorKey: 'status',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Status" />
            ),
            cell: ({ row }) => {
                const status = row.original.status;

                const statusConfig = {
                    active: {
                        dotClass: "status-dot-active",
                        badgeClass: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20",
                        label: "Active"
                    },
                    maintenance: {
                        dotClass: "status-dot-warning",
                        badgeClass: "bg-amber-500/10 text-amber-600 border-amber-500/20",
                        label: "Maintenance"
                    },
                    inactive: {
                        dotClass: "",
                        badgeClass: "bg-gray-500/10 text-gray-600 border-gray-500/20",
                        label: "Inactive"
                    },
                    decommissioned: {
                        dotClass: "status-dot-error",
                        badgeClass: "bg-rose-500/10 text-rose-600 border-rose-500/20",
                        label: "Decommissioned"
                    }
                };

                const config = statusConfig[status] || statusConfig.inactive;

                return (
                    <div className="flex items-center gap-2">
                        <span className={`status-dot ${config.dotClass}`} />
                        <Badge variant="outline" className={config.badgeClass}>
                            {config.label}
                        </Badge>
                    </div>
                );
            },
        },
        {
            accessorKey: 'manufacturer',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Manufacturer" />
            ),
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
                            <DropdownMenuItem
                                onClick={() => {
                                    setEditingEquipment(item);
                                    setEditDialogOpenOpen(true);
                                }}
                                className="flex items-center cursor-pointer"
                            >
                                <Edit className="mr-2 h-4 w-4" />
                                Edit Details
                            </DropdownMenuItem>
                            <DropdownMenuItem asChild>
                                <Link href={`/home/equipment/${item.id}`} className="flex items-center">
                                    <Settings2 className="mr-2 h-4 w-4" />
                                    View History
                                </Link>
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                                onClick={() => {
                                    if (confirm('Are you sure you want to decommission this equipment?')) {
                                        deleteMutation.mutate(item.id);
                                    }
                                }}
                                className="text-destructive flex items-center cursor-pointer"
                            >
                                <Trash className="mr-2 h-4 w-4" />
                                Decommission
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                );
            },
        },
    ], [deleteMutation]);

    const columns = useMemo<ColumnDef<Equipment>[]>(() => {
        if (role !== 'admin' && role !== 'supervisor') {
            return baseColumns.filter(col => col.id !== 'actions');
        }
        return baseColumns;
    }, [role, baseColumns]);

    const filteredData = useMemo(() => {
        if (!equipment) return [];
        return equipment.filter(item => {
            const matchesSearch =
                item.designation.toLowerCase().includes(search.toLowerCase()) ||
                item.manufacturer.toLowerCase().includes(search.toLowerCase()) ||
                item.model.toLowerCase().includes(search.toLowerCase());

            const matchesStatus = !statusFilter || item.status === statusFilter;

            return matchesSearch && matchesStatus;
        });
    }, [equipment, search, statusFilter]);

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
                        placeholder="Search equipment..."
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
                                {statusFilter ? (
                                    <span className="capitalize">{statusFilter}</span>
                                ) : (
                                    "Filter Status"
                                )}
                                <ChevronDown className="h-4 w-4 opacity-50" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => setStatusFilter(null)}>
                                All Statuses
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onClick={() => setStatusFilter('active')}>Active</DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setStatusFilter('maintenance')}>Maintenance</DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setStatusFilter('inactive')}>Inactive</DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setStatusFilter('decommissioned')}>Decommissioned</DropdownMenuItem>
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

            {editingEquipment && (
                <EquipmentEditDialog
                    equipment={editingEquipment}
                    open={editDialogOpen}
                    onOpenChange={setEditDialogOpenOpen}
                />
            )}
        </div>
    );
}
