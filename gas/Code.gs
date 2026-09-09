/**
 * スカジャン絵師 横地広海知 — ご依頼フォームの受け口
 * Google スプレッドシートに1行ずつ記録し、通知メールを送ります。
 * 設定手順は同じフォルダの README.md を参照してください。
 */

// ===== 設定 ===============================================================
/**
 * スプレッドシートのIDは、このファイルには書きません。
 * このリポジトリは公開されているため、IDを書くと git の履歴に残り続けます。
 * 万一シートの共有設定が「リンクを知っている全員」になった場合、
 * 問い合わせ全件（氏名・メール・電話番号）が読める状態になります。
 *
 * 代わりに Apps Script のスクリプトプロパティに入れてください。
 *   Apps Script エディタ → 左の歯車「プロジェクトの設定」
 *   → 「スクリプト プロパティ」→ プロパティ名 SHEET_ID、値にIDを貼る
 *
 * 一度設定すれば、このファイルを貼り直しても消えません。
 */
const SHEET_ID = PropertiesService.getScriptProperties().getProperty('SHEET_ID');

/* Cloudflare Turnstile のシークレットキー。SHEET_ID と同じ理由でここには書かない。
   「プロジェクトの設定」→「スクリプト プロパティ」に TURNSTILE_SECRET を追加する。
   未設定のあいだは検証をせず素通しする（サイト側もウィジェットを出さない）。 */
const TURNSTILE_SECRET =
  PropertiesService.getScriptProperties().getProperty('TURNSTILE_SECRET');

const SHEET_NAME = 'briefs';        // ご依頼フォーム（brief.html）
const CONTACT_SHEET = 'contacts';   // お問い合わせフォーム（contact.html）
const ESTIMATE_SHEET = 'estimates'; // 自動見積もり（estimate.html）
const DESIGN_SHEET = 'design';      // 柄のデザインのみ（estimate.html）
const RECRUIT_SHEET = 'recruit';    // アルバイト応募（recruit.html）
const SECRET     = 'm5u0-yxSl-ByIk';   // build.py の FORM_SECRET と同じ文字列
const NOTIFY_TO  = 'info@ichi-pj.com';   // 通知メールの宛先。空にすると送りません
const AUTO_REPLY = true;                 // 送信者へ受付メールを自動で返すか
const REPLY_NAME = 'スカジャン絵師 横地広海知 / 合同会社ICHI';
// =========================================================================

const HEADERS = [
  '受信日時','書類番号','文書ハッシュ',
  '会社名・お名前','ご担当者','メール',
  'ご依頼の種類','用途','ご要望','着数','希望納期','ご予算',
  '利用区分','地域','期間','媒体','商品ラインナップ',
  '支給物・持込IP','備考','制作コンセプト（自動生成）','UA'
];

const DESIGN_HEADERS = [
  '受信日時','お名前・会社名','メール','電話',
  '柄の点数','仕上げ','柄の規模','色数の目安','のせるアイテム',
  '使用する媒体','使用期間','使用地域','権利の形','生産予定数',
  '希望納期','既存IP','クレジット','実績掲載',
  'モチーフ・参考','補足','知ったきっかけ','UA'
];

const ESTIMATE_HEADERS = [
  '受信日時','お名前・会社名','メール','電話',
  'ご依頼の種類','着数','ボディ','刺繍箇所','色数・柄の密度','生地','仕様','希望納期',
  '1着あたり概算','合計概算','補足','知ったきっかけ','UA'
];

const RECRUIT_HEADERS = [
  '受信日時','お名前','ふりがな','メール','電話','年代','お住まい',
  'やってみたいこと','入れる曜日・日数','働き始められる時期',
  '志望のきっかけ','SNS・ポートフォリオ','知ったきっかけ','UA'
];

const CONTACT_HEADERS = [
  '受信日時','ご用件','お名前・会社名','メール','電話',
  '来店希望日','時間帯','人数','見たいもの',
  '媒体名','媒体の種類','依頼の形式','取材希望日','掲載・放送予定日','取材場所',
  'ご相談内容','知ったきっかけ','UA'
];

/* Turnstile のトークンを Cloudflare に問い合わせて確かめる。
   これをサーバー側でやらないと、ウィジェットを置いただけで素通しになる。 */
