-- Migration: Add JWT auth fields to users table + role/permission junction tables
-- Phase 3 - Wave 1

-- Extend users table for refresh token tracking and account security
ALTER TABLE admin.users
    ADD COLUMN IF NOT EXISTS refresh_token_jti VARCHAR(64) NULL,
    ADD COLUMN IF NOT EXISTS refresh_token_expires TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS failed_login_attempts INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ NULL;

CREATE INDEX IF NOT EXISTS idx_users_refresh_token_jti
    ON admin.users(refresh_token_jti);

-- User-Role many-to-many junction table
CREATE TABLE IF NOT EXISTS admin.user_roles (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES admin.users(id) ON DELETE CASCADE,
    role_id INT NOT NULL REFERENCES admin.roles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON admin.user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role_id ON admin.user_roles(role_id);

-- Role-Permission many-to-many junction table
CREATE TABLE IF NOT EXISTS admin.role_permissions (
    id SERIAL PRIMARY KEY,
    role_id INT NOT NULL REFERENCES admin.roles(id) ON DELETE CASCADE,
    permission_id INT NOT NULL REFERENCES admin.permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(role_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id ON admin.role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission_id ON admin.role_permissions(permission_id);
