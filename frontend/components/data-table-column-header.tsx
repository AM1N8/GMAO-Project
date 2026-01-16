"use client"

import { Column, Table } from "@tanstack/react-table"
import { ArrowDown, ArrowUp, ChevronsUpDown, EyeOff } from "lucide-react"

import { cn } from "@kit/ui/utils"
import { Button } from "@kit/ui/button"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@kit/ui/dropdown-menu"
import { useMemo } from "react"

interface DataTableColumnHeaderProps<TData, TValue>
    extends React.HTMLAttributes<HTMLDivElement> {
    column: Column<TData, TValue>
    table: Table<TData>
    title: string
}

export function DataTableColumnHeader<TData, TValue>({
    column,
    table,
    title,
    className,
}: DataTableColumnHeaderProps<TData, TValue>) {
    if (!column.getCanSort()) {
        return <div className={cn(className)}>{title}</div>
    }

    // Calculate distribution for mini-graph
    const distribution = useMemo(() => {
        // Get all values from the core model (unfiltered, using full dataset potentially)
        // We access table.getCoreRowModel() via the passed table instance
        const rows = table.getCoreRowModel().rows;
        // Safely get value
        const values = rows.map(row => row.getValue(column.id));

        // Count frequencies
        const counts: Record<string, number> = {};
        let maxCount = 0;

        values.forEach(val => {
            const key = String(val ?? 'null');
            counts[key] = (counts[key] || 0) + 1;
            maxCount = Math.max(maxCount, counts[key]);
        });

        // Prepare chart bars (limit to top 15 categories)
        let keys = Object.keys(counts);

        if (keys.length > 20) {
            keys = keys.sort((a, b) => counts[b] - counts[a]).slice(0, 15);
        } else {
            keys = keys.sort();
        }

        return keys.map(key => ({
            key,
            count: counts[key] ?? 0,
            height: maxCount > 0 ? ((counts[key] ?? 0) / maxCount) * 100 : 0
        }));
    }, [column, table]);

    return (
        <div className={cn("flex flex-col space-y-1", className)}>
            <div className="flex items-center space-x-2">
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="-ml-3 h-8 data-[state=open]:bg-accent"
                        >
                            <span>{title}</span>
                            {column.getIsSorted() === "desc" ? (
                                <ArrowDown className="ml-2 h-4 w-4" />
                            ) : column.getIsSorted() === "asc" ? (
                                <ArrowUp className="ml-2 h-4 w-4" />
                            ) : (
                                <ChevronsUpDown className="ml-2 h-4 w-4" />
                            )}
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start">
                        <DropdownMenuItem onClick={() => column.toggleSorting(false)}>
                            <ArrowUp className="mr-2 h-3.5 w-3.5 text-muted-foreground/70" />
                            Asc
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => column.toggleSorting(true)}>
                            <ArrowDown className="mr-2 h-3.5 w-3.5 text-muted-foreground/70" />
                            Desc
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => column.toggleVisibility(false)}>
                            <EyeOff className="mr-2 h-3.5 w-3.5 text-muted-foreground/70" />
                            Hide
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>

            {/* Mini Graph (Sparkline/Bar) */}
            {distribution.length > 1 && (
                <div className="flex items-end gap-[1px] h-4 w-full max-w-[100px] opacity-50 hover:opacity-100 transition-opacity" title="Data Distribution">
                    {distribution.map((d, i) => (
                        <div
                            key={i}
                            className="bg-primary/50 w-1 rounded-t-[1px]"
                            style={{ height: `${Math.max(15, d.height)}%` }}
                            title={`${d.key}: ${d.count}`}
                        />
                    ))}
                </div>
            )}
        </div>
    )
}
