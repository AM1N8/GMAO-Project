import { PageHeader } from '@kit/ui/page';
import { AmdecDashboard } from './_components/amdec-dashboard';

export const metadata = {
    title: 'AMDEC - Risk Analysis',
    description: 'Failure Mode and Effects Analysis with RPN calculation',
};

import { SupervisorOrAbove } from '~/components/auth/role-guard';

export default function AmdecPage() {
    return (
        <SupervisorOrAbove>
            <div className="flex flex-col space-y-6">
                <PageHeader
                    title="AMDEC - Risk Analysis"
                    description="Failure Mode and Effects Analysis (FMEA) with Risk Priority Number (RPN) calculation"
                />
                <AmdecDashboard />
            </div>
        </SupervisorOrAbove>
    );
}
