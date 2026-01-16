'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@kit/ui/card';
import { Button } from '@kit/ui/button';
import { Input } from '@kit/ui/input';
import { Label } from '@kit/ui/label';
import { Badge } from '@kit/ui/badge';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import {
    Activity, Clock, TrendingUp, Wrench, AlertTriangle, CheckCircle,
    BarChart3, Calendar, Filter, RefreshCw, Download, Loader2
} from 'lucide-react';
import {
    LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, Legend, ResponsiveContainer, AreaChart, Area
} from 'recharts';
import { ReportDownloadButton } from '~/components/reports/report-download-button';
import { AdminOnly, SupervisorOrAbove } from '~/components/auth/role-guard';

// Stat Card Component
function StatCard({ title, value, icon: Icon, description, trend }: {
    title: string;
    value: string | number;
    icon: React.ElementType;
    description?: string;
    trend?: { value: number; positive: boolean };
}) {
    return (
        <Card className="card-hover relative overflow-hidden group">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 to-cyan-500" />
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
                <div className="h-9 w-9 rounded-xl bg-primary/10 flex items-center justify-center transition-transform duration-300 group-hover:scale-110">
                    <Icon className="h-4 w-4 text-primary" />
                </div>
            </CardHeader>
            <CardContent>
                <div className="text-3xl font-bold tracking-tight">{value}</div>
                {description && <p className="text-xs text-muted-foreground mt-2">{description}</p>}
                {trend && (
                    <Badge
                        variant="secondary"
                        className={`mt-2 ${trend.positive
                            ? 'bg-emerald-500/10 text-emerald-600'
                            : 'bg-red-500/10 text-red-600'}`}
                    >
                        {trend.positive ? '↑' : '↓'} {Math.abs(trend.value).toFixed(1)}% vs last period
                    </Badge>
                )}
            </CardContent>
        </Card>
    );
}

