'use client';

import { Activity, BarChart3, Clock, AlertTriangle } from 'lucide-react';
import { StatsCard, MaintenanceTrendChart, AssetAvailabilityChart, RecentInterventionsTable, CriticalRisksCard } from '../dashboard-components';

export function SupervisorHomeDashboard({ stats, ranking, recentInterventions, interventionTrend, assetStatusData }: any) {
    return (
        <div className="space-y-6 pb-12">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <StatsCard
                    title="Total Assets"
                    value={stats?.equipment_count || 0}
                    icon={BarChart3}
                    description="Equipment under supervision"
                    color="blue"
                />
                <StatsCard
                    title="Active Interventions"
                    value={stats?.intervention_count || 0}
                    icon={Activity}
                    description="Ongoing maintenance"
                    color="green"
                />
                <StatsCard
                    title="Spare Parts"
                    value={stats?.spare_part_count || 0}
                    icon={Clock}
                    description="Inventory status"
                    color="orange"
                />
                <StatsCard
                    title="Critical Risks"
                    value={ranking?.critical_count || 0}
                    icon={AlertTriangle}
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
        </div>
    );
}
