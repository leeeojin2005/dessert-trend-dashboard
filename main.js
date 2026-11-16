/* 대시보드 동작 — data/dashboard.json 을 읽어서 화면을 그립니다 */

let D = null;                 // dashboard.json
let cur = "탕후루";            // 선택된 디저트
let cat = "전체";              // 선택된 분석 주제
let upto = 129;               // 슬라이더 위치
let timer = null;

const ORDER = ["탕후루", "마라탕", "요아정", "모찌"];
const CATS = ["전체", "검색량", "매장", "생존", "상권", "예측"];
const $ = (id) => document.getElementById(id);
const n = (v) => v.toLocaleString("ko-KR");

fetch("data/dashboard.json")
  .then(r => r.json())
  .then(d => { D = d; init(); })
  .catch(() => {
    $("gallery").innerHTML =
      '<p class="note">data/dashboard.json 을 불러오지 못했습니다. ' +
      'VS Code Live Server 나 GitHub Pages 로 열어 주세요. (파일을 더블클릭하면 안 됩니다)</p>';
  });

function init() {
  $("totalStores").textContent = n(D.total_stores);
  buildKpis();
  buildCards();
  buildControls();
  $("monthSlider").max = D.months.length - 1;
  $("monthSlider").value = upto = D.months.length - 1;
  $("monthSlider").addEventListener("input", e => { stop(); upto = +e.target.value; drawChart(); });
  $("playBtn").addEventListener("click", togglePlay);
  bindHover();
  buildFinder();
  bindScroll();
  buildScenario();
  select("탕후루");
}

/* ───── 상단 KPI ───── */
function buildKpis() {
  const t = D.items["탕후루"], y = D.items["요아정"], m = D.items["모찌"];
  const rows = [
    [n(D.total_stores) + "곳", "분석한 카피캣 매장"],
    [t.close_rate + "%", "탕후루 폐업률 (648곳 중)"],
    [t.lag_months + "개월", "탕후루 검색 정점 → 매장 정점"],
    [Math.round((1 - y.search_now / y.search_peak_value) * 100) + "%↓", "요아정 검색 관심 감소 (매장은 2%↓)"],
    [m.stores + "곳", "모찌 카피캣 (유행 시작 3개월)"],
  ];
  $("kpis").innerHTML = rows.map(([a, b]) =>
    `<div class="kpi"><div class="n">${a}</div><div class="t">${b}</div></div>`).join("");
}

/* ───── 아이템 카드 ───── */
function buildCards() {
  $("cards").innerHTML = ORDER.map(name => {
    const it = D.items[name];
    return `<button class="card" data-item="${name}" style="--c:${it.color}">
      <div class="top"><span class="nm">${name}</span><span class="lb">${it.label}</span></div>
      <div class="big">${it.close_rate}%</div>
      <div class="sub">폐업률 · ${n(it.stores)}곳 중 ${n(it.closed)}곳</div>
      <dl>
        <dt>유행 시작</dt><dd>${it.start}</dd>
        <dt>매장 정점</dt><dd>${it.peak} (${n(it.peak_count)}곳)</dd>
        <dt>감퇴 시작</dt><dd>${it.decline || "아직 없음"}</dd>
        <dt>현재</dt><dd>${n(it.now_count)}곳</dd>
      </dl></button>`;
  }).join("");
  $("cards").querySelectorAll(".card")
    .forEach(b => b.addEventListener("click", () => select(b.dataset.item)));
}

/* ───── 컨트롤 ───── */
function buildControls() {
  $("itemSelect").innerHTML = ORDER.map(x => `<option value="${x}">${x}</option>`).join("");
  $("itemSelect").addEventListener("change", e => select(e.target.value));
  $("catBtns").innerHTML = CATS.map(c =>
    `<button data-cat="${c}" class="${c === cat ? "on" : ""}">${c}</button>`).join("");
  $("catBtns").querySelectorAll("button").forEach(b =>
    b.addEventListener("click", () => {
      cat = b.dataset.cat;
      $("catBtns").querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b));
      drawGallery();
    }));
}

