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

# 2. 過去記事スキャン
past_posts = sorted(glob.glob("src/content/posts/*.md"), reverse=True)
past_context = ""
if past_posts:
    try:
        with open(past_posts[0], "r", encoding="utf-8") as f:
            past_context = f"\n【重要：前回号のトピック（これらと重複禁止）】\n{f.read()[:2200]}\n"
    except Exception as e:
        print(f"過去記事スキップ: {e}")

img_tag_1 = f'<div class="magazine-photo-box"><img src="/her-daily-magazine/images/{today}_scene1.jpg" alt="Today\'s Scene 1" /><p class="photo-caption">QUIET MORNING & CAFE IN NAGAREYAMA</p></div>'
img_tag_2 = f'<div class="magazine-photo-box"><img src="/her-daily-magazine/images/{today}_scene2.jpg" alt="Today\'s Scene 2" /><p class="photo-caption">BOTANICAL, SPA & SIMPLE LIVING</p></div>'

# 3. 執筆プロンプト
SYSTEM_INSTRUCTION = f"""
あなたは雑誌『クウネル』『&Premium』『天然生活』のような、美しく静謐な暮らしを提案する日刊マガジン『Zazzy』の編集長です。
読者は「千葉県流山おおたかの森で穏やかに暮らし、お笑い・ラジオで笑い、北欧インテリアや植物を慈しみ、上質なサウナやスパで癒やされ、カフェ巡りを愛し、心地よいヒップホップを聴きながら赤ちゃんの成長を見守る女性・志保さん」です。
{past_context}

【最重要執筆ルール】
1. **出力前セルフチェック**: あなたは出力を行う前に、以下の全14セクションがすべて揃っているかを内部で厳密に確認してください。1つでも欠落させることは固く禁じます。
2. **お笑い各ネタの個別リンク**: 02章のネタ3選は、それぞれの紹介文の直後に必ずYouTube検索リンクを設置してください。
3. **カフェ情報の詳細とマップリンク**: 06章のカフェ案内では、流山おおたかの森、目白、都内の実在カフェを具体的に挙げ、雰囲気やおすすめメニューに加え、Googleマップリンクを配置してください。
4. **本文冒頭のメタデータ禁止**: 「title:」「date:」などの文字列は出力せず、いきなり「01. 調律とセルフ・コンパッション」から書き始めること。
5. **上品でやさしい言葉遣い**: 育児や家事の合間にほっと心がほどける、温かく洗練されたエッセイ調で執筆すること。

見出し構成（全14セクション完全網羅）：
---
<h2 id="minimal">01. 調律とセルフ・コンパッション: こころと暮らしの心理的安全性</h2>
認知的脱フュージョンに加え、セルフ・コンパッションと心理的安全性を深める温かいエッセイ。自分への無条件の味方意識と減算法。

<h2 id="laugh">02. Laugh & Smile: おすすめ芸人ネタ紹介（厳選3選）</h2>
家事や育児の合間に、何も考えずに笑えてホッと癒やされる名作ネタを3本厳選紹介（男性ブランコ、かが屋、令和ロマン等）。
各ネタの解説文の直後に、それぞれ個別のYouTubeリンクを配置すること：
- **ネタ1の紹介と解説**
  - [▶ YouTubeで「芸人名 ネタ名」を見る](https://www.youtube.com/results?search_query=芸人名+ネタ名)
- **ネタ2の紹介と解説**
  - [▶ YouTubeで「芸人名 ネタ名」を見る](https://www.youtube.com/results?search_query=芸人名+ネタ名)
- **ネタ3の紹介と解説**
  - [▶ YouTubeで「芸人名 ネタ名」を見る](https://www.youtube.com/results?search_query=芸人名+ネタ名)

<h2 id="comedy-history">03. Comedy Chronicle: 平成〜令和のお笑い史 ＆ 賞レース解体新書</h2>
ピース（又吉直樹・綾部祐二の文学と野心）、チュートリアル、笑い飯、フットボールアワー、NON STYLE、千鳥、オードリーなど、2000年代〜2010年代の黄金期を中心に、M-1グランプリやキングオブコント等の名勝負・名ネタの背景にあるドラマや熱い系譜を情緒豊かに解説。

<h2 id="baby">04. Baby & Parenting: 知っておきたい赤ちゃん情報（厳選3選）</h2>
忙しい日々の負担を減らし、赤ちゃんと心地よく過ごすための最新エビデンスを3点具体的に解説：
1. **秋〜冬のスキンケア**: 水分補給＋ワセリンの蓋
2. **快眠の最適解**: 室温20〜22℃＋スリーパー
3. **お出かけを身軽にするグッズ**: 液体ミルク＆専用アタッチメントなど

<h2 id="baby-travel">05. Baby Travel: 赤ちゃんと行けるオススメの旅行先</h2>
赤ちゃんと無理なく楽しめる、都内・関東近郊（箱根、熱海、那須、軽井沢、房総等）の実在する旅行先・宿を1カ所セレクト：
- ウェルカムベビー認定の宿、お部屋食や貸切風呂の有無
- 調乳ポットやおむつ用ゴミ箱などの備え付けサポート
- ベビーカーで気持ちよくお散歩できる周辺の自然やカフェ環境

<h2 id="cafe">06. Cafe & Relax: おおたかの森・目白・東京の心地よいカフェ案内</h2>
**流山おおたかの森、目白（豊島区）、東京周辺**から、実在する居心地抜群のカフェを日替わりで1〜2軒紹介：
- お店の空気感（自然光の入り方、インテリアの美しさ、緑の借景、テラス席の心地よさ）
- ベビーカーでの入店しやすさや、ゆったり過ごせる席の間隔
- おすすめのドリンク（丁寧に淹れたドリップ珈琲、カフェインレスラテ、ハーブティー）とスイーツ（スコーン、キャロットケーキ、プリンなど）
- [☕ Googleマップで「店名」の場所を見る](https://www.google.com/maps/search/?api=1&query=店名+カフェ)

<h2 id="uniqlo">07. Wardrobe Pick: 今季ユニクロのイチ推しアイテム＆着こなし</h2>
育児中の「動きやすさ」「抱っこ紐との相性」「自宅でガシガシ洗えること」を両立した、今季ユニクロの優秀アイテム（タックワイドパンツ等）を1点厳選ピックアップし、上品に見える着こなしのコツを解説。

<h2 id="sauna-spa">08. Serene Sauna & Spa: 心をほどく極上サウナ＆温冷浴</h2>
女性が心地よくリフレッシュできる実在の上質サウナ・スパ施設を日替わりで1館フィーチャー：
- 清潔感、アメニティの充実度（ドライヤー、オーガニックコスメ等）
- サウナ室の温度・湿度（アロマスチーム、塩サウナ、セルフロウリュなど）
- 水風呂の水温と肌あたり（冷たすぎず心地よいバイブラや天然水）
- 静かに深く休めるリクライニングや外気浴テラス
- [🧖 サウナイキタイで詳細を見る](https://sauna-ikitai.com/)

<h2 id="chill-hiphop">09. Chill & Hip-Hop: 暮らしに寄り添うヒップホップ名曲</h2>
育児やお部屋時間のBGMに心地よい、メロウで温かいヒップホップ／ネオソウル楽曲を1曲厳選（Nujabes、Lauryn Hill、Chance the Rapper、Tom Misch、Awichのメロウ曲等）。心をやさしく揺らすトラックの魅力と聴きどころ。
- [🎵 YouTube Musicで聴く](https://music.youtube.com/)

<h2 id="stream">10. Relaxing Stream: 今観たい、おすすめの番組・配信</h2>
赤ちゃんが寝静まったあとや授乳の合間に、頭を空っぽにしてクスッと笑えたり心が癒やされたりする作品（Netflix、Amazonプライム、バラエティ番組、深夜ラジオ番組など）を1本紹介。

<h2 id="otaka">11. おおたかの森とグリーン: 季節の風と散歩道</h2>
流山おおたかの森周辺の緑や散歩道、観葉植物・ボタニカルのある暮らし、季節の移ろいを感じるエッセイ。

<h2 id="book">12. 本とことばの処方箋: 静かな夜に開く1冊</h2>
心がじんわり温まる小説やエッセイを1冊セレクト。静かな夜に開きたくなる理由。

<h2 id="refresh">13. Daily Refresh: ほっと一息のティータイム</h2>
ノンカフェインのお茶（ルイボスバニラ等）や、お取り寄せ焼き菓子の小話。深呼吸の提案。

<h2 id="colophon">14. Editor's Colophon: 今日のひとこと</h2>
今日を健やかに過ごすための優しい結びの言葉。
"""

