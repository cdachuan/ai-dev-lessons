// 大屏主逻辑：ECharts 三图 + /summary 轮询 + /ask 问数联动（对话面板版）
// API 地址：同源优先（da serve 托管），file:// 打开时回退 8636
const API = location.protocol.startsWith("http") ? "" : "http://localhost:8636";

// ---------- 时钟 ----------
setInterval(() => {
  document.getElementById("clock").textContent =
    new Date().toLocaleString("zh-CN", { hour12: false });
}, 1000);

// ---------- ECharts 初始化 ----------
const chartTheme = {
  textStyle: { color: "#8fb0d8", fontSize: 11 },
  tooltip: { backgroundColor: "rgba(10,20,44,.9)", borderColor: "#2e6fd8", textStyle: { color: "#c8d8f0" } },
};

// 短省份名 → china.js 注册全名（mock 数据用短名，地图注册名带后缀）
const PROV_NAME_MAP = {
  "北京": "北京市", "天津": "天津市", "上海": "上海市", "重庆": "重庆市",
  "河北": "河北省", "山西": "山西省", "辽宁": "辽宁省", "吉林": "吉林省",
  "黑龙江": "黑龙江省", "江苏": "江苏省", "浙江": "浙江省", "安徽": "安徽省",
  "福建": "福建省", "江西": "江西省", "山东": "山东省", "河南": "河南省",
  "湖北": "湖北省", "湖南": "湖南省", "广东": "广东省", "海南": "海南省",
  "四川": "四川省", "贵州": "贵州省", "云南": "云南省", "陕西": "陕西省",
  "甘肃": "甘肃省", "青海": "青海省", "台湾": "台湾省",
  "内蒙古": "内蒙古自治区", "广西": "广西壮族自治区", "西藏": "西藏自治区",
  "宁夏": "宁夏回族自治区", "新疆": "新疆维吾尔自治区",
  "香港": "香港特别行政区", "澳门": "澳门特别行政区",
};
const toMapName = n => PROV_NAME_MAP[n] || n;

const mapChart = echarts.init(document.getElementById("mapChart"));
const barChart = echarts.init(document.getElementById("barChart"));
const trendChart = echarts.init(document.getElementById("trendChart"));

function renderMap(data, highlight) {
  const maxV = Math.max(...data.map(d => d.value), 1);
  mapChart.setOption({
    ...chartTheme,
    tooltip: { ...chartTheme.tooltip, trigger: "item", formatter: p => `${p.name}: ${p.value ? p.value.toLocaleString() : "无数据"}` },
    visualMap: {
      min: 0, max: maxV, left: 8, bottom: 8,
      calculable: true, text: ["高", "低"],
      inRange: { color: ["#12306e", "#2e6fd8", "#4dd8ff"] },
      textStyle: { color: "#7d9cc5", fontSize: 10 },
    },
    series: [{
      type: "map", map: "china", roam: false,
      emphasis: { label: { color: "#fff" }, itemStyle: { areaColor: "#ffd479" } },
      data: data.map(d => ({ name: toMapName(d.name), value: d.value, selected: d.name === highlight })),
    }],
  });
}

function renderBar(data) {
  barChart.setOption({
    ...chartTheme,
    grid: { left: 8, right: 8, top: 8, bottom: 8, containLabel: true },
    xAxis: { type: "value", splitLine: { lineStyle: { color: "rgba(46,111,216,.15)" } } },
    yAxis: { type: "category", data: data.map(d => d.name), axisLine: { lineStyle: { color: "#2e6fd8" } } },
    series: [{
      type: "bar", data: data.map(d => d.value), barWidth: "55%",
      itemStyle: {
        borderRadius: 3,
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: "#1c4aa0" }, { offset: 1, color: "#4dd8ff" }]),
      },
      label: { show: true, position: "right", color: "#8fb0d8", fontSize: 10, formatter: p => (p.value / 10000).toFixed(1) + "万" },
    }],
  });
}

function renderTrend(data) {
  trendChart.setOption({
    ...chartTheme,
    grid: { left: 8, right: 8, top: 16, bottom: 4, containLabel: true },
    xAxis: { type: "category", data: data.map(d => d.name), axisLine: { lineStyle: { color: "#2e6fd8" } } },
    yAxis: { type: "value", splitLine: { lineStyle: { color: "rgba(46,111,216,.15)" } } },
    series: [{
      type: "line", data: data.map(d => d.value), smooth: true, symbol: "circle", symbolSize: 4,
      lineStyle: { color: "#4dd8ff", width: 2 },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: "rgba(77,216,255,.35)" }, { offset: 1, color: "rgba(77,216,255,0)" }]) },
    }],
  });
}

// ---------- /summary 轮询 ----------
async function refreshSummary() {
  try {
    const r = await (await fetch(API + "/summary")).json();
    document.getElementById("kpi-total").textContent = r.kpi.total_7d.toLocaleString();
    document.getElementById("kpi-orders").textContent = r.kpi.orders_7d.toLocaleString();
    const wowEl = document.getElementById("kpi-wow");
    wowEl.textContent = (r.kpi.wow_pct > 0 ? "+" : "") + r.kpi.wow_pct + "%";
    wowEl.className = "num " + (r.kpi.wow_pct >= 0 ? "up" : "down");
    document.getElementById("kpi-avg").textContent = r.kpi.avg_order.toLocaleString();
    renderMap(r.region_top);
    renderBar(r.category);
    renderTrend(r.daily_trend);
  } catch (e) {
    console.warn("summary 加载失败", e);
  }
}
refreshSummary();
setInterval(refreshSummary, 30000);

