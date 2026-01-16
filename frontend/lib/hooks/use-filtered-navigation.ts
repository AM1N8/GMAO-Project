'use client';

import { useMemo } from 'react';
import { useUserRole } from '~/lib/hooks/use-user-role';
import { navigationConfig } from '~/config/navigation.config';
import { UserRoleType } from '~/lib/roles';

/**
 * Hook to get the navigation configuration filtered by the current user's role.
 */
export function useFilteredNavigation() {
    const { role, isLoading } = useUserRole();

    const filteredRoutes = useMemo(() => {
        if (isLoading) return [];

        // Recursive function to filter routes and their children immutably
        const filterItems = (items: any[]): any[] => {
            return items.reduce((acc, item) => {
                // Check current item access
                if (item.allowedRoles && !item.allowedRoles.includes(role)) {
                    return acc;
                }

                // Create a clone of the item to avoid mutating the original config
                const clonedItem = { ...item };

                // Recursively filter children if they exist
                if (clonedItem.children) {
                    clonedItem.children = filterItems(clonedItem.children);

                    // If a group has children but they were all filtered out, hide the group
                    if (clonedItem.children.length === 0) {
                        return acc;
                    }
                }

                return [...acc, clonedItem];
            }, []);
        };

        return filterItems([...navigationConfig.routes]);
    }, [role, isLoading]);

    return {
        ...navigationConfig,
        routes: filteredRoutes,
    };
}
