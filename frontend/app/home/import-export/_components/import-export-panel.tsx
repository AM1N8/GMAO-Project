'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@kit/ui/card';
import { Button } from '@kit/ui/button';
import { Input } from '@kit/ui/input';
import { Label } from '@kit/ui/label';
import { RadioGroup, RadioGroupItem } from '@kit/ui/radio-group';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@kit/ui/select';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { Download, Upload, FileSpreadsheet, FileText, Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@kit/ui/alert';

export function ImportExportPanel() {
    const [importFile, setImportFile] = useState<File | null>(null);
    const [isExporting, setIsExporting] = useState(false);
    const [isImporting, setIsImporting] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

    // Selection states
    const [exportType, setExportType] = useState('interventions');
    const [exportFormat, setExportFormat] = useState('csv');
    const [importType, setImportType] = useState('gmao');

    const api = useGmaoApi();

    const handleExport = async () => {
        setIsExporting(true);
        setMessage(null);

        try {
            let blob: Blob;

            switch (exportType) {
                case 'interventions':
                    blob = await api.exportInterventions(exportFormat as 'csv' | 'excel');
                    break;
                case 'equipment':
                    blob = await api.exportEquipment(exportFormat as 'csv' | 'excel');
                    break;
                case 'spare-parts':
                    blob = await api.exportSpareParts(exportFormat as 'csv' | 'excel');
                    break;
                case 'kpi-report':
                    blob = await api.exportKpiReport(exportFormat as 'excel' | 'pdf');
                    break;
                case 'amdec-report':
                    blob = await api.exportAmdecReport(exportFormat as 'excel' | 'pdf');
                    break;
                default:
                    throw new Error('Invalid export type');
            }

            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const ext = exportFormat === 'excel' ? 'xlsx' : exportFormat;
            a.download = `gmao_${exportType}_${new Date().toISOString().split('T')[0]}.${ext}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            setMessage({ type: 'success', text: 'Export completed successfully!' });
        } catch (err) {
            console.error(err);
            setMessage({ type: 'error', text: 'Export failed. Please try again.' });
        } finally {
            setIsExporting(false);
        }
    };

    const handleImport = async () => {
        if (!importFile) return;

        setIsImporting(true);
        setMessage(null);

        try {
            let result;
            switch (importType) {
                case 'gmao':
                    result = await api.importGmao(importFile);
                    break;
                case 'amdec':
                    result = await api.importAmdec(importFile);
                    break;
                case 'workload':
                    result = await api.importWorkload(importFile);
                    break;
                default:
                    throw new Error('Invalid import type');
            }

            setMessage({
                type: 'success',
                text: `Import successful! ${result.total_processed || 'Data'} records processed.`
            });
            setImportFile(null);
            // Reset file input value manually if needed, or rely on key change
        } catch (err: any) {
            console.error(err);
            setMessage({ type: 'error', text: err.message || 'Import failed. Check file format.' });
        } finally {
            setIsImporting(false);
        }
    };

    return (
        <div className="grid gap-6 lg:grid-cols-2">
            {/* EXPORT CARD */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Download className="h-5 w-5" />
                        Export Data
                    </CardTitle>
                    <CardDescription>
                        Download reports and datasets from the system.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="space-y-3">
                        <Label>Select Data Type</Label>
                        <RadioGroup value={exportType} onValueChange={setExportType} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="flex items-center space-x-2 border rounded p-3 hover:bg-accent cursor-pointer">
                                <RadioGroupItem value="interventions" id="exp-interventions" />
                                <Label htmlFor="exp-interventions" className="cursor-pointer">Interventions</Label>
                            </div>
                            <div className="flex items-center space-x-2 border rounded p-3 hover:bg-accent cursor-pointer">
                                <RadioGroupItem value="equipment" id="exp-equipment" />
                                <Label htmlFor="exp-equipment" className="cursor-pointer">Equipment</Label>
                            </div>
                            <div className="flex items-center space-x-2 border rounded p-3 hover:bg-accent cursor-pointer">
                                <RadioGroupItem value="spare-parts" id="exp-sp" />
                                <Label htmlFor="exp-sp" className="cursor-pointer">Spare Parts</Label>
                            </div>
                            <div className="flex items-center space-x-2 border rounded p-3 hover:bg-accent cursor-pointer">
                                <RadioGroupItem value="kpi-report" id="exp-kpi" />
                                <Label htmlFor="exp-kpi" className="cursor-pointer">KPI Report</Label>
                            </div>
                            <div className="flex items-center space-x-2 border rounded p-3 hover:bg-accent cursor-pointer">
                                <RadioGroupItem value="amdec-report" id="exp-amdec" />
                                <Label htmlFor="exp-amdec" className="cursor-pointer">AMDEC Report</Label>
                            </div>
                        </RadioGroup>
                    </div>

                    <div className="space-y-3">
                        <Label>Format</Label>
                        <div className="flex gap-2">
                            {['kpi-report', 'amdec-report'].includes(exportType) ? (
                                <>
                                    <Button
                                        variant={exportFormat === 'excel' ? 'default' : 'outline'}
                                        onClick={() => setExportFormat('excel')}
                                        size="sm"
                                        className="w-24 border-zinc-200 dark:border-zinc-800"
                                    >
                                        <FileSpreadsheet className="mr-2 h-4 w-4" />
                                        Excel
                                    </Button>
                                    <Button
                                        variant={exportFormat === 'pdf' ? 'default' : 'outline'}
                                        onClick={() => setExportFormat('pdf')}
                                        size="sm"
                                        className="w-24 border-zinc-200 dark:border-zinc-800"
                                    >
                                        <FileText className="mr-2 h-4 w-4" />
                                        PDF
                                    </Button>
                                </>
                            ) : (
                                <>
                                    <Button
                                        variant={exportFormat === 'csv' ? 'default' : 'outline'}
                                        onClick={() => setExportFormat('csv')}
                                        size="sm"
                                        className="w-24 border-zinc-200 dark:border-zinc-800"
                                    >
                                        <FileText className="mr-2 h-4 w-4" />
                                        CSV
                                    </Button>
                                    <Button
                                        variant={exportFormat === 'excel' ? 'default' : 'outline'}
                                        onClick={() => setExportFormat('excel')}
                                        size="sm"
                                        className="w-24 border-zinc-200 dark:border-zinc-800"
                                    >
                                        <FileSpreadsheet className="mr-2 h-4 w-4" />
                                        Excel
                                    </Button>
                                </>
                            )}
                        </div>
                    </div>

                    <Button
                        onClick={handleExport}
                        disabled={isExporting}
                        className="w-full"
                    >
                        {isExporting ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Exporting...
                            </>
                        ) : (
                            <>
                                <Download className="mr-2 h-4 w-4" />
                                Download {exportType.replace('-', ' ').toUpperCase()}
                            </>
                        )}
                    </Button>
                </CardContent>
            </Card>

            {/* IMPORT CARD */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Upload className="h-5 w-5" />
                        Import Data
                    </CardTitle>
                    <CardDescription>
                        Upload CSV files to update the system database.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="space-y-3">
                        <Label>Import Type</Label>
                        <Select value={importType} onValueChange={setImportType}>
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="gmao">GMAO Data (Spare Parts Linkage)</SelectItem>
                                <SelectItem value="amdec">AMDEC Data (Failure Modes)</SelectItem>
                                <SelectItem value="workload">Workload Data (Technicians)</SelectItem>
                            </SelectContent>
                        </Select>
                        <p className="text-xs text-muted-foreground p-1">
                            {importType === 'gmao' && "Expects CSV with: Désignation, Pièce, Quantité, etc."}
                            {importType === 'amdec' && "Expects CSV with: Mode de défaillance, Cause, Effet, etc."}
                            {importType === 'workload' && "Expects CSV with: Intervenant, Heures, Date, etc."}
                        </p>
                    </div>

                    <div className="space-y-3">
                        <Label htmlFor="import-file">Select File</Label>
                        <Input
                            id="import-file"
                            type="file"
                            accept=".csv"
                            className="cursor-pointer file:cursor-pointer"
                            onChange={(e) => {
                                if (e.target.files && e.target.files[0]) {
                                    setImportFile(e.target.files[0]);
                                    setMessage(null);
                                }
                            }}
                        />
                    </div>

                    <Alert variant="default" className="bg-muted/50">
                        <AlertDescription className="text-xs text-muted-foreground">
                            Note: Max file size is 10MB. Only CSV files are supported for import.
                            Duplicate entries will be handled according to system rules.
                        </AlertDescription>
                    </Alert>

                    <Button
                        onClick={handleImport}
                        disabled={!importFile || isImporting}
                        className="w-full"
                    >
                        {isImporting ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Importing...
                            </>
                        ) : (
                            <>
                                <Upload className="mr-2 h-4 w-4" />
                                Start Import
                            </>
                        )}
                    </Button>
                </CardContent>
            </Card>

            {/* STATUS MESSAGE */}
            {message && (
                <div className="lg:col-span-2">
                    <Alert variant={message.type === 'success' ? 'default' : 'destructive'}
                        className={message.type === 'success' ? 'border-green-200 bg-green-50 dark:bg-green-900/20 dark:border-green-800' : ''}>
                        {message.type === 'success' ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                        <AlertTitle>{message.type === 'success' ? 'Success' : 'Error'}</AlertTitle>
                        <AlertDescription>{message.text}</AlertDescription>
                    </Alert>
                </div>
            )}
        </div>
    );
}
