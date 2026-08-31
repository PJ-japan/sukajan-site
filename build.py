#!/usr/bin/env python3
"""サイトを組み立てて dist/ に書き出す。Python標準ライブラリのみ。

  python3 build.py              → このファイルの隣の dist/ に出力
  OUT_DIR=../public build.py    → 出力先を変えたいとき
"""
import json, os, pathlib, html, re, shutil
from datetime import date
from datetime import date
from datetime import date
from datetime import date
from datetime import date
from datetime import date

# このファイルが置かれている場所を基準にする（どこから実行しても動く）
ROOT = pathlib.Path(__file__).resolve().parent
OUT = pathlib.Path(os.environ.get("OUT_DIR") or (ROOT / "dist"))
OUT.mkdir(parents=True, exist_ok=True)
BASE = "https://hiromichiyokochi.com/"

# --------------------------------------------------------------------------
# フォームの送信先（Google Apps Script）
# ここだけ書き換えればよい。ビルド時に brief.html / contact.html へ差し込まれる。
# 手順は gas/README.md を参照。
# --------------------------------------------------------------------------
FORM_ENDPOINT = "https://script.google.com/macros/s/AKfycbyqXhWO6n93qLfer90h07fHA9CvWFR469xffpViUB5dY6s70F1Q_dPwlXuAXxNsVARL/exec"
FORM_SECRET   = "m5u0-yxSl-ByIk"  # gas/Code.gs の SECRET と同じ文字列にする
FORM_MAIL     = "info@ichi-pj.com"
CSS = (ROOT / "_style.css").read_text(encoding="utf-8")
DOCJS = (ROOT / "_doc.js").read_text(encoding="utf-8")


def content(name):
    """content/*.json を読む。無ければ空で続行する。"""
    f = ROOT / "content" / (name + ".json")
    if not f.exists():
        return [] if name != "notice" else {}
    return json.loads(f.read_text(encoding="utf-8"))


NOTICE = content("notice")
PRESS = content("press")
WORKS = content("works")


def press_html():
    years = {}
    for it in PRESS:
        y = str(it.get("date", ""))[:4] or "—"
        years.setdefault(y, []).append(it)
    out = []
    for y in sorted(years, reverse=True):
        rows = []
        for it in years[y]:
            tag = "a" if it.get("url") else "div"
            href = ' href="%s" target="_blank" rel="noopener"' % html.escape(it["url"], quote=True) if it.get("url") else ""
            rows.append(
                '<%s class="item"%s>'
                '<span class="item__d">%s</span>'
                '<span><p class="item__t">%s</p><p class="item__o">%s</p></span>'
                '<span class="item__k">%s</span></%s>' % (
                    tag, href,
                    html.escape(it.get("date", "")),
                    html.escape(it.get("title", "")),
                    html.escape(it.get("outlet", "")),
                    html.escape(it.get("kind", "")),
                    tag))
        out.append('<div class="press__year rise"><p class="press__y">%s</p>'
                   '<div class="press__list">%s</div></div>' % (y, "".join(rows)))
    return "\n".join(out) or '<p class="note">掲載情報がまだ登録されていません。content/press.json に追加してください。</p>'


# 用途別の索引。works.json の "use" に、この key を配列で入れる。
# 件数が 0 の用途は出力しない（空の見出しを出さないため）。
USES = [
    ("order",  "オーダーメイド・フルオーダー",
     "一着ずつ柄を描き起こし、横振り刺繍で仕上げる一点物。"),
    ("oem",    "スカジャンOEM・ブランド別注",
     "自社で量産しているスカジャン。この品質で、御社の別注をお受けします。"),
    ("design", "スカジャン柄のデザイン提供",
     "スカジャン以外の媒体にのせる柄。原画のみをお納めした案件。"),
    # 掲載できる事例が出たら use に "artist" を付ければ、この見出しが現れる
    ("artist", "アーティストコラボ",
     "ミュージシャン・作家との協業。ステージ衣装、ツアー物販。"),
]


def work_images(w):
    """images（配列）が正。古い image（単数）も読めるようにしておく。"""
    if w.get("images"):
        return [i for i in w["images"] if i]
    return [w["image"]] if w.get("image") else []


def work_href(w):
    """事例カードの飛び先。個別ページがあればそちら、無ければ外部リンク。"""
    if w.get("slug"):
        return "works-%s.html" % w["slug"]
    return w.get("url") or ""


def rail_html(items, wrap=False):
    cells = []
    for w in items:
        imgs = work_images(w)
        alt = html.escape(w.get("title", ""))
        if not imgs:
            img = '<div class="slot">背面</div>'
        elif len(imgs) >= 2:
            # 2枚目があるカードは、ホバーで裏面に切り替える（タッチ端末では起きない）
            img = ('<span class="flip"><img src="%s" alt="%s" loading="lazy">'
                   '<img class="flip__b" src="%s" alt="" aria-hidden="true" loading="lazy"></span>'
                   % (html.escape(imgs[0], quote=True), alt, html.escape(imgs[1], quote=True)))
        else:
            img = '<img src="%s" alt="%s" loading="lazy">' % (html.escape(imgs[0], quote=True), alt)
        body = '%s<h3>%s</h3><p class="note">%s</p>' % (
            img, alt, html.escape(w.get("meta", "")))
        url = work_href(w)
        if url:
            ext = ' target="_blank" rel="noopener"' if url.startswith("http") else ""
            cells.append('<a href="%s"%s>%s</a>' % (html.escape(url, quote=True), ext, body))
        else:
            # 飛び先が無いときはリンクなしのカードにする（press.json と同じ扱い）
            cells.append('<div>%s</div>' % body)
    cls = "rail rail--wrap" if wrap else "rail"
    return '<div class="%s">%s</div>' % (cls, "".join(cells))


def works_html(limit=None, drafts=False, wrap=False):
    """draft: true の事例は works2.html にだけ出す。
    公開するときは works.json から "draft" を消すだけでよい。"""
    items = [w for w in WORKS if bool(w.get("draft")) == drafts]
    if drafts and not items:
        return '<p class="note">いま下書き中の事例はありません。</p>'
    return rail_html(items[:limit] if limit else items, wrap=wrap)


def works_use_html(key):
    """特定の用途の事例だけを並べる（各サービスページ用）。下書きは除く。"""
    items = [w for w in WORKS if not w.get("draft") and key in (w.get("use") or [])]
    return rail_html(items, wrap=True)


