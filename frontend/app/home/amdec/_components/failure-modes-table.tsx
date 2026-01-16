'use client';

import { useMemo } from 'react';
import {
    ColumnDef,
    flexRender,
    getCoreRowModel,
    useReactTable,
    getPaginationRowModel,
    getSortedRowModel,
    SortingState,
} from '@tanstack/react-table';
import { useState } from 'react';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@kit/ui/table';
import { Button } from '@kit/ui/button';
import { Input } from '@kit/ui/input';
import { Badge } from '@kit/ui/badge';
import {
    Edit, Trash2, MoreHorizontal, ChevronLeft, ChevronRight,
    Search, Plus, Eye, History
} from 'lucide-react';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@kit/ui/dropdown-menu';
import Link from 'next/link';

interface FailureMode {
    id: number;
    equipment_id: number;
    mode_name: string;
    description: string;
    failure_cause: string;
    failure_effect: string;
    detection_method: string;
    is_active: boolean;
    latest_rpn?: number;
    equipment?: {
        designation: string;
    };
}

interface FailureModesTableProps {
    data: FailureMode[];
    onDelete: (id: number) => void;
}

export function FailureModesTable({ data, onDelete }: FailureModesTableProps) {
    const [sorting, setSorting] = useState<SortingState>([]);
    const [globalFilter, setGlobalFilter] = useState('');

    const columns = useMemo<ColumnDef<FailureMode>[]>(
        () => [
            {
                accessorKey: 'equipment.designation',
                header: 'Equipment',
                cell: ({ row }) => row.original.equipment?.designation || `ID: ${row.original.equipment_id}`,
            },
            {
                accessorKey: 'mode_name',
                header: 'Failure Mode',
                cell: ({ row }) => (
                    <div className="flex flex-col">
                        <span className="font-medium">{row.original.mode_name}</span>
                        <span className="text-xs text-muted-foreground line-clamp-1">{row.original.description}</span>
                    </div>
                ),
            },
            {
                accessorKey: 'failure_cause',
                header: 'Cause / Effect',
                cell: ({ row }) => (
                    <div className="text-xs">
                        <p><span className="text-muted-foreground">C:</span> {row.original.failure_cause || '-'}</p>
                        <p><span className="text-muted-foreground">E:</span> {row.original.failure_effect || '-'}</p>
                    </div>
                ),
            },
            {
                accessorKey: 'latest_rpn',
                header: 'Latest RPN',
                cell: ({ row }) => {
                    const rpn = row.original.latest_rpn;
                    if (!rpn) return <span className="text-xs text-muted-foreground">No analysis</span>;

                    let color = 'bg-green-100 text-green-800';
                    if (rpn >= 200) color = 'bg-red-100 text-red-800';
                    else if (rpn >= 100) color = 'bg-orange-100 text-orange-800';
                    else if (rpn >= 50) color = 'bg-yellow-100 text-yellow-800';

                    return <Badge className={color}>{rpn}</Badge>;
                },
            },
            {
                accessorKey: 'is_active',
                header: 'Status',
                cell: ({ row }) => (
                    <Badge variant={row.original.is_active ? 'default' : 'secondary'}>
                        {row.original.is_active ? 'Active' : 'Inactive'}
                    </Badge>
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
                                    <MoreHorizontal className="h-4 w-4" />
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                                <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                <DropdownMenuItem asChild>
                                    <Link href={`/home/amdec/failure-modes/${item.id}`}>
                                        <Eye className="mr-2 h-4 w-4" /> View Details
                                    </Link>
                                </DropdownMenuItem>
                                <DropdownMenuItem asChild>
                                    <Link href={`/home/amdec/failure-modes/${item.id}/edit`}>
                                        <Edit className="mr-2 h-4 w-4" /> Edit
                                    </Link>
                                </DropdownMenuItem>
                                <DropdownMenuItem asChild>
                                    <Link href={`/home/amdec/rpn-analysis/new?failure_mode_id=${item.id}`}>
                                        <History className="mr-2 h-4 w-4" /> New RPN Analysis
                                    </Link>
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                    className="text-destructive"
                                    onClick={() => onDelete(item.id)}
                                >
                                    <Trash2 className="mr-2 h-4 w-4" /> Delete
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    );
                },
            },
        ],
        [onDelete]
    );

    const table = useReactTable({
        data,
        columns,
        getCoreRowModel: getCoreRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        getSortedRowModel: getSortedRowModel(),
        onSortingChange: setSorting,
        state: {
            sorting,
            globalFilter,
        },
        onGlobalFilterChange: setGlobalFilter,
    });

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between gap-4">
                <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search failure modes..."
                        value={globalFilter ?? ''}
                        onChange={(e) => setGlobalFilter(e.target.value)}
                        className="pl-8"
                    />
                </div>
                <Link href="/home/amdec/failure-modes/new">
                    <Button>
                        <Plus className="h-4 w-4 mr-2" /> Add Failure Mode
                    </Button>
                </Link>
            </div>

            <div className="rounded-md border">
                <Table>
                    <TableHeader>
                        {table.getHeaderGroups().map((headerGroup) => (
                            <TableRow key={headerGroup.id}>
                                {headerGroup.headers.map((header) => (
                                    <TableHead key={header.id}>
                                        {header.isPlaceholder
                                            ? null
                                            : flexRender(
                                                header.column.columnDef.header,
                                                header.getContext()
                                            )}
                                    </TableHead>
                                ))}
                            </TableRow>
                        ))}
                    </TableHeader>
                    <TableBody>
                        {table.getRowModel().rows?.length ? (
                            table.getRowModel().rows.map((row) => (
                                <TableRow key={row.id}>
                                    {row.getVisibleCells().map((cell) => (
                                        <TableCell key={cell.id}>
                                            {flexRender(
                                                cell.column.columnDef.cell,
                                                cell.getContext()
                                            )}
                                        </TableCell>
                                    ))}
                                </TableRow>
                            ))
                        ) : (
                            <TableRow>
                                <TableCell
                                    colSpan={columns.length}
                                    className="h-24 text-center"
                                >
                                    No failure modes found.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>

            <div className="flex items-center justify-end space-x-2">
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => table.previousPage()}
                    disabled={!table.getCanPreviousPage()}
                >
                    <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => table.nextPage()}
                    disabled={!table.getCanNextPage()}
                >
                    <ChevronRight className="h-4 w-4" />
                </Button>
            </div>
        </div>
    );
}
