'use client';

import { type ReactNode } from 'react';
import { useUserRole } from '~/lib/hooks/use-user-role';
import { type UserRoleType } from '~/lib/roles';

interface RoleGuardProps {
    /**
     * Roles that are allowed to see the children.
     */
    allowedRoles: UserRoleType[];

    /**
     * Content to show when user has required role.
     */
    children: ReactNode;

    /**
     * Optional content to show when user doesn't have required role.
     * If not provided, nothing is rendered.
     */
    fallback?: ReactNode;

    /**
     * If true, shows loading state while role is being determined.
     * Default: false (renders nothing while loading)
     */
    showLoadingState?: boolean;
}

/**
 * RoleGuard component for conditional rendering based on user role.
 * Use this to hide/show UI elements based on the user's role.
 *
 * @example
 * // Show button only for admins and supervisors
 * <RoleGuard allowedRoles={['admin', 'supervisor']}>
 *   <DeleteButton />
 * </RoleGuard>
 *
 * @example
 * // Show different content for different roles
 * <RoleGuard allowedRoles={['admin']} fallback={<ViewOnlyMessage />}>
 *   <EditForm />
 * </RoleGuard>
 */
export function RoleGuard({
    allowedRoles,
    children,
    fallback = null,
    showLoadingState = false,
}: RoleGuardProps) {
    const { role, isLoading, hasRole } = useUserRole();

    // Handle loading state
    if (isLoading) {
        if (showLoadingState) {
            return (
                <div className="animate-pulse bg-muted h-8 w-24 rounded" />
            );
        }
        return null;
    }

    // Check if user has required role
    if (hasRole(allowedRoles)) {
        return <>{children}</>;
    }

    // User doesn't have required role
    return <>{fallback}</>;
}

/**
 * Convenience component for admin-only content.
 */
export function AdminOnly({
    children,
    fallback,
}: {
    children: ReactNode;
    fallback?: ReactNode;
}) {
    return (
        <RoleGuard allowedRoles={['admin']} fallback={fallback}>
            {children}
        </RoleGuard>
    );
}

/**
 * Convenience component for supervisor+ content (supervisor and admin).
 */
export function SupervisorOrAbove({
    children,
    fallback,
}: {
    children: ReactNode;
    fallback?: ReactNode;
}) {
    return (
        <RoleGuard allowedRoles={['admin', 'supervisor']} fallback={fallback}>
            {children}
        </RoleGuard>
    );
}

/**
 * Convenience component for technician+ content (technician, supervisor, admin).
 */
export function TechnicianOrAbove({
    children,
    fallback,
}: {
    children: ReactNode;
    fallback?: ReactNode;
}) {
    return (
        <RoleGuard
            allowedRoles={['admin', 'supervisor', 'technician']}
            fallback={fallback}
        >
            {children}
        </RoleGuard>
    );
}

/**
 * Convenience component for technician-only content.
 */
export function TechnicianOnly({
    children,
    fallback,
}: {
    children: ReactNode;
    fallback?: ReactNode;
}) {
    return (
        <RoleGuard allowedRoles={['technician']} fallback={fallback}>
            {children}
        </RoleGuard>
    );
}
