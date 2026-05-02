-- Migration: Performance indexes for Phase 4
-- Wave 1

-- Funds: frequent lookups by fund_code
CREATE INDEX IF NOT EXISTS idx_funds_fund_code ON business.funds(fund_code);

-- Announcements: frequent filters by publish_date
CREATE INDEX IF NOT EXISTS idx_announcements_publish_date ON business.announcements(publish_date);
CREATE INDEX IF NOT EXISTS idx_announcements_fund_code ON business.announcements(fund_code);

-- Users: login lookups
CREATE INDEX IF NOT EXISTS idx_users_username ON admin.users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON admin.users(email);

-- Dividends: frequent queries by fund_code + record_date
CREATE INDEX IF NOT EXISTS idx_dividends_fund_code ON business.dividends(fund_code);
CREATE INDEX IF NOT EXISTS idx_dividends_record_date ON business.dividends(record_date);
