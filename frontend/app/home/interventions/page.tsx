'use client';

import { PageBody, PageHeader } from '@kit/ui/page';
import { InterventionsTable } from './_components/interventions-table';
import { ReportDownloadButton } from '~/components/reports/report-download-button';
import { useGmaoApi } from '~/lib/hooks/use-gmao-api';
import { SupervisorOrAbove, TechnicianOnly } from '~/components/auth/role-guard';
import { Button } from '@kit/ui/button';
import { Sparkles } from 'lucide-react';
import Link from 'next/link';

export default function InterventionsPage() {
    const api = useGmaoApi();

    return (
        <>
            <PageHeader
                title="Interventions"
                description="Track and manage maintenance tasks."
            >
                <div className="flex gap-2">
                    <TechnicianOnly>
                        <Button asChild>
                            <Link href="/home/interventions/new">
                                <Sparkles className="mr-2 h-4 w-4" />
                                Log Intervention
                            </Link>
                        </Button>
                    </TechnicianOnly>

                    <SupervisorOrAbove>
                        <ReportDownloadButton
                            reportType="interventions"
                            onDownload={(format) => api.downloadInterventionsReport(format === 'pdf' ? 'excel' : format)}
                            supportsPdf={false}
                        />
                    </SupervisorOrAbove>
                </div>
            </PageHeader>

            <PageBody>
                <InterventionsTable />
            </PageBody>
        </>
    );
}
