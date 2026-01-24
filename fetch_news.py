import requests
import os
import urllib.parse
from datetime import datetime, timedelta

MARKETAUX_KEY = os.getenv("MARKETAUX_API_KEY")
WECHAT_WEBHOOK = os.getenv("WECHAT_WEBHOOK")

# 核心白名单信源
WHITELIST_SOURCES = ["Bloomberg", "Reuters", "The Wall Street Journal", "CNBC", "Financial Times", "MarketWatch", "Forbes"]

def google_translate(text):
    """强制使用 Google 翻译镜像"""
    try:
        encoded_text = urllib.parse.quote(text[:400])
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t&q={encoded_text}"
        r = requests.get(url, timeout=10)
        return "".join([s[0] for s in r.json()[0]])
    except:
        return text

def fetch_data(params):
    """通用抓取函数"""
    base_url = "https://api.marketaux.com/v1/news/all"
    params.update({"api_token": MARKETAUX_KEY, "language": "en", "limit": 10})
    try:
        res = requests.get(base_url, params=params, timeout=15).json()
        return res.get('data', [])
    except:
        return []

def get_integrated_report():
    # 1. 获取宏观金融 (美债, 黄金, 指数, 欧日市场)
    macro_params = {
        "entity_types": "index,commodity,currency",
        "published_after": (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M')
    }
    
    # 2. 获取前沿科技 (AI, 航空航天, Web3)
    tech_params = {
        "search": "AI,Aerospace,Web3,SpaceX,NVIDIA,OpenAI",
        "industries": "Technology,Industrials"
    }

    raw_news = fetch_data(macro_params) + fetch_data(tech_params)
    
    # 筛选与去重
    final_items = []
    seen_titles = set()
    
    for item in raw_news:
        title = item.get('title', '')
        source = item.get('source', '')
        
        # 仅保留白名单信源或极高质量源
        is_pro_source = any(ws in source for ws in WHITELIST_SOURCES)
        
        if title not in seen_titles and is_pro_source:
            zh_title = google_translate(title)
            
            # 转换时间
            pub_at = item.get('published_at', '')
            time_str = "NEW"
            if pub_at:
                dt = datetime.strptime(pub_at, '%Y-%m-%dT%H:%M:%S.%fZ') + timedelta(hours=8)
                time_str = dt.strftime('%H:%M')
            
            final_items.append({
                "time": time_str,
                "source": source,
                "title": zh_title
            })
            seen_titles.add(title)

    if not final_items:
        return "### 🌐 顶级财经内参\n> 监测中：暂无来自 WSJ/Bloomberg 的实时核心快讯。"

    # 构建排版
    now_bj = (datetime.now() + timedelta(hours=8)).strftime('%m-%d %H:%M')
    content = f"### 🌐 顶级财经内参 (华尔街专线)\n> 覆盖：宏观金融 | AI | 航天 | Web3\n> 更新时间：{now_bj}\n\n"
    
    for i, news in enumerate(final_items[:12], 1): # 取前12条精华
        content += f"{i}. **[{news['time']}]** {news['title']}\n   *信源: {news['source']}*\n\n"
    
    content += "---\n> ⚡ 仅推送 Bloomberg/Reuters/WSJ 等专业信源"
    return content

if __name__ == "__main__":
    report = get_integrated_report()
    if WECHAT_WEBHOOK:
        requests.post(WECHAT_WEBHOOK, json={"msgtype": "markdown", "markdown": {"content": report}})