def works_by_use_html():
    """用途ごとに見出しで区切って並べる。下書きも含めた全件が対象。
    絞り込みは JS ではなくアンカーで行う（URL が残り、検索にも載る）。"""
    out = []
    for key, label, lead in USES:
        items = [w for w in WORKS if key in (w.get("use") or [])]
        if not items:
            continue
        out.append(
            '<h3 id="use-%s">%s<span class="note" style="font-size:11px">　%d件</span></h3>'
            '<p class="note">%s</p>%s'
            % (key, html.escape(label), len(items), html.escape(lead), rail_html(items, wrap=True)))
    untagged = [w for w in WORKS if not w.get("use")]
    if untagged:
        out.append('<p class="note">※ 用途タグが未設定の事例が %d 件あります。'
                   'works.json の "use" に %s のいずれかを配列で入れてください。</p>'
                   % (len(untagged), " / ".join(k for k, _, _ in USES)))
    return "".join(out)


PERSON = {
    "@type": "Person",
    "@id": BASE + "#person",
    "name": "横地広海知",
    "alternateName": "Hiromichi Yokochi",
    "jobTitle": "スカジャン絵師 / スカジャン柄デザイナー",
    "description": "横須賀ドブ板通りを拠点に、スカジャンの柄をデザインするスカジャン絵師。1940-50年代の伝統柄の復興をライフワークとする。",
    "url": BASE,
    "sameAs": [
        "https://www.instagram.com/hiromichiyokochi/",
        "https://x.com/HiromichiYKC",
        "https://note.com/hiromichiyokochi",
        "https://prtimes.jp/main/html/searchrlp/company_id/185297",
    ],
    "knowsAbout": ["スカジャン", "横振り刺繍", "刺繍デザイン", "アパレルOEM"],
}

LOCAL = {
    "@type": "LocalBusiness",
    "@id": BASE + "#studio",
    "name": "ICHIドブ板本店",
    "alternateName": "スカジャン絵師 横地広海知",
    "description": "横須賀ドブ板通りの店舗。スカジャンの実物サンプル、横振り刺繍と機械刺繍の比較、生地見本をご確認いただけます。営業時間内はご予約なしでご来店いただけます。",
    "url": BASE,
    "image": BASE + "assets/ogp.jpg",
    "telephone": "+81-90-9924-4608",
    "address": {
        "@type": "PostalAddress",
        "postalCode": "238-0041",
        "streetAddress": "本町3-11-7 アイ's ビル 1F",
        "addressLocality": "横須賀市",
        "addressRegion": "神奈川県",
        "addressCountry": "JP",
    },
    "areaServed": "JP",
}

