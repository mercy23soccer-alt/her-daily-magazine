import os
import sys
import io
import time
import glob
import re
import random
import requests
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from PIL import Image
from google import genai

# 日本時間（JST）の厳格取得
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

# 1. 天気の取得（流山おおたかの森）
weather_res = requests.get(
    "https://api.open-meteo.com/v1/forecast?latitude=35.87&longitude=139.93&current=temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m&daily=sunset&timezone=Asia%2FTokyo"
).json()
current = weather_res.get("current", {})
daily = weather_res.get("daily", {})
current_temp = str(current.get("temperature_2m", "22"))
sunset = daily.get("sunset", ["18:00"])[0].split("T")[-1]

# 2. 【過去90日分】全記事から重複禁止トピックを自動抽出
past_posts = sorted(glob.glob("src/content/posts/*.md"), reverse=True)[:90]
past_used_topics = []

for p in past_posts:
    try:
        with open(p, "r", encoding="utf-8") as f:
            c = f.read()
            date_label = os.path.basename(p).replace(".md", "")
            items = []
            for line in c.splitlines():
                line_str = line.strip()
                if line_str.startswith("#") or line_str.startswith("<h2") or line_str.startswith("<h3"):
                    clean_h = re.sub(r'<[^>]+>|[#*]', '', line_str).strip()
                    if clean_h and not any(k in clean_h for k in [
                        "調律", "Laugh & Smile", "Comedy Chronicle", "Baby & Parenting",
                        "Baby Travel", "Cafe & Relax", "Wardrobe Pick", "Serene Sauna",
                        "Chill & Hip-Hop", "Relaxing Stream", "おおたかの森とグリーン", "本とことば",
                        "Daily Refresh", "Editor's Colophon"
                    ]):
                        items.append(clean_h)
                elif any(k in line_str for k in ["ネタ", "芸人", "カフェ", "店", "サウナ", "宿", "温泉", "本", "曲", "番組"]):
                    bolds = re.findall(r'\*\*(.*?)\*\*', line_str)
                    if bolds:
                        items.extend(bolds[:2])
                    else:
                        clean_l = re.sub(r'<[^>]+>|\[.*?\]\(.*?\)|\*', '', line_str).strip()
                        if 3 < len(clean_l) < 45:
                            items.append(clean_l)

            seen = set()
            unique_items = [x for x in items if not (x in seen or seen.add(x))]
            if unique_items:
                past_used_topics.append(f"【{date_label}号】: " + " / ".join(unique_items[:8]))
    except Exception as e:
        pass

past_context = "\n".join(past_used_topics) if past_used_topics else "（過去90日間の記録なし）"

img_tag_1 = f'<div class="magazine-photo-box"><img src="/her-daily-magazine/images/{today}_scene1.jpg" alt="Today\'s Scene 1" /><p class="photo-caption">QUIET MORNING & CAFE SCENE</p></div>'
img_tag_2 = f'<div class="magazine-photo-box"><img src="/her-daily-magazine/images/{today}_scene2.jpg" alt="Today\'s Scene 2" /><p class="photo-caption">BOTANICAL, SPA & SIMPLE LIVING</p></div>'