/* ───── 디저트 선택 ───── */
function select(name) {
  cur = name;
  const c = D.items[name].color;
  document.documentElement.style.setProperty("--c", c);
  $("cards").querySelectorAll(".card")
    .forEach(b => b.classList.toggle("on", b.dataset.item === name));
  $("itemSelect").value = name;
  $("curName").textContent = name;
  $("curDot").style.background = c;
  $("curLabel").textContent = D.items[name].label;
  drawChart();
  drawTimeline();
  drawGallery();
  drawConclusion();
}

/* ───── 메인 차트 (캔버스에 직접 그림 — 외부 라이브러리 없음) ───── */
const PAD = { l: 58, r: 52, t: 14, b: 30 };
let hoverIdx = -1, geom = null;

function drawChart() {
  const it = D.items[cur];
  const cut = upto + 1;
  const rows = it.series.slice(0, cut);
  const cvs = $("mainChart"), box = cvs.parentElement;
  const dpr = window.devicePixelRatio || 1;
  const W = box.clientWidth, H = box.clientHeight;
  cvs.width = W * dpr; cvs.height = H * dpr;
  cvs.style.width = W + "px"; cvs.style.height = H + "px";
  const g = cvs.getContext("2d");
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, W, H);

  const x0 = PAD.l, x1 = W - PAD.r, y0 = PAD.t, y1 = H - PAD.b;
  const maxS = Math.max(10, ...rows.map(r => r.operating));
  const maxQ = Math.max(1, ...rows.map(r => r.search ?? 0));
  const X = i => rows.length < 2 ? x0 : x0 + (x1 - x0) * i / (rows.length - 1);
  const Ys = v => y1 - (y1 - y0) * v / (maxS * 1.08);
  const Yq = v => y1 - (y1 - y0) * v / (maxQ * 1.08);
  geom = { x0, x1, y0, y1, len: rows.length };

  // 가로 눈금선 + 좌우 축 숫자
  g.font = "11px system-ui, sans-serif"; g.textBaseline = "middle";
  for (let k = 0; k <= 4; k++) {
    const y = y0 + (y1 - y0) * k / 4;
    g.strokeStyle = "#f0eae4"; g.lineWidth = 1;
    g.beginPath(); g.moveTo(x0, y); g.lineTo(x1, y); g.stroke();
    g.fillStyle = "#9b9088"; g.textAlign = "right";
    g.fillText(n(Math.round(maxS * 1.08 * (1 - k / 4))), x0 - 8, y);
    g.textAlign = "left";
    g.fillText((maxQ * 1.08 * (1 - k / 4)).toFixed(maxQ < 5 ? 1 : 0), x1 + 8, y);
  }
  // x축 월 표시
  g.fillStyle = "#9b9088"; g.textAlign = "center"; g.textBaseline = "top";
  const fit = Math.max(2, Math.floor((x1 - x0) / 62));      // 화면 폭에 맞는 라벨 개수
  const step = Math.max(1, Math.ceil((rows.length - 1) / (fit - 1)));
  for (let i = 0; i < rows.length; i += step) {
    if (X(i) > x1 - 24) break;                                // 오른쪽 끝에 붙는 라벨은 생략
    g.fillText(rows[i].m, X(i), y1 + 8);
  }

  // 매장 수 — 면적 + 선
  g.beginPath(); g.moveTo(X(0), y1);
  rows.forEach((r, i) => g.lineTo(X(i), Ys(r.operating)));
  g.lineTo(X(rows.length - 1), y1); g.closePath();
  g.fillStyle = it.color + "22"; g.fill();
  g.beginPath();
  rows.forEach((r, i) => i ? g.lineTo(X(i), Ys(r.operating)) : g.moveTo(X(i), Ys(r.operating)));
  g.strokeStyle = it.color; g.lineWidth = 2.5; g.lineJoin = "round"; g.stroke();

  // 검색 관심도 — 점선
  g.beginPath(); g.setLineDash([3, 3]);
  rows.forEach((r, i) => {
    const y = Yq(r.search ?? 0);
    i ? g.lineTo(X(i), y) : g.moveTo(X(i), y);
  });
  g.strokeStyle = "#9b9088"; g.lineWidth = 1.6; g.stroke(); g.setLineDash([]);

  // 마우스 올린 위치 표시
  if (hoverIdx >= 0 && hoverIdx < rows.length) {
    const hx = X(hoverIdx);
    g.beginPath(); g.moveTo(hx, y0); g.lineTo(hx, y1);
    g.strokeStyle = "#c9bdb3"; g.lineWidth = 1; g.stroke();
    g.beginPath(); g.arc(hx, Ys(rows[hoverIdx].operating), 4.5, 0, Math.PI * 2);
    g.fillStyle = it.color; g.fill();
    g.strokeStyle = "#fff"; g.lineWidth = 2; g.stroke();
  }

  // 축 이름
  g.save(); g.translate(14, (y0 + y1) / 2); g.rotate(-Math.PI / 2);
  g.fillStyle = "#857c75"; g.textAlign = "center"; g.textBaseline = "middle";
  g.fillText("영업 매장 수", 0, 0); g.restore();
  g.save(); g.translate(W - 10, (y0 + y1) / 2); g.rotate(Math.PI / 2);
  g.fillStyle = "#857c75"; g.textAlign = "center";
  g.fillText("검색 관심도", 0, 0); g.restore();

  // 슬라이더 숫자판
  const s = it.series[upto];
  $("monthOut").textContent = D.months[upto];
  $("readout").innerHTML = [
    ["영업 중", n(s.operating) + "곳"],
    ["그 달 개업", s.opened + "곳"],
    ["그 달 폐업", s.closed + "곳"],
    ["검색 관심도", s.search == null ? "-" : s.search],
  ].map(([k, v]) => `<div><div class="v">${v}</div><div class="k">${k}</div></div>`).join("");
}