PAGES = {
    "index": dict(
        title="スカジャン絵師 横地広海知｜オリジナルスカジャンのオーダー・OEM｜横須賀ドブ板",
        desc="横須賀ドブ板通りのスカジャン絵師・横地広海知。オリジナルスカジャンの柄を描き起こし、一着のオーダーメイドからブランド別注・スカジャンOEMまで対応します。ご予約から引渡しまで3ヶ月〜。",
        nav="Home",
        crumbs=[],
        extra=[PERSON, LOCAL],
    ),
    "about": dict(
        title="横地広海知について｜オリジナルスカジャン柄を描くスカジャン絵師の経歴と実績",
        desc="オリジナルスカジャンの柄を専門に描くスカジャン絵師・横地広海知の経歴と作風。1981年名古屋生まれ、2008年に横須賀ドブ板通りへ。GU・PUMA・大阪関西万博・モンスターハンター・徳川美術館へのスカジャン柄デザイン提供実績。",
        nav="About",
        crumbs=[("横地広海知について", "about.html")],
        extra=[PERSON],
    ),
    "process": dict(
        title="オーダースカジャンの納期と進め方｜ご予約から引渡しまで3ヶ月〜",
        desc="オーダーメイドスカジャンとスカジャンOEMの納期。ヒアリングから納品までの日程、週次報告、修正回数の取り決めを公開しています。一着は3ヶ月〜、量産は最短3ヶ月半が目安です。",
        nav="Process",
        crumbs=[("納期と進め方", "process.html")],
        # ナビは主導線だけに絞る。ここはフッターの About 欄から辿れる
        unlisted=True,
        faq=[
            ("いちばん早くていつ届きますか", "一着のフルオーダーは、ご予約から引渡しまで3ヶ月〜が目安です。一点ずつお作りするため、ご予約の順にお受けしています。お急ぎの場合は個別にご相談ください。時期によっては最短1ヶ月での納品も可能です（別途特急料金が必要）。"),
            ("イベントに間に合わせたい日があります", "先に納品日をお知らせください。そこから逆算して間に合う進め方をご提案します。間に合わない場合はその場でお伝えします。"),
            ("途中でデザインを変えられますか", "デザイン確定日より前であれば可能です。確定後の変更は刺繍データの作り直しになるため、納期と費用が変わります。"),
            ("進捗はどうやって分かりますか", "週に一度、担当からご報告します。制作中の写真もお送りします。"),
        ],
    ),
    "oem": dict(
        title="スカジャンOEM・オリジナルスカジャン製作｜柄の専門デザイナーが1着から｜横地広海知",
        desc="オリジナルスカジャンのOEM・ブランド別注。GU・PUMA・大阪関西万博・徳川美術館などのコラボで柄を描いてきたスカジャン柄専門デザイナーが、柄のデザインから刺繍データ、量産手配まで一貫対応。1着から、目安価格を公開しています。",
        nav="OEM",
        crumbs=[("別注・量産", "oem.html")],
        service="スカジャンのブランド別注・OEM・柄デザイン",
        # 誰が描くのか（Person）と、どこで実物を見られるか（LocalBusiness）を載せる
        extra=[PERSON, LOCAL],
        faq=[
            ("柄のデザインからお願いできますか",
             "はい。柄の設計がむしろ本業です。スカジャン柄を専門に描いてきたデザイナーが、モチーフの選定と構図から起こします。刺繍でどう出るかを踏まえて描くため、量産時に柄が崩れません。"),
            ("契約書や発注書は、こちらの書式でも大丈夫ですか",
             "はい。秘密保持契約（NDA）、取引基本契約書、発注請書、見積書・請求書、反社会的勢力の排除に関する確認書など、御社所定の書式でご用意いただいて構いません。適格請求書発行事業者ですので、インボイス制度に対応した請求書を発行します。購買システムへの登録や取引先審査にも対応します。当方からは、著作権の扱いと利用許諾の範囲を明記した顧問弁護士監修の契約書をご用意しています。"),
            ("柄が何もない状態でも相談できますか",
             "はい。むしろその状態からのご依頼がほとんどです。入れたいモチーフや周年などのテーマだけ決まっていれば、構図から描き起こします。GUの全国流通商品や大阪・関西万博の公式ライセンス商品に採用された柄と同じ手で制作します。"),
            ("遠方ですが、打ち合わせに行く必要がありますか",
             "ヒアリング、ラフ確認、修正、進行報告まで、ほぼ全ての工程をオンラインで完結できます。オンライン会議と進行管理ツールで進めるため、所在地による進行の差はありません。実物をご覧になりたい場合は横須賀のICHIドブ板本店へお越しいただけます。"),
            ("デザインと生産を別々に手配するのと何が違いますか",
             "柄を描くデザイナーに加えて、生産管理の担当が同じ窓口にいます。しかもそのデザイナー自身が、ナショナルクライアントの案件で進行管理を担ってきたプロジェクトマネージャーです。デザインと生産の両方が分かる人間がヒアリングにあたるため、仕様の実現可能性と日程を打ち合わせの場でお答えできます。"),
            ("何着から受けてもらえますか",
             "1着から承ります。まず横振り刺繍で一着つくり、社内承認を取ってから量産に移す進め方もよくあります。"),
            ("デザインだけ、量産だけでも頼めますか",
             "どちらも可能です。柄のデザインデータのみの納品、すでにお持ちの図案での量産、どちらも承ります。"),
            ("スカジャン以外のアイテムの柄も頼めますか",
             "承ります。スウェットやTシャツなど、スカジャン以外のアイテム向けの柄も手がけています。"),
            ("発注前に実物を見られますか",
             "横須賀ドブ板通りのICHIドブ板本店で、実物のサンプルをご確認いただけます。横振り刺繍と機械刺繍の仕上がりの違い、生地見本、これまでの制作事例をご覧いただけます。営業時間内はご予約なしでご来店いただけます。遠方の場合は生地見本と刺繍サンプルの郵送でも対応します。"),
        ],
    ),
    "design": dict(
        title="スカジャン柄のデザイン依頼｜柄だけをお納めします｜スカジャン絵師 横地広海知",
        desc="スカジャン柄のデザインだけをご依頼いただけます。生産ラインをお持ちのブランド向けに、柄のイラストデータのみを納品。GU・PUMAへの柄提供実績。スウェットやTシャツなどスカジャン以外のアイテムの柄も承ります。刺繍化を前提とした線で描きます。",
        nav="柄のデザイン",
        crumbs=[("柄のデザイン", "design.html")],
        service="スカジャン柄のデザイン制作（柄データのみの納品）",
        extra=[PERSON],
    ),
    "order": dict(
        title="オーダーメイドスカジャン｜オリジナル柄を一着から｜フルオーダー｜横須賀ドブ板",
        desc="オーダーメイドのオリジナルスカジャンを一着から。入れたいモチーフをうかがって柄をゼロから描き起こし、ドブ板の横振り刺繍で仕上げる一点物。標準165,000円（税込）〜、ご予約から引渡しまで3ヶ月〜。海外からのご注文も対応。",
        nav="Made to order",
        crumbs=[("フルオーダー", "order.html")],
        service="フルオーダースカジャンの制作",
        faq=[
            ("絵の資料がなくても頼めますか", "大丈夫です。言葉でうかがって、こちらでラフを起こします。ご契約後には、過去の制作実績の資料もご覧いただけます。"),
            ("同じ柄をもう一着作れますか", "横振りは一点物のため、まったく同じものにはなりません。近い柄で作り直すか、機械刺繍に切り替える方法があります。"),
            ("海外から注文できますか", "可能です。英語でのやりとりにも対応しています。"),
        ],
    ),
    "works": dict(
        title="制作事例｜オーダースカジャン・ブランド別注の実績",
        desc="オリジナルスカジャンの制作事例。オーダーメイドの一点物、ブランド別注、アーティストグッズ、周年記念など、これまでに描いたスカジャン柄を掲載。最新の実績はInstagram（@hiromichiyokochi）で公開しています。",
        nav="Works",
        crumbs=[("制作事例", "works.html")],
    ),
    # 事例の書き溜め用。ナビ・フッター・sitemap には出さず noindex。
    # works.json に "draft": true を付けた項目だけがここに出る
    "works2": dict(
        title="制作事例（下書き）｜公開前の作業用ページ",
        desc="公開前の制作事例を確認するための作業用ページです。",
        nav="Works (draft)",
        crumbs=[("制作事例（下書き）", "works2.html")],
        unlisted=True,
        noindex=True,
    ),
    # 事例の個別ページ。ナビには出さないが、検索には載せる（noindex は付けない）
    "works-aoi-karakusa": dict(
        title="葵唐草鷹狩図黒天鵞絨羽織｜徳川美術館の所蔵品から起こしたスカジャン柄｜横地広海知",
        desc="中京テレビ『ムジナバケール』×徳川美術館の企画で制作した《葵唐草鷹狩図黒天鵞絨羽織》。家康公の「しかみ像」を題材に、鷹狩りと葵唐草を掛け合わせた新しい柄を描き起こしました。柄の決め方から刺繍の仕上げまで、制作の全工程を公開しています。",
        nav="葵唐草鷹狩図",
        crumbs=[("制作事例", "works.html"), ("葵唐草鷹狩図黒天鵞絨羽織", "works-aoi-karakusa.html")],
        unlisted=True,
    ),
    "press": dict(
        title="掲載・出演・受賞｜スカジャン絵師 横地広海知",
        desc="スカジャン絵師 横地広海知のメディア掲載・出演・受賞の記録。GU・PUMA・大阪関西万博などオリジナルスカジャンの案件に関する報道を、東京新聞・日本経済新聞・NHKほか38件まとめています。",
        nav="Press",
        crumbs=[("掲載・受賞", "press.html")],
    ),
    "brief": dict(
        title="ご依頼フォーム｜質問に答えるだけで仕様確認書ができます",
        desc="質問に答えるだけで、制作コンセプト・利用許諾の範囲・禁止事項まで入った仕様確認書が自動で作成されます。PDFで保存でき、内容はそのまま受注者へ届きます。5分ほどで終わります。",
        nav="Brief",
        crumbs=[("ご依頼フォーム", "brief.html")],
        unlisted=True,
        noindex=True,
        service="スカジャン制作のヒアリングと仕様確認書の作成",
        js=True,
    ),
    # 受注者側の業務用ツール。ナビ・フッター・sitemap には出さず、
    # noindex で検索結果からも外す。URLを直接開けば従来どおり使える
    "spec": dict(
        title="仕様確認書・発注確認書ジェネレーター｜制作コンセプトと確定事項を残す",
        desc="スカジャン制作の方向性、確定事項、修正回数、権利の範囲、改訂履歴を1枚にまとめてPDF化できるツール。入力はブラウザ内で完結し、送信されません。",
        nav="Spec sheet",
        crumbs=[("仕様確認書", "spec.html")],
        service="制作仕様の確認書作成",
        js=True,
        unlisted=True,
        noindex=True,
    ),
    "interview": dict(
        title="インタビュー｜スカジャンの歴史を研究する理由｜スカジャン絵師 横地広海知",
        desc="スカジャンの歴史をなぜモノから整理するのか。パラシュート生地説の検証、エジプトと中国の戦争土産、柄は祈りであること。オリジナルスカジャンを描くスカジャン絵師のロングインタビュー全文（2022年8月）。",
        nav="Interview",
        crumbs=[("インタビュー", "interview.html")],
        # ナビは主導線だけに絞る。ここはフッターの About 欄から辿れる
        unlisted=True,
        extra=[PERSON],
    ),
    "access": dict(
        title="アクセス｜ICHIドブ板本店（横須賀ドブ板通り）｜スカジャンの実物サンプル",
        desc="オリジナルスカジャンの実物を見られる店。横須賀ドブ板通りのICHIドブ板本店で、横振り刺繍と機械刺繍の比較、生地見本、オーダー事例をご覧いただけます。京急汐入駅から徒歩3分。営業時間内はご予約なしでご来店いただけます。",
        nav="Access",
        crumbs=[("アクセス", "access.html")],
        extra=[LOCAL],
        faq=[
            ("予約なしで行ってもいいですか",
             "営業時間は週ごとに変わるため、Googleマップの表示をご確認ください。オーダーのご相談は事前にご連絡いただけると確実です。"),
            ("何が見られますか",
             "横振り刺繍と機械刺繍の実物比較、生地見本（ポリエステルサテン・別珍など）、これまでの制作事例をご覧いただけます。"),
            ("遠方で行けないのですが",
             "生地見本と刺繍サンプルの郵送で対応します。ご相談の際にお知らせください。"),
        ],
    ),
    "privacy": dict(
        title="プライバシーポリシー｜合同会社ICHI（スカジャン絵師 横地広海知）",
        desc="当ウェブサイトおよびスカジャン制作の業務で取得する個人情報の取り扱いについて。取得する情報、利用目的、第三者提供と委託、外部サービス、開示等のご請求窓口を記載しています。",
        nav="Privacy",
        crumbs=[("プライバシーポリシー", "privacy.html")],
        unlisted=True,
    ),
    "estimate": dict(
        title="スカジャン自動見積もり｜オリジナル・OEMの概算がその場で出ます｜横地広海知",
        desc="オリジナルスカジャンのオーダーメイド、スカジャンOEM・ブランド別注の概算をその場で計算します。着数・ボディ・刺繍箇所・色数を選ぶだけ。公開している目安価格にもとづいた金額が、メールアドレスの入力なしで出ます。",
        nav="見積もり・ご相談",
        crumbs=[("自動見積もり", "estimate.html")],
        service="スカジャンのオーダーメイド・OEMの概算見積もり",
        extra=[PERSON],
    ),
    "contact": dict(
        title="ご相談・お問い合わせ｜スカジャン絵師 横地広海知",
        desc="オリジナルスカジャンのオーダーメイド、スカジャンOEM・ブランド別注、柄デザインのご相談。用途と希望納期をお知らせいただければ、可否とおおよその日程を最初にお答えします。",
        nav="Contact",
        crumbs=[("ご相談", "contact.html")],
        # 見積もりページ（estimate）が問い合わせの主導線。
        # このページは取材・来店予約など、金額の話ではないご相談の受け皿。
        # ナビには出さず、フッターから辿れるようにしている。
        unlisted=True,
        extra=[LOCAL],
    ),
}

