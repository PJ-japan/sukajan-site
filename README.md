# スカジャン絵師 横地広海知 — サイト一式

静的サイト。`build.py`（Python標準ライブラリのみ）が `pages/` と `content/` から
HTMLを組み立てます。Node不要、依存パッケージなし。

## まず読むもの

| 迷ったら | 読むファイル |
|---|---|
| はじめて動かす（Mac） | `START-mac.md` |
| GitHubを準備する | `GITHUB-mac.md` |
| ふだんの更新のしかた | `UPDATE.md` |
| Claude Codeへのルール | `CLAUDE.md`（Claude Codeが自動で読みます） |
| スプレッドシート連携 | `gas/README.md` |

## 動かしてみる

```bash
cd ~/Documents/sukajan-site
python3 build.py                    # dist/ に書き出す
python3 -m http.server -d dist 8000 # http://localhost:8000 で確認
```

`dist/` は毎回作り直されるので、GitHubには入りません（`.gitignore` 済み）。

### 隠しフォルダについて

`.github/` `.claude/` `.gitignore` は名前が `.` で始まるため、**Finderでは既定で見えません**。
Finderで **⌘ + Shift + .（ピリオド）** を押すと表示が切り替わります。
フォルダをコピーするときは、これらが一緒に移動しているか確認してください。
`.github/` が無いと自動公開が動かず、`.claude/` が無いと `/press` などのコマンドが使えません。

## 中身

```
content/          ← ふだん編集するのはここ
  notice.json       ヘッダー直下の告知帯（1行）
  press.json        掲載・出演・受賞
  works.json        制作事例
pages/            ← 各ページの本文
  index / about / order / oem / process / works / press / brief / access / contact
  spec              受注者用の業務ツール。ナビ・sitemap には出さない（noindex）
assets/           ← 画像（自分で作ります）
_style.css        デザイン
_doc.js           契約条項（弁護士確認のうえ編集）
build.py          組み立て。ふだん触りません
gas/              スプレッドシート連携（Google Apps Script）
.github/          push したら自動でビルド・公開
.claude/commands/ /press /notice /publish
```

## 公開前にやること

- `class="tbd"` の箇所を埋める（金額、サイズ表、営業時間、電話番号など）
- 画像を `assets/` に置き、`class="slot"` の点線枠を `<img>` に差し替える
- 実績5件（GU / PUMA / 大阪関西万博 / モンスターハンター / 還ジャン&reg;）の掲載可否を確認
  ※ オリンピック関連は権利上掲載不可。追加しないこと
- `brief.html` の送信先（`ENDPOINT`）を設定 → `gas/README.md`
- プライバシーポリシーのページを追加（`brief.html` は入力内容を送信します）
- `_doc.js` の条項を顧問弁護士にレビューしてもらう
- 既存サイトを差し替える場合は、旧URLから **301リダイレクト**を設定
