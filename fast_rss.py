import feedparser
import smtplib
from email.mime.text import MIMEText
import requests
import re
import datetime
import sys
import json

# 全局编码防乱码
sys.stdout.reconfigure(encoding='utf-8')

# ---------------------- 已填好你的信息，不用改 ----------------------
SENDER_EMAIL = "1047372945@qq.com"  # 发件QQ邮箱
SENDER_PWD = "excnvmaryozwbech"    # QQ邮箱16位授权码
RECEIVER_EMAIL = "1047372945@qq.com"  # 收件邮箱
# -------------------------------------------------------------------

# 国内零注册短链接+HTML托管（tmp.link，点击即开，国内秒开）
def get_cn_short_link(html_content):
    try:
        # 零注册上传HTML，生成国内短链接
        url = "https://tmp.link/api/upload"
        files = {
            'file': ('彭博速递.html', html_content.encode('utf-8'), 'text/html')
        }
        res = requests.post(url, files=files, timeout=30, verify=False)
        res_json = json.loads(res.text)
        # 提取国内可点击短链接
        cn_short_link = res_json['data']['url']
        print(f"✅ 国内短链接生成成功：{cn_short_link}（点击即开）")
        return cn_short_link
    except:
        # 备选零注册平台（双重保障，同样零注册）
        url = "https://file.io/"
        files = {'file': ('彭博速递.html', html_content.encode('utf-8'), 'text/html')}
        res = requests.post(url, files=files, timeout=30, verify=False)
        res_json = json.loads(res.text)
        cn_short_link = res_json['link']
        print(f"✅ 备选短链接生成成功：{cn_short_link}")
        return cn_short_link

# 抓取彭博资讯（重试3次，确保拿到数据）
def get_news():
    for _ in range(3):
        try:
            res = requests.get("https://bloombergnew.buzzing.cc/feed.xml", headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            res.encoding = 'utf-8'
            return feedparser.parse(res.text)['entries']
        except:
            continue
    return []

# 生成带样式的资讯HTML（黄色时间+蓝色链接）
def make_html(news_list):
    if not news_list:
        return "<h2 style='color: #FFD700; text-align: center;'>暂无彭博资讯（资讯源正常后自动更新）</h2>"
    
    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ background: #1a1a1a; color: #fff; font-family: 微软雅黑, Arial; max-width: 800px; margin: 20px auto; padding: 20px; }}
            h1 {{ color: #2E4057; text-align: center; margin-bottom: 30px; }}
            .item {{ margin: 20px 0; padding: 15px; border-left: 4px solid #1E88E5; background: #222; border-radius: 4px; }}
            .time {{ color: #FFD700; font-weight: bold; margin-right: 10px; }}
            .link {{ color: #1E88E5; text-decoration: underline; margin-top: 5px; display: inline-block; }}
            .update-time {{ text-align: right; color: #999; font-size: 12px; margin-top: 40px; }}
        </style>
    </head>
    <body>
        <h1>彭博速递（共{len(news_list)}条最新资讯）</h1>
    """
    for i, n in enumerate(news_list, 1):
        # 提取时间（容错处理）
        t = re.search(r'(\d{2}:\d{2})<\/time>', n.get("content", [{}])[0].get("value", ""))
        time_str = t.group(1) if t else "未知时间"
        # 标题/链接编码容错
        title = n.get("title", "").encode('utf-8', errors='replace').decode('utf-8')
        link = n.get("link", "").encode('utf-8', errors='replace').decode('utf-8')
        # 拼接单条资讯
        html += f"""
        <div class="item">
            <span class="time">【{time_str}】</span>
            <span>{title}</span>
            <br>
            <a href="{link}" class="link" target="_blank">👉 查看原文链接</a>
        </div>
        """
    html += f"<div class='update-time'>更新时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div></body></html>"
    return html

# 发送邮件（短链接+点击即开，国内100%可访问）
def send_email():
    print("🔍 抓取彭博资讯中...")
    news_list = get_news()
    news_count = len(news_list)
    html_content = make_html(news_list)
    
    print("📤 生成国内短链接...")
    cn_short_link = get_cn_short_link(html_content)  # 零注册生成短链接

    try:
        # 邮件正文：蓝色可点击短链接，QQ邮箱直接跳转
        email_html = f"""
        <div style="font-family: 微软雅黑; max-width: 600px; margin: 0 auto;">
            <h3 style="color: #2E4057; margin-bottom: 20px;">彭博速递最新资讯更新</h3>
            <p style="font-size: 15px; margin-bottom: 25px;">本次共推送 <span style="color: #1E88E5; font-weight: bold;">{news_count}</span> 条资讯，点击下方链接直接查看：</p>
            <p style="margin-bottom: 30px;">
                <a href="{cn_short_link}" target="_blank" style="background: #1E88E5; color: white; padding: 12px 25px; border-radius: 5px; text-decoration: none; font-weight: bold; font-size: 16px;">
                    🔗 点击打开资讯页面（国内秒开）
                </a>
            </p>
            <p style="color: #999; font-size: 12px;">
                提示：链接为国内免费托管，无需注册/登录，点击后直接在浏览器打开，手机/电脑都适配～
            </p>
        </div>
        """
        msg = MIMEText(email_html, "html", "utf-8")
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECEIVER_EMAIL
        msg["Subject"] = f"彭博速递（{news_count}条）- 点击即开"

        # 发送邮件
        server = smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=30)
        server.login(SENDER_EMAIL, SENDER_PWD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print(f"✅ 邮件发送成功！短链接：{cn_short_link}（直接点击打开）")
    except smtplib.SMTPAuthenticationError:
        print("❌ 登录失败：请检查QQ邮箱授权码/账号是否正确（必看！）")
    except Exception as e:
        print(f"❌ 发送失败：{str(e)}")

# 一键运行（不用管其他，点运行就行）
if __name__ == "__main__":
    send_email()