# 生成するページ（サイトの構成順）
# --------------------------------------------------------------------------
# 事例の個別ページ。works.json の slug ごとに1枚ずつ作る。
# pages/works-{slug}.html を置けば、そちらが優先される（手書きの記事用）。
# --------------------------------------------------------------------------
USE_LABEL = {
    "order":  ("MADE TO ORDER", "オーダーメイド"),
    "oem":    ("OEM", "スカジャンOEM・量産"),
    "design": ("PATTERN DESIGN", "柄のデザイン提供"),
    "artist": ("ARTIST", "アーティストコラボ"),
}
USE_PAGE = {"order": "order.html", "oem": "oem.html", "design": "design.html",
            "artist": "design.html"}


def work_page_body(w):
    key = (w.get("use") or ["design"])[0]
    en, ja = USE_LABEL.get(key, USE_LABEL["design"])
    title = html.escape(w.get("title", ""))
    meta = html.escape(w.get("meta", ""))
    figs = []
    for i, src in enumerate(work_images(w)):
        cap = "背面" if i == 0 else "別のカット"
        figs.append('<figure class="figure%s"><img src="%s" alt="%s" '
                    'width="900" height="900" loading="lazy">'
                    '<figcaption>%s</figcaption></figure>'
                    % (" figure--wide" if i == 0 else "",
                       html.escape(src, quote=True), title, cap))
    if not figs:
        figs.append('<div class="slot slot--wide">写真は準備中です</div>')
    ext = ""
    if w.get("url", "").startswith("http"):
        ext = ('<p class="note">この事例は<a class="link" href="%s" target="_blank" '
               'rel="noopener">Instagram の投稿</a>でもご覧いただけます。</p>'
               % html.escape(w["url"], quote=True))
    return """<section class="hero">
  <h1 class="hero__title">
    <span class="kicker">Sukajan pattern &mdash; %(en)s</span>
    <span class="en">%(en)s</span>
    <span class="sub">%(title)s</span>
  </h1>
  <p class="lead hero__lead">%(meta)s</p>
  <div class="btns">
    <a class="btn btn--solid" href="estimate.html">同じように柄から作る</a>
    <a class="btn btn--ghost" href="works.html#uses">ほかの制作事例</a>
  </div>
</section>

<div class="panel">
  <section class="band rise">
    <div class="band__grid">
      <div class="band__aside">
        <p class="tag"><span class="tag__en">THE WORK</span><span class="tag__ja">この一着</span></p>
        <p>%(ja)s。</p>
      </div>
      <div class="band__main">
        <h2>%(title)s</h2>
        %(figs)s
        <div class="tw">
          <table>
            <thead><tr><th>項目</th><th>内容</th></tr></thead>
            <tbody>
              <tr><th>柄の名前</th><td>%(title)s</td></tr>
              <tr><th>ご依頼の形</th><td><a class="link" href="%(usepage)s">%(ja)s</a></td></tr>
              <tr><th>仕様</th><td>%(meta)s</td></tr>
            </tbody>
          </table>
        </div>
        %(ext)s
      </div>
    </div>
  </section>
</div>

<section class="band rise">
  <div class="band__grid">
    <div class="band__aside">
      <p class="tag"><span class="tag__en">NEXT</span><span class="tag__ja">ご依頼</span></p>
      <p>柄から起こします。</p>
    </div>
    <div class="band__main">
      <h2>この作り方で、<br>あなたの柄もお描きします</h2>
      <p class="lead">入れたいモチーフをうかがって、<strong>柄をゼロから描き起こします。</strong>一着だけのオーダーメイドから、ブランドの別注・量産、柄のデータだけのご提供まで承ります。</p>
      <div class="btns">
        <a class="btn btn--solid" href="estimate.html">今すぐ自動見積もり</a>
        <a class="btn btn--ghost" href="%(usepage)s">%(ja)sについて</a>
      </div>
    </div>
  </div>
</section>
""" % dict(en=en, ja=ja, title=title, meta=meta, figs="\n        ".join(figs),
           usepage=USE_PAGE.get(key, "design.html"), ext=ext)


