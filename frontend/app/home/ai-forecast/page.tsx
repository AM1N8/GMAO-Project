'use client';

import { useState, useEffect } from 'react';
import { PageHeader } from '@kit/ui/page';
import { Button } from '@kit/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@kit/ui/select';
import { Alert, AlertDescription, AlertTitle } from '@kit/ui/alert';
import { Loader2, BrainCircuit, AlertCircle, Calendar } from 'lucide-react';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { ForecastResponse } from '~/lib/gmao-api';

import { RulGauge } from './_components/rul-gauge';
import { ForecastChart } from './_components/forecast-chart';
import { Card, CardContent, CardHeader, CardTitle } from '@kit/ui/card';
import { RoleGuard } from '~/components/auth/role-guard';

export default function AiForecastPage() {
    const api = useGmaoApi();
    const [selectedEquipment, setSelectedEquipment] = useState<string>('');
    const [loading, setLoading] = useState(false);
    const [forecast, setForecast] = useState<ForecastResponse | null>(null);
    const [equipmentList, setEquipmentList] = useState<{ id: number, designation: string }[]>([]);
    const [error, setError] = useState<string | null>(null);

    // Fetch equipment list on mount
    useEffect(() => {
        api.listEquipment().then(data => {
            setEquipmentList(data.map((e: any) => ({ id: e.id, designation: e.designation })));
            if (data.length > 0) setSelectedEquipment(data[0].id.toString());
        }).catch(err => console.error("Failed to load equipment", err));
    }, [api]);

    // Fetch forecast when equipment changes
    useEffect(() => {
        if (!selectedEquipment) return;

        const fetchForecast = async () => {
            setLoading(true);
            setError(null);
            try {
                const data = await api.getForecast(parseInt(selectedEquipment));
                setForecast(data);
            } catch (err: any) {
                console.error(err);
                setError(err.message || 'Failed to generate forecast');
                setForecast(null);
            } finally {
                setLoading(false);
            }
        };

        fetchForecast();
    }, [selectedEquipment, api]);

    return (
        <RoleGuard allowedRoles={['admin', 'supervisor', 'viewer']}>
            <div className="space-y-6">
                <PageHeader
                    title="AI Predictive Maintenance"
                    description="Forecast failures and maintenance needs using advanced ML models."
                />

                {/* Controls */}
                <div className="flex items-center gap-4 bg-card p-4 rounded-lg border">
                    <BrainCircuit className="h-6 w-6 text-primary" />
                    <div className="flex-1">
                        <Select value={selectedEquipment} onValueChange={setSelectedEquipment}>
                            <SelectTrigger className="w-[300px]">
                                <SelectValue placeholder="Select Equipment to Analyze" />
                            </SelectTrigger>
                            <SelectContent>
                                {equipmentList.map(eq => (
                                    <SelectItem key={eq.id} value={eq.id.toString()}>
                                        {eq.designation}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    {loading && <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />}
                </div>

                {error && (
                    <Alert variant="destructive">
                        <AlertCircle className="h-4 w-4" />
                        <AlertTitle>Forecast Error</AlertTitle>
                        <AlertDescription>{error}</AlertDescription>
                    </Alert>
                )}

                {forecast && (
                    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                        {/* RUL Gauge */}
                        <div className="md:col-span-1">
                            <RulGauge
                                rulDays={forecast.rul.predicted_rul_days}
                                confidence={forecast.rul.confidence_score}
                            />
                        </div>

                        {/* Stats */}
                        <Card className="md:col-span-1">
                            <CardHeader>
                                <CardTitle>Predicted Downtime (30d)</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-4xl font-bold">
                                    {Math.round(forecast.predicted_downtime_30d)}h
                                </div>
                                <p className="text-sm text-muted-foreground mt-2">
                                    Based on current MTTR of {Math.round(forecast.current_mttr)}h
                                </p>
                            </CardContent>
                        </Card>

                        <Card className="md:col-span-1">
                            <CardHeader>
                                <CardTitle>Next Failure Date</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="flex items-center gap-2 text-2xl font-bold">
                                    <Calendar className="h-6 w-6 text-primary" />
                                    {forecast.rul.predicted_failure_date || 'N/A'}
                                </div>
                                <p className="text-sm text-muted-foreground mt-2">
                                    Model: {forecast.rul.model_used} (RMSE: {forecast.rul.rmse_accuracy})
                                </p>
                            </CardContent>
                        </Card>

                        {/* Charts */}
                        <div className="col-span-full">
                            <ForecastChart
                                data={'error' in forecast.mtbf_forecast ? [] : (forecast.mtbf_forecast.forecast || [])}
                                modelName={'error' in forecast.mtbf_forecast ? 'Unavailable' : (forecast.mtbf_forecast.model || 'Unknown')}
                            />
                        </div>
                    </div>
                )}
            </div>
        </RoleGuard>
    );
}