function turnstileOk_(token) {
  if (!TURNSTILE_SECRET) return true;   // 未設定のあいだは素通し
  if (!token) { tsLog_('トークンが届いていません'); return false; }
  try {
    const res = UrlFetchApp.fetch(
      'https://challenges.cloudflare.com/turnstile/v0/siteverify', {
        method: 'post',
        payload: { secret: TURNSTILE_SECRET, response: token },
        muteHttpExceptions: true
      });
    const r = JSON.parse(res.getContentText());
    if (r.success === true) return true;
    tsLog_((r['error-codes'] || ['(コードなし)']).join(' / '));
    return false;
  } catch (err) {
    tsLog_(String(err));
    return false;
  }
}

/* 直近の判定失敗を1件だけ残す。診断URLから読めるようにして、
   ブラウザの開発者ツールを開かなくても理由が分かるようにする。 */
function tsLog_(msg) {
  try {
    PropertiesService.getScriptProperties().setProperty(
      'TURNSTILE_LAST_ERROR',
      Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'MM-dd HH:mm') + '  ' + msg);
  } catch (err) { /* 記録できなくても本処理は止めない */ }
}

/* メールは1通ずつ独立して送る。自動返信が失敗しても、運営への通知だけは
   必ず試みる。1日あたりの送信上限に達したときに、問い合わせが丸ごと
   消えるのを防ぐため。シートへの行追加はメール送信より前に済ませている。 */
let MAIL_ERRORS = [];

function sendMail_(opts) {
  try { MailApp.sendEmail(opts); return true; }
  catch (err) {
    MAIL_ERRORS.push((opts.to === NOTIFY_TO ? '[通知] ' : '[自動返信] ') + String(err));
    return false;
  }
}

/* 運営への通知が送れたかどうかを ok とする。自動返信だけが失敗した場合は
   受付は成立しているので、送信者に「失敗」と出して二重送信させない。 */
function done_(extra) {
  const out = extra || {};
  const critical = MAIL_ERRORS.filter(function (m) { return m.indexOf('[通知] ') === 0; });
  out.ok = critical.length === 0;
  if (MAIL_ERRORS.length) out.mailError = MAIL_ERRORS.join(' / ');
  return json(out);
}

function doPost(e) {
  MAIL_ERRORS = [];
  try {
    const body = JSON.parse(e.postData.contents);
    if (body.secret !== SECRET) return json({ ok: false, error: 'unauthorized' });

    /* ボット判定。ここを通らないものはシートにも書かず、メールも送らない */
    if (!turnstileOk_(body.turnstile)) {
      return json({ ok: false, error: 'bot-check-failed' });
    }

    // お問い合わせフォーム（contact.html）はこちらで処理する
    if (body.form === 'contact') return handleContact_(body);

    // 自動見積もり（estimate.html）からの正式見積もり依頼
    if (body.form === 'estimate') return handleEstimate_(body);

    // 柄のデザインのみ（estimate.html）。金額は出さず、伺った条件を渡す
    if (body.form === 'design') return handleDesign_(body);

    // アルバイト応募（recruit.html）
    if (body.form === 'recruit') return handleRecruit_(body);

    const a = body.answers || {};
    const d = body.doc || {};
    const sh = sheet_();

    sh.appendRow(safeRow_([
      new Date(),
      body.docNo || '',
      body.hash || '',
      a.company || '',
      a.person || '',
      a.email || '',
      a.kind || '',
      a.purpose || '',
      a.desc || '',
      a.qty || '',
      a.due || '',
      a.budget || '',
      a.use || '',
      a.area || '',
      a.term || '',
      (a.media || []).join(' / '),
      a.lineup || '',
      a.ip || '',
      a.note || '',
      d.s_concept || '',
      body.ua || ''
    ]));

    if (NOTIFY_TO) {
      sendMail_({
        to: NOTIFY_TO,
        subject: '【ご依頼フォーム】' + (a.company || '名称未記入') + '／' + (body.docNo || ''),
        body: [
          '書類番号: ' + (body.docNo || ''),
          '文書ハッシュ: ' + (body.hash || ''),
          '',
          '会社名・お名前: ' + (a.company || ''),
          'ご担当者: ' + (a.person || ''),
          'メール: ' + (a.email || ''),
          'ご依頼の種類: ' + (a.kind || ''),
          '用途: ' + (a.purpose || ''),
          '着数: ' + (a.qty || ''),
          '希望納期: ' + (a.due || ''),
          'ご予算: ' + (a.budget || ''),
          '利用区分: ' + (a.use || ''),
          '地域: ' + (a.area || '') + ' / 期間: ' + (a.term || ''),
          '媒体: ' + ((a.media || []).join(' / ')),
          '商品ラインナップ: ' + (a.lineup || ''),
          '',
          '【ご要望】',
          a.desc || '',
          '',
          '【支給物・持込IP】',
          a.ip || '',
          '',
          '【備考】',
          a.note || '',
          '',
          'スプレッドシート: https://docs.google.com/spreadsheets/d/' + SHEET_ID
        ].join('\n')
      });
    }

    return done_({ docNo: body.docNo });
  } catch (err) {
    return json({ ok: false, error: String(err) });
  }
}

