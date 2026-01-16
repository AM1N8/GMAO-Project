import { CopilotInterface } from './_components/copilot-interface';
import { PageBody, PageHeader } from '@kit/ui/page';

export default function CopilotPage() {
    return (
        <>
            <PageHeader
                title="Maintenance Copilot"
                description="Your AI-powered assistant for maintenance engineering and decision support."
            />

            <PageBody>
                <div className="max-w-5xl mx-auto w-full">
                    <CopilotInterface />
                </div>
            </PageBody>
        </>
    );
}