# 3. 執筆プロンプト
SYSTEM_INSTRUCTION = f"""
あなたは雑誌『クウネル』『&Premium』『天然生活』のような、美しく静謐な暮らしを提案する日刊マガジン『Zazzy』の編集長です。
読者は「千葉県流山おおたかの森で穏やかに暮らし、お笑い・ラジオで笑い、北欧インテリアや植物を慈しみ、上質なサウナやスパで癒やされ、カフェ巡りを愛し、心地よいヒップホップを聴きながら赤ちゃんの成長を見守る女性・志保さん」です。

【最重要：過去90日間に取り上げたトピック・固有名詞一覧】
以下の過去90日間に登場した「芸人、ネタ、カフェ店名、育児情報、旅行先・宿、サウナ施設、音楽、番組、思想・哲学テーマ」は絶対に重複・再使用しないでください：
{past_context}

【最重要執筆ルール】
1. **出力前セルフチェック**: あなたは出力を行う前に、以下の全14セクションがすべて揃っており、上記の過去90日間の記録と一切被りがないかを内部で厳密に確認してください。
2. **お笑いネタの多様化と個別リンク**: 特定の芸人に固執せず、ベテラン・中堅・若手賞レース注目株、劇場で話題のコント師、大学お笑い出身など幅広くリサーチし、過去90日間に登場していない癒やしの名作ネタを3組紹介してください。各ネタの直後に必ず専用の個別YouTubeリンクを設置すること。
3. **カフェ案内の広域化**: おおたかの森駅周辺が尽きそうになったら、**近隣の柏の葉キャンパス、柏、松戸、野田、TX沿線、目白（豊島区）、都内各所（清澄白河、蔵前、代々木上原、神保町等）**まで広げ、過去90日間で一度も紹介されていない実在の居心地の良いカフェ・ロースタリー・喫茶店を日替わりで紹介し、Googleマップリンクを配置してください。
4. **育児情報の広域化**: 睡眠やスキンケアの固定化を避け、月齢に応じた遊び、離乳食の素材選び、知育・絵本の選び方、海外（北欧等）の育児思想など、周辺知識へ幅広く広げ、過去90日間のトピックと重複させないでください。
5. **こころの調律の深化**: 決まり文句（脱フュージョン・減算法など）に頼らず、心理学（セルフ・コンパッション、ポジティブ心理学等）、西洋哲学（ストア派、エピクロス、モンテーニュ等）、仏教（禅、中道、放下着等）、東洋思想（知足、中庸等）から日替わりで異なる思想を選び、育児や暮らしに寄り添う温かい心の持ち方を語りかけてください。
6. **本文冒頭のメタデータ禁止**: 「title:」「date:」などの文字列は出力せず、いきなり「01. 調律とセルフ・コンパッション」から書き始めること。

見出し構成（全14セクション完全網羅）：
---
<h2 id="minimal">01. 調律とセルフ・コンパッション: こころと暮らしの心理的安全性</h2>
過去90日間で取り上げていない心理学や東洋・西洋哲学（禅、ストア派、セルフ・コンパッション、老荘思想、アドラー等）から1つを選び、母親としての肩の荷をふっと下ろし、自分自身への絶対的な味方意識を育む温かいエッセイ。

<h2 id="laugh">02. Laugh & Smile: おすすめ芸人ネタ紹介（厳選3選）</h2>
ベテランから気鋭若手まで、日常の合間にクスッと笑えて癒やされる名作ネタを3本厳選（過去90日間と重複禁止）。
各ネタの解説文の直後に、それぞれ個別のYouTubeリンクを配置すること：
- **ネタ1の紹介と見どころ解説**
  - [▶ YouTubeで「芸人名 ネタ名」を見る](https://www.youtube.com/results?search_query=芸人名+ネタ名)
- **ネタ2の紹介と見どころ解説**
  - [▶ YouTubeで「芸人名 ネタ名」を見る](https://www.youtube.com/results?search_query=芸人名+ネタ名)
- **ネタ3の紹介と見どころ解説**
  - [▶ YouTubeで「芸人名 ネタ名」を見る](https://www.youtube.com/results?search_query=芸人名+ネタ名)

<h2 id="comedy-history">03. Comedy Chronicle: 平成〜令和のお笑い史 ＆ 賞レース解体新書</h2>
平成〜令和の黄金期を彩ったコンビ・トリオや、M-1、KOC等の賞レースの名勝負・名ネタの背景にある人間ドラマと熱い系譜を情緒豊かに解説（過去90日間と被らない対象）。

<h2 id="baby">04. Baby & Parenting: 知っておきたい赤ちゃん情報（厳選3選）</h2>
睡眠、スキンケア、感覚遊び、離乳食、小児科学の最新知見など、多角的な周辺情報から過去90日間と被らない3点解説。

<h2 id="baby-travel">05. Baby Travel: 赤ちゃんと行けるオススメの旅行先</h2>
都内・関東近郊（箱根、伊香保、那須、軽井沢、房総等）の実在するウェルカムベビーなお宿や自然豊かなスポットを1カ所セレクト（過去90日間と被らないこと）。

<h2 id="cafe">06. Cafe & Relax: おおたかの森・目白・東京の心地よいカフェ案内</h2>
**流山おおたかの森、柏、松戸、目白、都内（清澄白河、蔵前、代々木上原等）**から、過去90日間で未紹介の実在する居心地抜群のカフェ・ロースタリーを1〜2軒紹介。
- お店の空気感、ベビーカーでの入りやすさ、おすすめのドリンク・スイーツ。
- [☕ Googleマップで「店名」の場所を見る](https://www.google.com/maps/search/?api=1&query=店名+カフェ)

<h2 id="uniqlo">07. Wardrobe Pick: 今季ユニクロのイチ推しアイテム＆着こなし</h2>
動きやすさと上品さを両立した今季の優秀アイテム1点と着こなしのコツ。

<h2 id="sauna-spa">08. Serene Sauna & Spa: 心をほどく極上サウナ＆温冷浴</h2>
女性が安心して寛げる実在の温浴・スパ施設（過去90日間と重複禁止）。
- [🧖 サウナイキタイで詳細を見る](https://sauna-ikitai.com/)

<h2 id="chill-hiphop">09. Chill & Hip-Hop: 暮らしに寄り添うヒップホップ名曲</h2>
お部屋やカフェタイムのBGMに心地よい、メロウで温かいヒップホップ／ネオソウル楽曲を1曲（過去90日間と重複禁止）。
- [🎵 YouTube Musicで聴く](https://music.youtube.com/)

<h2 id="stream">10. Relaxing Stream: 今観たい、おすすめの番組・配信</h2>
授乳や寝かしつけの合間に頭を空っぽにして笑える・癒やされる配信番組やラジオ番組を1本紹介（過去90日間と被らないこと）。

<h2 id="otaka">11. おおたかの森とグリーン: 季節の風と散歩道</h2>
流山おおたかの森周辺の緑や散歩道、観葉植物・ボタニカルのある暮らしのエッセイ。

<h2 id="book">12. 本とことばの処方箋: 静かな夜に開く1冊</h2>
心がじんわり温まる小説やエッセイを1冊セレクト（過去90日間と重複禁止）。

<h2 id="refresh">13. Daily Refresh: ほっと一息のティータイム</h2>
ノンカフェインのお茶や、お取り寄せ焼き菓子の小話。

<h2 id="colophon">14. Editor's Colophon: 今日のひとこと</h2>
今日を健やかに過ごすための優しい結びの言葉。
"""

