'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@kit/ui/card';
import { Button } from '@kit/ui/button';
import { Input } from '@kit/ui/input';
import { Label } from '@kit/ui/label';
import { Badge } from '@kit/ui/badge';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import {
    Filter, RefreshCw, Calendar, BookOpen, AlertCircle,
    CheckCircle2, TrendingUp, AlertTriangle
} from 'lucide-react';
import { TrainingPriorityChart } from './training-priority-chart';
import { TrainingPriorityTable } from './training-priority-table';
import { toast } from 'sonner';

// Helper to get date strings
const getDefaultDates = () => {
    const end = new Date();
    const start = new Date();
    start.setMonth(start.getMonth() - 12);
    return {
        start: start.toISOString().split('T')[0],
        end: end.toISOString().split('T')[0]
    };
};

export function TrainingPriorityDashboard() {
    const api = useGmaoApi();
    const defaultDates = getDefaultDates();

    // Filter state
    const [startDate, setStartDate] = useState(defaultDates.start);
    const [endDate, setEndDate] = useState(defaultDates.end);
    const [appliedFilters, setAppliedFilters] = useState({
        start: defaultDates.start,
        end: defaultDates.end,
    });

    // Queries
    const { data: priorities, isLoading: isLoadingPriorities } = useQuery({
        queryKey: ['formation-priorities', appliedFilters.start, appliedFilters.end],
        queryFn: () => api.getFormationPriorities({
            start_date: appliedFilters.start,
            end_date: appliedFilters.end,
        }),
    });

    const { data: normalized, isLoading: isLoadingNormalized } = useQuery({
        queryKey: ['formation-priorities-normalized', appliedFilters.start, appliedFilters.end],
        queryFn: () => api.getFormationPrioritiesNormalized({
            start_date: appliedFilters.start,
            end_date: appliedFilters.end,
        }),
    });

    // Handlers
    const handleApplyFilter = () => {
        setAppliedFilters({
            start: startDate,
            end: endDate,
        });
    };

    const handleResetFilters = () => {
        setStartDate(defaultDates.start);
        setEndDate(defaultDates.end);
        setAppliedFilters({ start: defaultDates.start, end: defaultDates.end });
    };

    return (
        <div className="space-y-6">
            {/* Filter Panel */}
            <Card className="bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
                <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Filter className="h-5 w-5 text-primary" />
                            <CardTitle className="text-lg">Analysis Period</CardTitle>
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-4 md:grid-cols-4 items-end">
                        <div className="space-y-2">
                            <Label htmlFor="start-date">Start Date</Label>
                            <Input
                                id="start-date"
                                type="date"
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="end-date">End Date</Label>
                            <Input
                                id="end-date"
                                type="date"
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                            />
                        </div>
                        <div className="flex gap-2">
                            <Button onClick={handleApplyFilter} className="flex-1">
                                Analyze
                            </Button>
                            <Button variant="outline" size="icon" onClick={handleResetFilters} title="Reset">
                                <RefreshCw className="h-4 w-4" />
                            </Button>
                        </div>

                        {/* Summary Badges */}
                        <div className="flex flex-col gap-2 justify-center">
                            <Badge variant="secondary" className="w-fit">
                                <Calendar className="h-3 w-3 mr-1" />
                                {appliedFilters.start} → {appliedFilters.end}
                            </Badge>
                            <Badge variant="outline" className="w-fit">
                                {priorities?.total_panne_types || 0} Dimensions Analyzed
                            </Badge>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Top Level Stats */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Critical Training Needs</CardTitle>
                        <AlertTriangle className="h-4 w-4 text-red-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{priorities?.high_priority_count || 0}</div>
                        <p className="text-xs text-muted-foreground">High Priority (Top 10%)</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Moderate Needs</CardTitle>
                        <AlertCircle className="h-4 w-4 text-amber-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{priorities?.medium_priority_count || 0}</div>
                        <p className="text-xs text-muted-foreground">Medium Priority (Above Avg)</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Well Controlled</CardTitle>
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{priorities?.low_priority_count || 0}</div>
                        <p className="text-xs text-muted-foreground">Low Priority (Stable)</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Avg TPS Score</CardTitle>
                        <TrendingUp className="h-4 w-4 text-blue-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {priorities?.priorities.length
                                ? (priorities.priorities.reduce((acc: number, curr: any) => acc + curr.training_priority_score, 0) / priorities.priorities.length).toFixed(0)
                                : 0
                            }
                        </div>
                        <p className="text-xs text-muted-foreground">Global Training Urgency</p>
                    </CardContent>
                </Card>
            </div>

            {/* Chart Section */}
            <div className="grid gap-6 lg:grid-cols-3">
                <div className="lg:col-span-1">
                    <Card className="h-full bg-primary/5 border-primary/20">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <BookOpen className="h-5 w-5 text-primary" />
                                Top Recommendation
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {priorities?.priorities?.[0] ? (
                                <div className="space-y-4">
                                    <div className="text-lg font-semibold">
                                        {priorities.priorities[0].recommended_training}
                                    </div>
                                    <div className="text-sm text-muted-foreground">
                                        Addressed to solve issues in <span className="font-bold text-foreground">{priorities.priorities[0].type_panne}</span>.
                                    </div>
                                    <div className="grid grid-cols-2 gap-2 text-sm">
                                        <div className="p-2 bg-background rounded border">
                                            <div className="text-xs text-muted-foreground">Frequency</div>
                                            <div className="font-mono font-bold">{priorities.priorities[0].frequency}</div>
                                        </div>
                                        <div className="p-2 bg-background rounded border">
                                            <div className="text-xs text-muted-foreground">Difficulty</div>
                                            <div className="font-mono font-bold">{(priorities.priorities[0].difficulty_rate * 100).toFixed(0)}%</div>
                                        </div>
                                    </div>
                                    <Button
                                        className="w-full"
                                        onClick={() => {
                                            toast.success('Training Request Sent', {
                                                description: `Request for ${priorities.priorities[0].recommended_training} forwarded to HR.`
                                            });
                                        }}
                                    >
                                        Schedule Training
                                    </Button>
                                </div>
                            ) : (
                                <p className="text-muted-foreground">No recommendations available.</p>
                            )}
                        </CardContent>
                    </Card>
                </div>
                <div className="lg:col-span-2">
                    <TrainingPriorityChart
                        data={normalized?.priorities}
                        isLoading={isLoadingNormalized}
                    />
                </div>
            </div>

            {/* Detailed Table */}
            <TrainingPriorityTable
                data={priorities?.priorities}
                isLoading={isLoadingPriorities}
            />
        </div>
    );
}
