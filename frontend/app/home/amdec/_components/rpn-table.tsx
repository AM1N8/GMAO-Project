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
    Search, Plus, Eye, Calendar, User
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

interface RPNAnalysis {
    id: number;
    failure_mode_id: number;
    rpn_value: number;
    gravity: number;
    occurrence: number;
    detection: number;
    analysis_date: string;
    analyst_name: string;
    action_status: string;
    failure_mode_name?: string;
    equipment_designation?: string;
}

interface RpnTableProps {
    data: RPNAnalysis[];
    onDelete: (id: number) => void;
}

export function RpnTable({ data, onDelete }: RpnTableProps) {
    const [sorting, setSorting] = useState<SortingState>([]);
    const [globalFilter, setGlobalFilter] = useState('');

    const columns = useMemo<ColumnDef<RPNAnalysis>[]>(
        () => [
            {
                accessorKey: 'equipment_designation',
                header: 'Equipment / Mode',
                cell: ({ row }) => (
                    <div className="flex flex-col">
                        <span className="font-medium text-sm">{row.original.failure_mode_name || `Mode ID: ${row.original.failure_mode_id}`}</span>
                        <span className="text-xs text-muted-foreground">{row.original.equipment_designation || 'N/A'}</span>
                    </div>
                )
            },
            {
                accessorKey: 'rpn_value',
                header: 'RPN',
                cell: ({ row }) => {
                    const val = row.original.rpn_value;
                    let color = 'bg-green-100 text-green-800';
                    if (val >= 200) color = 'bg-red-100 text-red-800';
                    else if (val >= 100) color = 'bg-orange-100 text-orange-800';
                    else if (val >= 50) color = 'bg-yellow-100 text-yellow-800';

                    return (
                        <div className="flex items-center gap-2">
                            <Badge className={color}>{val}</Badge>
                            <span className="text-[10px] text-muted-foreground uppercase">(G:{row.original.gravity} O:{row.original.occurrence} D:{row.original.detection})</span>
                        </div>
                    );
                },
            },
            {
                accessorKey: 'analysis_date',
                header: 'Date / Analyst',
                cell: ({ row }) => (
                    <div className="text-xs space-y-1">
                        <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3 text-muted-foreground" />
                            {new Date(row.original.analysis_date).toLocaleDateString()}
                        </div>
                        <div className="flex items-center gap-1">
                            <User className="h-3 w-3 text-muted-foreground" />
                            {row.original.analyst_name || 'Anonymous'}
                        </div>
                    </div>
                ),
            },
            {
                accessorKey: 'action_status',
                header: 'Status',
                cell: ({ row }) => (
                    <Badge variant={row.original.action_status === 'completed' ? 'default' : 'outline'}>
                        {row.original.action_status}
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
                                    <Link href={`/home/amdec/failure-modes/${item.failure_mode_id}`}>
                                        <Eye className="mr-2 h-4 w-4" /> View Mode
                                    </Link>
                                </DropdownMenuItem>
                                <DropdownMenuItem asChild>
                                    <Link href={`/home/amdec/rpn-analysis/${item.id}/edit`}>
                                        <Edit className="mr-2 h-4 w-4" /> Edit Analysis
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
                        placeholder="Search analyses..."
                        value={globalFilter ?? ''}
                        onChange={(e) => setGlobalFilter(e.target.value)}
                        className="pl-8"
                    />
                </div>
                <Link href="/home/amdec/rpn-analysis/new">
                    <Button>
                        <Plus className="h-4 w-4 mr-2" /> New Analysis
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
                                    No RPN analyses found.
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
