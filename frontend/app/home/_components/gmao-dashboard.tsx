'use client';

import { useQuery } from '@tanstack/react-query';
import { Activity, AlertTriangle, CheckCircle, Clock } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@kit/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@kit/ui/alert';

import { useGmaoApi } from '~/lib/hooks/use-gmao-api';

export function GmaoDashboard() {
    const api = useGmaoApi();

    const { data: stats, isLoading, error } = useQuery({
        queryKey: ['gmao-stats'],
        queryFn: () => api.getStats(),
    });

    if (isLoading) {
        return <div className="p-4">Loading dashboard statistics...</div>;
    }

    if (error) {
        return (
            <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>
                    Failed to load dashboard data. Please ensure the backend is running.
                </AlertDescription>
            </Alert>
        );
    }

    return (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <StatsCard
                title="Equipment"
                value={stats?.equipment_count || 0}
                icon={CheckCircle}
                description="Total active assets"
            />
            <StatsCard
                title="Interventions"
                value={stats?.intervention_count || 0}
                icon={Activity}
                description="Recorded maintenance activities"
            />
            <StatsCard
                title="Spare Parts"
                value={stats?.spare_part_count || 0}
                icon={Clock} // Placeholder icon
                description="Inventory items"
            />
            <StatsCard
                title="Predictive Models"
                // Hardcoded or fetched from another endpoint
                value={stats?.rag_document_count ? "Active" : "Ready"}
                icon={AlertTriangle}
                description="ML & RAG System Status"
            />
        </div>
    );
}

function StatsCard({
    title,
    value,
    icon: Icon,
    description,
}: {
    title: string;
    value: string | number;
    icon: any;
    description: string;
}) {
    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{title}</CardTitle>
                <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
                <div className="text-2xl font-bold">{value}</div>
                <p className="text-xs text-muted-foreground">{description}</p>
            </CardContent>
        </Card>
    );
}
