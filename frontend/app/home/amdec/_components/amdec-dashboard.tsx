'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@kit/ui/card';
import { Button } from '@kit/ui/button';
import { Badge } from '@kit/ui/badge';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import {
    AlertTriangle, AlertCircle, AlertOctagon, CheckCircle,
    TrendingUp, Wrench, BarChart3, Plus, RefreshCw, Loader2
} from 'lucide-react';
import Link from 'next/link';
import { RiskMatrix } from './risk-matrix';
import { ReportDownloadButton } from '~/components/reports/report-download-button';
import { SupervisorOrAbove } from '~/components/auth/role-guard';

// Risk level color mapping
const riskColors = {
    critical: { bg: 'bg-red-100 dark:bg-red-950', text: 'text-red-700 dark:text-red-300', border: 'border-red-500' },
    high: { bg: 'bg-orange-100 dark:bg-orange-950', text: 'text-orange-700 dark:text-orange-300', border: 'border-orange-500' },
    medium: { bg: 'bg-yellow-100 dark:bg-yellow-950', text: 'text-yellow-700 dark:text-yellow-300', border: 'border-yellow-500' },
    low: { bg: 'bg-green-100 dark:bg-green-950', text: 'text-green-700 dark:text-green-300', border: 'border-green-500' }
};

const riskIcons = {
    critical: AlertOctagon,
    high: AlertTriangle,
    medium: AlertCircle,
    low: CheckCircle
};

