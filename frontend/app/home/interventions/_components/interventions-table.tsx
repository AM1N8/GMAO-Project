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
    Calendar,
    Wrench
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
import { InterventionEditDialog } from './intervention-edit-dialog';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { DataTableColumnHeader } from '~/components/data-table-column-header';
import { AdminOnly, TechnicianOrAbove, SupervisorOrAbove } from '~/components/auth/role-guard';
import { useUserRole } from '~/lib/hooks/use-user-role';

type Intervention = {
    id: number;
    type_panne: string;
    resume_intervention: string;
    status: 'open' | 'in_progress' | 'completed' | 'closed' | 'cancelled';
    equipment_id: number;
    date_intervention: string;
    cause?: string;
    resultat?: string;
    duree_arret?: number;
    cout_materiel?: number;
    nombre_heures_mo?: number;
};

export function InterventionsTable() {
    const api = useGmaoApi();
    const { role } = useUserRole();
    const queryClient = useQueryClient();
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState<string | null>(null);

    // State for Edit Dialog
    const [editingIntervention, setEditingIntervention] = useState<Intervention | null>(null);
    const [editDialogOpen, setEditDialogOpenOpen] = useState(false);

    const { data: interventions, isLoading } = useQuery({
        queryKey: ['interventions'],
        queryFn: () => api.listInterventions(),
    });

    // Delete Mutation
    const deleteMutation = useMutation({
        mutationFn: (id: number) => api.deleteIntervention(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['interventions'] });
            toast.success('Intervention deleted successfully');
        },
        onError: (error: any) => {
            toast.error(`Delete failed: ${error.message}`);
        }
    });

    const baseColumns = useMemo<ColumnDef<Intervention>[]>(() => [
        {
            accessorKey: 'type_panne',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Type" />
            ),
            cell: ({ row }) => (
                <div className="flex items-center gap-2">
                    <div className="p-2 rounded-full bg-primary/10 text-primary">
                        <Wrench className="h-4 w-4" />
                    </div>
                    <span className="font-semibold">{row.original.type_panne || 'General Maintenance'}</span>
                </div>
            )
        },
        {
            accessorKey: 'resume_intervention',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Summary" />
            ),
            cell: ({ row }) => (
                <span className="text-muted-foreground truncate max-w-[300px] block" title={row.original.resume_intervention}>
                    {row.original.resume_intervention || '-'}
                </span>
            )
        },
        {
            accessorKey: 'status',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Status" />
            ),
            cell: ({ row }) => {
                const status = row.original.status || 'open';

                const statusConfig: Record<string, { dotClass: string; badgeClass: string; label: string }> = {
                    completed: {
                        dotClass: "status-dot-active",
                        badgeClass: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20",
                        label: "Completed"
                    },
                    closed: {
                        dotClass: "status-dot-active",
                        badgeClass: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20",
                        label: "Closed"
                    },
                    in_progress: {
                        dotClass: "status-dot-warning",
                        badgeClass: "bg-blue-500/10 text-blue-600 border-blue-500/20",
                        label: "In Progress"
                    },
                    cancelled: {
                        dotClass: "status-dot-error",
                        badgeClass: "bg-rose-500/10 text-rose-600 border-rose-500/20",
                        label: "Cancelled"
                    },
                    open: {
                        dotClass: "",
                        badgeClass: "bg-gray-500/10 text-gray-600 border-gray-500/20",
                        label: "Open"
                    }
                };

                const config = statusConfig[status] || statusConfig.open!;

                return (
                    <div className="flex items-center gap-2">
                        <span className={`status-dot ${config.dotClass}`} />
                        <Badge variant="outline" className={config.badgeClass}>
                            {config.label}
                        </Badge>
                    </div>
                );
            }
        },
        {
            accessorKey: 'date_intervention',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Date" />
            ),
            cell: ({ row }) => {
                const dateStr = row.original.date_intervention;
                if (!dateStr) return <span className="text-muted-foreground">N/A</span>;
                return (
                    <div className="flex items-center gap-2 text-sm">
                        <Calendar className="h-3 w-3 text-muted-foreground" />
                        {new Date(dateStr).toLocaleDateString()}
                    </div>
                );
            }
        },
        {
            accessorKey: 'duree_arret',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Downtime (h)" />
            ),
            cell: ({ row }) => (
                <div className="font-medium">
                    {row.original.duree_arret ? `${row.original.duree_arret} h` : '-'}
                </div>
            )
        },
        {
            accessorKey: 'cout_materiel',
            header: ({ column, table }) => (
                <DataTableColumnHeader column={column} table={table} title="Cost (€)" />
            ),
            cell: ({ row }) => (
                <div className="font-medium">
                    {row.original.cout_materiel ? `€${row.original.cout_materiel.toFixed(2)}` : '-'}
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
                            <SupervisorOrAbove>
                                <DropdownMenuItem
                                    onClick={() => {
                                        setEditingIntervention(item);
                                        setEditDialogOpenOpen(true);
                                    }}
                                    className="flex items-center cursor-pointer"
                                >
                                    <Edit className="mr-2 h-4 w-4" />
                                    Edit Report
                                </DropdownMenuItem>
                            </SupervisorOrAbove>

                            <AdminOnly>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                    onClick={() => {
                                        if (confirm('Are you sure you want to delete this intervention?')) {
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

    const columns = useMemo<ColumnDef<Intervention>[]>(() => {
        // Viewers should not see actions at all
        if (role === 'viewer') {
            return baseColumns.filter(col => col.id !== 'actions');
        }
        return baseColumns;
    }, [role, baseColumns]);

    const filteredData = useMemo(() => {
        if (!interventions) return [];
        return interventions.filter(item => {
            const matchesSearch =
                (item.type_panne || '').toLowerCase().includes(search.toLowerCase()) ||
                (item.resume_intervention || '').toLowerCase().includes(search.toLowerCase());

            const matchesStatus = !statusFilter || item.status === statusFilter;

            return matchesSearch && matchesStatus;
        });
    }, [interventions, search, statusFilter]);

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
                        placeholder="Search interventions..."
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
                            <DropdownMenuItem onClick={() => setStatusFilter('open')}>Open</DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setStatusFilter('in_progress')}>In Progress</DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setStatusFilter('completed')}>Completed</DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setStatusFilter('closed')}>Closed</DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setStatusFilter('cancelled')}>Cancelled</DropdownMenuItem>
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

            {editingIntervention && (
                <InterventionEditDialog
                    intervention={editingIntervention}
                    open={editDialogOpen}
                    onOpenChange={setEditDialogOpenOpen}
                />
            )}
        </div>
    );
}