/* 마우스 올렸을 때 뜨는 말풍선 */
function bindHover() {
  const box = $("mainChart").parentElement;
  box.addEventListener("mousemove", e => {
    if (!geom) return;
    const r = box.getBoundingClientRect();
    const px = e.clientX - r.left;
    if (px < geom.x0 - 10 || px > geom.x1 + 10) return hideTip();
    const t = (px - geom.x0) / (geom.x1 - geom.x0);
    hoverIdx = Math.max(0, Math.min(geom.len - 1, Math.round(t * (geom.len - 1))));
    const s = D.items[cur].series[hoverIdx];
    const el = $("tip");
    el.hidden = false;
    el.innerHTML = `<b>${s.m}</b><br>영업 ${n(s.operating)}곳 · 개업 ${s.opened} · 폐업 ${s.closed}`
      + `<br>검색 관심도 ${s.search ?? "-"}`;
    el.style.left = (geom.x0 + (geom.x1 - geom.x0) * hoverIdx / (geom.len - 1)) + "px";
    el.style.top = (geom.y0 + 12) + "px";
    drawChart();
  });
  box.addEventListener("mouseleave", hideTip);
  window.addEventListener("resize", () => drawChart());
}
function hideTip() { hoverIdx = -1; $("tip").hidden = true; drawChart(); }

/* 재생 버튼 */
function togglePlay() {
  if (timer) return stop();
  if (upto >= D.months.length - 1) upto = 0;
  $("playBtn").textContent = "⏸ 정지";
  timer = setInterval(() => {
    upto++;
    if (upto >= D.months.length - 1) { upto = D.months.length - 1; stop(); }
    $("monthSlider").value = upto;
    drawChart();
  }, 70);
}
function stop() {
  clearInterval(timer); timer = null;
  $("playBtn").textContent = "▶ 재생";
}

/* ───── 유행 타임라인 ───── */
function drawTimeline() {
  const it = D.items[cur];
  const steps = [
    ["유행 시작", it.start + (it.start_source === "검색량" ? " (검색량 기준)" : "")],
    ["검색 정점", it.search_peak],
    ["매장 정점", `${it.peak} · ${n(it.peak_count)}곳`],
    ["감퇴 시작", it.decline || "아직 없음"],
    ["현재", `2026-10 · ${n(it.now_count)}곳`],
  ];
  $("timeline").innerHTML =
    `<div class="tl-row">` +
    steps.map(([k, v]) => `<span class="tl-step">${k} <b>${v}</b></span>`).join('<span class="tl-arrow">→</span>') +
    `</div>`;
}