GENERATED = {}
for _w in WORKS:
    _slug = _w.get("slug")
    if not _slug:
        continue
    _name = "works-%s" % _slug
    if _name in PAGES:
        continue
    _key = (_w.get("use") or ["design"])[0]
    _ja = USE_LABEL.get(_key, USE_LABEL["design"])[1]
    PAGES[_name] = dict(
        title="%s｜%sの制作事例｜スカジャン絵師 横地広海知" % (_w["title"], _ja),
        desc="%s %s スカジャン柄の制作事例です。" % (_w["title"], _w.get("meta", "")),
        nav=_w["title"][:12],
        crumbs=[("制作事例", "works.html"), (_w["title"], _name + ".html")],
        unlisted=True,
    )
    if not (ROOT / "pages" / (_name + ".html")).exists():
        GENERATED[_name] = work_page_body(_w)


PAGE_ORDER = ["index", "about", "interview", "design", "order", "oem", "process",
              "works", "works2", "works-aoi-karakusa", "press", "brief", "spec", "access", "estimate", "contact", "privacy"]

# 事例の個別ページを末尾に足す（ナビには出ない。sitemap には載る）
PAGE_ORDER += [n for n in PAGES if n.startswith("works-") and n not in PAGE_ORDER]

# ヘッダーのナビに出すページ。unlisted のものは除く
NAV_ORDER = [s for s in PAGE_ORDER if not PAGES[s].get("unlisted")]

# 追従CTA。ページごとに主導線を変える。
# brief / spec / contact は、そのページ自体が着地点なので出さない
CTA = {
    "index":     ("一着から、量産まで",         "相談する",           "contact.html", "別注・量産について", "oem.html"),
    "about":     ("柄のご相談を承っています",   "相談する",           "contact.html", "制作事例を見る", "works.html"),
    "interview": ("柄のご相談を承っています",   "相談する",           "contact.html", "横地広海知について", "about.html"),
    "order":     ("一着から柄を描き起こします", "今すぐ自動見積もり", "estimate.html", "制作事例を見る", "works.html"),
    "oem":       ("柄がなくても始められます",   "今すぐ自動見積もり", "estimate.html", "納期と進め方", "process.html"),
    "design":    ("柄だけのご依頼も承ります",   "柄の相談をする",     "estimate.html", "別注・量産について", "oem.html"),
    "estimate":  ("概算はその場で出ます",       "この内容で依頼する", "#send", "別注・量産について", "oem.html"),
    "process":   ("納期のご相談も承ります",     "相談する",           "contact.html", "別注・量産について", "oem.html"),
    "works":     ("同じように柄から作れます",   "相談する",           "contact.html", "Instagram で見る", "https://www.instagram.com/hiromichiyokochi/"),
    "press":     ("取材のご依頼も承ります",     "お問い合わせ",       "contact.html", "横地広海知について", "about.html"),
    "access":    ("ご予約なしでご来店いただけます", "ご来店について相談する", "contact.html", "WEBストア", "https://ichi-dobuita.square.site/"),
}


def cta_html(slug):
    c = CTA.get(slug)
    if not c:
        return ""
    label, p_txt, p_href, s_txt, s_href = c
    ext = ' target="_blank" rel="noopener"' if s_href.startswith("http") else ""
    return ('<div class="cta" id="cta" hidden>'
            '<p class="cta__label">%s</p>'
            '<a class="btn btn--solid" href="%s">%s</a>'
            '<a class="btn" href="%s"%s>%s</a>'
            '</div>' % (html.escape(label), p_href, html.escape(p_txt), s_href, ext, html.escape(s_txt)))


