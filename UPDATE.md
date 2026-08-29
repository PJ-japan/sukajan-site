# サイトの更新のしかた

このリポジトリは **content と見た目が分離** されています。
ふだんの更新で触るのは `content/` の3ファイルだけです。HTMLは書きません。

```
content/notice.json   ヘッダー直下の告知帯（1行）
content/press.json    掲載・出演・受賞
content/works.json    制作事例
pages/*.html          各ページの本文（文章を直すときだけ）
_style.css            デザイン
_doc.js               契約条項（弁護士確認のうえ編集）
build.py              組み立て。ふだん触りません
```

`main` に push すると GitHub Actions が `build.py` を実行し、公開先へ自動で反映されます。

---

## よくある更新

### 告知を出す

`content/notice.json`

```json
{
  "enabled": true,
  "date": "2026.10",
  "text": "◯◯にて展示会に出展します",
  "href": "works.html"
}
```

**終わったら `"enabled": false` に戻してください。** 出しっぱなしが一番よくありません。

### 掲載情報を足す

`content/press.json` の配列の**先頭**に足します。年ごとの見出しは自動で作られます。

```json
{
  "date": "2026.10.01",
  "title": "記事のタイトル",
  "outlet": "媒体名",
  "kind": "Web",
  "url": "https://example.com/article"
}
```

`url` を空文字にすると、リンクなしの行になります（掲載制約がある場合に）。

### 事例を足す

`content/works.json`

```json
{
  "title": "鳳凰と桜",
  "meta": "フルオーダー／横振り刺繍／レーヨン／制作期間 1ヶ月",
  "image": "assets/works/houou.webp",
  "url": "works/houou.html"
}
```

`image` を空にすると点線のプレースホルダになります。
画像は `assets/works/` に置いてください（ビルド時にそのままコピーされます）。

### 文章を直す

`pages/` の該当ファイルを開いて書き換えます。ヘッダー・フッター・ナビは共通なので触りません。

---

## ローカルで確認する

```bash
python3 build.py          # dist/ に書き出される
python3 -m http.server -d dist 8000
```

`http://localhost:8000` で確認できます。Python以外に必要なものはありません。

---

## 公開先の設定（最初に1回だけ）

GitHub の Settings → Secrets and variables → Actions で設定します。

### A. GMO などのレンタルサーバー（FTPS）

**Variables**

| 名前 | 値 |
|---|---|
| `DEPLOY_TARGET` | `ftp` |

**Secrets**

| 名前 | 値 |
|---|---|
| `FTP_HOST` | ftp.example.com |
| `FTP_USER` | FTPユーザー名 |
| `FTP_PASSWORD` | FTPパスワード |
| `FTP_DIR` | `/public_html/` など公開ディレクトリ |

### B. Cloudflare Pages

**Variables**：`DEPLOY_TARGET` = `cloudflare`、`CF_PROJECT` = プロジェクト名
**Secrets**：`CF_API_TOKEN`、`CF_ACCOUNT_ID`

> パスワードやトークンは必ず GitHub の Secrets に入れてください。
> リポジトリのファイルや、チャットに貼るのは避けてください。

---

## 移行のときの注意

既存の `hiromichiyokochi.com` を差し替える場合、**公開前に旧URLを全部書き出して301を設定**してください。
指名検索（「横地広海知」「スカジャン絵師」）の順位を落とさないことが最優先です。

---

## Claude Code で回す場合

このリポジトリには `CLAUDE.md` と、よく使う操作のコマンドを同梱しています。

```
CLAUDE.md                    触っていい場所・ダメな場所のルール
.claude/commands/press.md    /press   掲載を1件追加
.claude/commands/notice.md   /notice  告知帯を出す・消す
.claude/commands/publish.md  /publish 検証して push
```

### 使い方の例

```
/press 2026年10月1日、Casa BRUTUSに掲載。タイトルは「横須賀の絵師」。URLは https://...
/notice 10月に横浜で展示会に出ます
/publish
```

`/publish` は、ビルドが通るか、各ページに `<h1>` が1つあるか、`class="tbd"` が何件残っているかを
確認してから、push してよいか聞いてきます。**確認なしに公開はしません。**

### CLAUDE.md で守らせていること

- `_doc.js`（契約条項）は明示的な指示がない限り変更しない
- `build.py` と `_style.css` は相談なしに触らない
- 実績を足すときは掲載許諾を確認済みか一度聞く
- 告知は終わったら `enabled: false` に戻す
- パスワードやAPIキーをリポジトリに書かない

ルールを足したいときは `CLAUDE.md` に1行書けば、次回から守られます。
