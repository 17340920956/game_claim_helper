import sys
import os

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.game.scraper import EpicScraper
from services.notification.service import push_service

def test_fetch_and_simulate_push():
    print("🚀 开始测试...")
    
    # 1. 爬取游戏
    print("\n📦 [1/2] 正在爬取 Epic 免费游戏...")
    scraper = EpicScraper()
    try:
        games_data = scraper.fetch_free_games()
        current_games = games_data.get("current", [])
        
        if not current_games:
            print("⚠️ 未获取到本周免费游戏！")
            return
            
        print(f"✅ 成功获取 {len(current_games)} 款本周免费游戏：")
        for i, game in enumerate(current_games, 1):
            print(f"   {i}. {game.get('title')} (Slug: {game.get('urlSlug')})")
            
    except Exception as e:
        print(f"❌ 爬取失败: {e}")
        return

    # 2. 模拟推送 (打印到控制台)
    print("\n📨 [2/2] 模拟推送通知...")
    
    # 构造模拟的推送内容
    if len(current_games) == 1:
        message = push_service._format_current_game_message(current_games[0])
    else:
        lines = ["Epic 本周多款免费游戏上线！\n"]
        for i, game in enumerate(current_games, 1):
            lines.append(f"{i}. {game.get('title', '未知')}")
            lines.append(f"   图片：{game.get('thumbnail', '无')}")
            lines.append(f"   链接：{game.get('url', '无')}")
            lines.append(f"   时间：{game.get('start_date', '未知')} ~ {game.get('end_date', '未知')}")
            lines.append("")
        lines.append('请回复"确认"表示已收到，或回复"领取"表示已领取游戏。')
        message = "\n".join(lines)
        
    print("-" * 50)
    print(message)
    print("-" * 50)
    print("✅ 模拟推送完成！")

if __name__ == "__main__":
    test_fetch_and_simulate_push()
