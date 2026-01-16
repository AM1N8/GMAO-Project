import { PageBody, PageHeader } from '@kit/ui/page';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@kit/ui/button';
import Link from 'next/link';

import { EquipmentDetails } from '../_components/equipment-details';

export default function EquipmentDetailsPage() {
    return (
        <>
            <PageHeader
                title="Equipment Details"
                description="View specifications and analytics."
            >
                <Button variant="ghost" asChild>
                    <Link href="/home/equipment">
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back to List
                    </Link>
                </Button>
            </PageHeader>

            <PageBody>
                <EquipmentDetails />
            </PageBody>
        </>
    );
}