// KPI Card with visual indicator
function KpiCard({ title, value, unit, icon: Icon, color, subtitle }: {
    title: string;
    value: number | null;
    unit: string;
    icon: React.ElementType;
    color: string;
    subtitle: string;
}) {
    const colorClasses: Record<string, { gradient: string; text: string; bg: string; glow: string }> = {
        green: { gradient: 'from-emerald-500 to-teal-500', text: 'text-emerald-600', bg: 'bg-emerald-500/10', glow: 'shadow-emerald-500/20' },
        blue: { gradient: 'from-blue-500 to-cyan-500', text: 'text-blue-600', bg: 'bg-blue-500/10', glow: 'shadow-blue-500/20' },
        orange: { gradient: 'from-amber-500 to-orange-500', text: 'text-amber-600', bg: 'bg-amber-500/10', glow: 'shadow-amber-500/20' },
        red: { gradient: 'from-red-500 to-red-600', text: 'text-red-600', bg: 'bg-red-500/10', glow: 'shadow-red-500/20' },
    };
    const c = colorClasses[color] ?? colorClasses['blue']!;

    return (
        <Card className={`card-hover relative overflow-hidden group`}>
            {/* Gradient left border */}
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

import { useUserRole } from '~/lib/hooks/use-user-role';
import { ManagementKpiDashboard } from '../../_components/dashboard/variants/management-kpi-dashboard';
import { OperationalKpiDashboard } from '../../_components/dashboard/variants/operational-kpi-dashboard';
import { PublicKpiDashboard } from '../../_components/dashboard/variants/public-kpi-dashboard';

export function KpiDashboard() {
    const api = useGmaoApi();
    const { role, isLoading: roleLoading } = useUserRole();
    const defaultDates = getDefaultDates();

    // Filter state
    const [startDate, setStartDate] = useState(defaultDates.start);
    const [endDate, setEndDate] = useState(defaultDates.end);
    const [selectedEquipment, setSelectedEquipment] = useState<number | null>(null);
    const [appliedFilters, setAppliedFilters] = useState({
        start: defaultDates.start,
        end: defaultDates.end,
        equipmentId: null as number | null
    });

    // Queries
    const { data: stats, isLoading: statsLoading } = useQuery({
        queryKey: ['stats'],
        queryFn: () => api.getStats(),
    });

    const { data: equipment } = useQuery({
        queryKey: ['equipment-list'],
        queryFn: () => api.listEquipment(),
    });

    const { data: monthlyKpis, isLoading: kpisLoading, isFetching } = useQuery({
        queryKey: ['monthly-kpis', appliedFilters.start, appliedFilters.end, appliedFilters.equipmentId],
        queryFn: () => api.getMonthlyKpis({
            start_date: appliedFilters.start,
            end_date: appliedFilters.end,
            equipment_id: appliedFilters.equipmentId || undefined
        }),
    });

    const { data: costData } = useQuery({
        queryKey: ['cost-analysis'],
        queryFn: () => api.getCostAnalysis(),
    });

    // Handlers
    const handleApplyFilter = () => {
        setAppliedFilters({
            start: startDate,
            end: endDate,
            equipmentId: selectedEquipment
        });
    };

    const handleQuickFilter = (months: number) => {
        const end = new Date();
        const start = new Date();
        start.setMonth(start.getMonth() - months);
        const startStr = start.toISOString().split('T')[0];
        const endStr = end.toISOString().split('T')[0];
        setStartDate(startStr);
        setEndDate(endStr);
        setAppliedFilters({ start: startStr, end: endStr, equipmentId: selectedEquipment });
    };

    const handleResetFilters = () => {
        setStartDate(defaultDates.start);
        setEndDate(defaultDates.end);
        setSelectedEquipment(null);
        setAppliedFilters({ start: defaultDates.start, end: defaultDates.end, equipmentId: null });
    };

    // Prepare chart data
    const chartData = useMemo(() => {
        const equipmentData = appliedFilters.equipmentId
            ? monthlyKpis?.equipment_data?.find((e: any) => e.equipment_id === appliedFilters.equipmentId)
            : monthlyKpis?.equipment_data?.[0];

        return equipmentData?.monthly_kpis?.map((m: any) => ({
            name: m.month_name?.split(' ')[0]?.substring(0, 3) + ' ' + String(m.year).slice(-2) || m.month,
            MTBF: m.mtbf_hours || 0,
            MTTR: m.mttr_hours || 0,
            Availability: m.availability_percentage || 0,
            Failures: m.failure_count || 0,
            Downtime: m.downtime_hours || 0
        })) || [];
    }, [monthlyKpis, appliedFilters.equipmentId]);

    const fleetSummary = monthlyKpis?.fleet_summary;
    const periodInfo = monthlyKpis?.period;

    if (statsLoading || kpisLoading || roleLoading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <span className="ml-2 text-muted-foreground">Loading KPIs...</span>
            </div>
        );
    }

    const commonProps = {
        stats,
        fleetSummary,
        chartData,
        costData,
        api,
        appliedFilters
    };

    return (
        <div className="space-y-6">
            {/* Shared Filter Panel */}
            <Card className="bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
                <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Filter className="h-5 w-5 text-primary" />
                            <CardTitle className="text-lg">Filters & Time Period</CardTitle>
                        </div>
                        {isFetching && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
                        <div className="space-y-2">
                            <Label htmlFor="equipment">Equipment</Label>
                            <select
                                id="equipment"
                                value={selectedEquipment || ''}
                                onChange={(e) => setSelectedEquipment(e.target.value ? Number(e.target.value) : null)}
                                className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                            >
                                <option value="">All Equipment (Fleet)</option>
                                {equipment?.map((eq: any) => (
                                    <option key={eq.id} value={eq.id}>
                                        {eq.designation || eq.code || `Equipment #${eq.id}`}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="start-date">Start Date</Label>
                            <Input id="start-date" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="end-date">End Date</Label>
                            <Input id="end-date" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
                        </div>

                        <div className="space-y-2">
                            <Label className="invisible">Actions</Label>
                            <div className="flex gap-2">
                                <Button onClick={handleApplyFilter} className="flex-1">Apply</Button>
                                <Button variant="outline" size="icon" onClick={handleResetFilters} title="Reset Filters"><RefreshCw className="h-4 w-4" /></Button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label>Quick Select</Label>
                            <div className="flex gap-1">
                                <Button variant="outline" size="sm" onClick={() => handleQuickFilter(3)}>3M</Button>
                                <Button variant="outline" size="sm" onClick={() => handleQuickFilter(6)}>6M</Button>
                                <Button variant="outline" size="sm" onClick={() => handleQuickFilter(12)}>1Y</Button>
                            </div>
                        </div>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-4 mt-4 pt-3 border-t">
                        <div className="flex flex-wrap gap-2">
                            <Badge variant="secondary"><Calendar className="h-3 w-3 mr-1" />{appliedFilters.start} → {appliedFilters.end}</Badge>
                            <Badge variant={appliedFilters.equipmentId ? 'default' : 'secondary'}>
                                <Wrench className="h-3 w-3 mr-1" />
                                {appliedFilters.equipmentId ? equipment?.find((e: any) => e.id === appliedFilters.equipmentId)?.designation || `#${appliedFilters.equipmentId}` : 'All Equipment'}
                            </Badge>
                            {periodInfo && <Badge variant="outline">{periodInfo.months_count} months</Badge>}
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Variant Dispatcher */}
            {role === 'admin' || role === 'supervisor' ? (
                <ManagementKpiDashboard {...commonProps} />
            ) : role === 'technician' ? (
                <OperationalKpiDashboard {...commonProps} />
            ) : (
                <PublicKpiDashboard {...commonProps} />
            )}
        </div>
    );
}
