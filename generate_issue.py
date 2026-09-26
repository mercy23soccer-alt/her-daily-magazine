import os
import sys
import io
import time
import glob
import re
import requests
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from PIL import Image
from google import genai

# 日本時間（JST = UTC+9）を明示的に取得
JST = timezone(timedelta(hours=9))
now_jst = datetime.now(JST)
today = now_jst.strftime("%Y-%m-%d")

api_key = os.environ.get("GEMINI_API_KEY")
client = None
if api_key:
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"Gemini初期化スキップ: {e}")

# 1. 天気の取得（流山おおたかの森周辺）
weather_res = requests.get(
    "https://api.open-meteo.com/v1/forecast?latitude=35.87&longitude=139.93&current=temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m&daily=sunset&timezone=Asia%2FTokyo"
).json()
current = weather_res.get("current", {})
daily = weather_res.get("daily", {})
current_temp = str(current.get("temperature_2m", "22"))
sunset = daily.get("sunset", ["18:00"])[0].split("T")[-1]

# 2. 過去記事の重複防止スキャン
past_posts = sorted(glob.glob("src/content/posts/*.md"), reverse=True)
past_context = ""
if past_posts:
    try:
        with open(past_posts[0], "r", encoding="utf-8") as f:
            past_context = f"\n【重要：前回号のトピック（これらと重複禁止）】\n{f.read()[:2000]}\n"
    except Exception as e:
        print(f"過去記事スキップ: {e}")

img_tag_1 = f'<div class="magazine-photo-box"><img src="/her-daily-magazine/images/{today}_scene1.jpg" alt="Today\'s Scene 1" /><p class="photo-caption">QUIET MORNING IN NAGAREYAMA</p></div>'
img_tag_2 = f'<div class="magazine-photo-box"><img src="/her-daily-magazine/images/{today}_scene2.jpg" alt="Today\'s Scene 2" /><p class="photo-caption">TEA, BOTANICAL & SIMPLE LIVING</p></div>'

# 3. 執筆プロンプト
SYSTEM_INSTRUCTION = f"""
あなたは雑誌『クウネル』『&Premium』『天然生活』のような、美しく静謐な暮らしを提案する日刊マガジン『Zazzy』の編集長です。
読者は「千葉県流山おおたかの森で穏やかに暮らし、お笑い・ラジオで笑い、北欧インテリアや植物を慈しみながら、赤ちゃんの成長を見守る女性」です。
{past_context}

【執筆ルール】
- 本文冒頭にタイトルやメタデータ（title:, date: など）は一切含めないこと。
- 心をほっと緩める、やさしく上品で文学的な言葉遣いで執筆すること。
- 各セクション、読み応えのある丁寧な文章量で記述すること。

見出し構成：
<h2 id="minimal">01. 調律と減算法: こころと暮らしの余白</h2>
<h2 id="laugh">02. 笑いとラジオ: 今日のクスッと</h2>
<h2 id="baby">03. 赤ちゃん便り: 小さな成長とエビデンス</h2>
<h2 id="otaka">04. おおたかの森とグリーン: 季節の風と散歩道</h2>
<h2 id="book">05. 本とことばの処方箋: 静かな夜に開く1冊</h2>
"""

user_prompt = f"""
本日の環境データ: 日付 {today} / 流山おおたかの森の気温 {current_temp}℃ / 日没 {sunset}
本文の適切な場所に以下の2枚の写真タグを配置してください：
{img_tag_1}
{img_tag_2}
やさしく知的なトーンで執筆してください。Markdown形式のみで出力してください。
"""

response_text = None

if client:
    print("--- Gemini API で執筆中 ---")
    try:
        res = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=user_prompt,
            config=dict(system_instruction=SYSTEM_INSTRUCTION, temperature=0.7),
        )
        if res and res.text and len(res.text) > 800:
            print("✅ 成功: Gemini APIで記事が完成しました！")
            response_text = res.text
    except Exception as e:
        print(f"⚠️ Gemini一時エラー: {str(e)[:100]}")

if not response_text:
    print("--- バックアップAIエンジンで執筆中 ---")
    try:
        combined_prompt = f"{SYSTEM_INSTRUCTION}\n\n---\n{user_prompt}"
        payload = {
            "messages": [{"role": "user", "content": combined_prompt}],
            "model": "openai",
            "seed": int(time.time())
        }
        r = requests.post("https://text.pollinations.ai/", json=payload, timeout=60)
        if r.status_code == 200 and len(r.text) > 800:
            print("✅ 成功: バックアップAIで記事が完成しました！")
            response_text = r.text
    except Exception as ex:
        print(f"バックアップAIエラー: {ex}")

if not response_text or len(response_text) < 500:
    print("❌ 記事生成に失敗しました。")
    sys.exit(1)

clean_text = re.sub(r'^(title:.*?\n|date:.*?\n|temp:.*?\n|sunset:.*?\n)+', '', response_text.strip(), flags=re.MULTILINE | re.IGNORECASE).strip()

# 4. 写真生成
os.makedirs("public/images", exist_ok=True)
prompt_1 = "Authentic candid 35mm film photograph of a bright scandinavian interior with natural oak table, green plant, soft morning sun, simple living magazine style"
prompt_2 = "Gentle lifestyle 35mm film photograph of a warm cup of herbal tea and an open book on a linen tablecloth, quiet peaceful atmosphere"

scenes = [
    (prompt_1, f"public/images/{today}_scene1.jpg"),
    (prompt_2, f"public/images/{today}_scene2.jpg")
]

def generate_and_save_photo(prompt_text, file_path):
    if client:
        try:
            img_res = client.models.generate_images(
                model="imagen-3.0-generate-002",
                prompt=prompt_text,
                config=dict(number_of_images=1, aspect_ratio="16:9")
            )
            for gen_img in img_res.generated_images:
                img = Image.open(io.BytesIO(gen_img.image.image_bytes))
                img.save(file_path, "JPEG")
                return
        except Exception:
            pass

    try:
        clean_prompt = quote(prompt_text)
        url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=1200&height=675&nologo=true&seed={int(time.time())}"
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(r.content)
    except Exception as ex:
        print(f"画像保存エラー: {ex}")

for p_text, s_path in scenes:
    generate_and_save_photo(p_text, s_path)

# 5. 保存
os.makedirs("src/content/posts", exist_ok=True)
frontmatter_block = f"""---
title: "Issue - {today}"
date: "{today}"
temp: "{current_temp}°C"
sunset: "{sunset}"
location: "Nagareyama Otakanomori"
---

"""

file_path = f"src/content/posts/{today}.md"
with open(file_path, "w", encoding="utf-8") as f:
    f.write(frontmatter_block + clean_text)

print(f"Successfully published issue: {file_path}")