/** お問い合わせフォームを contacts シートに1行追加し、通知を送る */
function handleDesign_(body) {
  const a = body.answers || {};
  const sh = sheet_(DESIGN_SHEET, DESIGN_HEADERS);
  const item  = (a.item  || []).join(' / ');
  const media = (a.media || []).join(' / ');

  sh.appendRow(safeRow_([
    new Date(),
    a.name || '', a.email || '', a.tel || '',
    a.count || '', a.finish || '', a.scale || '', a.colors || '', item,
    media, a.period || '', a.area || '', a.right || '', a.volume || '',
    a.due || '', a.ip || '', a.credit || '', a.pr || '',
    a.motif || '', a.msg || '', a.source || '', body.ua || ''
  ]));

  if (AUTO_REPLY && a.email) {
    sendMail_({
      to: a.email,
      name: REPLY_NAME,
      replyTo: NOTIFY_TO,
      subject: '柄のデザインのご相談を承りました｜スカジャン絵師 横地広海知',
      body: [
        (a.name || '') + ' 様',
        '',
        'ご相談をありがとうございます。以下の内容で承りました。',
        '柄のデザインの費用は、使用する媒体・期間・権利の形で決まります。',
        'いただいた条件をもとに、1営業日以内にお見積りと進め方をご返信します。',
        '',
        '──────────────',
        '柄の点数: ' + (a.count || '未記入'),
        '仕上げ: ' + (a.finish || '未記入'),
        '柄の規模: ' + (a.scale || '未記入'),
        '色数の目安: ' + (a.colors || '未記入'),
        'のせるアイテム: ' + (item || '未選択'),
        '',
        '使用する媒体: ' + (media || '未選択'),
        '使用期間: ' + (a.period || '未記入'),
        '使用地域: ' + (a.area || '未記入'),
        '権利の形: ' + (a.right || '未記入'),
        '生産予定数: ' + (a.volume || '未記入'),
        '',
        '希望納期: ' + (a.due || '未記入'),
        '既存IPの持ち込み: ' + (a.ip || '未記入'),
        'クレジット表記: ' + (a.credit || '未記入'),
        '実績掲載: ' + (a.pr || '未記入'),
        '──────────────',
        '',
        'モチーフ・参考:',
        a.motif || '（未記入）',
        '',
        '補足:',
        a.msg || '（未記入）',
        '',
        '※ このメールは自動送信です。ご返信いただければ担当に届きます。',
        '',
        REPLY_NAME,
        '神奈川県横須賀市本町3-11-7 アイ\'s ビル 1F',
        'https://hiromichiyokochi.com/'
      ].join('\n')
    });
  }

  if (NOTIFY_TO) {
    sendMail_({
      to: NOTIFY_TO,
      replyTo: a.email || NOTIFY_TO,
      subject: '【柄のデザイン】' + (a.name || '名称未記入') + '／' + (a.count || '') +
               '／' + (a.period || '') + '／' + (a.right || ''),
      body: [
        'お名前・会社名: ' + (a.name || ''),
        'メール: ' + (a.email || ''),
        '電話: ' + (a.tel || ''),
        '',
        '柄の点数: ' + (a.count || ''),
        '仕上げ: ' + (a.finish || ''),
        '柄の規模: ' + (a.scale || ''),
        '色数の目安: ' + (a.colors || ''),
        'のせるアイテム: ' + item,
        '',
        '使用する媒体: ' + media,
        '使用期間: ' + (a.period || ''),
        '使用地域: ' + (a.area || ''),
        '権利の形: ' + (a.right || ''),
        '生産予定数: ' + (a.volume || ''),
        '',
        '希望納期: ' + (a.due || ''),
        '既存IP: ' + (a.ip || ''),
        'クレジット: ' + (a.credit || ''),
        '実績掲載: ' + (a.pr || ''),
        '',
        'モチーフ・参考:',
        a.motif || '（未記入）',
        '',
        '補足:',
        a.msg || '（未記入）',
        '',
        '知ったきっかけ: ' + (a.source || ''),
        'UA: ' + (body.ua || '')
      ].join('\n')
    });
  }

  return done_();
}


