'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@kit/ui/card';
import { Activity, AlertTriangle, CheckCircle, Clock } from 'lucide-react';

interface RulGaugeProps {
    rulDays: number | null;
    confidence: number;
    loading?: boolean;
}

export function RulGauge({ rulDays, confidence, loading }: RulGaugeProps) {
    if (loading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Remaining Useful Life (RUL)</CardTitle>
                </CardHeader>
                <CardContent className="flex justify-center items-center h-48">
                    <Activity className="animate-pulse h-10 w-10 text-muted-foreground" />
                </CardContent>
            </Card>
        );
    }

    if (rulDays === null) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Remaining Useful Life (RUL)</CardTitle>
                </CardHeader>
                <CardContent className="text-center py-10 text-muted-foreground">
                    Not enough data for RUL prediction.
                </CardContent>
            </Card>
        );
    }

    // Color logic
    let colorClass = 'text-green-500';
    let Icon = CheckCircle;
    let statusText = 'Healthy';

    if (rulDays < 30) {
        colorClass = 'text-red-500';
        Icon = AlertTriangle;
        statusText = 'Critical - Action Required';
    } else if (rulDays < 90) {
        colorClass = 'text-yellow-500';
        Icon = Clock;
        statusText = 'Warning - Plan Maintenance';
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center justify-between">
                    <span>Remaining Useful Life (RUL)</span>
                    <Icon className={`h-5 w-5 ${colorClass}`} />
                </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col items-center justify-center space-y-4">
                <div className={`text-6xl font-bold ${colorClass}`}>
                    {Math.round(rulDays)}
                    <span className="text-xl text-muted-foreground ml-2">days</span>
                </div>

                <div className="text-center space-y-1">
                    <p className="font-medium text-lg">{statusText}</p>
                    <p className="text-sm text-muted-foreground">
                        Machine Confidence: {Math.round(confidence)}%
                    </p>
                </div>

                <div className="w-full bg-secondary h-2 rounded-full overflow-hidden mt-4">
                    <div
                        className={`h-full ${colorClass.replace('text-', 'bg-')}`}
                        style={{ width: `${Math.min(confidence, 100)}%` }}
                    />
                </div>
            </CardContent>
        </Card>
    );
}