def jsonld(slug, meta):
    graph = []
    graph.append({
        "@type": "WebSite",
        "@id": BASE + "#website",
        "url": BASE,
        "name": "スカジャン絵師 横地広海知",
        "inLanguage": "ja",
        "publisher": {"@id": BASE + "#person"},
    })
    for e in meta.get("extra", []):
        graph.append(e)
    if meta.get("service"):
        graph.append({
            "@type": "Service",
            "name": meta["service"],
            "provider": {"@id": BASE + "#person"},
            "areaServed": "JP",
            "serviceType": "スカジャンのデザイン・制作",
        })
    if meta.get("faq"):
        graph.append({
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": q,
                 "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in meta["faq"]
            ],
        })
    items = [{"@type": "ListItem", "position": 1, "name": "ホーム", "item": BASE}]
    for i, (label, href) in enumerate(meta["crumbs"], start=2):
        items.append({"@type": "ListItem", "position": i, "name": label, "item": BASE + href})
    if len(items) > 1:
        graph.append({"@type": "BreadcrumbList", "itemListElement": items})
    return json.dumps({"@context": "https://schema.org", "@graph": graph},
                      ensure_ascii=False, indent=2)


HOLD_RE = re.compile(r"[ \t]*<!--HOLD-->.*?<!--/HOLD-->[ \t]*\n?", re.S)


def hold(body):
    """<!--HOLD--> ... <!--/HOLD--> で囲んだ範囲を出力から外す。
    未確定の内容を、ソースから消さずに一時的に非公開にするための仕組み。"""
    # 入れ子にすると内側の閉じで切れて、タグの対応が壊れる
    if body.count("<!--HOLD-->") != body.count("<!--/HOLD-->"):
        raise SystemExit("HOLD の開始と終了の数が合いません")
    out = HOLD_RE.sub("", body)
    if "HOLD" in out:
        raise SystemExit("HOLD が入れ子になっています。囲みは重ねないでください")
    return out


def notice_html():
    if not NOTICE or not NOTICE.get("enabled"):
        return ""
    return ('<a class="notice" href="%s"><time>%s</time><span>%s</span><em>&rarr;</em></a>'
            % (NOTICE["href"], html.escape(NOTICE["date"]), html.escape(NOTICE["text"])))


def nav_html(current):
    out = []
    for slug in NAV_ORDER:
        href = "index.html" if slug == "index" else f"{slug}.html"
        cur = ' aria-current="page"' if slug == current else ""
        # 見積もりは主導線なのでナビでもボタンにする
        cls = ' class="nav--cta"' if slug == "estimate" else ""
        out.append(f'<a href="{href}"{cls}{cur}>{PAGES[slug]["nav"]}</a>')
    return "\n        ".join(out)


def crumbs_html(meta):
    if not meta["crumbs"]:
        return ""
    trail = '<a href="index.html">ホーム</a>'
    last = len(meta["crumbs"]) - 1
    for i, (label, href) in enumerate(meta["crumbs"]):
        # 末尾は現在地なのでリンクにしない
        cell = f'<span>{label}</span>' if i == last else f'<a href="{href}">{label}</a>'
        trail += f' &rsaquo; {cell}'
    return f'<nav class="crumbs" aria-label="パンくず">{trail}</nav>'


SHELL = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">{robots}{alt}
<meta name="theme-color" content="#0A0A0B">
<link rel="icon" href="assets/favicon.png" type="image/png">
<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="スカジャン絵師 横地広海知">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="https://hiromichiyokochi.com/assets/ogp.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="675">
<meta property="og:locale" content="ja_JP">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@100..125,400..900&family=Space+Mono:wght@400;700&family=Noto+Sans+JP:wght@400;500&display=swap" rel="stylesheet">
<style>
{css}
</style>
{docjs}
<script type="application/ld+json">
{ld}
</script>
</head>
<body>
<a href="#main" class="skip">本文へ</a>
<header class="masthead" id="masthead">
  <div class="masthead__in">
    <a class="brand" href="index.html"><b>Hiromichi Yokochi</b><span>Sukajan Pattern Designer</span></a>
    <button class="menu__btn" type="button" id="menubtn" aria-label="メニュー"
            aria-expanded="false" aria-controls="nav" hidden>
      <span class="menu__bars" aria-hidden="true"></span>
      <span class="menu__label" aria-hidden="true"></span>
    </button>
    <nav class="nav" id="nav" aria-label="メインナビゲーション">
      {nav}
    </nav>
  </div>
</header>
<script>
/* ハンバーガー。JSが動くときだけボタンを出す。
   動かない環境では nav がそのまま残り、横スクロールで全項目に届く */
(function(){{
  var h = document.getElementById("masthead"), b = document.getElementById("menubtn");
  if(!h || !b) return;
  h.setAttribute("data-js", "1");
  b.hidden = false;
  function set(open){{
    b.setAttribute("aria-expanded", open ? "true" : "false");
    if(open){{ h.setAttribute("data-open", ""); }} else {{ h.removeAttribute("data-open"); }}
  }}
  b.addEventListener("click", function(){{
    set(b.getAttribute("aria-expanded") !== "true");
  }});
  // リンクを押したら閉じる（同一ページ内アンカー用）
  h.querySelector(".nav").addEventListener("click", function(e){{
    if(e.target.closest("a")) set(false);
  }});
  document.addEventListener("keydown", function(e){{
    if(e.key === "Escape" && h.hasAttribute("data-open")){{ set(false); b.focus(); }}
  }});
  document.addEventListener("click", function(e){{
    if(h.hasAttribute("data-open") && !h.contains(e.target)) set(false);
  }});
  // 画面が広がったら開閉状態を捨てる
  var mq = window.matchMedia("(min-width:881px)");
  (mq.addEventListener ? mq.addEventListener.bind(mq, "change") : mq.addListener.bind(mq))(function(){{ set(false); }});
}})();

</script>
{notice}
{crumbs}

<main id="main">
{body}
</main>

