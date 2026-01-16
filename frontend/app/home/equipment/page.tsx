'use client';

import { PageBody, PageHeader } from '@kit/ui/page';
import { Button } from '@kit/ui/button';
import { Plus } from 'lucide-react';
import Link from 'next/link';

import { EquipmentTable } from './_components/equipment-table';
import { ReportDownloadButton } from '~/components/reports/report-download-button';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { SupervisorOrAbove } from '~/components/auth/role-guard';

export default function EquipmentPage() {
    const api = useGmaoApi();

    return (
        <>
            <PageHeader
                title="Equipment"
                description="Manage your machinery and assets."
            >
                <div className="flex gap-2">
                    {/* Export: Supervisor+ only */}
                    <SupervisorOrAbove>
                        <ReportDownloadButton
                            reportType="equipment"
                            onDownload={(format) => api.downloadEquipmentReport(format === 'pdf' ? 'excel' : format)}
                            supportsPdf={false}
                        />
                    </SupervisorOrAbove>

                    {/* Add Equipment: Supervisor+ only */}
                    <SupervisorOrAbove>
                        <Button asChild>
                            <Link href="/home/equipment/new">
                                <Plus className="mr-2 h-4 w-4" />
                                Add Equipment
                            </Link>
                        </Button>
                    </SupervisorOrAbove>
                </div>
            </PageHeader>

            <PageBody>
                <EquipmentTable />
            </PageBody>
        </>
    );
}