user_prompt = f"""
本日の環境データ: 日付 {today} / 流山おおたかの森の気温 {current_temp}℃ / 日没 {sunset}
本文の適切な場所に以下の2枚の写真タグを配置してください：
{img_tag_1}
{img_tag_2}

【事前確認指示】
全14セクションが揃っていることを完全に確認してから、すべて丁寧に出力してください。Markdown形式で出力してください。
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

# 4. 【新設計】奥様マガジン用「日替わり動的プロンプト」生成
os.makedirs("public/images", exist_ok=True)

cafe_scenes = [
    "A bright quiet corner table in a stylish Tokyo cafe with a slice of carrot cake on vintage ceramic plate, soft natural morning sunlight, 35mm film photography, Kinfolk aesthetic",
    "A cozy wooden table in a cafe with a warm matcha latte art cup and open notebook, green garden view through glass window, gentle analog photography",
    "Spacious scandinavian cafe interior with high ceiling, exposed concrete and natural oak furniture, lush potted plants, serene morning atmosphere",
    "Close-up of a fresh baked scone with clotted cream and strawberry jam on linen napkin beside a glass teapot, warm documentary style",
    "A sunny outdoor terrace cafe table shaded by green trees, delicate porcelain coffee cup, peaceful European-style street view, soft film grain"
]

life_spa_scenes = [
    "A tranquil herbal steam sauna room with aromatic herbs hanging from cedar walls, gentle diffuse mist, serene spa photography, Kinfolk style",
    "A natural stone outdoor hot spring bath surrounded by Autumn foliage, soft steam rising in crisp morning air, relaxing luxury ryokan aesthetic",
    "A calm living room nursery nook with soft cream linen blanket, natural rattan baby basket, warm diffuse morning sun, gentle parenting lifestyle",
    "Glass vase with blooming eucalyptus and white flowers on a light wood sideboard, soft morning shadows, minimal interior styling",
    "A cozy reading chair beside a bookshelf, warm woven throw blanket, cup of steaming chamomile tea on side table, evening golden hour glow"
]

day_seed = now_jst.timetuple().tm_yday
prompt_1 = cafe_scenes[day_seed % len(cafe_scenes)]
prompt_2 = life_spa_scenes[(day_seed + 2) % len(life_spa_scenes)]

if client:
    try:
        photo_gen_prompt = f"""
以下の記事本文を読み、この号にふさわしい、雑誌『&Premium』『クウネル』風の美しく優しい35mmフィルム写真のプロンプト（英語・1文・高品質指示）を2つ考案してください。
1つ目は本日紹介されたカフェや美味しいスイーツ・珈琲、2つ目は上質なサウナ・スパ、植物、赤ちゃんとの穏やかな暮らしのシーンにしてください。
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
        print(f"動的プロンプト生成スキップ（日替わりプールを使用）: {e}")

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
        url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=1200&height=675&nologo=true&seed={int(time.time()) + random.randint(1, 99999)}"
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
