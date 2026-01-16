'use client';

import { useState } from 'react';
import { Download, FileSpreadsheet, FileText, Loader2, ChevronDown } from 'lucide-react';
import { Button } from '@kit/ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@kit/ui/dropdown-menu';
import { toast } from 'sonner';

export type ReportFormat = 'excel' | 'pdf';

interface ReportDownloadButtonProps {
    /** Report type identifier */
    reportType: 'kpi' | 'amdec' | 'equipment' | 'interventions' | 'spare-parts';
    /** Function to perform the download, returns the Blob */
    onDownload: (format: ReportFormat) => Promise<Blob>;
    /** Button variant */
    variant?: 'default' | 'outline' | 'secondary' | 'ghost';
    /** Button size */
    size?: 'default' | 'sm' | 'lg';
    /** Additional class names */
    className?: string;
    /** Whether PDF format is available */
    supportsPdf?: boolean;
}

const REPORT_NAMES: Record<string, string> = {
    kpi: 'KPI Report',
    amdec: 'AMDEC Report',
    equipment: 'Equipment Report',
    interventions: 'Interventions Report',
    'spare-parts': 'Spare Parts Report',
};

/**
 * Reusable report download button with format selection.
 * Supports Excel and PDF formats with loading state and error handling.
 */
export function ReportDownloadButton({
    reportType,
    onDownload,
    variant = 'outline',
    size = 'default',
    className = '',
    supportsPdf = true,
}: ReportDownloadButtonProps) {
    const [isLoading, setIsLoading] = useState(false);
    const [loadingFormat, setLoadingFormat] = useState<ReportFormat | null>(null);

    const handleDownload = async (format: ReportFormat) => {
        setIsLoading(true);
        setLoadingFormat(format);

        try {
            const blob = await onDownload(format);

            // Create download link
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;

            // Generate filename
            const timestamp = new Date().toISOString().slice(0, 10);
            const extension = format === 'excel' ? 'xlsx' : 'pdf';
            link.download = `${reportType}_report_${timestamp}.${extension}`;

            // Trigger download
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);

            toast.success(`${REPORT_NAMES[reportType]} downloaded successfully`, {
                description: `Format: ${format.toUpperCase()}`,
            });
        } catch (error: any) {
            console.error('Download error:', error);
            toast.error('Failed to download report', {
                description: error.message || 'Please try again later',
            });
        } finally {
            setIsLoading(false);
            setLoadingFormat(null);
        }
    };

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button
                    variant={variant}
                    size={size}
                    className={`gap-2 ${className}`}
                    disabled={isLoading}
                >
                    {isLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                        <Download className="h-4 w-4" />
                    )}
                    {isLoading ? 'Generating...' : 'Download Report'}
                    <ChevronDown className="h-3 w-3 opacity-50" />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem
                    onClick={() => handleDownload('excel')}
                    disabled={isLoading}
                    className="cursor-pointer"
                >
                    <FileSpreadsheet className="h-4 w-4 mr-2 text-green-600" />
                    <span>Excel (.xlsx)</span>
                    {loadingFormat === 'excel' && (
                        <Loader2 className="h-3 w-3 ml-auto animate-spin" />
                    )}
                </DropdownMenuItem>
                {supportsPdf && (
                    <DropdownMenuItem
                        onClick={() => handleDownload('pdf')}
                        disabled={isLoading}
                        className="cursor-pointer"
                    >
                        <FileText className="h-4 w-4 mr-2 text-red-600" />
                        <span>PDF (.pdf)</span>
                        {loadingFormat === 'pdf' && (
                            <Loader2 className="h-3 w-3 ml-auto animate-spin" />
                        )}
                    </DropdownMenuItem>
                )}
            </DropdownMenuContent>
        </DropdownMenu>
    );
}
