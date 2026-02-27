# Database Schema (MySQL)

```sql
CREATE TABLE IF NOT EXISTS `users` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `epic_account` VARCHAR(100) NOT NULL COMMENT 'Epic Games Account',
  `contact_type` ENUM('wechat_official', 'qq') NOT NULL COMMENT 'Contact Type',
  `contact_id` VARCHAR(50) NOT NULL COMMENT 'Contact ID (WeChat OpenID or QQ Number)',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation Time',
  PRIMARY KEY (`id`),
  INDEX `ix_users_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User Information Table';

CREATE TABLE IF NOT EXISTS `push_logs` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL COMMENT 'User ID',
  `game_slug` VARCHAR(100) NOT NULL COMMENT 'Game Slug',
  `game_title` VARCHAR(100) NOT NULL COMMENT 'Game Title',
  `contact_type` ENUM('wechat_official', 'qq') NOT NULL COMMENT 'Contact Type',
  `contact_id` VARCHAR(50) NOT NULL COMMENT 'Contact ID',
  `status` ENUM('success', 'failed') NOT NULL COMMENT 'Push Status',
  `message` TEXT COMMENT 'Push Message',
  `error_msg` TEXT COMMENT 'Error Message',
  `confirmation_status` ENUM('pending', 'confirmed', 'claimed') DEFAULT 'pending' COMMENT 'Confirmation Status',
  `confirmation_time` DATETIME COMMENT 'Confirmation Time',
  `is_next_week` TINYINT(1) DEFAULT 0 COMMENT 'Is Next Week Game',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation Time',
  PRIMARY KEY (`id`),
  INDEX `ix_push_logs_id` (`id`),
  INDEX `ix_push_logs_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Push Notification Logs';
```
