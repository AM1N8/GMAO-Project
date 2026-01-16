import { PageBody, PageHeader } from '@kit/ui/page';
import { RagChatInterface } from './_components/rag-chat-interface';

export default function AssistantPage() {
    return (
        <>
            <PageHeader
                title="AI Assistant"
                description="Ask questions about equipment, procedures, and interventions."
            />

            <PageBody>
                <RagChatInterface />
            </PageBody>
        </>
    );
}
