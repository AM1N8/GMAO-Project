'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import { Badge } from '@kit/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@kit/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@kit/ui/tabs';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { Activity, Calendar, MapPin, Settings } from 'lucide-react';

export function EquipmentDetails() {
    const params = useParams();
    const id = Number(params?.id);
    const api = useGmaoApi();

    const { data: equipment, isLoading } = useQuery({
        queryKey: ['equipment', id],
        queryFn: () => api.getEquipment(id),
        enabled: !!id,
    });

    const { data: predictions, isLoading: isLoadingPreds } = useQuery({
        queryKey: ['equipment-predictions', id],
        queryFn: () => api.getEquipmentPredictions(id, 'mtbf'),
        enabled: !!id,
    });

    if (isLoading) return <div>Loading details...</div>;
    if (!equipment) return <div>Equipment not found</div>;

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">{equipment.designation}</h1>
                    <div className="mt-2 flex items-center space-x-4 text-sm text-muted-foreground">
                        <span className="flex items-center">
                            <Settings className="mr-1 h-4 w-4" />
                            {equipment.model}
                        </span>
                        <span className="flex items-center">
                            <MapPin className="mr-1 h-4 w-4" />
                            {equipment.location}
                        </span>
                        <Badge variant={equipment.status === 'active' ? 'default' : 'secondary'}>
                            {equipment.status}
                        </Badge>
                    </div>
                </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle>Specifications</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">Manufacturer:</span>
                            <span className="font-medium">{equipment.manufacturer}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">Serial Number:</span>
                            <span className="font-medium">{equipment.serial_number || 'N/A'}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">Type:</span>
                            <span className="font-medium">{equipment.type}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">Acquisition Date:</span>
                            <span className="font-medium">
                                {equipment.acquisition_date ? new Date(equipment.acquisition_date).toLocaleDateString() : 'N/A'}
                            </span>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>AI Insights (ML)</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {isLoadingPreds ? (
                            <div>Analyzing...</div>
                        ) : (
                            <div className="space-y-4">
                                <div className="rounded-lg border p-4">
                                    <div className="text-sm text-muted-foreground">Predicted MTBF</div>
                                    <div className="text-2xl font-bold text-primary">
                                        {predictions?.predicted_value
                                            ? `${predictions.predicted_value.toFixed(2)} hours`
                                            : 'Not enough data'}
                                    </div>
                                    {predictions?.confidence_score && (
                                        <div className="mt-1 text-xs text-muted-foreground">
                                            Confidence: {(predictions.confidence_score * 100).toFixed(1)}%
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            <Tabs defaultValue="history">
                <TabsList>
                    <TabsTrigger value="history">Intervention History</TabsTrigger>
                    <TabsTrigger value="docs">Documentation (RAG)</TabsTrigger>
                </TabsList>
                <TabsContent value="history" className="pt-4">
                    <Card>
                        <CardContent className="pt-6">
                            <div className="text-center text-muted-foreground">
                                No recent interventions.
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
                <TabsContent value="docs" className="pt-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Ask about this equipment</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-center text-muted-foreground">
                                RAG Chat integration coming soon.
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
