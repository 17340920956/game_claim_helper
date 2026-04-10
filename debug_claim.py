#!/usr/bin/env python3
"""
调试脚本：检查领取游戏失败的原因
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.base import User, FreeGame
from app.repositories.game.game_repository import GameRepository
from app.services.game.claim_service import epic_claim_service
from app.core.crypto import decrypt_password
from datetime import datetime, timezone


def check_database_connection():
    """检查数据库连接"""
    print("=" * 60)
    print("1. 检查数据库连接")
    print("=" * 60)
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        print("✅ 数据库连接正常")
        db.close()
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


def check_games():
    """检查游戏数据"""
    print("\n" + "=" * 60)
    print("2. 检查游戏数据")
    print("=" * 60)
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        print(f"当前时间(UTC): {now}")
        
        # 所有游戏
        all_games = db.query(FreeGame).all()
        print(f"\n数据库中的游戏总数: {len(all_games)}")
        
        # 当前免费游戏
        game_repo = GameRepository(db)
        current_games = game_repo.get_active_games()
        print(f"当前免费游戏数量: {len(current_games)}")
        
        if current_games:
            print("\n当前免费游戏详情:")
            for game in current_games:
                print(f"\n游戏: {game.name}")
                print(f"  - offer_id: {game.offer_id}")
                print(f"  - namespace: {game.namespace}")
                print(f"  - 开始时间: {game.start_time}")
                print(f"  - 结束时间: {game.end_time}")
                print(f"  - 链接: {game.link}")
                
                if not game.offer_id or not game.namespace:
                    print("  ⚠️ 缺少领取信息")
        else:
            print("\n❌ 没有当前免费游戏")
            print("请回复'刷新'更新游戏数据")
            
        return current_games
    except Exception as e:
        print(f"❌ 查询游戏失败: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        db.close()


def check_user_binding(openid: str = None):
    """检查用户绑定状态"""
    print("\n" + "=" * 60)
    print("3. 检查用户绑定状态")
    print("=" * 60)
    db = SessionLocal()
    try:
        if openid:
            user = db.query(User).filter(User.wx_id == openid).first()
        else:
            # 获取最新的绑定用户
            user = db.query(User).filter(
                User.epic_refresh_token.isnot(None)
            ).order_by(User.updated_at.desc()).first()
        
        if not user:
            print("❌ 未找到绑定用户")
            return None
        
        print(f"\n用户 ID: {user.id}")
        print(f"微信 ID: {user.wx_id}")
        print(f"Epic 邮箱: {user.epic_email}")
        print(f"Epic ID: {user.epic_id}")
        print(f"Refresh Token: {'已绑定' if user.epic_refresh_token else '未绑定'}")
        print(f"Device Auth: {'已绑定' if user.epic_device_id else '未绑定'}")
        
        return user
    except Exception as e:
        print(f"❌ 查询用户失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


def test_claim(user, game):
    """测试领取游戏"""
    print("\n" + "=" * 60)
    print(f"4. 测试领取游戏: {game.name}")
    print("=" * 60)
    
    try:
        print(f"\n领取参数:")
        print(f"  - offer_id: {game.offer_id}")
        print(f"  - namespace: {game.namespace}")
        print(f"  - account_id: {user.epic_id}")
        print(f"  - 有 refresh_token: {bool(user.epic_refresh_token)}")
        print(f"  - 有 device_auth: {bool(user.epic_device_id)}")
        
        result = epic_claim_service.claim_game(
            offer_id=game.offer_id,
            namespace=game.namespace,
            encrypted_refresh_token=user.epic_refresh_token,
            device_id=user.epic_device_id,
            encrypted_device_secret=user.epic_device_secret,
            account_id=user.epic_id,
            email=user.epic_email or "",
            encrypted_password=user.epic_password or "",
        )
        
        print(f"\n领取结果:")
        print(f"  - 成功: {result.get('success')}")
        print(f"  - 消息: {result.get('message')}")
        print(f"  - 游戏名: {result.get('game_name')}")
        
        if result.get('new_refresh_token'):
            print(f"  - 新 refresh_token: 已返回")
        
        return result
    except Exception as e:
        print(f"❌ 领取异常: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数"""
    print("Epic 游戏领取调试工具")
    print("=" * 60)
    
    # 1. 检查数据库连接
    if not check_database_connection():
        print("\n❌ 数据库连接失败，请检查配置")
        return
    
    # 2. 检查游戏数据
    games = check_games()
    
    # 3. 检查用户绑定
    user = check_user_binding()
    
    if not user:
        print("\n❌ 未找到绑定用户")
        return
    
    if not games:
        print("\n❌ 没有可领取的游戏")
        return
    
    # 4. 测试领取第一个游戏
    if games and user:
        test_claim(user, games[0])
    
    print("\n" + "=" * 60)
    print("调试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
