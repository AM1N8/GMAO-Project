import { PageBody, PageHeader } from '@kit/ui/page';
import { KpiDashboard } from './_components/kpi-dashboard';

export default function KpiPage() {
    return (
        <>
            <PageHeader
                title="KPI Analytics"
                description="Monitor key performance indicators and maintenance metrics."
            />

            <PageBody>
                <KpiDashboard />
            </PageBody>
        </>
    );
}
