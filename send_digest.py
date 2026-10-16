import glob
import os
import re
import smtplib
from email.message import EmailMessage
import requests


def main():
    posts = sorted(glob.glob("src/content/posts/*.md"))
    if not posts:
        print("No posts found. Skipping digest.")
        return

    latest_file = posts[-1]
    issue_date = os.path.basename(latest_file).replace(".md", "")
    with open(latest_file, "r", encoding="utf-8") as f:
        content = f.read()

    temp_m = re.search(r'^temp:\s*"?([^"\n]+)"?', content, re.M)
    sunset_m = re.search(r'^sunset:\s*"?([^"\n]+)"?', content, re.M)
    pickup_m = re.search(r'^pickup:\s*"?([^"\n]+)"?', content, re.M)
    temp_val = temp_m.group(1) if temp_m else "-"
    sunset_val = sunset_m.group(1) if sunset_m else "-"
    pickup_val = pickup_m.group(1) if pickup_m else "今日の注目スポット"

    sections = re.split(r"<h2[^>]*>(.*?)</h2>", content)
    digest_items = []
    line_lines = []
    for i in range(1, len(sections), 2):
        h_title = re.sub(r"<[^>]+>", "", sections[i]).strip()
        sec_body = sections[i + 1] if i + 1 < len(sections) else ""
        bolds = [
            b.strip()
            for b in re.findall(r"\*\*(.*?)\*\*", sec_body)
            if 2 < len(b.strip()) < 65
        ]
        sub_preview = " / ".join(bolds[:2]) if bolds else ""
        if sub_preview:
            digest_items.append(
                f'<li style="margin-bottom:10px;"><strong>{h_title}</strong><br><span style="color:#555;font-size:13px;">▸ {sub_preview}</span></li>'
            )
            line_lines.append(f"■ {h_title}\n  ▸ {sub_preview}")
        else:
            digest_items.append(
                f'<li style="margin-bottom:8px;"><strong>{h_title}</strong></li>'
            )
            line_lines.append(f"■ {h_title}")

    digest_html = "\n".join(digest_items)
    site_url = "https://mercy23soccer-alt.github.io/her-daily-magazine/"

    # 1. Gmail 送信
    gmail_user = os.environ.get("GMAIL_USER", "").strip()
    gmail_pass = (
        os.environ.get("GMAIL_APP_PASSWORD", "").strip().replace(" ", "")
    )
    to_raw = os.environ.get("NOTIFY_EMAIL", "").strip() or gmail_user

    if gmail_user and gmail_pass:
        html_body = f"""
        <div style="font-family:'Helvetica Neue',Arial,'Hiragino Kaku Gothic ProN',sans-serif;max-width:600px;margin:0 auto;background:#fffaf8;border:1px solid #f0e6e0;padding:28px;color:#2c2825;">
          <div style="font-size:11px;letter-spacing:0.15em;color:#8a7a72;border-bottom:2px solid #d4a373;padding-bottom:8px;margin-bottom:16px;">
            DAILY MORNING NOTE · NAGAREYAMA / {issue_date}
          </div>
          <h1 style="font-size:28px;margin:0 0 6px 0;letter-spacing:0.08em;color:#2c2825;">Zazzy</h1>
          <p style="font-size:13px;color:#7a6d65;margin:0 0 18px 0;">
            🌡 気温: {temp_val} &nbsp;|&nbsp; 🌇 日の入り: {sunset_val} &nbsp;|&nbsp; ✨ {pickup_val}
          </p>
          <div style="text-align:center;margin:24px 0;">
            <a href="{site_url}" style="display:inline-block;background:#d4a373;color:#ffffff;text-decoration:none;padding:14px 28px;border-radius:4px;font-weight:bold;font-size:15px;">
              🌸 今日のノートをWebで開く ↗
            </a>
          </div>
          <h3 style="font-size:14px;border-bottom:1px solid #e8ded8;padding-bottom:6px;margin-top:24px;color:#4a3f38;">今日のラインナップ（全{len(digest_items)}コーナー）</h3>
          <ul style="padding-left:18px;line-height:1.6;font-size:14px;">
            {digest_html}
          </ul>
          <div style="margin-top:28px;padding-top:14px;border-top:1px solid #f0e6e0;font-size:12px;color:#8a7a72;text-align:center;">
            <a href="{site_url}" style="color:#d4a373;">最新号を読む</a> ・ <a href="{site_url}archive/" style="color:#d4a373;">バックナンバー一覧</a>
          </div>
        </div>
        """
        recipients = [
            addr.strip() for addr in to_raw.split(",") if addr.strip()
        ]
        msg = EmailMessage()
        msg["Subject"] = (
            f"🌸 【Zazzy】本日のモーニングノート（{issue_date}号）が届きました"
        )
        msg["From"] = f"Zazzy Daily Magazine <{gmail_user}>"
        msg["To"] = ", ".join(recipients)
        msg.set_content(
            f"Zazzy ({issue_date}号) が発行されました。\n以下のURLからご覧ください：\n{site_url}"
        )
        msg.add_alternative(html_body, subtype="html")

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(gmail_user, gmail_pass)
                smtp.send_message(msg)
            print(f"✅ ダイジェストメール送信完了: {recipients}")
        except Exception as e:
            print(f"⚠️ メール送信エラー: {e}")
    else:
        print(
            "ℹ️ GMAIL_USER または GMAIL_APP_PASSWORD が未設定のためメール送信をスキップしました。"
        )

    # 2. LINE Messaging API 送信
    line_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    line_user_id = os.environ.get("LINE_USER_ID", "").strip()
    if line_token:
        line_text = (
            f"🌸 【Zazzy】{issue_date}号\n"
            f"🌡 {temp_val} | 🌇 {sunset_val} | ✨ {pickup_val}\n\n"
            f"📖 最新号をWebで開く:\n{site_url}\n\n"
            + "\n".join(line_lines[:8])
        )[:4900]
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {line_token}",
        }
        try:
            if line_user_id:
                r = requests.post(
                    "https://api.line.me/v2/bot/message/push",
                    headers=headers,
                    json={
                        "to": line_user_id,
                        "messages": [{"type": "text", "text": line_text}],
                    },
                    timeout=15,
                )
            else:
                r = requests.post(
                    "https://api.line.me/v2/bot/message/broadcast",
                    headers=headers,
                    json={"messages": [{"type": "text", "text": line_text}]},
                    timeout=15,
                )
            print(f"✅ LINE送信結果: status={r.status_code}, resp={r.text}")
        except Exception as e:
            print(f"⚠️ LINE送信エラー: {e}")
    else:
        print("ℹ️ LINE_CHANNEL_ACCESS_TOKEN が未設定のためLINE送信をスキップしました。")


if __name__ == "__main__":
    main()