/* ───── 그래프 갤러리 ───── */
function drawGallery() {
  const key = D.items[cur].key;
  const list = D.charts.filter(c => cat === "전체" || c.cat === cat);
  $("gallery").innerHTML = list.map(c => {
    const src = c.per_item && c.img_item ? c.img_item.replace("{key}", key) : c.img;
    const only = c.per_item ? ` · ${cur}` : "";
    return `<article class="g-card">
      <div><img src="${src}" alt="${c.title}" loading="lazy"
        onerror="this.outerHTML='&lt;div class=\\'miss\\'&gt;그래프 준비 중<br>${src}&lt;/div&gt;'"></div>
      <div>
        <span class="tag">그래프 ${c.id} · ${c.cat}${only}</span>
        <h3>${c.title}</h3>
        <p>${c.desc}</p>
      </div></article>`;
  }).join("");
}

/* ───── 결론 ───── */
function drawConclusion() {
  const m = D.items["모찌"], t = D.items["탕후루"], ma = D.items["마라탕"], y = D.items["요아정"];
  $("conclusion").innerHTML = `
    <p class="punch">모찌는 아직 '반짝 유행'의 속도를 보이지 않습니다.</p>
    <p>유행이 시작된 뒤 첫 3개월 동안 문을 연 매장은 탕후루 ${t.first3_opened}곳, 마라탕 ${ma.first3_opened}곳,
    요아정 ${y.first3_opened}곳인 데 비해 모찌는 <b>${m.first3_opened}곳</b>에 그쳤습니다.
    검색 관심도 역시 마라탕 최고점의 ${Math.round(m.search_peak_value / ma.search_peak_value * 100)}% 수준입니다.</p>
    <p>앞선 세 사례(디저트 2종 + 비교군 마라탕)에 비춰 보면 모찌가 갈 수 있는 길은 셋입니다.</p>
    <div class="verdict">
      <div style="border-color:${t.color}">
        <div class="h" style="color:${t.color}">① 탕후루 길</div>
        <div class="s">8개월 만에 정점 → 1년 안에 급락. 폐업률 ${t.close_rate}%.
        확산 속도가 느려 가능성은 낮아 보입니다.</div></div>
      <div style="border-color:${y.color}">
        <div class="h" style="color:${y.color}">② 요아정 길</div>
        <div class="s">관심은 빠르게 식지만 매장은 메뉴를 바꿔가며 버팀.
        모찌가 기존 카페·떡집 메뉴로 흡수되면 이 길에 가깝습니다.</div></div>
      <div style="border-color:${ma.color}">
        <div class="h" style="color:${ma.color}">③ 마라탕 길 <span style="font-weight:600;font-size:.78rem;color:#8a7c72">(비교군)</span></div>
        <div class="s">수년에 걸쳐 완만히 늘며 일상 메뉴로 정착.
        현재의 완만한 개업 속도는 이 패턴과 비슷합니다.</div></div>
    </div>
    <p class="small" style="margin-top:16px">※ 모찌는 유행 시작 3개월째로 표본이 ${m.stores}곳에 불과해
    생존 분석에서는 제외했습니다. 또한 요아정 매장이 모찌를 파는 경우처럼 상호명에 키워드가 없는 판매처는
    집계되지 않아, 실제 모찌 판매처는 이보다 많을 수 있습니다.</p>`;
}

/* ═══════════ 매장 찾아보기 ═══════════ */
const NAME = { tanghulu: "탕후루", malatang: "마라탕", yoajung: "요아정", mochi: "모찌" };
let shown = 0, picked = -1;

function buildFinder() {
  $("fItem").innerHTML = '<option value="">전체 메뉴</option>' +
    ORDER.map(x => `<option value="${D.items[x].key}">${x}</option>`).join("");
  ["q", "fItem", "fStat"].forEach(id =>
    $(id).addEventListener("input", () => { shown = 60; picked = -1; $("detail").hidden = true; drawTable(); }));
  shown = 60;
  drawTable();
}

function filtered() {
  const q = $("q").value.trim().toLowerCase();
  const it = $("fItem").value, st = $("fStat").value;
  return D.store_list.filter(s =>
    (!it || s.i === it) &&
    (!st || (st === "closed" ? s.c : !s.c)) &&
    (!q || s.n.toLowerCase().includes(q) || s.r.includes(q)));
}