// ---------- 数据源选择 ----------
const datasetSelect = document.getElementById("datasetSelect");
let currentDataset = "dash_orders";

async function loadDatasets() {
  try {
    const r = await (await fetch(API + "/datasets")).json();
    datasetSelect.innerHTML = r.datasets
      .map(d => `<option value="${d.name}" title="${d.desc || ""}">${d.name}</option>`).join("");
    datasetSelect.value = currentDataset;
    datasetSelect.addEventListener("change", () => { currentDataset = datasetSelect.value; });
  } catch (e) { console.warn("datasets 加载失败", e); }
}
loadDatasets();

// ---------- 问数（对话工作台） ----------
const history = document.getElementById("chatHistory");
const input = document.getElementById("chatInput");
const btn = document.getElementById("chatBtn");
const face = document.getElementById("avatarFace");
const status = document.getElementById("avatarStatus");

function esc(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function addUserMsg(q) {
  const div = document.createElement("div");
  div.className = "msg user";
  div.innerHTML = `<div class="bubble">${esc(q)}</div>`;
  history.appendChild(div);
  history.scrollTop = history.scrollHeight;
}

function addTyping() {
  const div = document.createElement("div");
  div.className = "msg bot";
  div.id = "typingMsg";
  div.innerHTML = `<div class="bubble"><span class="typing"><i></i><i></i><i></i></span></div>`;
  history.appendChild(div);
  history.scrollTop = history.scrollHeight;
}

function removeTyping() {
  document.getElementById("typingMsg")?.remove();
}

function addBotMsg(q, a, caliber, info) {
  const chips = [];
  if (info?.verified === true) chips.push(`<span class="chip verify-pass">双路径核验 ✓</span>`);
  else if (info?.verified === false) chips.push(`<span class="chip verify-fail">核验未通过</span>`);
  if (info?.asset_hit) chips.push(`<span class="chip asset">资产复用</span>`);
  if (info?.has_chart) chips.push(`<span class="chip chart" id="lastChartChip">已联动图表</span>`);
  if (info?.latency != null) chips.push(`<span class="chip latency">${info.latency}s</span>`);
  const div = document.createElement("div");
  div.className = "msg bot";
  div.innerHTML = `<div class="bubble">${esc(a)}</div>` +
    (chips.length ? `<div class="meta">${chips.join("")}</div>` : "") +
    (caliber ? `<div class="caliber-text">口径：${esc(caliber)}</div>` : "");
  history.appendChild(div);
  history.scrollTop = history.scrollHeight;
}

async function ask() {
  const q = input.value.trim();
  if (!q) return;
  input.value = ""; btn.disabled = true;
  addUserMsg(q);
  addTyping();
  status.textContent = "思考中…"; status.className = "avatar-status";
  try {
    const resp = await fetch(API + "/ask", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, dataset: currentDataset }),
    });
    const r = await resp.json();
    removeTyping();
    if (!r.ok) throw new Error(r.error || "接口错误");
    addBotMsg(q, r.answer, r.caliber, {
      verified: r.verified, asset_hit: r.asset_hit,
      has_chart: !!r.chart_spec, latency: r.latency,
    });
    // 联动：chart_spec 驱动地图/柱图/趋势
    if (r.chart_spec) {
      const spec = r.chart_spec;
      if (spec.chart_type === "map" || spec.dimension === "province") {
        renderMap(spec.data, spec.data[0] && spec.data[0].name);
      } else if (spec.chart_type === "line") {
        renderTrend(spec.data);
      } else {
        renderBar(spec.data);
      }
    }
    // 数字人说话
    speak(r.answer);
  } catch (e) {
    removeTyping();
    addBotMsg(q, "（问数失败：" + e.message + "）", "", null);
    status.textContent = "出错了，请重试";
  } finally {
    btn.disabled = false;
    if (!face.classList.contains("talking")) status.textContent = "待命中";
  }
}
btn.addEventListener("click", ask);
input.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(); }
});
document.querySelectorAll("#quickAsks span").forEach(s => {
  s.addEventListener("click", () => { input.value = s.textContent; ask(); });
});

// 对话面板折叠
document.getElementById("chatToggle").addEventListener("click", () => {
  const collapsed = document.body.classList.toggle("chat-collapsed");
  document.getElementById("chatToggle").textContent = collapsed ? "▶" : "◀";
  setTimeout(() => { mapChart.resize(); barChart.resize(); trendChart.resize(); }, 300);
});

// ---------- 数字人 L1：edge-tts + 口型 ----------
let audio = null;
async function speak(text) {
  if (!text) return;
  try {
    const resp = await fetch("http://localhost:8636/tts", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!resp.ok) throw new Error("tts fail");
    const blob = await resp.blob();
    if (audio) audio.pause();
    audio = new Audio(URL.createObjectURL(blob));
    face.classList.add("talking");
    status.textContent = "正在播报…"; status.className = "avatar-status speaking";
    audio.onended = audio.onerror = () => {
      face.classList.remove("talking");
      status.textContent = "待命中 · 点击下方提问"; status.className = "avatar-status";
    };
    audio.play();
  } catch (e) {
    // TTS 不可用不影响问答，只提示
    status.textContent = "（语音不可用，已文本回答）";
    setTimeout(() => { status.textContent = "待命中"; status.className = "avatar-status"; }, 2500);
  }
}
