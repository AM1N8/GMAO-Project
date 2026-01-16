import { PageBody, PageHeader } from '@kit/ui/page';
import { SupervisorOrAbove } from '~/components/auth/role-guard';
import { TrainingPriorityDashboard } from './_components/training-dashboard';
import { DocumentationSheet } from './_components/documentation-sheet';

export const metadata = {
    title: 'Training Priority Analysis',
    description: 'AI-driven training prioritization based on AMDEC risk and intervention history.',
};

export default function TrainingPriorityPage() {
    return (
        <SupervisorOrAbove>
            <PageHeader
                title="Training Priority Analysis"
                description="Prioritize technical training based on meaningful maintenance data and AMDEC risk assessment."
            >
                <div className="flex items-center gap-2">
                    <DocumentationSheet />
                </div>
            </PageHeader>

            <PageBody>
                <TrainingPriorityDashboard />
            </PageBody>
        </SupervisorOrAbove>
    );
}
