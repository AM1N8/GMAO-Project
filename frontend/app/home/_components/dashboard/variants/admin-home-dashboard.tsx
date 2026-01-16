'use client';

import { Activity, BarChart3, Clock, AlertTriangle } from 'lucide-react';
import { StatsCard, MaintenanceTrendChart, AssetAvailabilityChart, RecentInterventionsTable, CriticalRisksCard, PerformanceMetricsGrid } from '../dashboard-components';

export function AdminHomeDashboard({ stats, ranking, recentInterventions, interventionTrend, assetStatusData, performanceMetrics }: any) {
    return (
        <div className="space-y-6 pb-12">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <StatsCard
                    title="Total Assets"
                    value={stats?.equipment_count || 0}
                    icon={BarChart3}
                    trend="+3 this month"
                    description="Managed inventory"
                    color="blue"
                />
                <StatsCard
                    title="Active Interventions"
                    value={stats?.intervention_count || 0}
                    icon={Activity}
                    trend="-2 from last week"
                    description="Ongoing maintenance"
                    color="green"
                />
                <StatsCard
                    title="Spare Parts"
                    value={stats?.spare_part_count || 0}
                    icon={Clock}
                    trend="8 low stock alerts"
                    description="Inventory status"
                    color="orange"
                />
                <StatsCard
                    title="Critical Risks"
                    value={ranking?.critical_count || 0}
                    icon={AlertTriangle}
                    trend="AMDEC Analysis"
                    description="High priority failure modes"
                    color="red"
                />
            </div>

            <div className="grid gap-6 lg:grid-cols-7">
                <div className="lg:col-span-4">
                    <MaintenanceTrendChart data={interventionTrend} />
                </div>
                <div className="lg:col-span-3">
                    <AssetAvailabilityChart data={assetStatusData} />
                </div>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
                <RecentInterventionsTable data={recentInterventions} />
                <CriticalRisksCard ranking={ranking} />
            </div>

            <PerformanceMetricsGrid metrics={performanceMetrics} />
        </div>
    );
}
