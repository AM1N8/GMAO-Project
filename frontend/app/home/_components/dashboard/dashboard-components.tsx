'use client';

import {
    Area,
    AreaChart,
    CartesianGrid,
    Cell,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts';
import { TrendingUp, Activity, BarChart3, Clock, AlertTriangle, CheckCircle } from 'lucide-react';

import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription,
    CardFooter
} from '@kit/ui/card';
import { Badge } from '@kit/ui/badge';
import { Button } from '@kit/ui/button';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@kit/ui/table';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#0ea5e9'];

// Reusable Stats Card
export function StatsCard({
    title,
    value,
    icon: Icon,
    description,
    trend,
    color
}: {
    title: string;
    value: string | number;
    icon: any;
    description: string;
    trend?: string;
    color: 'blue' | 'green' | 'orange' | 'red';
}) {
    const gradientMap = {
        blue: 'from-blue-500 to-blue-700',
        green: 'from-emerald-500 to-teal-600',
        orange: 'from-amber-500 to-orange-600',
        red: 'from-red-500 to-red-600',
    };

    const bgMap = {
        blue: 'bg-blue-500/10 dark:bg-blue-500/20',
        green: 'bg-emerald-500/10 dark:bg-emerald-500/20',
        orange: 'bg-amber-500/10 dark:bg-amber-500/20',
        red: 'bg-red-500/10 dark:bg-red-500/20',
    };

    return (
        <Card className={`card-hover overflow-hidden relative group`}>
            <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${gradientMap[color]}`} />
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
                <div className={`p-2.5 rounded-xl ${bgMap[color]} transition-all duration-300 group-hover:scale-110`}>
                    <Icon className="h-5 w-5" style={{ color: color === 'blue' ? '#3b82f6' : color === 'green' ? '#10b981' : color === 'orange' ? '#f59e0b' : '#ef4444' }} />
                </div>
            </CardHeader>
            <CardContent className="pt-0">
                <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-bold tracking-tight">{value}</span>
                </div>
                <div className="flex items-center justify-between mt-3">
                    {trend && (
                        <Badge variant="secondary" className="text-xs font-medium">
                            {trend}
                        </Badge>
                    )}
                    <p className="text-xs text-muted-foreground">{description}</p>
                </div>
            </CardContent>
        </Card>
    );
}

// Maintenance Activity Chart
export function MaintenanceTrendChart({ data }: { data: any[] }) {
    return (
        <Card className="card-hover">
            <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-blue-500/10">
                        <TrendingUp className="h-4 w-4 text-blue-500" />
                    </div>
                    <div>
                        <CardTitle>Maintenance Activity</CardTitle>
                        <CardDescription>Monthly intervention trends</CardDescription>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="h-[280px] pt-4">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data}>
                        <defs>
                            <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.4} />
                                <stop offset="50%" stopColor="#0ea5e9" stopOpacity={0.2} />
                                <stop offset="100%" stopColor="#06b6d4" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <XAxis dataKey="name" axisLine={false} tickLine={false} className="text-xs" />
                        <YAxis axisLine={false} tickLine={false} className="text-xs" />
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted))" />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: 'hsl(var(--popover))',
                                border: '1px solid hsl(var(--border))',
                                borderRadius: '8px'
                            }}
                        />
                        <Area
                            type="monotone"
                            dataKey="count"
                            stroke="#3b82f6"
                            strokeWidth={2}
                            fillOpacity={1}
                            fill="url(#colorCount)"
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
}

// Asset Availability Pie Chart
export function AssetAvailabilityChart({ data }: { data: any[] }) {
    return (
        <Card>
            <CardHeader>
                <CardTitle>Asset Availability</CardTitle>
                <CardDescription>Current status of all equipment</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px] flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                        <Pie
                            data={data}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={80}
                            paddingAngle={5}
                            dataKey="value"
                        >
                            {data.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                        </Pie>
                        <Tooltip />
                    </PieChart>
                </ResponsiveContainer>
            </CardContent>
            <CardFooter className="flex flex-wrap justify-center gap-4 text-sm">
                {data.map((entry, index) => (
                    <div key={entry.name} className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted/50">
                        <div
                            className="h-2.5 w-2.5 rounded-full shadow-sm"
                            style={{ backgroundColor: COLORS[index % COLORS.length] }}
                        />
                        <span className="text-xs font-medium">{entry.name}</span>
                        <span className="text-xs text-muted-foreground">({entry.value})</span>
                    </div>
                ))}
            </CardFooter>
        </Card>
    );
}

// Recent Interventions Table
export function RecentInterventionsTable({ data }: { data: any[] }) {
    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between">
                <div>
                    <CardTitle>Recent Interventions</CardTitle>
                    <CardDescription>Last maintenance activities recorded</CardDescription>
                </div>
                <Button variant="outline" size="sm" asChild>
                    <a href="/home/interventions">View All</a>
                </Button>
            </CardHeader>
            <CardContent>
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Equipment</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead className="text-right">Date</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {data?.map((int: any) => (
                            <TableRow key={int.id}>
                                <TableCell className="font-medium">{int.equipment_designation}</TableCell>
                                <TableCell>{int.type_panne}</TableCell>
                                <TableCell>
                                    <Badge variant="outline" className={`
                                        ${int.status === 'completed' ? 'bg-green-50 text-green-700 border-green-200' :
                                            int.status === 'in_progress' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                                                'bg-yellow-50 text-yellow-700 border-yellow-200'}
                                    `}>
                                        {int.status}
                                    </Badge>
                                </TableCell>
                                <TableCell className="text-right">
                                    {new Date(int.date_intervention).toLocaleDateString()}
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    );
}

// AMDEC Critical Risks Card
export function CriticalRisksCard({ ranking }: { ranking: any }) {
    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between">
                <div>
                    <CardTitle>Critical Failure Modes</CardTitle>
                    <CardDescription>Top risks requiring corrective action</CardDescription>
                </div>
                <Button variant="ghost" size="sm" asChild>
                    <a href="/home/amdec">Open AMDEC</a>
                </Button>
            </CardHeader>
            <CardContent>
                {ranking?.ranking?.length > 0 ? (
                    <div className="space-y-4">
                        {ranking.ranking.map((risk: any) => (
                            <div key={risk.failure_mode_id} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                                <div>
                                    <p className="font-medium text-sm">{risk.failure_mode_name}</p>
                                    <p className="text-xs text-muted-foreground">{risk.equipment_designation}</p>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="text-right">
                                        <p className="text-xs font-semibold text-red-600">RPN</p>
                                        <p className="text-sm font-bold">{risk.rpn_value}</p>
                                    </div>
                                    <Badge className={risk.rpn_value >= 200 ? "bg-red-500" : "bg-orange-500"}>
                                        {risk.risk_level}
                                    </Badge>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-8 text-muted-foreground">
                        <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-500 opacity-20" />
                        <p>No critical failure modes identified</p>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

// Performance Metrics Grid
export function PerformanceMetricsGrid({ metrics }: { metrics: any[] }) {
    return (
        <Card className="overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-600 via-cyan-500 to-blue-400" />
            <CardHeader className="pb-2">
                <CardTitle className="text-lg">Performance Metrics</CardTitle>
                <CardDescription>Key indicators for Q4 2025</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {metrics.map((item) => (
                        <div key={item.name} className="group relative flex flex-col items-center justify-center p-6 rounded-xl border bg-gradient-to-br from-muted/50 to-muted/20 hover:from-muted/80 hover:to-muted/40 transition-all duration-300">
                            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{item.name}</p>
                            <div className="flex items-baseline gap-1 mt-3">
                                <span className="text-4xl font-bold tracking-tight text-gradient">{item.value}</span>
                                <span className="text-sm font-medium text-muted-foreground">{item.unit}</span>
                            </div>
                            <Badge
                                variant="secondary"
                                className={`mt-3 ${item.trend.startsWith('+')
                                    ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20'
                                    : 'bg-red-500/10 text-red-600 border-red-500/20'}`}
                            >
                                {item.trend}
                            </Badge>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}
