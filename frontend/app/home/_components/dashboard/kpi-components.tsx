'use client';

import {
    LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, Legend, ResponsiveContainer, AreaChart, Area
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@kit/ui/card';
import { Badge } from '@kit/ui/badge';
import { TrendingUp, Clock, AlertTriangle, BarChart3 } from 'lucide-react';

// KPI Card with visual indicator
export function KpiSummaryCard({ title, value, unit, icon: Icon, color, subtitle }: {
    title: string;
    value: number | null;
    unit: string;
    icon: any;
    color: string;
    subtitle: string;
}) {
    const colorClasses: Record<string, { gradient: string; text: string; bg: string }> = {
        green: { gradient: 'from-emerald-500 to-teal-500', text: 'text-emerald-600', bg: 'bg-emerald-500/10' },
        blue: { gradient: 'from-blue-500 to-cyan-500', text: 'text-blue-600', bg: 'bg-blue-500/10' },
        orange: { gradient: 'from-amber-500 to-orange-500', text: 'text-amber-600', bg: 'bg-amber-500/10' },
        red: { gradient: 'from-red-500 to-red-600', text: 'text-red-600', bg: 'bg-red-500/10' },
    };
    const c = colorClasses[color] ?? colorClasses['blue']!;

    return (
        <Card className={`card-hover relative overflow-hidden group`}>
            <div className={`absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b ${c.gradient}`} />
            <CardHeader className="pb-2 pl-5">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-base font-semibold flex items-center gap-2">
                        <div className={`p-2 rounded-lg ${c.bg} transition-transform duration-300 group-hover:scale-110`}>
                            <Icon className={`h-4 w-4 ${c.text}`} />
                        </div>
                        {title}
                    </CardTitle>
                    <Badge variant="secondary" className={c.bg}>{unit}</Badge>
                </div>
            </CardHeader>
            <CardContent className="pl-5">
                <div className={`text-4xl font-bold tracking-tight ${c.text}`}>
                    {typeof value === 'number' ? value.toFixed(1) : 'N/A'}
                </div>
                <p className="text-sm text-muted-foreground mt-2">{subtitle}</p>
            </CardContent>
        </Card>
    );
}

// Trend Charts Component
export function KpiTrendCharts({ chartData }: { chartData: any[] }) {
    return (
        <div className="space-y-6">
            <div className="grid gap-6 lg:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Reliability Metrics Trend</CardTitle>
                        <CardDescription>MTBF (higher is better) vs MTTR (lower is better)</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <ResponsiveContainer width="100%" height={280}>
                            <LineChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                <XAxis dataKey="name" className="text-xs" />
                                <YAxis className="text-xs" />
                                <Tooltip
                                    contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
                                />
                                <Legend />
                                <Line type="monotone" dataKey="MTBF" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
                                <Line type="monotone" dataKey="MTTR" stroke="#0ea5e9" strokeWidth={2} dot={{ r: 3 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Monthly Failure Count</CardTitle>
                        <CardDescription>Number of failures per month</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <ResponsiveContainer width="100%" height={280}>
                            <BarChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                <XAxis dataKey="name" className="text-xs" />
                                <YAxis className="text-xs" />
                                <Tooltip
                                    contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
                                />
                                <Bar dataKey="Failures" fill="#ef4444" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Availability Over Time</CardTitle>
                    <CardDescription>Equipment uptime percentage trend</CardDescription>
                </CardHeader>
                <CardContent>
                    <ResponsiveContainer width="100%" height={220}>
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
                                fillOpacity={0.2}
                                strokeWidth={2}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>
        </div>
    );
}

// Cost Analysis Component
export function CostAnalysisSection({ costData, fleetSummary }: { costData: any, fleetSummary?: any }) {
    if (!costData) return null;

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                    <TrendingUp className="h-5 w-5" />
                    Cost Analysis
                </CardTitle>
                <CardDescription>Maintenance cost breakdown and distribution</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="grid lg:grid-cols-2 gap-6">
                    <div className="space-y-4">
                        <div className="p-6 bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20 rounded-xl">
                            <div className="flex items-center justify-between">
                                <div>
                                    <div className="text-sm font-medium text-muted-foreground">Total Maintenance Cost</div>
                                    <div className="text-4xl font-bold text-primary mt-1">
                                        €{(costData.total_cost || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })}
                                    </div>
                                </div>
                                <div className="h-16 w-16 rounded-full bg-primary/20 flex items-center justify-center">
                                    <TrendingUp className="h-8 w-8 text-primary" />
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="p-4 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg">
                                <div className="flex items-center gap-2 mb-2">
                                    <div className="h-3 w-3 rounded-full bg-blue-500" />
                                    <span className="text-sm font-medium text-blue-700 dark:text-blue-300">Material</span>
                                </div>
                                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                                    €{(costData.material_cost || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })}
                                </div>
                            </div>
                            <div className="p-4 bg-orange-50 dark:bg-orange-950/30 border border-orange-200 dark:border-orange-800 rounded-lg">
                                <div className="flex items-center gap-2 mb-2">
                                    <div className="h-3 w-3 rounded-full bg-orange-500" />
                                    <span className="text-sm font-medium text-orange-700 dark:text-orange-300">Labor</span>
                                </div>
                                <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                                    €{(costData.labor_cost || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="flex flex-col items-center justify-center">
                        <ResponsiveContainer width="100%" height={250}>
                            <BarChart
                                data={[
                                    { name: 'Material', value: costData.material_cost || 0, fill: '#3b82f6' },
                                    { name: 'Labor', value: costData.labor_cost || 0, fill: '#f97316' }
                                ]}
                                layout="vertical"
                            >
                                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" horizontal={false} />
                                <XAxis type="number" tickFormatter={(v) => `€${v.toLocaleString()}`} className="text-xs" />
                                <YAxis type="category" dataKey="name" width={80} className="text-xs" />
                                <Tooltip
                                    formatter={(value: number) => [`€${value.toLocaleString('fr-FR', { minimumFractionDigits: 2 })}`, 'Cost']}
                                    contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }}
                                />
                                <Bar dataKey="value" radius={[0, 4, 4, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t">
                    <MetricItem value={costData.intervention_count} label="Total Interventions" />
                    <MetricItem value={`€${(costData.avg_cost_per_intervention || 0).toFixed(2)}`} label="Avg. per Intervention" />
                    <MetricItem value={(costData.material_cost / (costData.labor_cost || 1)).toFixed(2)} label="Material/Labor Ratio" />
                    {fleetSummary?.total_interventions > 0 && (
                        <MetricItem value={`€${(costData.total_cost / fleetSummary.total_interventions).toFixed(2)}`} label="Cost per Failure" />
                    )}
                </div>
            </CardContent>
        </Card>
    );
}

function MetricItem({ value, label }: { value: any, label: string }) {
    return (
        <div className="text-center">
            <div className="text-2xl font-bold">{value}</div>
            <div className="text-xs text-muted-foreground">{label}</div>
        </div>
    );
}
