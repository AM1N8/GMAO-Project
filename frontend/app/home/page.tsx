import { PageBody, PageHeader } from '@kit/ui/page';

import { GmaoHomeDashboard } from '~/home/_components/gmao-home-dashboard';

export default function HomePage() {
  return (
    <>
      <PageHeader
        title="GMAO Dashboard"
        description="Unified overview of maintenance operations, asset health, and critical risks."
      />

      <PageBody>
        <GmaoHomeDashboard />
      </PageBody>
    </>
  );
}