function RiskCard({ level, count, total }: { level: string; count: number; total: number }) {
    const colors = riskColors[level as keyof typeof riskColors] || riskColors.low;
    const Icon = riskIcons[level as keyof typeof riskIcons] || CheckCircle;
    const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;

    const gradientMap: Record<string, string> = {
        critical: 'from-rose-500 to-red-600',
        high: 'from-amber-500 to-orange-600',
        medium: 'from-yellow-400 to-amber-500',
        low: 'from-emerald-400 to-green-500'
    };

    return (
        <Card className={`card-hover relative overflow-hidden group`}>
            {/* Gradient left border */}
            <div className={`absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b ${gradientMap[level] || gradientMap.low}`} />
            <CardContent className="p-5 pl-6">
                <div className="flex items-center justify-between">
                    <div>
                        <p className={`text-xs font-bold ${colors.text} uppercase tracking-wider`}>{level}</p>
                        <p className={`text-4xl font-bold ${colors.text} mt-1`}>{count}</p>
                        <p className="text-xs text-muted-foreground mt-1">{percentage}% of total</p>
                    </div>
                    <div className={`p-3 rounded-xl ${colors.bg} transition-transform duration-300 group-hover:scale-110`}>
                        <Icon className={`h-8 w-8 ${colors.text}`} />
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

function RpnBadge({ value }: { value: number }) {
    let className = 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20';
    if (value >= 200) className = 'bg-rose-500/10 text-rose-600 border-rose-500/20 animate-pulse';
    else if (value >= 100) className = 'bg-amber-500/10 text-amber-600 border-amber-500/20';
    else if (value >= 50) className = 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20';

    return (
        <Badge variant="outline" className={`font-bold text-sm px-3 py-1 ${className}`}>
            {value}
        </Badge>
    );
}

export function AmdecDashboard() {
    const api = useGmaoApi();
    const [selectedRiskLevel, setSelectedRiskLevel] = useState<string | null>(null);

    const { data: ranking, isLoading, refetch } = useQuery({
        queryKey: ['rpn-ranking', selectedRiskLevel],
        queryFn: () => api.getRpnRanking({
            risk_levels: selectedRiskLevel || undefined,
            limit: 20
        }),
    });

    const { data: criticalEquipment } = useQuery({
        queryKey: ['critical-equipment'],
        queryFn: () => api.getCriticalEquipment(200),
    });

    const { data: failureModes } = useQuery({
        queryKey: ['failure-modes'],
        queryFn: () => api.listFailureModes({ include_rpn: true }),
    });

    const summary = {
        total: ranking?.total_failure_modes || 0,
        critical: ranking?.critical_count || 0,
        high: ranking?.high_count || 0,
        medium: ranking?.medium_count || 0,
        low: ranking?.low_count || 0
    };

    return (
        <div className="space-y-6">
            {/* Actions Bar */}
            <div className="flex items-center justify-between">
                <div className="flex gap-2">
                    <SupervisorOrAbove>
                        <Link href="/home/amdec/failure-modes">
                            <Button variant="outline">
                                <Wrench className="h-4 w-4 mr-2" />
                                Failure Modes
                            </Button>
                        </Link>
                    </SupervisorOrAbove>
                    <SupervisorOrAbove>
                        <Link href="/home/amdec/rpn-analysis">
                            <Button variant="outline">
                                <BarChart3 className="h-4 w-4 mr-2" />
                                RPN Analyses
                            </Button>
                        </Link>
                    </SupervisorOrAbove>
                </div>
                <div className="flex gap-2">
                    <SupervisorOrAbove>
                        <ReportDownloadButton
                            reportType="amdec"
                            onDownload={(format) => api.downloadAmdecReport(format)}
                            supportsPdf={true}
                            size="sm"
                        />
                    </SupervisorOrAbove>
                    <Button variant="outline" size="sm" onClick={() => refetch()}>
                        <RefreshCw className="h-4 w-4" />
                    </Button>
                    <SupervisorOrAbove>
                        <Link href="/home/amdec/failure-modes/new">
                            <Button>
                                <Plus className="h-4 w-4 mr-2" />
                                New Failure Mode
                            </Button>
                        </Link>
                    </SupervisorOrAbove>
                </div>
            </div>

            {/* Risk Distribution Cards */}
            <div className="grid gap-4 md:grid-cols-4">
                <RiskCard level="critical" count={summary.critical} total={summary.total} />
                <RiskCard level="high" count={summary.high} total={summary.total} />
                <RiskCard level="medium" count={summary.medium} total={summary.total} />
                <RiskCard level="low" count={summary.low} total={summary.total} />
            </div>

            {/* Filter Buttons */}
            <div className="flex gap-2">
                <Button
                    variant={selectedRiskLevel === null ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSelectedRiskLevel(null)}
                >
                    All
                </Button>
                {['critical', 'high', 'medium', 'low'].map((level) => (
                    <Button
                        key={level}
                        variant={selectedRiskLevel === level ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setSelectedRiskLevel(level)}
                    >
                        {level.charAt(0).toUpperCase() + level.slice(1)}
                    </Button>
                ))}
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
                {/* Left Column: Rankings */}
                <div className="space-y-6">
                    <Card className="h-full">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <TrendingUp className="h-5 w-5" />
                                RPN Ranking
                            </CardTitle>
                            <CardDescription>
                                Top {ranking?.ranking?.length || 0} risks by RPN
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {isLoading ? (
                                <div className="flex items-center justify-center py-8">
                                    <Loader2 className="h-6 w-6 animate-spin" />
                                </div>
                            ) : ranking?.ranking?.length > 0 ? (
                                <div className="space-y-2 max-h-[500px] overflow-auto pr-2">
                                    {ranking.ranking.map((item: any, idx: number) => (
                                        <div
                                            key={item.failure_mode_id}
                                            className="flex items-center justify-between p-3 bg-muted/50 hover:bg-muted rounded-lg transition-colors border border-transparent hover:border-border"
                                        >
                                            <div className="flex items-center gap-3">
                                                <span className={`
                                                    text-xs font-bold w-6 h-6 rounded-full flex items-center justify-center
                                                    ${idx < 3 ? 'bg-primary text-primary-foreground' : 'bg-muted-foreground/20 text-muted-foreground'}
                                                `}>
                                                    {idx + 1}
                                                </span>
                                                <div>
                                                    <p className="font-medium text-sm line-clamp-1" title={item.failure_mode_name}>{item.failure_mode_name}</p>
                                                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
                                                        {item.equipment_designation}
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <div className="text-right hidden sm:block">
                                                    <div className="text-[10px] text-muted-foreground font-mono space-x-1">
                                                        <span title="Severity">G:{item.gravity}</span>
                                                        <span title="Occurrence">O:{item.occurrence}</span>
                                                        <span title="Detection">D:{item.detection}</span>
                                                    </div>
                                                </div>
                                                <RpnBadge value={item.rpn_value} />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-12 text-muted-foreground">
                                    <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-20" />
                                    <p>No failure modes found</p>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* Right Column: Matrix & Critical Equip */}
                <div className="space-y-6">
                    <RiskMatrix data={ranking?.matrix_data || []} />

                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="flex items-center gap-2 text-base">
                                <AlertOctagon className="h-4 w-4 text-red-500" />
                                Critical Equipment (RPN ≥ 200)
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {criticalEquipment && criticalEquipment.length > 0 ? (
                                <div className="grid gap-2">
                                    {criticalEquipment.map((eq: any) => (
                                        <div
                                            key={eq.equipment_id}
                                            className="flex items-center justify-between p-3 bg-red-50/50 dark:bg-red-950/20 border border-red-100 dark:border-red-900/50 rounded-lg text-sm"
                                        >
                                            <span className="font-medium">{eq.equipment_designation}</span>
                                            <div className="flex items-center gap-2">
                                                <span className="text-xs text-muted-foreground">{eq.critical_failure_modes} issues</span>
                                                <Badge variant="destructive" className="h-5 text-[10px]">{eq.max_rpn}</Badge>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-6 text-muted-foreground text-sm">
                                    <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500/50" />
                                    No critical equipment found
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>

            {/* Quick Stats */}
            <Card>
                <CardHeader>
                    <CardTitle>AMDEC Summary</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="text-center p-4 bg-muted rounded-lg">
                            <p className="text-3xl font-bold">{failureModes?.length || 0}</p>
                            <p className="text-sm text-muted-foreground">Total Failure Modes</p>
                        </div>
                        <div className="text-center p-4 bg-muted rounded-lg">
                            <p className="text-3xl font-bold">{summary.total}</p>
                            <p className="text-sm text-muted-foreground">With RPN Analysis</p>
                        </div>
                        <div className="text-center p-4 bg-red-50 dark:bg-red-950/30 rounded-lg">
                            <p className="text-3xl font-bold text-red-600">{summary.critical + summary.high}</p>
                            <p className="text-sm text-muted-foreground">High Priority (Critical + High)</p>
                        </div>
                        <div className="text-center p-4 bg-muted rounded-lg">
                            <p className="text-3xl font-bold">{criticalEquipment?.length || 0}</p>
                            <p className="text-sm text-muted-foreground">Critical Equipment</p>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
