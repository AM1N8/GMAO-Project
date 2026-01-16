'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@kit/ui/card';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface ForecastData {
    date: string;
    predicted_mtbf: number;
    lower_bound: number;
    upper_bound: number;
}

interface ForecastChartProps {
    data: ForecastData[];
    modelName: string;
}

export function ForecastChart({ data, modelName }: ForecastChartProps) {
    return (
        <Card className="col-span-1 lg:col-span-2">
            <CardHeader>
                <CardTitle>MTBF Forecast Trend ({modelName || 'Unknown'})</CardTitle>
            </CardHeader>
            <CardContent className="h-[400px]">
                {(!data || data.length === 0) ? (
                    <div className="flex h-full items-center justify-center text-muted-foreground">
                        No forecast data available (insufficient history)
                    </div>
                ) : (
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                            <defs>
                                <linearGradient id="colorMtbf" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8} />
                                    <stop offset="95%" stopColor="#8884d8" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <XAxis dataKey="date" />
                            <YAxis label={{ value: 'MTBF (Hours)', angle: -90, position: 'insideLeft' }} />
                            <CartesianGrid strokeDasharray="3 3" />
                            <Tooltip />

                            <Area
                                type="monotone"
                                dataKey="lower_bound"
                                stackId="1"
                                stroke="transparent"
                                fill="transparent"
                            />
                            <Area
                                type="monotone"
                                dataKey="predicted_mtbf"
                                stackId="2"
                                stroke="#8884d8"
                                fillOpacity={1}
                                fill="url(#colorMtbf)"
                                name="Forecast MTBF"
                            />
                            <Area
                                type="monotone"
                                dataKey="upper_bound"
                                stackId="3"
                                stroke="transparent"
                                fill="#8884d8"
                                fillOpacity={0.1}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                )}
            </CardContent>
        </Card>
    );
}
