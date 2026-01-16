'use client';

import { Wrench, Activity, AlertTriangle, CheckCircle, TrendingUp, Clock } from 'lucide-react';
import { KpiSummaryCard, KpiTrendCharts, CostAnalysisSection } from '../kpi-components';
import { AdminOnly } from '~/components/auth/role-guard';
import { ReportDownloadButton } from '~/components/reports/report-download-button';

export function ManagementKpiDashboard({
    stats,
    fleetSummary,
    chartData,
    costData,
    api,
    appliedFilters
}: any) {
    return (
        <div className="space-y-6">
            <div className="flex justify-end">
                <ReportDownloadButton
                    reportType="kpi"
                    onDownload={(format) => api.downloadKpiReport(format, {
                        start_date: appliedFilters.start,
                        end_date: appliedFilters.end,
                        equipment_id: appliedFilters.equipmentId || undefined
                    })}
                    supportsPdf={true}
                />
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <KpiSummaryCard title="Total Equipment" value={stats?.equipment_count || 0} icon={Wrench} color="blue" subtitle="Registered assets" unit="units" />
                <KpiSummaryCard title="Interventions" value={fleetSummary?.total_interventions || 0} icon={Activity} color="green" subtitle="In selected period" unit="count" />
                <KpiSummaryCard title="Total Failures" value={fleetSummary?.total_failures || 0} icon={AlertTriangle} color="red" subtitle="Recorded failures" unit="count" />
                <AdminOnly>
                    <KpiSummaryCard title="Technicians" value={stats?.technician_count || 0} icon={CheckCircle} color="blue" subtitle="Active personnel" unit="users" />
                </AdminOnly>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
                <KpiSummaryCard
                    title="Availability"
                    value={fleetSummary?.availability_percentage}
                    unit="%"
                    icon={TrendingUp}
                    color="green"
                    subtitle="Equipment uptime percentage"
                />
                <KpiSummaryCard
                    title="MTBF"
                    value={fleetSummary?.mtbf_hours}
                    unit="hours"
                    icon={Clock}
                    color="blue"
                    subtitle="Mean Time Between Failures"
                />
                <KpiSummaryCard
                    title="MTTR"
                    value={fleetSummary?.mttr_hours}
                    unit="hours"
                    icon={AlertTriangle}
                    color="orange"
                    subtitle="Mean Time To Repair"
                />
            </div>

            <KpiTrendCharts chartData={chartData} />

            <CostAnalysisSection costData={costData} fleetSummary={fleetSummary} />
        </div>
    );
}
