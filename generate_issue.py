import os
import sys
import io
import time
import glob
import requests
from datetime import datetime
from urllib.parse import quote
from PIL import Image
from google import genai

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found.")
    sys.exit(1)

client = genai.Client(api_key=api_key)
today = datetime.now().strftime("%Y-%m-%d")

# 1. 流山周辺の天気を取得
weather_res = requests.get(
    "https://api.open-meteo.com/v1/forecast?latitude=35.88&longitude=139.92&current=temperature_2m,relative_humidity_2m,weather_code&daily=sunset&timezone=Asia%2FTokyo"
).json()
current = weather_res.get("current", {})
daily = weather_res.get("daily", {})
current_temp = str(current.get("temperature_2m", "20"))
sunset = daily.get("sunset", ["18:00"])[0].split("T")[-1]

# 2. 過去号の被り防止チェック
past_posts = sorted(glob.glob("src/content/posts/*.md"), reverse=True)
past_context = ""
if past_posts:
    try:
        with open(past_posts[0], "r", encoding="utf-8") as f:
            past_context = f"\n【重要：前回号のトピック（これらと内容・選曲・紹介芸人・サウナ施設・カフェ・ユニクロ商品が絶対に重複しないこと）】\n{f.read()[:2000]}\n"
    except Exception as e:
        print(f"過去記事読み込みスキップ: {e}")

# 3. 雑誌用写真タグ
img_tag_1 = f'<div class="magazine-photo-box"><img src="/her-daily-magazine/images/{today}_scene1.jpg" alt="Today\'s Scene 1" /><p class="photo-caption">LIFE & PERSPECTIVE / ESSENTIAL LIVING</p></div>'
img_tag_2 = f'<div class="magazine-photo-box"><img src="/her-daily-magazine/images/{today}_scene2.jpg" alt="Today\'s Scene 2" /><p class="photo-caption">QUIET MOMENT / COFFEE & BOTANICAL</p></div>'

# 4. プロンプト（Zazzyエディトリアル・奥様専用）
SYSTEM_INSTRUCTION = f"""
あなたは上質で心地よい暮らしと豊かなカルチャーを提案する日刊プライベートマガジン『Zazzy（ザジー）』の編集長です。
読者は「育休中で赤ちゃんを育てており、流山おおたかの森エリアで暮らし、真空ジェシカやマユリカなどエッジの効いたお笑いラジオを愛し、エミネムやSOUL'd OUTなどクラシックなHip-Hop/Rapを好み、ユニクロやGUの洗練された着こなしに関心があり、シンプリストの暮らしを目指しながら、強迫性障害（OCD）の思考の癖を優しく調律して前向きに暮らしたい女性」です。
{past_context}

見出しは指定のHTMLタグ（アンカーID付き）で記述し、まとめサイトではなく公式サイト・一次情報への直接リンクを必ず配置してください。

---
<h2 id="simplicity">01. The Simplicity: シンプリストの心得・今日の名言</h2>
- 著名なミニマリスト・シンプリストの言葉や哲学を1つ紹介。
- モノだけでなく「情報」「思考」を手放し、余白をつくるための朝のヒント。

<h2 id="ocd-recovery">02. Mind & Recovery: 強迫性障害（OCD）と付き合い、手放すための思考調律コラム</h2>
【最重要：毎日異なる角度から、具体的・臨床心理学的に心を軽くする1,000〜1,200文字の本格エッセイとして執筆すること】
- **日替わりアプローチ**: 暴露反応妨害法（ERP）の実践、認知的脱フュージョン（「〜という強迫観念が浮かんでいるだけ」とラベリング）、不確実性の受容（「100%の安心」を求めない勇気）、脳の警報装置（扁桃体）の誤作動の捉え方、自責の解除。
- 育児中の「ちゃんと清潔にできているか」「戸締まり・安全確認」などへの過度な不安に対する具体的・現実的な処方箋。

<h2 id="comedy">03. The Comedy Wave: 深夜ラジオ・YouTube・ライブ解体</h2>
- **ピックアップ**: 真空ジェシカ、マユリカ、ランジャタイ、ママタルト、ダイアン、ロバートなどから日替わりで1組。
- 最近のラジオ（Podcast/TBSラジオ等）の神回、YouTube企画、ライブの熱量、尖った笑いの魅力を熱く語る。
- **【必須】リンク**: [▶ YouTubeでお笑い・ラジオを見る](https://www.youtube.com/results?search_query=芸人名+ラジオ+コント)

<h2 id="hiphop">04. The Classic Beat: Hip-Hop & Rap Archive</h2>
- エミネム（Eminem）、SOUL'd OUT、または90s-00sの日米クラシックな名曲を厳選。
- トラックの魅力、グルーヴ、リリックのパンチラインを解説。
- **【必須】リンク**: 
  - [🎵 YouTube Musicで聴く](https://music.youtube.com/search?q=曲名+アーティスト名)
  - [▶ YouTubeでMVを見る](https://www.youtube.com/results?search_query=曲名+アーティスト名)

<h2 id="baby">05. Baby & Motherhood: 赤ちゃん関連の重要トピック（厳選3選）</h2>
育休中のママが知っておきたい、エビデンスに基づいたリアルな知恵を3点具体的に解説：
1. **乳幼児の睡眠科学・ネントレのコツ** ([こども家庭庁](https://www.cfa.go.jp/))
2. **月齢ごとの発達と簡単ふれあい遊び** ([日本小児科学会](https://www.jpeds.or.jp/))
3. **ママの身体ケアと息抜きの工夫** ([厚生労働省 e-ヘルスネット](https://www.e-healthnet.mhlw.go.jp/))

<h2 id="fashion">06. Daily Style: ユニクロ・GU・ファーストリテイリング最新分析</h2>
- 今週チェックすべきユニクロ/GUのマストバイアイテム、機能美、着回しのヒント。
- ファーストリテイリングの企業動向やサステナビリティの最新ニュース。
- **【必須】リンク**: [👕 UNIQLO公式で最新アイテムを見る](https://www.uniqlo.com/jp/ja/) / [GU公式](https://www.gu-global.com/jp/ja/)

<h2 id="local-cafe">07. Local Living & Cafe: 流山おおたかの森 & 素敵なカフェ</h2>
- 流山おおたかの森周辺の耳寄り情報、美味しいテイクアウト、子連れにも優しいカフェご飯。
- こだわりのコーヒーや空間が魅力のカフェを日替わりで1軒紹介。
- **【必須】リンク**: [☕ 食べログで流山おおたかの森のカフェを見る](https://tabelog.com/chiba/A1203/A120305/rstLst/cafe/)

<h2 id="sauna">08. Steam & Escape: 周辺の名サウナ・温浴施設</h2>
- スパメッツァおおたかの森、野天風呂湯の郷など、流山周辺やアクセス良好な名温浴施設を日替わりで1館フィーチャー。
- 女性サウナ・炭酸泉・泥パック・外気浴スペースのスペックとリフレッシュ法。
- **【必須】リンク**: [🧖 サウナイキタイで「施設名」を見る](https://sauna-ikitai.com/search?keyword=施設名)

<h2 id="evidence">09. Evidence Wellness: 論文が教える健康と整え方</h2>
- PubMedなどの最新研究論文に基づく、睡眠・腸内環境・カフェイン・メンタル回復の知性。
- 具体的な生活への取り入れ方を分かりやすく解説。

<h2 id="colophon">10. Editor's Colophon</h2>
- 今日の流山の風や空、暮らしのリズムについての静かな1行。
"""