function handleEstimate_(body) {
  const a = body.answers || {};
  const sh = sheet_(ESTIMATE_SHEET, ESTIMATE_HEADERS);
  const place = (a.place || []).join(' / ');

  sh.appendRow(safeRow_([
    new Date(),
    a.name || '', a.email || '', a.tel || '',
    a.kind || '', a.qty || '', a.body || '', place,
    a.colors || '', a.fabric || '', a.side || '', a.due || '',
    a.unit || '', a.total || '',
    a.msg || '', a.source || '', body.ua || ''
  ]));

  // 送信者への受付メール。画面に出したのと同じ概算をそのまま控えとして返す。
  // 契約上の見積書ではないことを必ず明記する。
  if (AUTO_REPLY && a.email) {
    sendMail_({
      to: a.email,
      name: REPLY_NAME,
      replyTo: NOTIFY_TO,
      subject: '正式見積もりのご依頼を承りました｜スカジャン絵師 横地広海知',
      body: [
        (a.name || '') + ' 様',
        '',
        'お見積りのご依頼をありがとうございます。以下の内容で承りました。',
        '生地と縫製の手配先に在庫と工程を確認したうえで、1営業日以内に正式な金額と日程をご返信します。',
        '',
        '──────────────',
        'ご依頼の種類: ' + (a.kind || '未記入'),
        '着数: ' + (a.qty || '未記入'),
        'ボディ: ' + (a.body || '未記入'),
        '刺繍箇所: ' + (place || '未記入'),
        '色数・柄の密度: ' + (a.colors || '未記入'),
        '生地: ' + (a.fabric || '未記入'),
        '仕様: ' + (a.side || '未記入'),
        '希望納期: ' + (a.due || '未記入'),
        '',
        '画面に表示された概算: ' + (a.total || '') + '（1着あたり ' + (a.unit || '') + '）',
        '──────────────',
        '',
        '※ 上の金額は、公開している目安価格から自動計算した「下限の目安」です。',
        '　 刺繍の面積・色数・柄の複雑さ・生地により変動します。契約上の見積書ではありません。',
        '　 正式なお見積りとの差が出る場合は、どの工程で何が変わったのかを添えてご説明します。',
        '',
        '補足:',
        a.msg || '（未記入）',
        '',
        '※ このメールは自動送信です。ご返信いただければ担当に届きます。',
        '',
        REPLY_NAME,
        '神奈川県横須賀市本町3-11-7 アイ\'s ビル 1F',
        'https://hiromichiyokochi.com/'
      ].join('\n')
    });
  }

  if (NOTIFY_TO) {
    sendMail_({
      to: NOTIFY_TO,
      replyTo: a.email || NOTIFY_TO,
      subject: '【自動見積もり】' + (a.name || '名称未記入') + '／' + (a.qty || '') + '／' + (a.total || ''),
      body: [
        'お名前・会社名: ' + (a.name || ''),
        'メール: ' + (a.email || ''),
        '電話: ' + (a.tel || ''),
        '',
        'ご依頼の種類: ' + (a.kind || ''),
        '着数: ' + (a.qty || ''),
        'ボディ: ' + (a.body || ''),
        '刺繍箇所: ' + place,
        '色数・柄の密度: ' + (a.colors || ''),
        '生地: ' + (a.fabric || ''),
        '仕様: ' + (a.side || ''),
        '希望納期: ' + (a.due || ''),
        '',
        '画面に出た概算: ' + (a.total || '') + '（1着あたり ' + (a.unit || '') + '）',
        '',
        '補足:',
        a.msg || '（未記入）',
        '',
        '知ったきっかけ: ' + (a.source || ''),
        'UA: ' + (body.ua || '')
      ].join('\n')
    });
  }

  return done_();
}


/* ご用件ごとの明細。空の項目は出さない */
function contactDetail_(a) {
  const out = [];
  const add = (k, v) => { if (v) out.push(k + ': ' + v); };
  add('来店希望日', a.v_date);
  add('時間帯', a.v_time);
  add('人数', a.v_num);
  add('見たいもの', (a.v_see || []).join(' / '));
  add('媒体名', a.p_outlet);
  add('媒体の種類', a.p_type);
  add('依頼の形式', a.p_form);
  add('取材希望日', a.p_when);
  add('掲載・放送予定日', a.p_pub);
  add('取材場所', a.p_where);
  return out;
}