function drawTable() {
  const rows = filtered();
  $("fCount").textContent = `${n(rows.length)}곳`;
  $("tbody").innerHTML = rows.slice(0, shown).map((s, i) => {
    const c = D.items[NAME[s.i]].color;
    return `<tr data-i="${i}" class="${i === picked ? "on" : ""}">
      <td>${s.n}</td>
      <td><span class="pill" style="background:${c}">${NAME[s.i]}</span></td>
      <td>${s.r}</td>
      <td class="num">${s.o.slice(0, 7)}</td>
      <td class="num ${s.c ? "" : "dead"}">${s.c ? s.c.slice(0, 7) : "영업 중"}</td>
      <td class="num">${s.c ? n(s.d) + "일" : "지금까지 " + n(s.d) + "일"}</td></tr>`;
  }).join("");
  $("fMore").textContent = rows.length > shown
    ? `${n(rows.length - shown)}곳 더 있습니다 — 아래로 스크롤하면 이어집니다`
    : (rows.length ? "" : "조건에 맞는 매장이 없습니다");
  $("tbody").querySelectorAll("tr").forEach(tr =>
    tr.addEventListener("click", () => pick(rows[+tr.dataset.i], +tr.dataset.i)));
}

function pick(s, i) {
  picked = i;
  const it = D.items[NAME[s.i]];
  const yrs = (s.d / 365).toFixed(1);
  $("detail").hidden = false;
  $("detail").style.setProperty("--c", it.color);
  $("detail").innerHTML = `<h4>${s.n}</h4>
    <div class="grid">
      <div><span class="k">메뉴</span><b style="color:${it.color}">${NAME[s.i]}</b></div>
      <div><span class="k">지역</span><b>${s.r}</b></div>
      <div><span class="k">개업일</span><b>${s.o}</b></div>
      <div><span class="k">폐업일</span><b>${s.c || "영업 중"}</b></div>
      <div><span class="k">${s.c ? "버틴 기간" : "영업 기간"}</span><b>${n(s.d)}일 (${yrs}년)</b></div>
      <div><span class="k">진입 시기</span><b>${s.s}</b></div>
    </div>
    <p class="small" style="margin:12px 0 0">
      ${NAME[s.i]} 유행은 ${it.start}에 시작해 ${it.peak}에 정점(${n(it.peak_count)}곳)을 찍었습니다.
      이 매장은 <b>${s.s}</b>에 문을 열었고, 같은 시기에 연 ${NAME[s.i]} 매장의 1년 내 폐업률은
      아래 그래프 8번에서 확인할 수 있습니다.</p>`;
  drawTable();
  $("detail").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/* 표 아래로 스크롤하면 더 불러오기 */
function bindScroll() {
  const box = document.querySelector(".table-box");
  box.addEventListener("scroll", () => {
    if (box.scrollTop + box.clientHeight > box.scrollHeight - 60) {
      const total = filtered().length;
      if (shown < total) { shown += 60; drawTable(); }
    }
  });
}

/* ═══════════ 모찌 예측 시나리오 ═══════════ */
let scRef = "tanghulu";

function buildScenario() {
  $("scBtns").innerHTML = ["탕후루", "요아정", "마라탕"].map((x, i) =>
    `<button data-k="${D.items[x].key}" class="${i === 0 ? "on" : ""}">${x}처럼 간다면</button>`).join("");
  $("scBtns").querySelectorAll("button").forEach(b =>
    b.addEventListener("click", () => {
      scRef = b.dataset.k;
      $("scBtns").querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b));
      drawScenario();
    }));
  drawScenario();
}

