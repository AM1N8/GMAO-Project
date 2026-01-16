'use client';

import { Activity, BarChart3, Clock } from 'lucide-react';
import { StatsCard, MaintenanceTrendChart, RecentInterventionsTable } from '../dashboard-components';

export function TechnicianHomeDashboard({ stats, recentInterventions, interventionTrend }: any) {
    return (
        <div className="space-y-6 pb-12">
            <div className="grid gap-4 md:grid-cols-3">
                <StatsCard
                    title="Managed Assets"
                    value={stats?.equipment_count || 0}
                    icon={BarChart3}
                    description="Equipment in system"
                    color="blue"
                />
                <StatsCard
                    title="Active Jobs"
                    value={stats?.intervention_count || 0}
                    icon={Activity}
                    description="Assigned maintenance"
                    color="green"
                />
                <StatsCard
                    title="Stock Status"
                    value={stats?.spare_part_count || 0}
                    icon={Clock}
                    description="Available spare parts"
                    color="orange"
                />
            </div>

            <div className="grid gap-6">
                <MaintenanceTrendChart data={interventionTrend} />
            </div>

            <div className="grid gap-6">
                <RecentInterventionsTable data={recentInterventions} />
            </div>
        </div>
    );
}
