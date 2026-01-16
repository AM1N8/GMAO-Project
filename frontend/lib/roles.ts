/**
 * User roles for RBAC.
 * Roles are sourced from Supabase app_metadata.role (single source of truth).
 */

export const UserRole = {
    ADMIN: 'admin',
    SUPERVISOR: 'supervisor',
    TECHNICIAN: 'technician',
    VIEWER: 'viewer',
} as const;

export type UserRoleType = (typeof UserRole)[keyof typeof UserRole];

/**
 * Role hierarchy for permission checks.
 * Higher index = more permissions.
 */
export const ROLE_HIERARCHY: UserRoleType[] = [
    UserRole.VIEWER,
    UserRole.TECHNICIAN,
    UserRole.SUPERVISOR,
    UserRole.ADMIN,
];

/**
 * Check if a role has at least the minimum permission level.
 */
export function hasMinimumRole(
    userRole: UserRoleType,
    minimumRole: UserRoleType
): boolean {
    const userIndex = ROLE_HIERARCHY.indexOf(userRole);
    const minimumIndex = ROLE_HIERARCHY.indexOf(minimumRole);
    return userIndex >= minimumIndex;
}

/**
 * Check if a user has one of the allowed roles.
 */
export function hasAllowedRole(
    userRole: UserRoleType,
    allowedRoles: UserRoleType[]
): boolean {
    return allowedRoles.includes(userRole);
}

/**
 * Default role for users without explicit assignment.
 */
export const DEFAULT_ROLE: UserRoleType = UserRole.VIEWER;
