/* ==========================================================================
   SPECDOC — 仕様確認書の共通エンジン
   条項の原文はここに一元化。弁護士の指摘はこのファイルだけ直せば全ページに反映される
   ========================================================================== */
window.SPECDOC = (function(){

  // 受注者（乙）の既定表記。ここを変えると全書類に反映される
  const VENDOR = "合同会社ICHI";

  // 当事者名に「（以下「甲」という。）」を自動で添える。
  // すでに甲乙の記載がある場合は二重に付けない
  function party(v, fallback, mark){
    const name = (v == null ? "" : String(v)).trim() || fallback;
    if(!name) return '<span style="color:#bbb">—</span>';
    const has = new RegExp('以下[\\s\u3000]*[「\'"]?' + mark).test(name);
    return esc(name) + (has ? "" : '（以下「' + mark + '」という。）');
  }

  const MEDIA = ["商品パッケージ","店頭POP","SNS","Webサイト","広告","YouTube",
                 "テレビCM","雑誌","展示会","ノベルティ","商品販売"];

  const COPYRIGHT = [
    "本イラストに関する著作権（著作権法第27条及び第28条の権利を含む。）その他一切の知的財産権は、乙又は乙が指定する制作者に帰属します。",
    "本契約は著作権の譲渡ではなく、利用許諾を目的とするものとします。",
    "甲は、本契約で許諾された範囲を超えて本イラストを利用できません。"
  ];

  const LICENCE = [
    "甲は、上記に掲げた媒体、地域及び期間の範囲内で本イラストを利用できます。",
    "上記に記載のない商品ラインナップを追加する場合、甲は事前に乙へ申告し、別途費用について協議するものとします。事前の申告なく追加された場合も同様に、追加費用の対象とします。",
    "海外での展開を行う場合、甲は事前に乙へその旨を申し出るものとします。",
    "期間満了後も継続して利用する場合は、更新について協議するものとします。"
  ];

  const BANS = [
    "線画の変更又は改変",
    "顔、表情又はポーズの変更",
    "彩色の変更（印刷工程上必要な色調整を除く。）",
    "キャラクター又はモチーフの追加又は削除",
    "他キャラクターとの合成",
    "他のイラストレーター又は第三者による加筆、修正又は描き直し",
    "AIを利用した加工、編集又は派生画像の生成",
    "AI学習への利用又はAIサービスへの入力",
    "本契約で許諾された範囲を超える利用",
    "本イラストを第三者へ再許諾し、譲渡し、又は提供する行為",
    "その他乙のブランド価値、信用又は作品の世界観を著しく損なう利用"
  ];

  const PRESETS = [
    ["作家性を活かしたオリジナル柄",
     "本件は、乙（スカジャン絵師 横地広海知）の作家性を活かしたオリジナルのスカジャン柄デザインを新規に制作するものです。特定の既存意匠を再現・模倣することを目的とするものではなく、モチーフの選定および作画の表現は乙の裁量に委ねられます。"],
    ["スカジャン風デザイン（他アイテム）",
     "本件は、乙の作家性を活かしたスカジャン風のデザインを、スカジャン以外のアイテム向けに制作するものです。刺繍ではなくプリントでの再現を前提とし、色数・線幅は当該製法に合わせて設計します。"],
    ["既存モチーフのアレンジ",
     "本件は、甲よりご指定のモチーフをもとに、乙の作画によりスカジャン柄として再構成するものです。元となる意匠の権利処理は甲の責任において完了しているものとします。"],
    ["柄デザインのみの提供",
     "本件は、スカジャン柄のデザインデータのみを制作・納品するものです。製品の生産、刺繍データ（パンチ）の作成、品質管理は本件に含まれず、甲側で実施されるものとします。"],
    ["一着物のフルオーダー",
     "本件は、横振り刺繍による一点物のスカジャンを制作するものです。横振り刺繍は職人が手作業で行う技法であり、同一の仕上がりを再現することはできません。仕上がりに個体差が生じることを、甲乙あらかじめ了解します。"],
    ["量産前提（原画の再設計を含む）",
     "本件は、乙が制作した原画をもとに、機械刺繍による量産用データへ再設計したうえで量産するものです。機械刺繍には色数・針数の制約があるため、原画と完全に同一の表現にはならないことを、甲乙あらかじめ了解します。"]
  ];

  const DEFAULT_EXTRA =
    "規定回数を超える修正、デザイン確定日以降の変更、成果物の追加、事前に申告のない商品ラインナップの追加、および許諾範囲の拡大が生じた場合は、別途お見積りのうえ、スケジュールを再設定します。";

  const esc = s => String(s == null ? "" : s)
    .replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const nl  = s => esc(s).replace(/\n/g,"<br>");
  const or  = (s,d) => (s && String(s).trim()) ? s : (d || "—");
  const p2  = n => String(n).padStart(2,"0");

  function docNo(){
    const d = new Date();
    return "SY-" + d.getFullYear() + p2(d.getMonth()+1) + p2(d.getDate()) + "-" +
      Math.random().toString(36).slice(2,5).toUpperCase();
  }

  function stamp(){
    const d = new Date();
    return d.getFullYear()+"-"+p2(d.getMonth()+1)+"-"+p2(d.getDate())+" "+
           p2(d.getHours())+":"+p2(d.getMinutes());
  }

  async function hash(obj){
    try{
      const buf = new TextEncoder().encode(JSON.stringify(obj));
      const h = await crypto.subtle.digest("SHA-256", buf);
      return [...new Uint8Array(h)].map(b=>b.toString(16).padStart(2,"0")).join("");
    }catch(e){ return ""; }
  }

  /* d: 書類データ / opts: {draft:true} でヒアリング草案の断り書きを入れる */
  function render(d, hex, opts){
    opts = opts || {};
    const revs = Array.isArray(d.revs) ? d.revs : [];
    const licence = String(d.s_own||"").indexOf("利用許諾") === 0;
    const personal = String(d.s_use||"").indexOf("個人") === 0;
    const media = Array.isArray(d.media) ? d.media : [];
    const now = stamp();

    const mediaHtml = (media.length || d.s_media_etc)
      ? `<div class="doc__tagrow">${media.map(m=>`<span>${esc(m)}</span>`).join("")}${
          d.s_media_etc ? `<span>${esc(d.s_media_etc)}</span>` : ""}</div>`
      : "—";

    const banAdd = String(d.s_ban_add||"").split("\n").map(s=>s.trim()).filter(Boolean);

    const revRows = revs.length
      ? revs.map((r,i)=>`<tr><td>rev.${p2(i+1)}</td><td>${esc(r.date)||"—"}</td><td>${nl(r.what)}</td><td>${esc(r.by)||"—"}</td></tr>`).join("")
      : `<tr><td>rev.00</td><td>${esc(now.slice(0,10))}</td><td>初版</td><td>—</td></tr>`;

    const draftBox = opts.draft ? `
      <div class="doc__draft">
        本書は、甲よりご入力いただいた内容にもとづき自動作成された<strong style="font-weight:500">仕様確認書の草案</strong>です。
        この時点では発注の確定を意味しません。乙による内容確認とお見積りの提示、
        および甲の承諾をもって、正式な発注として成立するものとします。
      </div>` : "";

    return `
      <div class="doc__head">
        <div>
          <p class="doc__title">${esc(d.s_kind || "仕様確認書")}</p>
          <p style="font-size:13px;margin:0">${or(esc(d.s_title),"（件名未入力）")}</p>
        </div>
        <div class="doc__meta">No. ${esc(d.s_no)}<br>作成 ${now}<br>rev.${p2(revs.length)}</div>
      </div>

      ${draftBox}

      <dl>
        <dt>発注者（甲）</dt><dd>${party(d.s_client, "", "甲")}</dd>
        <dt>受注者（乙）</dt><dd>${party(d.s_vendor, VENDOR, "乙")}</dd>
      </dl>
      <p style="font-size:11px;color:#777;margin-top:8px">以下、発注者を「甲」、受注者を「乙」、本件で制作する図案を「本イラスト」といいます。</p>

      <h4>1. 制作コンセプト</h4>
      <div class="doc__concept">${or(nl(d.s_concept),"（未入力）本件で何を制作するのかを、着手前に必ず記載してください。")}</div>

      <h4>2. 本件に含まないもの</h4>
      <p>${or(nl(d.s_out))}</p>

      <h4>3. 成果物と仕様</h4>
      <dl>
        <dt>成果物</dt><dd>${or(nl(d.s_deliv))}</dd>
        <dt>数量・着数</dt><dd>${or(esc(d.s_qty))}</dd>
        <dt>刺繍・製法</dt><dd>${or(esc(d.s_tech))}</dd>
      </dl>

      <h4>4. 修正回数とスケジュール</h4>
      <dl>
        <dt>ラフ段階</dt><dd>${or(esc(d.s_rev1))}</dd>
        <dt>本描き段階</dt><dd>${or(esc(d.s_rev2))}</dd>
        <dt>デザイン確定日</dt><dd>${or(esc(d.s_fix))}</dd>
        <dt>納品予定日</dt><dd>${or(esc(d.s_due))}</dd>
      </dl>

      <h4>5. 費用</h4>
      <dl>
        <dt>金額（税別）</dt><dd>${or(esc(d.s_fee))}</dd>
        <dt>支払条件</dt><dd>${or(esc(d.s_pay))}</dd>
        <dt>追加費用</dt><dd>${or(nl(d.s_extra), DEFAULT_EXTRA)}</dd>
      </dl>

      <h4>6. 著作権の帰属</h4>
      ${licence
        ? `<ol class="doc__clauses">${COPYRIGHT.map(c=>`<li>${esc(c)}</li>`).join("")}</ol>`
        : `<p>著作権の取り扱いは別途協議のうえ決定します。本書の時点では確定していません。</p>`}

      <h4>7. 利用許諾の範囲</h4>
      <dl>
        <dt>利用区分</dt><dd>${or(esc(d.s_use))}</dd>
        <dt>地域</dt><dd>${or(esc(d.s_area))}</dd>
        <dt>期間</dt><dd>${or(esc(d.s_term))}${d.s_start ? "（起算日 "+esc(d.s_start)+"）" : ""}</dd>
        <dt>更新</dt><dd>${or(esc(d.s_renew))}</dd>
        ${personal ? "" : `<dt>媒体</dt><dd>${mediaHtml}</dd>
        <dt>商品ラインナップ</dt><dd>${or(nl(d.s_lineup))}</dd>`}
        <dt>クレジット</dt><dd>${or(esc(d.s_credit))}</dd>
        <dt>支給物・持込IP</dt><dd>${or(nl(d.s_ip))}</dd>
      </dl>
      <ol class="doc__clauses" style="margin-top:12px">
        ${LICENCE.map(c=>`<li>${esc(c)}</li>`).join("")}
      </ol>

      <h4>8. 禁止事項</h4>
      <p style="margin-bottom:6px">甲は、次の行為を行ってはなりません。</p>
      <ol class="doc__clauses">
        ${BANS.map(b=>`<li>${esc(b)}</li>`).join("")}
        ${banAdd.map(b=>`<li>${esc(b)}</li>`).join("")}
      </ol>

      <div class="doc__fixed">
        <strong style="font-weight:500">確定事項について</strong><br>
        本書に記載の内容は、甲乙双方の確認をもって本件の確定事項とします。デザイン確定日以降、
        規定回数を超える修正のご依頼があった場合、または許諾範囲を超える利用のご要望があった場合は、
        本書の記載を前提として、追加費用およびスケジュールの再設定についてあらためて協議するものとします。
      </div>

      <h4>9. 改訂履歴</h4>
      <table><thead><tr><th>版</th><th>日付</th><th>変更内容</th><th>合意方法</th></tr></thead>
      <tbody>${revRows}</tbody></table>

      <div class="doc__sign">
        <div><span>甲（発注者）確認</span>日付　　　　／　署名</div>
        <div><span>乙（受注者）確認</span>日付　　　　／　署名</div>
      </div>

      <p class="doc__note">
        本書は制作の方向性、許諾範囲及び確定事項を相互に確認するための書面です。契約書に代わるものではありません。<br>
        文書ハッシュ（SHA-256）<br><span class="doc__hash">${hex || "（この環境では算出できません）"}</span>
      </p>`;
  }

  function download(name, text, type){
    const blob = new Blob([text], {type: type || "application/json"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = name; a.click();
    URL.revokeObjectURL(a.href);
  }

  return {MEDIA, COPYRIGHT, LICENCE, BANS, PRESETS, DEFAULT_EXTRA,
          esc, nl, or, p2, docNo, stamp, hash, render, download};
})();