function handleContact_(body) {
  const a = body.answers || {};
  const sh = sheet_(CONTACT_SHEET, CONTACT_HEADERS);

  sh.appendRow(safeRow_([
    new Date(), a.kind || '',
    a.name || '', a.email || '', a.tel || '',
    a.v_date || '', a.v_time || '', a.v_num || '', (a.v_see || []).join(' / '),
    a.p_outlet || '', a.p_type || '', a.p_form || '', a.p_when || '', a.p_pub || '', a.p_where || '',
    a.msg || '', a.source || '', body.ua || ''
  ]));

  // 送信者への受付メール。金額は書かない（自動見積りはしない）
  if (AUTO_REPLY && a.email) {
    sendMail_({
      to: a.email,
      name: REPLY_NAME,
      replyTo: NOTIFY_TO,
      subject: 'お問い合わせを承りました｜スカジャン絵師 横地広海知',
      body: [
        (a.name || '') + ' 様',
        '',
        'お問い合わせいただきありがとうございます。以下の内容で承りました。',
        '担当より、1営業日以内に概算のお見積りとおおよその日程をご返信します。',
        '',
        '──────────────',
        'ご用件: ' + (a.kind || '未記入'),
        contactDetail_(a).join('\n'),
        '──────────────',
        '',
        'ご相談内容:',
        a.msg || '（未記入）',
        '',
        '※ このメールは自動送信です。ご返信いただければ担当に届きます。',
        '',
        REPLY_NAME,
        '神奈川県横須賀市本町3-11-7 アイ\'s ビル 1F',
        'https://hiromichiyokochi.com/'
      ].join('\n')
    });
  }

  if (NOTIFY_TO) {
    sendMail_({
      to: NOTIFY_TO,
      replyTo: a.email || NOTIFY_TO,
      subject: '【お問い合わせ】' + (a.name || '名称未記入') + '／' + (a.kind || ''),
      body: [
        'お名前・会社名: ' + (a.name || ''),
        'メール: ' + (a.email || ''),
        '電話: ' + (a.tel || ''),
        '',
        'ご用件: ' + (a.kind || ''),
        contactDetail_(a).join('\n'),
        '',
        'ご相談内容:',
        a.msg || '（未記入）',
        '',
        '知ったきっかけ: ' + (a.source || ''),
        'UA: ' + (body.ua || '')
      ].join('\n')
    });
  }
  return done_();
}

function handleRecruit_(body) {
  const a = body.answers || {};
  const sh = sheet_(RECRUIT_SHEET, RECRUIT_HEADERS);

  sh.appendRow(safeRow_([
    new Date(),
    a.name || '', a.kana || '', a.email || '', a.tel || '',
    a.age || '', a.from || '',
    (a.want || []).join(' / '),
    a.days || '', a.start || '',
    a.msg || '', a.url || '', a.source || '', body.ua || ''
  ]));

  // 応募者への受付メール。選考結果ではなく「受け取った」ことだけを伝える
  if (AUTO_REPLY && a.email) {
    sendMail_({
      to: a.email,
      name: REPLY_NAME,
      replyTo: NOTIFY_TO,
      subject: 'アルバイトのご応募を承りました｜ICHIドブ板本店',
      body: [
        (a.name || '') + ' 様',
        '',
        'この度はご応募いただきありがとうございます。以下の内容で承りました。',
        '内容を拝見のうえ、1週間以内にご連絡します。',
        '',
        '──────────────',
        'お名前: ' + (a.name || ''),
        'やってみたいこと: ' + ((a.want || []).join(' / ') || '未記入'),
        '入れる曜日・日数: ' + (a.days || '未記入'),
        '働き始められる時期: ' + (a.start || '未記入'),
        '──────────────',
        '',
        'いただいた個人情報は採用選考の目的にのみ使用し、',
        '選考終了後は責任をもって削除します。',
        '',
        '※ このメールは自動送信です。ご返信いただければ担当に届きます。',
        '',
        REPLY_NAME,
        'ICHIドブ板本店　神奈川県横須賀市本町3-11-7 アイ\'s ビル 1F',
        'https://hiromichiyokochi.com/recruit.html'
      ].join('\n')
    });
  }

  if (NOTIFY_TO) {
    sendMail_({
      to: NOTIFY_TO,
      replyTo: a.email || NOTIFY_TO,
      subject: '【アルバイト応募】' + (a.name || '名称未記入'),
      body: [
        'お名前: ' + (a.name || '') + '（' + (a.kana || '') + '）',
        'メール: ' + (a.email || ''),
        '電話: ' + (a.tel || ''),
        '年代: ' + (a.age || '') + '／お住まい: ' + (a.from || ''),
        '',
        'やってみたいこと: ' + ((a.want || []).join(' / ') || ''),
        '入れる曜日・日数: ' + (a.days || ''),
        '働き始められる時期: ' + (a.start || ''),
        'SNS・ポートフォリオ: ' + (a.url || ''),
        '',
        '志望のきっかけ・お伝えしたいこと:',
        a.msg || '（未記入）',
        '',
        '知ったきっかけ: ' + (a.source || ''),
        'UA: ' + (body.ua || '')
      ].join('\n')
    });
  }
  return done_();
}

