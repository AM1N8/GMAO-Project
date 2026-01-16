'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import { PageHeader, PageDescription } from '@kit/ui/page';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@kit/ui/card';
import { Button } from '@kit/ui/button';
import { Badge } from '@kit/ui/badge';
import { Loader2, Wrench, Calendar, Info, Shield, Eye, Edit, History, AlertTriangle, AlertCircle } from 'lucide-react';
import Link from 'next/link';

export default function FailureModeDetailsPage() {
    const api = useGmaoApi();
    const params = useParams();
    const id = parseInt(params.id as string);

    const { data: failureMode, isLoading } = useQuery({
        queryKey: ['failure-mode', id],
        queryFn: () => api.getFailureMode(id),
    });

    const { data: analyses } = useQuery({
        queryKey: ['failure-mode-analyses', id],
        queryFn: () => api.listRpnAnalyses({ failure_mode_id: id }),
    });

    if (isLoading) {
        return (
            <div className="flex items-center justify-center p-24">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    if (!failureMode) {
        return (
            <div className="p-24 text-center">
                <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                <p>Failure mode not found.</p>
            </div>
        );
    }

    const latestRpn = failureMode.latest_rpn;
    let rpnColor = 'bg-green-100 text-green-800';
    if (latestRpn >= 200) rpnColor = 'bg-red-100 text-red-800';
    else if (latestRpn >= 100) rpnColor = 'bg-orange-100 text-orange-800';
    else if (latestRpn >= 50) rpnColor = 'bg-yellow-100 text-yellow-800';

    return (
        <div className="flex flex-col space-y-6">
            <PageHeader
                title={failureMode.mode_name}
                description={failureMode.equipment?.designation || "Failure Mode Details"}
            >
                <div className="flex items-center gap-2">
                    <Link href={`/home/amdec/failure-modes/${id}/edit`}>
                        <Button variant="outline" size="sm">
                            <Edit className="h-4 w-4 mr-2" />
                            Edit
                        </Button>
                    </Link>
                    <Link href={`/home/amdec/rpn-analysis/new?failure_mode_id=${id}`}>
                        <Button size="sm">
                            <History className="h-4 w-4 mr-2" />
                            Analyze RPN
                        </Button>
                    </Link>
                </div>
            </PageHeader>

            <div className="grid gap-6 md:grid-cols-3">
                <Card className="md:col-span-2">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-lg">
                            <Info className="h-5 w-5" />
                            General Information
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="grid gap-4 md:grid-cols-2">
                            <div>
                                <p className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Equipment</p>
                                <Link href={`/home/equipment/${failureMode.equipment_id}`} className="text-primary hover:underline font-medium">
                                    {failureMode.equipment?.designation || `Equipment #${failureMode.equipment_id}`}
                                </Link>
                            </div>
                            <div>
                                <p className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Status</p>
                                <Badge variant={failureMode.is_active ? 'default' : 'secondary'}>
                                    {failureMode.is_active ? 'Active' : 'Inactive'}
                                </Badge>
                            </div>
                        </div>

                        <div>
                            <p className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">Description</p>
                            <p className="p-3 bg-muted rounded-lg text-sm leading-relaxed">
                                {failureMode.description || 'No description provided.'}
                            </p>
                        </div>

                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="p-3 bg-muted/50 rounded-lg border border-muted">
                                <p className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2 mb-2">
                                    <AlertTriangle className="h-4 w-4 text-orange-500" />
                                    Potential Cause
                                </p>
                                <p className="text-sm">{failureMode.failure_cause || 'None specified'}</p>
                            </div>
                            <div className="p-3 bg-muted/50 rounded-lg border border-muted">
                                <p className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2 mb-2">
                                    <AlertCircle className="h-4 w-4 text-red-500" />
                                    Failure Effect
                                </p>
                                <p className="text-sm">{failureMode.failure_effect || 'None specified'}</p>
                            </div>
                        </div>

                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="p-3 bg-muted/50 rounded-lg border border-muted">
                                <p className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2 mb-2">
                                    <Eye className="h-4 w-4 text-blue-500" />
                                    Detection Method
                                </p>
                                <p className="text-sm">{failureMode.detection_method || 'None specified'}</p>
                            </div>
                            <div className="p-3 bg-muted/50 rounded-lg border border-muted">
                                <p className="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2 mb-2">
                                    <Shield className="h-4 w-4 text-green-500" />
                                    Prevention Action
                                </p>
                                <p className="text-sm">{failureMode.prevention_action || 'None specified'}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <div className="space-y-6">
                    {/* Latest RPN Badge */}
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium uppercase text-muted-foreground">Latest RPN</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            <div className="flex items-end gap-3">
                                <span className={`text-5xl font-bold rounded-lg px-4 py-2 ${rpnColor}`}>
                                    {latestRpn || 'N/A'}
                                </span>
                                {latestRpn && (
                                    <div className="text-sm text-muted-foreground mb-1">
                                        / 1000 Max
                                    </div>
                                )}
                            </div>
                            {latestRpn && (
                                <Badge variant="outline" className="mt-2">
                                    Analysis from {new Date(failureMode.latest_rpn_date).toLocaleDateString()}
                                </Badge>
                            )}
                        </CardContent>
                    </Card>

                    {/* RPN Components */}
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium uppercase text-muted-foreground">Components</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex justify-between items-center">
                                <span>Gravity (G)</span>
                                <Badge variant="secondary" className="h-8 w-8 flex items-center justify-center text-lg">{failureMode.gravity || '-'}</Badge>
                            </div>
                            <div className="flex justify-between items-center">
                                <span>Occurrence (O)</span>
                                <Badge variant="secondary" className="h-8 w-8 flex items-center justify-center text-lg">{failureMode.occurrence || '-'}</Badge>
                            </div>
                            <div className="flex justify-between items-center">
                                <span>Detection (D)</span>
                                <Badge variant="secondary" className="h-8 w-8 flex items-center justify-center text-lg">{failureMode.detection || '-'}</Badge>
                            </div>
                            <p className="text-[10px] text-muted-foreground text-center mt-2">Scale: 1 (Lowest) to 10 (Highest)</p>
                        </CardContent>
                    </Card>
                </div>
            </div>

            {/* Analysis History */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <History className="h-5 w-5" />
                        Analysis History
                    </CardTitle>
                    <CardDescription>Previous RPN evaluations for this failure mode</CardDescription>
                </CardHeader>
                <CardContent>
                    {analyses && analyses.length > 0 ? (
                        <div className="space-y-4">
                            {analyses.map((analysis: any) => (
                                <div key={analysis.id} className="flex items-center justify-between border-b pb-4 last:border-0 last:pb-0">
                                    <div className="flex gap-4">
                                        <div className="text-center w-12 flex flex-col items-center">
                                            <span className="text-2xl font-bold">{analysis.rpn_value}</span>
                                            <span className="text-[10px] uppercase text-muted-foreground">RPN</span>
                                        </div>
                                        <div>
                                            <p className="text-sm font-medium">Analyst: {analysis.analyst_name || 'N/A'}</p>
                                            <p className="text-xs text-muted-foreground flex items-center gap-1">
                                                <Calendar className="h-3 w-3" />
                                                {new Date(analysis.analysis_date).toLocaleDateString()}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex flex-col items-end gap-2 text-xs">
                                        <div className="flex gap-2">
                                            <span className="px-2 py-0.5 bg-muted rounded">G:{analysis.gravity}</span>
                                            <span className="px-2 py-0.5 bg-muted rounded">O:{analysis.occurrence}</span>
                                            <span className="px-2 py-0.5 bg-muted rounded">D:{analysis.detection}</span>
                                        </div>
                                        <Badge variant={analysis.action_status === 'completed' ? 'default' : 'outline'}>
                                            {analysis.action_status}
                                        </Badge>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-center py-8 text-muted-foreground italic">No analysis history available.</p>
                    )}
                </CardContent>
            </Card>
        </div >
    );
}
