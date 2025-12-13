import feedparser
import smtplib
from email.mime.text import MIMEText
import requests
import re
import os

# ---------------------- 已填入你的QQ邮箱信息 ----------------------
SENDER_EMAIL = "1047372945@qq.com"  # 发件邮箱
SENDER_PWD = "excnvmaryozwbech"    # 16位授权码
RECEIVER_EMAIL = "1047372945@qq.com"  # 接收邮箱
SMTP_SERVER = "smtp.qq.com"        # QQ邮箱SMTP服务器
# -----------------------------------------------------------------

# 基础配置
RSS_URL = "https://reutersnew.buzzing.cc/feed.xml"
LAST_LINK_FILE = "last_link.txt"   # 存储最新资讯链接
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

# 提取分时/月日（有分时显分时，无分时显月日）
def get_show_time(news):
    content = news.get("content", [{}])[0].get("value", "") if news.get("content") else ""
    try:
        pattern = r'(\d{2}:\d{2})<\/time>'
        hour_min = re.search(pattern, content).group(1)
        return hour_min
    except:
        updated_str = news.get("updated", news.get("published", ""))
        date_part = updated_str.split('T')[0]
        month_day = '-'.join(date_part.split('-')[1:])
        return month_day

# 抓取资讯和最新链接
def fetch_news():
    try:
        response = requests.get(RSS_URL, headers=REQUEST_HEADERS, timeout=10)
        response.raise_for_status()
        news_list = feedparser.parse(response.content).entries
        if not news_list:
            print("📥 未抓取到任何资讯")
            return None, None
        latest_link = news_list[0]["link"].strip()
        print(f"📥 成功抓取到{len(news_list)}条资讯")
        return news_list, latest_link
    except Exception as e:
        print(f"❌ 抓取资讯失败：{e}")
        return None, None

# 判断是否推送（首次强制推，后续仅链接变化推）
def check_push():
    is_first = not os.path.exists(LAST_LINK_FILE)
    last_link = ""

    if not is_first:
        with open(LAST_LINK_FILE, 'r', encoding='utf-8') as f:
            last_link = f.read().strip()

    all_news, current_link = fetch_news()
    if not all_news or not current_link:
        return False, None

    # 首次运行或链接变化，推送并保存新链接
    if is_first or current_link != last_link:
        with open(LAST_LINK_FILE, 'w', encoding='utf-8') as f:
            f.write(current_link)
        if is_first:
            print("🚀 首次运行，强制推送全部资讯")
        else:
            print("🔄 检测到新资讯，推送全部内容")
        return True, all_news
    else:
        print("ℹ️  暂无新资讯，不推送")
        return False, None

# 生成纯文本邮件内容（避免邮箱拦截）
def make_content(all_news):
    if not all_news:
        return "暂无可用资讯"
    # 仅推最新10条，减少内容量
    news_list = all_news[:10]
    latest = news_list[0]
    time = get_show_time(latest)
    date = latest.get("updated", "").split('T')[0]
    title = f"路透社最新资讯 {date} {time}\n" + "-"*40 + "\n"

    content = []
    for i, news in enumerate(news_list, 1):
        link = news["link"]
        title_news = news["title"]
        show_t = get_show_time(news)
        content.append(f"{i}. 【{show_t}】{title_news}\n链接：{link}\n")

    return title + "\n".join(content)

# 同步发送邮件（确保发送完成，不被中断）
def send_email(content):
    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = "路透社实时资讯推送"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    try:
        print("📡 开始发送邮件...")
        server = smtplib.SMTP_SSL(SMTP_SERVER, 465, timeout=20)
        server.login(SENDER_EMAIL, SENDER_PWD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("✅ 邮件发送成功！")
    except Exception as e:
        print(f"❌ 邮件发送失败：{e}")

# 核心入口
if __name__ == "__main__":
    print("🔍 开始检测路透社资讯（每6分钟检测1次）...")
    need_push, news = check_push()
    if need_push and news:
        email_content = make_content(news)
        send_email(email_content)