function doGet(e) {
  const p = (e && e.parameter) || {};
  if (p.diag !== SECRET) return json({ ok: true, message: 'endpoint alive' });

  /* 診断用。?diag=<SECRET> を付けて開くと状態を返す。
     フォームが「送信しました」と出るのにメールが届かないとき、
     原因がメールの送信残量なのか、シートなのかを切り分けるために使う。
     シートは存在確認だけで、作成はしない。 */
  const out = { ok: true, mailQuotaLeft: null, sheetId: !!SHEET_ID,
                turnstile: TURNSTILE_SECRET ? '有効' : '未設定（素通し）',
                turnstileLastError: PropertiesService.getScriptProperties()
                  .getProperty('TURNSTILE_LAST_ERROR') || 'なし', sheets: {} };
  try { out.mailQuotaLeft = MailApp.getRemainingDailyQuota(); }
  catch (err) { out.mailQuotaLeft = String(err); }
  if (SHEET_ID) {
    try {
      const ss = SpreadsheetApp.openById(SHEET_ID);
      [SHEET_NAME, CONTACT_SHEET, ESTIMATE_SHEET, DESIGN_SHEET, RECRUIT_SHEET]
        .forEach(function (n) {
          const sh = ss.getSheetByName(n);
          if (!sh) { out.sheets[n] = '未作成（初回送信時に作られます）'; return; }
          /* 件数と最終受信日時だけを返す。氏名やメールは返さない */
          const last = sh.getLastRow();
          const info = { rows: Math.max(0, last - 1) };
          if (last > 1) {
            const t = sh.getRange(last, 1).getValue();
            info.lastAt = (t instanceof Date) ? Utilities.formatDate(
              t, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm') : String(t);
          }
          out.sheets[n] = info;
        });
    } catch (err) { out.sheets.error = String(err); }
  }
  return json(out);
}

/* スプレッドシートは = + - @ で始まる文字列を数式として解釈する。
   フォームからの値をそのまま書くと、外部から数式を仕込めてしまう（CSVインジェクション）。
   先頭にアポストロフィを付けて、必ず文字列として入るようにする。 */
function safe_(v) {
  if (v === null || v === undefined) return '';
  if (v instanceof Date) return v;
  const s = String(v);
  return /^[=+\-@\t\r]/.test(s) ? "'" + s : s;
}

function safeRow_(row) {
  return row.map(safe_);
}

function sheet_(name, headers) {
  if (!SHEET_ID) {
    throw new Error(
      'SHEET_ID が未設定です。Apps Script の「プロジェクトの設定」→'
      + '「スクリプト プロパティ」に SHEET_ID を追加してください。');
  }
  const nm = name || SHEET_NAME;
  const hd = headers || HEADERS;
  const ss = SpreadsheetApp.openById(SHEET_ID);
  let sh = ss.getSheetByName(nm);
  if (!sh) sh = ss.insertSheet(nm);
  if (sh.getLastRow() === 0) {
    sh.appendRow(hd);
    sh.getRange(1, 1, 1, hd.length).setFontWeight('bold');
    sh.setFrozenRows(1);
  }
  return sh;
}

function json(o) {
  return ContentService.createTextOutput(JSON.stringify(o))
    .setMimeType(ContentService.MimeType.JSON);
}

/** 動作確認用。エディタから実行してシートに1行入ることを確かめる */
function testAppend() {
  sheet_().appendRow(safeRow_([new Date(), 'TEST-0000', 'hash', 'テスト株式会社', '担当A',
    'test@example.com', 'ブランド別注・量産', '販売用の商品', 'テスト送信', '100着以上',
    '', '', '商用利用', '日本国内', '2年間', 'SNS / Webサイト', '', '', '', '', '']));
}
