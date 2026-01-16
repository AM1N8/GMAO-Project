'use client';

import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell
} from 'recharts';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@kit/ui/card';
import { Loader2, TrendingUp } from 'lucide-react';

type PriorityItem = {
    type_panne: string;
    normalized_score: number;
    training_priority_score: number;
    priority_level: string;
};

interface TrainingPriorityChartProps {
    data: PriorityItem[] | undefined;
    isLoading: boolean;
}

export function TrainingPriorityChart({ data, isLoading }: TrainingPriorityChartProps) {
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
        return (
            <Card>
                <CardContent className="flex flex-col items-center justify-center h-[350px] text-muted-foreground">
                    <TrendingUp className="h-12 w-12 mb-4 opacity-20" />
                    <p>No data available for the selected period</p>
                </CardContent>
            </Card>
        );
    }

    // Colors by priority level
    const getBarColor = (level: string) => {
        switch (level) {
            case 'HIGH': return '#ef4444'; // Red-500
            case 'MEDIUM': return '#f59e0b'; // Amber-500
            case 'LOW': return '#22c55e'; // Green-500
            default: return '#3b82f6'; // Blue-500
        }
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>Training Priority Ranking (Normalized)</CardTitle>
                <CardDescription>
                    Visual comparison of training needs based on TPS (0-100 scale)
                </CardDescription>
            </CardHeader>
            <CardContent>
                <ResponsiveContainer width="100%" height={350}>
                    <BarChart
                        data={data}
                        layout="vertical"
                        margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                    >
                        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                        <XAxis type="number" domain={[0, 100]} hide />
                        <YAxis
                            dataKey="type_panne"
                            type="category"
                            width={120}
                            tick={{ fontSize: 12 }}
                        />
                        <Tooltip
                            cursor={{ fill: 'transparent' }}
                            content={({ active, payload, label }) => {
                                if (active && payload && payload.length && payload[0]) {
                                    const data = payload[0].payload;
                                    return (
                                        <div className="bg-background border rounded-lg p-3 shadow-lg text-sm">
                                            <div className="font-bold mb-1">{label}</div>
                                            <div className="flex flex-col gap-1">
                                                <span className="text-muted-foreground">
                                                    Normalized Score: <span className="text-foreground font-medium">{data.normalized_score.toFixed(1)}</span>
                                                </span>
                                                <span className="text-muted-foreground">
                                                    Raw TPS: <span className="text-foreground font-medium">{data.training_priority_score.toFixed(0)}</span>
                                                </span>
                                                <span className="text-muted-foreground">
                                                    Priority: <span style={{ color: getBarColor(data.priority_level) }} className="font-bold">{data.priority_level}</span>
                                                </span>
                                            </div>
                                        </div>
                                    );
                                }
                                return null;
                            }}
                        />
                        <Bar dataKey="normalized_score" radius={[0, 4, 4, 0]}>
                            {data.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={getBarColor(entry.priority_level)} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
}
