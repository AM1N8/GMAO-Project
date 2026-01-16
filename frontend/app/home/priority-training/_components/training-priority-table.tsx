'use client';

import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@kit/ui/table';
import { Badge } from '@kit/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@kit/ui/card';
import { Loader2, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@kit/ui/tooltip';

type PriorityItem = {
    type_panne: string;
    training_priority_score: number;
    priority_level: string;
    rpn_average: number;
    frequency: number;
    difficulty_rate: number;
    safety_factor: number;
    recommended_training: string;
    problematic_interventions: number;
    total_interventions: number;
};

interface TrainingPriorityTableProps {
    data: PriorityItem[] | undefined;
    isLoading: boolean;
}

export function TrainingPriorityTable({ data, isLoading }: TrainingPriorityTableProps) {
    if (isLoading) {
        return (
            <Card>
                <CardContent className="flex items-center justify-center h-[350px]">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </CardContent>
            </Card>
        );
    }

    if (!data || data.length === 0) {
        return null;
    }

    // Colors by priority level
    const getBadgeVariant = (level: string): "default" | "secondary" | "destructive" | "outline" => {
        switch (level) {
            case 'HIGH': return 'destructive';
            case 'MEDIUM': return 'secondary'; // Orange-ish usually handled by custom class
            case 'LOW': return 'outline';
            default: return 'outline';
        }
    };

    const getDifficultyColor = (rate: number) => {
        if (rate > 0.5) return 'text-red-500 font-bold';
        if (rate > 0.2) return 'text-amber-500 font-medium';
        return 'text-green-500';
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>Detailed Analysis</CardTitle>
                <CardDescription>
                    Breakdown of metrics contributing to the priority score.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Failure Type</TableHead>
                            <TableHead className="text-right">Priority</TableHead>
                            <TableHead className="text-right">TPS</TableHead>
                            <TableHead className="text-right">RPN (Avg)</TableHead>
                            <TableHead className="text-right">Freq.</TableHead>
                            <TableHead className="text-right">Difficulty</TableHead>
                            <TableHead className="text-right">Safety</TableHead>
                            <TableHead>Recommended Training</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {data.map((item) => (
                            <TableRow key={item.type_panne}>
                                <TableCell className="font-medium">
                                    {item.type_panne}
                                </TableCell>
                                <TableCell className="text-right">
                                    <Badge variant={getBadgeVariant(item.priority_level)}>
                                        {item.priority_level}
                                    </Badge>
                                </TableCell>
                                <TableCell className="text-right font-bold">
                                    {item.training_priority_score.toFixed(0)}
                                </TableCell>
                                <TableCell className="text-right">
                                    {item.rpn_average.toFixed(1)}
                                </TableCell>
                                <TableCell className="text-right">
                                    {item.frequency}
                                </TableCell>
                                <TableCell className="text-right">
                                    <TooltipProvider>
                                        <Tooltip>
                                            <TooltipTrigger>
                                                <span className={getDifficultyColor(item.difficulty_rate)}>
                                                    {(item.difficulty_rate * 100).toFixed(0)}%
                                                </span>
                                            </TooltipTrigger>
                                            <TooltipContent>
                                                <p>{item.problematic_interventions} issues / {item.total_interventions} total</p>
                                            </TooltipContent>
                                        </Tooltip>
                                    </TooltipProvider>
                                </TableCell>
                                <TableCell className="text-right">
                                    {item.safety_factor}x
                                </TableCell>
                                <TableCell>
                                    <span className="text-sm text-muted-foreground">
                                        {item.recommended_training}
                                    </span>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    );
}
