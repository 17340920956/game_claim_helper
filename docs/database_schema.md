CREATE TABLE `user` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户ID，主键',
    `wx_id` VARCHAR(64) DEFAULT NULL COMMENT '微信号',
    `qq_id` VARCHAR(64) DEFAULT NULL COMMENT 'QQ号',
    `epic_id` VARCHAR(64) DEFAULT NULL COMMENT 'Epic账号ID',
    `epic_email` VARCHAR(128) DEFAULT NULL COMMENT 'Epic账号邮箱',
    `epic_password` VARCHAR(256) DEFAULT NULL COMMENT '加密存储的Epic密码',
    `epic_token` VARCHAR(512) DEFAULT NULL COMMENT 'Epic授权Token',
    `token_expired_at` DATETIME DEFAULT NULL COMMENT 'Token过期时间',
    `is_del` TINYINT(1) DEFAULT 0 COMMENT '软删除标记，0=有效，1=删除',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uniq_wx` (`wx_id`),
    UNIQUE KEY `uniq_qq` (`qq_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

CREATE TABLE `push_log` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '日志ID，主键',
    `user_id` BIGINT UNSIGNED NOT NULL COMMENT '关联用户ID',
    `push_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '推送时间',
    `status` TINYINT(1) DEFAULT 0 COMMENT '推送状态，0=失败，1=成功',
    `note` VARCHAR(256) DEFAULT NULL COMMENT '备注',
    PRIMARY KEY (`id`),
    KEY `idx_user` (`user_id`),
    CONSTRAINT `fk_push_user` FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='推送日志表';


免费游戏表（Redis 数据结构设计）

每周抓取到的免费游戏信息存 Redis，常用的设计方案：

🔹 数据结构建议
1. Hash：存储每个游戏详细信息

key: epic:free_game:<game_id>

value (hash):

name -> 游戏名称
start_time -> yyyy-mm-dd HH:MM:SS
end_time -> yyyy-mm-dd HH:MM:SS
image_url -> 封面图片链接
link -> Epic游戏页面链接
note -> 备注
created_at -> 数据抓取时间
updated_at -> 更新时间