user_prompt = f"""
本日の環境データ: 日付 {today} / 流山おおたかの森の気温 {current_temp}℃ / 日没 {sunset}
本文の適切な場所に以下の2枚の写真タグを配置してください：
{img_tag_1}
{img_tag_2}

【事前確認指示】
全14セクションが揃っており、過去90日間のトピックと重複が一切ないことを点検してから出力してください。Markdown形式で出力してください。
"""

response_text = None

if client:
    print("--- Gemini API で執筆中 ---")
    try:
        res = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=user_prompt,
            config=dict(system_instruction=SYSTEM_INSTRUCTION, temperature=0.75),
        )
        if res and res.text and len(res.text) > 1400:
            print("✅ 成功: Gemini APIでフルボリューム記事が完成しました！")
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
        r = requests.post("https://text.pollinations.ai/", json=payload, timeout=90)
        if r.status_code == 200 and len(r.text) > 1300:
            print("✅ 成功: バックアップAIで記事が完成しました！")
            response_text = r.text
    except Exception as ex:
        print(f"バックアップAIエラー: {ex}")

if not response_text or len(response_text) < 800:
    print("❌ 記事生成に失敗しました。")
    sys.exit(1)

clean_text = re.sub(r'^(title:.*?\n|date:.*?\n|temp:.*?\n|sunset:.*?\n)+', '', response_text.strip(), flags=re.MULTILINE | re.IGNORECASE).strip()

# 4. 【完全改修】画像の生成完了確認（2枚揃ってから記事出力へ進む）
os.makedirs("public/images", exist_ok=True)
prompt_1 = "Authentic candid 35mm film photograph of a bright stylish cafe corner with a ceramic cup of latte, green plant on natural wood table, soft morning sun, simple living magazine style"
prompt_2 = "Gentle lifestyle 35mm film photograph of a cozy natural spa and warm herbal sauna atmosphere with cedar wood, relaxing ambiance, quiet peaceful feeling"

