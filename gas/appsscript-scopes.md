# 外部リクエストの権限が下りないときは、マニフェストに書く

`UrlFetchApp` を後から足しても、Apps Script は自動では再承認を求めない。
実行しても承認画面が出ず、`You do not have permission to call UrlFetchApp.fetch`
のまま終わる。**`appsscript.json` に `oauthScopes` を明示すると、必ず承認画面が出る。**

## 承認関数で try/catch をしない

権限不足の例外は、**外に投げて初めて承認ダイアログが出る。**
`try/catch` で捕まえてログに書くと、ダイアログが出ないまま「実行完了」になり、
何度実行しても承認できない。`authorizeExternalRequest()` に catch を書かないのはそのため。

## 手順

1. Apps Script エディタ → 左の歯車「プロジェクトの設定」
2. **「appsscript.json マニフェスト ファイルをエディタで表示する」にチェック**
3. 左のファイル一覧に `appsscript.json` が現れるので開く
4. 既存の中身は消さず、`"oauthScopes"` の項目だけを足す
5. 保存 → `authorizeExternalRequest` を実行 → 承認画面で「許可」
6. **「新しいバージョン」でデプロイ**（マニフェストの変更は再デプロイで反映される）

## 足す内容

```json
  "oauthScopes": [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/script.send_mail",
    "https://www.googleapis.com/auth/script.external_request"
  ]
```

## この3つで足りる理由

| 権限 | 使っている場所 |
|---|---|
| `spreadsheets` | `SpreadsheetApp.openById` / `appendRow` / `insertSheet` |
| `script.send_mail` | `MailApp.sendEmail` / `MailApp.getRemainingDailyQuota` |
| `script.external_request` | `UrlFetchApp.fetch`（Turnstile の検証） |

`PropertiesService`・`Utilities`・`Session.getScriptTimeZone`・`ContentService` は権限不要。

**書き漏らすとその機能だけが動かなくなる**ので、APIを足したときはこの表も更新する。
