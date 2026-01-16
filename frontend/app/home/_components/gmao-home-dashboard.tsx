'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    Activity,
    AlertTriangle,
    CheckCircle,
    Clock,
    Wrench,
    BarChart3,
    History,
    TrendingUp,
    FileText
} from 'lucide-react';
import {
    Area,
    AreaChart,
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts';

import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription,
    CardFooter
} from '@kit/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@kit/ui/alert';
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
import { Skeleton } from '@kit/ui/skeleton';
import { SupervisorOrAbove, TechnicianOrAbove } from '~/components/auth/role-guard';

import { useGmaoApi } from '~/lib/hooks/use-gmao-api';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#0ea5e9'];

import { useUserRole } from '~/lib/hooks/use-user-role';
import { AdminHomeDashboard } from './dashboard/variants/admin-home-dashboard';
import { SupervisorHomeDashboard } from './dashboard/variants/supervisor-home-dashboard';
import { TechnicianHomeDashboard } from './dashboard/variants/technician-home-dashboard';
import { ViewerHomeDashboard } from './dashboard/variants/viewer-home-dashboard';
import { StatsCard } from './dashboard/dashboard-components';

export function GmaoHomeDashboard() {
    const api = useGmaoApi();
    const { role, isLoading: roleLoading } = useUserRole();

    // Fetch core stats
    const { data: stats, isLoading: statsLoading } = useQuery({
        queryKey: ['gmao-stats'],
        queryFn: () => api.getStats(),
    });

    // Fetch AMDEC ranking for critical alerts
    const { data: ranking, isLoading: rankingLoading } = useQuery({
        queryKey: ['rpn-ranking'],
        queryFn: () => api.getRpnRanking({ limit: 5 }),
    });

    // Fetch recent interventions
    const { data: recentInterventions, isLoading: interventionsLoading } = useQuery({
        queryKey: ['recent-interventions'],
        queryFn: () => api.getRecentInterventions(5),
    });

    // Asset status distribution - shared logic
    const assetStatusData = useMemo(() => {
        if (!stats?.equipment_status_breakdown) return [];
        return stats.equipment_status_breakdown.map((item: any) => ({
            name: item.status.charAt(0).toUpperCase() + item.status.slice(1),
            value: item.count
        }));
    }, [stats]);

    // Trend logic - shared logic
    const { data: trends } = useQuery({
        queryKey: ['kpi-trends'],
        queryFn: () => api.getKpiTrends('failures', 'month'),
    });

    const interventionTrend = useMemo(() => {
        return trends?.data_points?.map((p: any) => {
            let name = p.period;
            if (typeof p.period === 'string' && p.period.includes('-')) {
                const parts = p.period.split('-');
                if (parts.length >= 2) name = parts[1];
            }
            return {
                name: name || 'Unknown',
                count: p.value || 0
            };
        }) || [];
    }, [trends]);

    const performanceMetrics = [
        { name: 'MTBF', value: 320, unit: 'hrs', trend: '+12%' },
        { name: 'MTTR', value: 4.5, unit: 'hrs', trend: '-5%' },
        { name: 'Availability', value: 98.2, unit: '%', trend: '+0.5%' },
        { name: 'OEE', value: 85.4, unit: '%', trend: '+2.1%' },
    ];

    if (statsLoading || roleLoading) {
        return <DashboardSkeleton />;
    }

    // Role-based Variant Dispatcher
    const variantProps = {
        stats,
        ranking,
        recentInterventions,
        interventionTrend,
        assetStatusData,
        performanceMetrics
    };

    switch (role) {
        case 'admin':
            return <AdminHomeDashboard {...variantProps} />;
        case 'supervisor':
            return <SupervisorHomeDashboard {...variantProps} />;
        case 'technician':
            return <TechnicianHomeDashboard {...variantProps} />;
        case 'viewer':
            return <ViewerHomeDashboard {...variantProps} />;
        default:
            return <ViewerHomeDashboard {...variantProps} />;
    }
}

function DashboardSkeleton() {
    return (
        <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {[...Array(4)].map((_, i) => (
                    <Skeleton key={i} className="h-32 w-full rounded-xl" />
                ))}
            </div>
            <div className="grid gap-6 lg:grid-cols-7">
                <Skeleton className="lg:col-span-4 h-[400px] w-full rounded-xl" />
                <Skeleton className="lg:col-span-3 h-[400px] w-full rounded-xl" />
            </div>
        </div>
    );
}