function drawScenario() {
  const refName = NAME[scRef], ref = D.items[refName], mo = D.items["모찌"];
  // 모찌의 초기 확산 속도 = 첫 3개월 개업 수 비율
  const scale = mo.first3_opened / ref.first3_opened;
  const curve = D.lifecycle[scRef].pct.map(p => p / 100 * ref.peak_count * scale);
  const actual = D.lifecycle.mochi.abs.map((_, i) => mo.first3_opened * (i + 1) / 3);

  const cvs = $("scChart"), box = cvs.parentElement;
  const dpr = window.devicePixelRatio || 1, W = box.clientWidth, H = box.clientHeight;
  cvs.width = W * dpr; cvs.height = H * dpr;
  cvs.style.width = W + "px"; cvs.style.height = H + "px";
  const g = cvs.getContext("2d");
  g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H);

  const x0 = 54, x1 = W - 16, y0 = 14, y1 = H - 30;
  const maxY = Math.max(...curve) * 1.12;
  const maxX = curve.length - 1;
  const X = e => x0 + (x1 - x0) * e / maxX;
  const Y = v => y1 - (y1 - y0) * v / maxY;

  g.font = "11px system-ui, sans-serif"; g.textBaseline = "middle";
  for (let k = 0; k <= 4; k++) {
    const y = y0 + (y1 - y0) * k / 4;
    g.strokeStyle = "#f0eae4"; g.lineWidth = 1;
    g.beginPath(); g.moveTo(x0, y); g.lineTo(x1, y); g.stroke();
    g.fillStyle = "#9b9088"; g.textAlign = "right";
    g.fillText(n(Math.round(maxY * (1 - k / 4))), x0 - 8, y);
  }
  g.textAlign = "center"; g.textBaseline = "top";
  const fitS = Math.max(2, Math.floor((x1 - x0) / 56));
  const stepS = Math.max(1, Math.ceil(maxX / (fitS - 1)));
  for (let e = 0; e <= maxX; e += stepS) {
    if (X(e) > x1 - 20) break;
    g.fillText(e + "개월", X(e), y1 + 8);
  }

  // 시나리오 곡선 (점선)
  g.beginPath(); g.setLineDash([5, 4]);
  curve.forEach((v, e) => e ? g.lineTo(X(e), Y(v)) : g.moveTo(X(e), Y(v)));
  g.strokeStyle = ref.color; g.lineWidth = 2.2; g.stroke(); g.setLineDash([]);

  // 지금까지의 모찌 (실선)
  g.beginPath();
  actual.forEach((v, e) => e ? g.lineTo(X(e), Y(v)) : g.moveTo(X(e), Y(v)));
  g.strokeStyle = D.items["모찌"].color; g.lineWidth = 3.2; g.stroke();
  g.beginPath(); g.arc(X(actual.length - 1), Y(actual[actual.length - 1]), 5, 0, Math.PI * 2);
  g.fillStyle = D.items["모찌"].color; g.fill();
  g.strokeStyle = "#fff"; g.lineWidth = 2; g.stroke();

  // 정점 표시
  const pi = curve.indexOf(Math.max(...curve));
  g.beginPath(); g.moveTo(X(pi), y0); g.lineTo(X(pi), y1);
  g.strokeStyle = ref.color + "66"; g.lineWidth = 1; g.setLineDash([2, 3]); g.stroke(); g.setLineDash([]);
  g.fillStyle = ref.color; g.textAlign = "center"; g.textBaseline = "bottom";
  g.fillText(`정점 ${pi}개월 · 약 ${n(Math.round(curve[pi]))}곳`, X(pi), y0 + 12);

  g.fillStyle = D.items["모찌"].color; g.textAlign = "left"; g.textBaseline = "middle";
  g.fillText("지금 (3개월)", X(2) + 8, Y(actual[2]) - 4);

  // 아래 숫자판
  const peakM = pi, last = curve[curve.length - 1];
  const half = curve.findIndex((v, i) => i > pi && v <= curve[pi] / 2);
  $("scOut").innerHTML = [
    ["확산 속도", `${refName}의 ${Math.round(scale * 100)}%`],
    ["예상 정점", `${peakM}개월 뒤 · 약 ${n(Math.round(curve[pi]))}곳`],
    ["절반으로 줄기까지", half > 0 ? `정점 후 ${half - pi}개월` : "아직 그 단계 아님"],
    ["끝 지점", `약 ${n(Math.round(last))}곳`],
  ].map(([k, v]) => `<div><div class="v" style="font-size:1rem">${v}</div><div class="k">${k}</div></div>`).join("");
}