<footer class="foot">
  <div class="foot__in">
    <div>
      <h4>Sukajan</h4>
      <ul>
        <li><a href="order.html">オーダーメイドスカジャン（一着）</a></li>
        <li><a href="oem.html">スカジャンOEM・ブランド別注</a></li>
        <li><a href="design.html">オリジナル柄のデザインのみ</a></li>
      </ul>
    </div>
    <div>
      <h4>About</h4>
      <ul>
        <li><a href="about.html">横地広海知について</a></li>
        <li><a href="interview.html">インタビュー</a></li>
        <li><a href="process.html">納期と進め方</a></li>
        <li><a href="works.html">スカジャンの制作事例</a></li>
        <li><a href="press.html">掲載・受賞</a></li>
      </ul>
    </div>
    <div>
      <h4>Contact</h4>
      <ul>
        <li><a href="estimate.html">見積もり・ご相談</a></li>
        <li><a class="foot__cta" href="contact.html">取材・その他のお問い合わせ</a></li>
        <li><a href="https://ichi-dobuita.square.site/" target="_blank" rel="noopener">WEBストア</a></li>
        <li><a href="access.html">アクセス・ご来店</a></li>
      </ul>
    </div>
    <div>
      <h4>Follow</h4>
      <ul>
        <li><a href="https://www.instagram.com/hiromichiyokochi/" target="_blank" rel="noopener">Instagram</a></li>
        <li><a href="https://x.com/HiromichiYKC" target="_blank" rel="noopener">X</a></li>
        <li><a href="https://note.com/hiromichiyokochi" target="_blank" rel="noopener">note</a></li>
        <li><a href="https://prtimes.jp/main/html/searchrlp/company_id/185297" target="_blank" rel="noopener">PR TIMES</a></li>
        <li><a href="en/">English</a></li>
      </ul>
    </div>
  </div>
  <div class="foot__legal">
    <a href="privacy.html">プライバシーポリシー</a>　運営：合同会社ICHI
    <span class="foot__copy">&copy; {year} ICHI / Hiromichi Yokochi &mdash; 柄・写真・文章の無断転載を禁じます</span>
  </div>
</footer>
{cta}
<script>
/* 追従CTA。ヒーローを過ぎたら出し、フッターに達したら引っ込める。
   フッターにも同じ導線があるので、重ねて出す意味がないため */
