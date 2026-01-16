'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ColumnDef } from '@tanstack/react-table';
import {
    MoreHorizontal,
    Search,
    Edit,
    Trash,
    ChevronDown,
    Filter,
    User,
    Mail,
    Banknote
} from 'lucide-react';

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
import { TechnicianEditDialog } from './technician-edit-dialog';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { useUserRole } from '~/lib/hooks/use-user-role';
import { DataTableColumnHeader } from '~/components/data-table-column-header';

type Technician = {
    id: number;
    nom: string;
    prenom: string;
    email: string;
    specialite: string;
    status: 'active' | 'inactive' | 'on_leave';
    taux_horaire: number;
    telephone?: string;
    date_embauche?: string;
    matricule?: string;
};

export function TechniciansTable() {
    const api = useGmaoApi();
    const { role } = useUserRole();
    const queryClient = useQueryClient();
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState<string | null>(null);

    // State for Edit Dialog
    const [editingTechnician, setEditingTechnician] = useState<Technician | null>(null);
    const [editDialogOpen, setEditDialogOpenOpen] = useState(false);

    const { data, isLoading } = useQuery({
        queryKey: ['technicians'],
        queryFn: () => api.listTechnicians(),
    });

    // Delete Mutation (Disable)
    const deleteMutation = useMutation({
        mutationFn: (id: number) => api.deleteTechnician(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['technicians'] });
            toast.success('Technician account disabled');
        },
        onError: (error: any) => {
            toast.error(`Operation failed: ${error.message}`);
        }
    });

    const baseColumns = useMemo<ColumnDef<Technician>[]>(() => [
        {
            accessorKey: 'name',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Technician" />
            ),
            cell: ({ row }) => (
                <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-full bg-secondary flex items-center justify-center text-secondary-foreground">
                        <User className="h-5 w-5" />
                    </div>
                    <div className="flex flex-col">
                        <span className="font-semibold">{row.original.prenom} {row.original.nom}</span>
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Mail className="h-3 w-3" />
                            {row.original.email}
                        </div>
                    </div>
                </div>
            )
        },
        {
            accessorKey: 'specialite',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Specialty" />
            ),
            cell: ({ row }) => (
                <Badge variant="secondary" className="font-medium">
                    {row.original.specialite || 'General Maintenance'}
                </Badge>
            )
        },
        {
            accessorKey: 'status',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Status" />
            ),
            cell: ({ row }) => {
                const status = row.original.status;
                let className = "";

                switch (status) {
                    case 'active':
                        className = "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400";
                        break;
                    case 'on_leave':
                        className = "bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400";
                        break;
                    case 'inactive':
                        className = "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400";
                        break;
                }

                return (
                    <Badge variant="outline" className={className}>
                        {status.replace('_', ' ').charAt(0).toUpperCase() + status.replace('_', ' ').slice(1)}
                    </Badge>
                );
            }
        },
        {
            accessorKey: 'taux_horaire',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Hourly Rate" />
            ),
            cell: ({ row }) => (
                <div className="flex items-center gap-1 font-medium">
                    <Banknote className="h-3 w-3 text-muted-foreground" />
                    €{row.original.taux_horaire?.toFixed(2) || '0.00'}
                </div>
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
                            <DropdownMenuItem
                                onClick={() => {
                                    setEditingTechnician(item);
                                    setEditDialogOpenOpen(true);
                                }}
                                className="flex items-center cursor-pointer"
                            >
                                <Edit className="mr-2 h-4 w-4" />
                                Edit Profile
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                                onClick={() => {
                                    if (confirm('Are you sure you want to disable this technician account?')) {
                                        deleteMutation.mutate(item.id);
                                    }
                                }}
                                className="text-destructive flex items-center cursor-pointer"
                            >
                                <Trash className="mr-2 h-4 w-4" />
                                Disable Account
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                );
            },
        },
    ], [deleteMutation]);

    const columns = useMemo<ColumnDef<Technician>[]>(() => {
        if (role !== 'admin') {
            return baseColumns.filter(col => col.id !== 'actions');
        }
        return baseColumns;
    }, [role, baseColumns]);

    const filteredData = useMemo(() => {
        if (!data) return [];
        return data.filter(item => {
            const fullName = `${item.prenom} ${item.nom}`.toLowerCase();
            const matchesSearch =
                fullName.includes(search.toLowerCase()) ||
                item.email.toLowerCase().includes(search.toLowerCase()) ||
                (item.specialite || '').toLowerCase().includes(search.toLowerCase());

            const matchesStatus = !statusFilter || item.status === statusFilter;

            return matchesSearch && matchesStatus;
        });
    }, [data, search, statusFilter]);

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
                        placeholder="Search technicians..."
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
                                    <span className="capitalize">{statusFilter.replace('_', ' ')}</span>
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
                            <DropdownMenuItem onClick={() => setStatusFilter('on_leave')}>On Leave</DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setStatusFilter('inactive')}>Inactive</DropdownMenuItem>
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

            {editingTechnician && (
                <TechnicianEditDialog
                    technician={editingTechnician}
                    open={editDialogOpen}
                    onOpenChange={setEditDialogOpenOpen}
                />
            )}
        </div>
    );
}
