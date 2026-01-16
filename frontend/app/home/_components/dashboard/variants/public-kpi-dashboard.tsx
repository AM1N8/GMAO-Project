'use client';

import { TrendingUp, Activity, BarChart3 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@kit/ui/card';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

import { KpiSummaryCard, KpiTrendCharts } from '../kpi-components';

export function PublicKpiDashboard({
    fleetSummary,
    chartData
}: any) {
    return (
        <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2">
                <KpiSummaryCard
                    title="Global Activity"
                    value={fleetSummary?.total_interventions || 0}
                    icon={Activity}
                    color="green"
                    subtitle="Interventions across all assets"
                    unit="count"
                />
                <KpiSummaryCard
                    title="System Health"
                    value={fleetSummary?.availability_percentage}
                    unit="%"
                    icon={TrendingUp}
                    color="blue"
                    subtitle="Average uptime percentage"
                />
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                        <BarChart3 className="h-5 w-5" />
                        Availability Trend
                    </CardTitle>
                    <CardDescription>Visual history of system performance</CardDescription>
                </CardHeader>
                <CardContent>
                    <ResponsiveContainer width="100%" height={300}>
                        <AreaChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                            <XAxis dataKey="name" className="text-xs" />
                            <YAxis domain={[0, 100]} className="text-xs" />
                            <Tooltip
                                contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
                            />
                            <Area
                                type="monotone"
                                dataKey="Availability"
                                stroke="#22c55e"
                                fill="#22c55e"
                                fillOpacity={0.1}
                                strokeWidth={2}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>
        </div>
    );
}
