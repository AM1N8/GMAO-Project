'use client';

import dynamic from 'next/dynamic';

import type { JwtPayload } from '@supabase/supabase-js';

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarNavigation,
} from '@kit/ui/shadcn-sidebar';

import { AppLogo } from '~/components/app-logo';
import { useFilteredNavigation } from '~/lib/hooks/use-filtered-navigation';
import { Tables } from '~/lib/database.types';

const ProfileAccountDropdownContainer = dynamic(
  () =>
    import('~/components/personal-account-dropdown-container').then(
      (mod) => mod.ProfileAccountDropdownContainer,
    ),
  { ssr: false },
);

export function HomeSidebar(props: {
  account?: Tables<'accounts'>;
  user: JwtPayload;
}) {
  const config = useFilteredNavigation();

  return (
    <Sidebar collapsible={'icon'}>
      <SidebarHeader className={'h-16 justify-center relative'}>
        <div className={'flex items-center justify-between space-x-2'}>
          <div>
            <AppLogo className={'max-w-full'} />
          </div>
        </div>
        {/* Gradient accent line */}
        <div className="absolute bottom-0 left-4 right-4 h-0.5 bg-gradient-to-r from-blue-600 via-blue-400 to-cyan-500 rounded-full opacity-60" />
      </SidebarHeader>

      <SidebarContent>
        <SidebarNavigation config={config} />
      </SidebarContent>

      <SidebarFooter>
        <ProfileAccountDropdownContainer
          user={props.user}
          account={props.account}
        />
      </SidebarFooter>
    </Sidebar>
  );
}
