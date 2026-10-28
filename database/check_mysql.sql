-- Quick health check as app user:
-- mysql -u jvoms -pJvOms@2026 jvoms < database/check_mysql.sql

SELECT DATABASE() AS current_db;
SELECT USER() AS current_user;
SHOW TABLES;
SELECT COUNT(*) AS user_count FROM users;
SELECT user_code, full_name, is_active FROM users ORDER BY user_code;
