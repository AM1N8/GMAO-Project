'use client';

import { PageBody, PageHeader } from '@kit/ui/page';
import { SparePartsTable } from './_components/spare-parts-table';
import { ReportDownloadButton } from '~/components/reports/report-download-button';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { SupervisorOrAbove } from '~/components/auth/role-guard';

export default function SparePartsPage() {
    const api = useGmaoApi();

    return (
        <>
            <PageHeader
                title="Spare Parts Inventory"
                description="Manage and track spare parts stock levels."
            >
                <SupervisorOrAbove>
                    <ReportDownloadButton
                        reportType="spare-parts"
                        onDownload={(format) => api.downloadSparePartsReport(format === 'pdf' ? 'excel' : format)}
                        supportsPdf={false}
                    />
                </SupervisorOrAbove>
            </PageHeader>

            <PageBody>
                <SparePartsTable />
            </PageBody>
        </>
    );
}
