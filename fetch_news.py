import feedparser
import time
import datetime
import requests
import os
import json

# 新闻源列表
FEEDS = [
    ("财新网", "https://rsshub.app/caixin/latest"),
    ("Reuters", "https://rsshub.app/reuters/channel/chinaNews"),
    ("Bloomberg", "https://rsshub.app/bloomberg/market"),
    ("WSJ", "https://rsshub.app/wsj/china")
]

def translate_title(title):
    """免费翻译英文标题为中文（DeepSeek API）"""
    if not title or any('\u4e00' <= c <= '\u9fff' for c in title):
        return title  # 已是中文
    try:
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个翻译助手，只返回简洁的中文翻译，不要解释。"},
                    {"role": "user", "content": f"翻译成中文：{title}"}
                ],
                "max_tokens": 100
            },
            timeout=10
        )
        if resp.ok:
            data = resp.json()
            return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"翻译失败: {e}")
        return title
      # 计算24小时前的时间
now = datetime.datetime.now(datetime.timezone.utc)
cutoff = now - datetime.timedelta(hours=24)

all_news = []
for source_name, url in FEEDS:
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:10]:  # 每个源最多取10条
            pub_time = getattr(entry, 'published_parsed', None)
            if not pub_time:
                continue
            pub_dt = datetime.datetime(*pub_time[:6], tzinfo=datetime.timezone.utc)
            if pub_dt >= cutoff:
                title_zh = translate_title(entry.title)
                all_news.append({
                    'title': title_zh,
                    'link': entry.link,
                    'source': source_name,
                    'pub_dt': pub_dt
                })
    except Exception as e:
        print(f"Error fetching {source_name}: {e}")

# 按时间排序（最新在前）
all_news.sort(key=lambda x: x['pub_dt'], reverse=True)

# 生成消息
if not all_news:
    message = "过去24小时暂无重要财经新闻。"
else:
    text = "【过去24小时全球财经要闻】\n\n"
    for i, item in enumerate(all_news[:8]):
        text += f"{i+1}. {item['title']}\n来源：{item['source']}\n链接：{item['link']}\n\n"
    text += "—— 每日19:50自动推送 | 数据源：财新/Reuters/Bloomberg/WSJ"
    message = text

# 发送到企业微信
webhook = os.getenv("WECHAT_WEBHOOK")
if webhook:
    try:
        requests.post(webhook, json={"msgtype": "text", "text": {"content": message}})
        print("✅ 推送成功！")
    except Exception as e:
        print(f"❌ 推送失败: {e}")
else:
    print("⚠ 未设置 WECHAT_WEBHOOK，消息预览：")
    print(message)