user_prompt = f"""
本日の環境データ:
- 日付: {today} / 流山の気温: {current_temp}℃ / 日没: {sunset}

記事本文の適切な場所に、以下の2つのライフスタイル写真タグを必ず配置してください：
{img_tag_1}
{img_tag_2}

「02. Mind & Recovery」は強迫性障害の思考調律コラムとしてしっかりとした文量（1,000文字以上）で執筆し、各リンクは指定に従ってMarkdown形式のみで出力してください。
"""

model_name = "gemini-3.6-flash"
response = None

print(f"--- モデル {model_name} で執筆開始 ---")
for attempt in range(1, 4):
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=dict(system_instruction=SYSTEM_INSTRUCTION, temperature=0.7),
        )
        if response and response.text:
            print("成功: 記事が完成しました！")
            break
    except Exception as e:
        err_str = str(e)
        print(f"試行 {attempt}/3 でエラー: {err_str}")
        time.sleep(10)

if not response or not response.text:
    print("生成をスキップしてデプロイを継続します。")
    sys.exit(0)

# 5. &Premium / Zazzy風の上品なライフスタイル写真を2枚生成
os.makedirs("public/images", exist_ok=True)
prompt_1 = "Authentic lifestyle 35mm film photograph of a minimalist clean bright kitchen counter with organic ceramic mugs and fresh botanical plants, soft natural daylight streaming in, &Premium magazine aesthetic, kinfolk style, peaceful atmosphere"
prompt_2 = "Candid lifestyle 35mm photograph of a cozy living room with a comfortable linen sofa, open art book, steaming cup of herbal tea, soft aesthetic shadows, minimalist interior design, documentary style"

scenes = [
    (prompt_1, f"public/images/{today}_scene1.jpg"),
    (prompt_2, f"public/images/{today}_scene2.jpg")
]

def generate_and_save_photo(prompt_text, file_path):
    try:
        img_res = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt_text,
            config=dict(number_of_images=1, aspect_ratio="16:9")
        )
        for gen_img in img_res.generated_images:
            img = Image.open(io.BytesIO(gen_img.image.image_bytes))
            img.save(file_path, "JPEG")
            print(f"Imagenで生成成功: {file_path}")
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
            print(f"フォトエンジンで保存完了: {file_path}")
    except Exception as ex:
        print(f"画像保存エラー: {ex}")

for p_text, s_path in scenes:
    generate_and_save_photo(p_text, s_path)

# 6. 保存
os.makedirs("src/content/posts", exist_ok=True)
frontmatter = f"""---
title: "Issue - {today}"
date: "{today}"
temp: "{current_temp}°C"
sunset: "{sunset}"
location: "Nagareyama Otakanomori"
---

"""

file_path = f"src/content/posts/{today}.md"
with open(file_path, "w", encoding="utf-8") as f:
    f.write(frontmatter + response.text)

print(f"Successfully published issue: {file_path}")
