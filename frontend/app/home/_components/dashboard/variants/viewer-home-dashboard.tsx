'use client';

import { Activity, BarChart3, Clock } from 'lucide-react';
import { StatsCard, MaintenanceTrendChart, AssetAvailabilityChart } from '../dashboard-components';

export function ViewerHomeDashboard({ stats, interventionTrend, assetStatusData }: any) {
    return (
        <div className="space-y-6 pb-12">
            <div className="grid gap-4 md:grid-cols-3">
                <StatsCard
                    title="Total Assets"
                    value={stats?.equipment_count || 0}
                    icon={BarChart3}
                    description="Monitored equipment"
                    color="blue"
                />
                <StatsCard
                    title="Global Activity"
                    value={stats?.intervention_count || 0}
                    icon={Activity}
                    description="Total interventions recorded"
                    color="green"
                />
                <StatsCard
                    title="Catalog Items"
                    value={stats?.spare_part_count || 0}
                    icon={Clock}
                    description="Spare parts inventory"
                    color="orange"
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
        </div>
    );
}
