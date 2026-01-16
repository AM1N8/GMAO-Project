import { PageBody, PageHeader } from '@kit/ui/page';
import { ImportExportPanel } from './_components/import-export-panel';
import { SupervisorOrAbove } from '~/components/auth/role-guard';

export default function ImportExportPage() {
    return (
        <SupervisorOrAbove>
            <PageHeader
                title="Import / Export"
                description="Bulk data management for the GMAO system."
            />

            <PageBody>
                <ImportExportPanel />
            </PageBody>
        </SupervisorOrAbove>
    );
}
