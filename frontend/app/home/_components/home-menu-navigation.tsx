'use client';

import dynamic from 'next/dynamic';

import {
  BorderedNavigationMenu,
  BorderedNavigationMenuItem,
} from '@kit/ui/bordered-navigation-menu';

import { AppLogo } from '~/components/app-logo';
import { useFilteredNavigation } from '~/lib/hooks/use-filtered-navigation';

const ProfileAccountDropdownContainer = dynamic(
  () =>
    import('~/components/personal-account-dropdown-container').then(
      (mod) => mod.ProfileAccountDropdownContainer,
    ),
  { ssr: false },
);

export function HomeMenuNavigation() {
  const { routes: filteredRoutes } = useFilteredNavigation();

  const routes = filteredRoutes.reduce<
    Array<{
      path: string;
      label: string;
      Icon?: React.ReactNode;
      end?: boolean | ((path: string) => boolean);
    }>
  >((acc, item) => {
    if ('children' in item) {
      return [...acc, ...item.children];
    }

    if ('divider' in item) {
      return acc;
    }

    return [...acc, item];
  }, []);

  return (
    <div className={'flex w-full flex-1 justify-between'}>
      <div className={'flex items-center space-x-8'}>
        <AppLogo />

        <BorderedNavigationMenu>
          {routes.map((route) => (
            <BorderedNavigationMenuItem {...route} key={route.path} />
          ))}
        </BorderedNavigationMenu>
      </div>

      <div className={'flex justify-end space-x-2.5'}>
        <div>
          <ProfileAccountDropdownContainer showProfileName={false} />
        </div>
      </div>
    </div>
  );
}
