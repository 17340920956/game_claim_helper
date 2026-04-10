-- 游戏领取助手数据库表结构

-- 用户表
CREATE TABLE IF NOT EXISTS user (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID，主键',
    wx_id VARCHAR(64) UNIQUE COMMENT '微信号',
    qq_id VARCHAR(64) UNIQUE COMMENT 'QQ号',
    epic_id VARCHAR(64) COMMENT 'Epic账号ID',
    epic_email VARCHAR(128) COMMENT 'Epic账号邮箱',
    epic_password VARCHAR(256) COMMENT '加密存储的Epic密码（旧方式，已弃用）',
    epic_device_id VARCHAR(128) COMMENT 'Epic Device Auth ID（旧方式，已弃用）',
    epic_device_secret VARCHAR(256) COMMENT '加密存储的Epic Device Auth Secret（旧方式，已弃用）',
    epic_refresh_token VARCHAR(512) COMMENT '加密存储的Epic Refresh Token',
    epic_token VARCHAR(512) COMMENT 'Epic授权Token',
    token_expired_at DATETIME COMMENT 'Token过期时间',
    is_del BOOLEAN DEFAULT FALSE COMMENT '软删除标记，0=有效，1=删除',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 推送日志表
CREATE TABLE IF NOT EXISTS push_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID，主键',
    user_id BIGINT NOT NULL COMMENT '关联用户ID',
    game_name VARCHAR(128) NOT NULL COMMENT '游戏名称',
    game_slug VARCHAR(128) COMMENT '游戏标识（用于关联Redis数据）',
    push_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '推送时间',
    status BOOLEAN DEFAULT FALSE COMMENT '推送状态，0=失败，1=成功',
    is_next_week BOOLEAN DEFAULT FALSE COMMENT '是否为下周预告推送',
    note VARCHAR(256) COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_game_name (game_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='推送日志表';
