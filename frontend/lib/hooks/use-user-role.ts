'use client';

import { useMemo } from 'react';
import { useUser } from '@kit/supabase/hooks/use-user';
import { UserRole, DEFAULT_ROLE, type UserRoleType } from '~/lib/roles';

/**
 * Hook to get the current user's role from Supabase JWT claims.
 * Role is sourced from app_metadata.role (single source of truth).
 *
 * @returns Object with role, loading state, and role check helpers
 */
export function useUserRole() {
    const { data: user, isLoading, error } = useUser();

    const role = useMemo<UserRoleType>(() => {
        if (!user) return DEFAULT_ROLE;

        // Try app_metadata.role first (Supabase standard)
        const appMetadata = (user as Record<string, unknown>).app_metadata as
            | Record<string, unknown>
            | undefined;
        if (appMetadata?.role) {
            const roleValue = appMetadata.role as string;
            if (Object.values(UserRole).includes(roleValue as UserRoleType)) {
                return roleValue as UserRoleType;
            }
        }

        // Fallback: check user_metadata
        const userMetadata = (user as Record<string, unknown>).user_metadata as
            | Record<string, unknown>
            | undefined;
        if (userMetadata?.role) {
            const roleValue = userMetadata.role as string;
            if (Object.values(UserRole).includes(roleValue as UserRoleType)) {
                return roleValue as UserRoleType;
            }
        }

        return DEFAULT_ROLE;
    }, [user]);

    // Role check helpers
    const isAdmin = role === UserRole.ADMIN;
    const isSupervisor = role === UserRole.SUPERVISOR;
    const isTechnician = role === UserRole.TECHNICIAN;
    const isViewer = role === UserRole.VIEWER;

    /**
     * Check if user has one of the allowed roles.
     */
    const hasRole = (allowedRoles: UserRoleType[]): boolean => {
        return allowedRoles.includes(role);
    };

    /**
     * Check if user is at least supervisor or admin.
     */
    const isSupervisorOrAbove = isAdmin || isSupervisor;

    /**
     * Check if user is at least technician.
     */
    const isTechnicianOrAbove = isAdmin || isSupervisor || isTechnician;

    return {
        role,
        isLoading,
        error,
        isAdmin,
        isSupervisor,
        isTechnician,
        isViewer,
        isSupervisorOrAbove,
        isTechnicianOrAbove,
        hasRole,
    };
}