if client:
    try:
        photo_gen_prompt = f"""
以下の記事本文を読み、この号にふさわしい、雑誌『&Premium』『クウネル』風の美しく優しい35mmフィルム写真のプロンプト（英語・1文・高品質指示）を2つ考案してください。
1つ目は本日紹介されたカフェやスイーツ、2つ目は上質なサウナ・スパ、植物、赤ちゃんとのお部屋時間をテーマにしてください。
出力形式：
PROMPT1: <英語プロンプト>
PROMPT2: <英語プロンプト>

記事抜粋：
{clean_text[:1200]}
"""
        p_res = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=photo_gen_prompt,
        )
        if p_res and p_res.text:
            m1 = re.search(r'PROMPT1:\s*(.+)', p_res.text)
            m2 = re.search(r'PROMPT2:\s*(.+)', p_res.text)
            if m1:
                prompt_1 = m1.group(1).strip() + ", authentic 35mm film photography, soft natural lighting, &Premium magazine style"
            if m2:
                prompt_2 = m2.group(1).strip() + ", authentic 35mm film photography, gentle warm atmosphere, quiet simple living"
            print("✅ 記事連動型オリジナル画像プロンプトの生成に成功！")
    except Exception as e:
        print(f"動的プロンプト生成スキップ: {e}")

scenes = [
    (prompt_1, f"public/images/{today}_scene1.jpg"),
    (prompt_2, f"public/images/{today}_scene2.jpg")
]

def generate_and_save_photo(prompt_text, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # A. Imagen (Gemini API)
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
                if os.path.exists(file_path) and os.path.getsize(file_path) > 5000:
                    print(f"✅ Imagenで生成成功: {file_path}")
                    return True
        except Exception as e:
            print(f"Imagenスキップ/失敗: {e}")

    # B. Pollinations AI（最大3回リトライ、60秒タイムアウト）
    clean_prompt = quote(prompt_text)
    for attempt in range(1, 4):
        try:
            seed_val = int(time.time()) + random.randint(1000, 99999)
            url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=1200&height=675&nologo=true&seed={seed_val}"
            print(f"画像生成試行中 ({attempt}/3): {file_path}")
            r = requests.get(url, timeout=60)
            if r.status_code == 200 and len(r.content) > 5000:
                with open(file_path, "wb") as f:
                    f.write(r.content)
                img = Image.open(file_path)
                img.verify()
                print(f"✅ フォトエンジンで生成完了: {file_path} ({os.path.getsize(file_path)} bytes)")
                return True
        except Exception as ex:
            print(f"⚠️ 画像生成リトライ中 ({attempt}/3): {ex}")
            time.sleep(5)

    # C. 高品質フォールバック写真の保存
    try:
        r = requests.get("https://picsum.photos/1200/675", timeout=30)
        if r.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(r.content)
            print(f"⚠️ バックアップ写真で保存完了: {file_path}")
            return True
    except Exception as e:
        print(f"フォールバック失敗: {e}")

    return False

print("=== 画像生成プロセス開始 ===")
for idx, (p_text, s_path) in enumerate(scenes):
    success = generate_and_save_photo(p_text, s_path)
    if not success or not os.path.exists(s_path) or os.path.getsize(s_path) < 1000:
        dummy = Image.new("RGB", (1200, 675), color=(245, 240, 235))
        dummy.save(s_path, "JPEG")
        print(f"⚠️ プレースホルダー画像を配置: {s_path}")
    if idx < len(scenes) - 1:
        print("2枚目の画像生成まで 6秒 待機します...")
        time.sleep(6)

assert os.path.exists(scenes[0][1]) and os.path.getsize(scenes[0][1]) > 500, "Scene 1 is missing!"
assert os.path.exists(scenes[1][1]) and os.path.getsize(scenes[1][1]) > 500, "Scene 2 is missing!"
print("✅ すべての画像（SCENE 01 / SCENE 02）がディスクに生成完了しました。")

# 5. 画像生成が完了した後に、Markdown記事を保存して出力完了
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
