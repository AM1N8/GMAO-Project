'use client';

import { Wrench, Activity, AlertTriangle, TrendingUp, Clock } from 'lucide-react';
import { KpiSummaryCard, KpiTrendCharts } from '../kpi-components';

export function OperationalKpiDashboard({
    stats,
    fleetSummary,
    chartData
}: any) {
    return (
        <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
                <KpiSummaryCard title="Equipment" value={stats?.equipment_count || 0} icon={Wrench} color="blue" subtitle="Assets in system" unit="units" />
                <KpiSummaryCard title="Interventions" value={fleetSummary?.total_interventions || 0} icon={Activity} color="green" subtitle="Maintenance records" unit="count" />
                <KpiSummaryCard title="Failures" value={fleetSummary?.total_failures || 0} icon={AlertTriangle} color="red" subtitle="Recorded failures" unit="count" />
            </div>

            <div className="grid gap-4 md:grid-cols-3">
                <KpiSummaryCard
                    title="Availability"
                    value={fleetSummary?.availability_percentage}
                    unit="%"
                    icon={TrendingUp}
                    color="green"
                    subtitle="Uptime percentage"
                />
                <KpiSummaryCard
                    title="MTBF"
                    value={fleetSummary?.mtbf_hours}
                    unit="hours"
                    icon={Clock}
                    color="blue"
                    subtitle="Between failures"
                />
                <KpiSummaryCard
                    title="MTTR"
                    value={fleetSummary?.mttr_hours}
                    unit="hours"
                    icon={AlertTriangle}
                    color="orange"
                    subtitle="To repair"
                />
            </div>

            <KpiTrendCharts chartData={chartData} />
        </div>
    );
}
