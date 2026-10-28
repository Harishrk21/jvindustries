-- JV-OMS MySQL bootstrap (run as MySQL admin / root)
-- PowerShell:
--   Get-Content .\database\setup_mysql.sql -Raw | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p --default-character-set=utf8mb4
-- Or:
--   .\scripts\setup-mysql.ps1 -RootPassword "YOUR_ROOT_PASSWORD"

CREATE DATABASE IF NOT EXISTS jvoms
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS jvoms_test
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'jvoms'@'localhost' IDENTIFIED BY 'JvOms@2026';
CREATE USER IF NOT EXISTS 'jvoms'@'%' IDENTIFIED BY 'JvOms@2026';

GRANT ALL PRIVILEGES ON jvoms.* TO 'jvoms'@'localhost';
GRANT ALL PRIVILEGES ON jvoms.* TO 'jvoms'@'%';
GRANT ALL PRIVILEGES ON jvoms_test.* TO 'jvoms'@'localhost';
GRANT ALL PRIVILEGES ON jvoms_test.* TO 'jvoms'@'%';
FLUSH PRIVILEGES;

-- Confirm:
-- SHOW DATABASES LIKE 'jvoms%';
-- SELECT user, host FROM mysql.user WHERE user = 'jvoms';
