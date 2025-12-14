import feedparser
import smtplib
from email.mime.text import MIMEText
import requests
import re
import os
import datetime

# ---------------------- 邮箱配置（已填好，无需修改） ----------------------
SENDER_EMAIL = "1047372945@qq.com"  # 发件邮箱
SENDER_PWD = "excnvmaryozwbech"    # 16位授权码
RECEIVER_EMAIL = "1047372945@qq.com"  # 接收邮箱
SMTP_SERVER = "smtp.qq.com"        # QQ邮箱SMTP服务器
# -------------------------------------------------------------------------

# 基础配置
RSS_URL = "https://reutersnew.buzzing.cc/lite/feed.xml"
LAST_LINK_FILE = "last_link.txt"   # 存储最新资讯链接（持久化对比）
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

# 提取分时/月日（有分时显分时，无分时显月日，原有逻辑不变）
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

# 抓取资讯和最新链接（容错优化，捕获网络异常）
def fetch_news():
    try:
        response = requests.get(RSS_URL, headers=REQUEST_HEADERS, timeout=15)  # 超时延长到15秒
        response.raise_for_status()  # 触发HTTP错误
        news_list = feedparser.parse(response.content).entries
        if not news_list:
            print("📭 未抓取到任何路透资讯")
            return None, None
        latest_link = news_list[0]["link"].strip()
        print(f"📭 成功抓取到{len(news_list)}条路透资讯")
        return news_list, latest_link
    except Exception as e:
        print(f"❌ 资讯抓取失败：{str(e)}")
        return None, None

# 判断是否推送（首次强制推，后续仅新资讯推，原有逻辑不变）
def check_push():
    is_first = not os.path.exists(LAST_LINK_FILE)
    last_link = ""

    if not is_first:
        try:
            with open(LAST_LINK_FILE, 'r', encoding='utf-8') as f:
                last_link = f.read().strip()
        except Exception as e:
            print(f"⚠️  读取历史链接失败，按首次运行处理：{str(e)}")
            is_first = True

    all_news, current_link = fetch_news()
    if not all_news or not current_link:
        return False, None

    if is_first or current_link != last_link:
        with open(LAST_LINK_FILE, 'w', encoding='utf-8') as f:
            f.write(current_link)
        if is_first:
            print("🚨 首次运行，强制推送最新资讯")
        else:
            print("🔄 检测到新资讯，立即推送")
        return True, all_news
    else:
        print("ℹ️  暂无新资讯，本次不推送")
        return False, None

# 生成邮件内容（核心修复：提升时间样式优先级，确保黄色生效）
def make_content(all_news):
    if not all_news:
        return "暂无可用的路透资讯"
    news_list = all_news[:300]  # 推300条

    # ---------------------- 颜色配置（可直接改下面的颜色代码） ----------------------
    title_color = "#2E4057"    # 「路透速递」标题颜色（深灰蓝，醒目不刺眼）
    time_color = "#FFD700"     # 时间颜色（亮黄色，强制生效）
    time_bg_color = "transparent" # 时间背景色（透明，避免干扰）
    serial_color = "#1E88E5"   # 资讯序号颜色（蓝色）
    news_title_color = "#333333"# 资讯标题颜色（深灰色，易读）
    link_text_color = "#4CAF50"# 「原文链接」文字颜色（绿色，区分普通文字）
    # -----------------------------------------------------------------------------

    # 标题：「彭博速递」（自定义颜色+加粗，更醒目）
    title = f"<p><strong><span style='color:{title_color};'>「路透速递」</span></strong></p>"

    content = []
    for i, news in enumerate(news_list, 1):
        link = news["link"]
        news_title = news["title"]
        show_t = get_show_time(news)
        # 核心修复：给时间添加!important提升优先级，取消下划线、设置背景透明，避免被邮箱样式覆盖
        content.append(f"""
        <p style='margin: 8px 0; padding: 0;'>
            <span style='color:{serial_color}; font-size: 16px;'>{i}</span>. 
            【<span style='color:{time_color}!important; text-decoration: none!important; background:{time_bg_color}; font-weight: bold; font-size: 16px;'>{show_t}</span>】
            <span style='color:{news_title_color}; font-size: 16px;'>{news_title}</span>
        </p>
        <p style='margin: 0 0 12px 0; padding: 0;'>👉 <a href='{link}' target='_blank' style='color:{link_text_color}; text-decoration: underline; font-size: 14px;'>原文链接</a></p>
        """)

    return title + "".join(content)

# 发送邮件（HTML格式支持超链接，容错优化）
def send_email(content):
    msg = MIMEText(content, "html", "utf-8")
    msg["Subject"] = "「路透速递」"  # 邮件主题与内容标题统一
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    try:
        print("📡 开始连接邮箱服务器发送邮件...")
        server = smtplib.SMTP_SSL(SMTP_SERVER, 465, timeout=20)
        server.login(SENDER_EMAIL, SENDER_PWD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("✅ 邮件发送成功！")
    except Exception as e:
        print(f"❌ 邮件发送失败：{str(e)}")
        raise  # 抛出异常触发重试

# 核心入口（新增双时区日志+全局异常捕获）
if __name__ == "__main__":
    # 打印精准执行时间，便于排查延迟
    utc_now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cst_now = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    print(f"==================================================")
    print(f"📅 执行时间 | UTC：{utc_now} | 东八区：{cst_now}")
    print(f"==================================================")

    try:
        need_push, news = check_push()
        if need_push and news:
            email_content = make_content(news)
            send_email(email_content)
        print(f"🎉 本次资讯检测+推送流程结束")
    except Exception as e:
        print(f"💥 流程执行失败：{str(e)}")
        raise  # 抛出异常，让Workflow触发重试