(function(){{
  var c = document.getElementById("cta");
  if(!c || !("IntersectionObserver" in window)) return;
  c.hidden = false;
  var hero = document.querySelector(".hero"), foot = document.querySelector(".foot");
  var pastHero = !hero, atFoot = false;
  function upd(){{
    if(pastHero && !atFoot){{ c.setAttribute("data-show", ""); }}
    else {{ c.removeAttribute("data-show"); }}
  }}
  if(hero){{
    new IntersectionObserver(function(e){{ pastHero = !e[0].isIntersecting; upd(); }})
      .observe(hero);
  }}
  if(foot){{
    new IntersectionObserver(function(e){{ atFoot = e[0].isIntersecting; upd(); }},
      {{rootMargin: "0px 0px -20% 0px"}}).observe(foot);
  }}
  upd();
}})();
</script>
</body>
</html>
"""

for slug in PAGE_ORDER:
    meta = PAGES[slug]
    src = ROOT / "pages" / f"{slug}.html"
    body = GENERATED[slug] if slug in GENERATED else src.read_text(encoding="utf-8")
    canonical = BASE if slug == "index" else BASE + f"{slug}.html"
    page = SHELL.format(
        title=html.escape(meta["title"], quote=True),
        desc=html.escape(meta["desc"], quote=True),
        canonical=canonical,
        robots=('\n<meta name="robots" content="noindex,nofollow">'
                if meta.get("noindex") else ""),
        # 英語版は1ページのみ。対にするのは日本語トップ
        alt=('\n<link rel="alternate" hreflang="ja" href="%s">'
             '\n<link rel="alternate" hreflang="en" href="%sen/">'
             '\n<link rel="alternate" hreflang="x-default" href="%s">'
             % (BASE, BASE, BASE)) if slug == "index" else "",
        css=CSS,
        docjs=("<script>\n" + DOCJS + "\n</script>") if meta.get("js") else "",
        ld=jsonld(slug, meta),
        nav=nav_html(slug),
        crumbs=crumbs_html(meta),
        notice=notice_html(),
        cta=cta_html(slug),
        year=date.today().year,
        body=(hold(body)
              .replace("<!--PRESS-->", press_html())
              .replace("<!--WORKS:WRAP-->", works_html(wrap=True))
              .replace("<!--WORKS:USE:design-->", works_use_html("design"))
              .replace("<!--WORKS:USE:order-->", works_use_html("order"))
              .replace("<!--WORKS:USE:oem-->", works_use_html("oem"))
              .replace("<!--WORKS:BYUSE-->", works_by_use_html())
              .replace("<!--WORKS:DRAFT-->", works_html(drafts=True))
              .replace("<!--WORKS-->", works_html())
              .replace("<!--WORKS:5-->", works_html(5))
              .replace('const ENDPOINT = "";',
                       'const ENDPOINT = "%s";' % FORM_ENDPOINT)
              .replace('const SHARED_SECRET = "change-me";',
                       'const SHARED_SECRET = "%s";' % FORM_SECRET)
              .replace('const MAIL = "info@ichi-pj.com";',
                       'const MAIL = "%s";' % FORM_MAIL)),
    )
    (OUT / f"{slug}.html").write_text(page, encoding="utf-8")
    mark = "  [非公開]" if meta.get("unlisted") else ""
    print(f"built {slug}.html  ({len(page):,} bytes){mark}")

# 静的ファイルをそのまま持っていく
for name in ("robots.txt",):
    src = ROOT / name
    if src.exists():
        shutil.copy2(src, OUT / name)
        print(f"copied {name}")

# sitemap.xml は PAGE_ORDER から作る。
# 手書きにしておくとページを足したときに載せ忘れる（実際に一度やった）。
SITEMAP_PRIORITY = {
    "index": "1.0", "oem": "0.9", "order": "0.9", "estimate": "0.9", "design": "0.9",
    "about": "0.9", "contact": "0.8", "access": "0.8",
    "privacy": "0.4",
}


def sitemap_xml():
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

    def url(loc, pri):
        rows.append("  <url>")
        rows.append(f"    <loc>{loc}</loc>")
        rows.append(f"    <priority>{pri}</priority>")
        rows.append("  </url>")

    url(BASE, SITEMAP_PRIORITY["index"])
    url(BASE + "en/", "0.8")
    for slug in PAGE_ORDER:
        meta = PAGES[slug]
        # noindex のページ（brief / spec）だけ外す。
        # privacy はナビには出さないが、検索に載せてよいので含める。
        if slug == "index" or meta.get("noindex"):
            continue
        url(f"{BASE}{slug}.html", SITEMAP_PRIORITY.get(slug, "0.8"))
    rows.append("</urlset>")
    return "\n".join(rows) + "\n"


(OUT / "sitemap.xml").write_text(sitemap_xml(), encoding="utf-8")
print("built  sitemap.xml")

# --------------------------------------------------------------------------
# 旧サイトのURLを生かす
# GitHub Pages はサーバー側の301リダイレクトができない。そこで、旧URLと同じ
# 場所に同じ内容を書き出し、canonical で正規URLを示して評価をまとめる。
# 外部からの被リンクはそのまま生きる。
# --------------------------------------------------------------------------
LEGACY_COPY = {"interview": "interview"}   # /interview/ ← interview.html

REL_HREF = re.compile(r'(href|src)="(?!https?:|mailto:|#|/)([^"]+)"')


def write_legacy():
    for slug, path in LEGACY_COPY.items():
        html_text = (OUT / f"{slug}.html").read_text(encoding="utf-8")
        # 1階層深くなるため、相対リンクをルート基準に書き換える
        html_text = REL_HREF.sub(r'\1="../\2"', html_text)
        html_text = html_text.replace("url(assets/", "url(../assets/")
        d = OUT / path
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(html_text, encoding="utf-8")
        print(f"legacy  /{path}/  ← {slug}.html")


write_legacy()


# --------------------------------------------------------------------------
# 英語版（1ページ）。旧サイトの /en をそのまま引き継ぐ
# --------------------------------------------------------------------------
EN_URL = BASE + "en/"
EN_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sukajan Pattern Designer Hiromichi Yokochi | Custom souvenir jackets from Yokosuka</title>
<meta name="description" content="Sukajan pattern designer based in Dobuita Street, Yokosuka. One-off custom jackets from 165,000 yen, brand collaboration and OEM from 1 to 100+ pieces. Patterns drawn for GU, PUMA and Expo 2025 Osaka. English enquiries welcome.">
<link rel="canonical" href="{en_url}">
<link rel="alternate" hreflang="en" href="{en_url}">
<link rel="alternate" hreflang="ja" href="{base}">
<link rel="alternate" hreflang="x-default" href="{base}">
<meta name="theme-color" content="#0A0A0B">
<link rel="icon" href="../assets/favicon.png" type="image/png">
<link rel="apple-touch-icon" href="../assets/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Sukajan Pattern Designer Hiromichi Yokochi">
<meta property="og:title" content="Sukajan Pattern Designer Hiromichi Yokochi">
<meta property="og:description" content="Custom sukajan from Dobuita Street, Yokosuka. One jacket or a full production run. English enquiries welcome.">
<meta property="og:url" content="{en_url}">
<meta property="og:image" content="{base}assets/ogp.jpg">
<meta property="og:locale" content="en_US">
<meta property="og:locale:alternate" content="ja_JP">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@100..125,400..900&family=Space+Mono:wght@400;700&family=Noto+Sans+JP:wght@400;500&display=swap" rel="stylesheet">
<style>
{css}
</style>
<script type="application/ld+json">
{ld}
</script>
</head>
<body>
<a href="#main" class="skip">Skip to content</a>
<header class="masthead">
  <div class="masthead__in">
    <a class="brand" href="./"><b>Hiromichi Yokochi</b><span>Sukajan Pattern Designer</span></a>
    <nav class="nav" aria-label="Language">
      <a href="./" aria-current="page">EN</a>
      <a href="../">JA</a>
    </nav>
  </div>
</header>

<main id="main">
{body}
</main>

<footer class="foot">
  <div class="foot__in">
    <div>
      <h4>Contact</h4>
      <ul>
        <li><a href="mailto:info@ichi-pj.com">info@ichi-pj.com</a></li>
        <li><a href="https://ichi-dobuita.square.site/" target="_blank" rel="noopener">Online store</a></li>
        <li>Ai&rsquo;s Bldg. 1F, 3-11-7 Honcho</li>
        <li>Yokosuka, Kanagawa, Japan</li>
      </ul>
    </div>
    <div>
      <h4>Follow</h4>
      <ul>
        <li><a href="https://www.instagram.com/hiromichiyokochi/" target="_blank" rel="noopener">Instagram</a></li>
        <li><a href="https://x.com/HiromichiYKC" target="_blank" rel="noopener">X</a></li>
        <li><a href="https://note.com/hiromichiyokochi" target="_blank" rel="noopener">note</a></li>
      </ul>
    </div>
    <div>
      <h4>Japanese</h4>
      <ul>
        <li><a href="../">Home</a></li>
        <li><a href="../oem.html">Brand / OEM</a></li>
        <li><a href="../order.html">Made to order</a></li>
        <li><a href="../access.html">Access</a></li>
      </ul>
    </div>
  </div>
  <div class="foot__legal">
    <a href="../privacy.html">Privacy policy</a>　Operated by ICHI LLC
    <span class="foot__copy">&copy; {year} ICHI / Hiromichi Yokochi &mdash; All rights reserved</span>
  </div>
</footer>
</body>
</html>
"""

EN_LD = json.dumps({
    "@context": "https://schema.org",
    "@graph": [
        {"@type": "WebSite", "@id": EN_URL + "#website", "url": EN_URL,
         "name": "Sukajan Pattern Designer Hiromichi Yokochi", "inLanguage": "en",
         "publisher": {"@id": BASE + "#person"}},
        PERSON, LOCAL,
        {"@type": "Service", "name": "Custom sukajan design and production",
         "provider": {"@id": BASE + "#person"}, "areaServed": "Worldwide",
         "serviceType": "Sukajan pattern design, embroidery and production"},
    ],
}, ensure_ascii=False, indent=2)

en_dir = OUT / "en"
en_dir.mkdir(parents=True, exist_ok=True)
(en_dir / "index.html").write_text(
    EN_SHELL.format(css=CSS.replace("url(assets/", "url(../assets/"),
                    ld=EN_LD, base=BASE, en_url=EN_URL,
                    year=date.today().year,
                    body=hold((ROOT / "pages" / "en.html").read_text(encoding="utf-8"))),
    encoding="utf-8")
print("built  en/index.html")


assets = ROOT / "assets"
if assets.is_dir():
    dst = OUT / "assets"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(assets, dst)
    n = sum(1 for _ in dst.rglob("*") if _.is_file())
    print(f"copied assets/ ({n} files)")

print(f"\n-> {OUT}")
