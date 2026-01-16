import { PageBody, PageHeader } from '@kit/ui/page';
import { OcrUploader } from './_components/ocr-uploader';
import { TechnicianOrAbove } from '~/components/auth/role-guard';

export default function OcrPage() {
    return (
        <>
            <PageHeader
                title="OCR Document Scanner"
                description="Extract text from images and scanned documents."
            />

            <PageBody>
                <TechnicianOrAbove>
                    <OcrUploader />
                </TechnicianOrAbove>
            </PageBody>
        </>
    );
}
