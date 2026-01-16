import { PageBody, PageHeader } from '@kit/ui/page';
import { TechniciansTable } from './_components/technicians-table';
import { AdminOnly } from '~/components/auth/role-guard';

export default function TechniciansPage() {
    return (
        <AdminOnly>
            <PageHeader
                title="Technicians"
                description="Manage technician profiles and assignments."
            />

            <PageBody>
                <TechniciansTable />
            </PageBody>
        </AdminOnly>
    );
}
