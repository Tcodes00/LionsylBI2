-- ============================================================
-- LionsylAI - MySQL Initialization Script
-- Run once on first deployment
-- ============================================================

CREATE DATABASE IF NOT EXISTS lionsylai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE lionsylai;

GRANT ALL PRIVILEGES ON lionsylai.* TO 'lionsylai_user'@'%';
FLUSH PRIVILEGES;

-- ---- Users --------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  username              VARCHAR(80)  NOT NULL UNIQUE,
  email                 VARCHAR(120) NOT NULL UNIQUE,
  password_hash         VARCHAR(256) NOT NULL,
  full_name             VARCHAR(120),
  org_name              VARCHAR(150),
  role                  VARCHAR(20) DEFAULT 'user',
  subscription          VARCHAR(20) DEFAULT 'free',
  is_active             BOOLEAN DEFAULT TRUE,
  is_email_verified     BOOLEAN DEFAULT FALSE,
  email_verify_token    VARCHAR(128),
  email_verify_expires  DATETIME,
  two_fa_secret         VARCHAR(64),
  two_fa_enabled        BOOLEAN DEFAULT FALSE,
  stripe_customer_id    VARCHAR(64),
  stripe_sub_id         VARCHAR(64),
  sub_expires_at        DATETIME,
  avatar_url            VARCHAR(256),
  preferences_json      TEXT,
  manual_status         VARCHAR(20),
  account_owner_id      INT NULL,
  created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_login            DATETIME,
  last_seen             DATETIME,
  INDEX idx_email    (email),
  INDEX idx_username (username),
  INDEX idx_account_owner (account_owner_id),
  FOREIGN KEY (account_owner_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---- Team Members ---------------------------------------------
CREATE TABLE IF NOT EXISTS team_members (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  user_id         INT NOT NULL,
  name            VARCHAR(120) NOT NULL,
  email           VARCHAR(120) NOT NULL,
  role            VARCHAR(60)  DEFAULT 'Analyst',
  status          VARCHAR(20)  DEFAULT 'Active',
  is_owner        BOOLEAN DEFAULT FALSE,
  -- Real account link: set once the invited email actually registers/logs
  -- in, so presence + activity reflect that person's genuine account.
  member_user_id  INT NULL,
  last_active     DATETIME DEFAULT CURRENT_TIMESTAMP,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (member_user_id) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_user_id (user_id),
  INDEX idx_member_user_id (member_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---- Integrations -----------------------------------------------
CREATE TABLE IF NOT EXISTS integrations (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT NOT NULL,
  name         VARCHAR(120) NOT NULL,
  itype        VARCHAR(60)  NOT NULL,
  status       VARCHAR(30)  DEFAULT 'Not Configured',
  api_endpoint VARCHAR(256),
  api_key_enc  TEXT,
  success_rate FLOAT DEFAULT 0.0,
  last_sync    DATETIME,
  sync_freq    VARCHAR(20) DEFAULT 'Daily',
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---- Reports ------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  user_id     INT NOT NULL,
  name        VARCHAR(200) NOT NULL,
  rtype       VARCHAR(60)  NOT NULL,
  status      VARCHAR(30)  DEFAULT 'Generated',
  description TEXT,
  data_json   MEDIUMTEXT,
  file_size   VARCHAR(20) DEFAULT '0 KB',
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---- Shared Reports ------------------------------------------
CREATE TABLE IF NOT EXISTS shared_reports (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  report_id      INT NOT NULL,
  owner_id       INT NOT NULL,
  shared_with_id INT NOT NULL,
  permission     VARCHAR(20) DEFAULT 'view',
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (report_id)      REFERENCES reports(id) ON DELETE CASCADE,
  FOREIGN KEY (owner_id)       REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (shared_with_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_owner_id (owner_id),
  INDEX idx_shared_with_id (shared_with_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---- Comments -----------------------------------------------
CREATE TABLE IF NOT EXISTS comments (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  report_id    INT NOT NULL,
  user_id      INT NOT NULL,
  comment_text TEXT NOT NULL,
  ctype        VARCHAR(30) DEFAULT 'General',
  urgency      VARCHAR(20) DEFAULT 'Low',
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id)   REFERENCES users(id)   ON DELETE CASCADE,
  INDEX idx_report_id (report_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---- Notifications ----------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,
  message    TEXT NOT NULL,
  ntype      VARCHAR(30) DEFAULT 'info',
  is_read    BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_user_unread (user_id, is_read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---- Audit Logs ---------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT,
  action     VARCHAR(80)  NOT NULL,
  details    TEXT,
  ip_address VARCHAR(45),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_user_id   (user_id),
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---- Budget Snapshots ------------------------------------------
CREATE TABLE IF NOT EXISTS budget_snapshots (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  user_id     INT NOT NULL,
  name        VARCHAR(120) NOT NULL,
  fiscal_year INT NOT NULL,
  currency    VARCHAR(10) DEFAULT 'USD',
  data_json   MEDIUMTEXT NOT NULL,
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---- User Sessions (persistent login / Remember Me) --------------
CREATE TABLE IF NOT EXISTS user_sessions (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  user_id     INT NOT NULL,
  token       VARCHAR(128) NOT NULL UNIQUE,
  remember_me BOOLEAN DEFAULT FALSE,
  user_agent  VARCHAR(256),
  ip_address  VARCHAR(45),
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  expires_at  DATETIME NOT NULL,
  last_seen   DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_token   (token),
  INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---- Login Attempts (brute-force lockout) -------------------------
CREATE TABLE IF NOT EXISTS login_attempts (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  identifier VARCHAR(120) NOT NULL,
  success    BOOLEAN DEFAULT FALSE,
  ip_address VARCHAR(45),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_identifier (identifier),
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---- Transactions (billing history: Stripe + SSLCommerz) ----------
CREATE TABLE IF NOT EXISTS transactions (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  user_id       INT NOT NULL,
  gateway       VARCHAR(30) NOT NULL,
  amount        FLOAT NOT NULL,
  currency      VARCHAR(10) DEFAULT 'USD',
  status        VARCHAR(20) DEFAULT 'completed',
  plan          VARCHAR(30) DEFAULT 'pro',
  billing_cycle VARCHAR(10) DEFAULT 'month',
  reference     VARCHAR(120),
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---- Seed Admin User -------------------------------------------
-- Password: Admin@2026! (bcrypt hash)
INSERT IGNORE INTO users
  (username, email, password_hash, full_name, org_name, role, subscription, is_active, is_email_verified)
VALUES (
  'admin',
  'admin@lionsylai.com',
  '$2b$12$LCqjZoiMCzj6Q0mF1Y5vvOvKlzqz5jJv8b.Wd1TzXQ8wGVQvhzM2i',
  'System Administrator',
  'LionsylAI HQ',
  'admin',
  'pro',
  TRUE,
  TRUE
);

INSERT IGNORE INTO integrations (user_id, name, itype, status, success_rate)
VALUES
  (1, 'ERP System',        'ERP',     'Active',          99.8),
  (1, 'CRM Platform',      'CRM',     'Active',          98.5),
  (1, 'Banking API',       'Banking', 'Needs Attention', 95.2),
  (1, 'Payment Processor', 'Payment', 'Active',          99.9);

INSERT IGNORE INTO team_members (user_id, name, email, role, status)
VALUES
  (1, 'Sarah Chen',     'sarah@lionsylai.com',  'Finance Manager', 'Active'),
  (1, 'Mike Rodriguez', 'mike@lionsylai.com',   'Analyst',         'Away'),
  (1, 'Jessica Wong',   'jessica@lionsylai.com','Viewer',          'Inactive');
