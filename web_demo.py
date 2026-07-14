#!/usr/bin/env python3
"""Small no-dependency web demo for the 1688 agent."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from typing import Any, Dict

from agent import ShopkeeperAgent


DEFAULT_GOAL = "帮我找适合抖店卖的夏季连衣裙，挑5个靠谱的并铺货"


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>1688 Shopkeeper Agent Demo</title>
  <style>
    :root {
      --bg: #eef1f5;
      --panel: #ffffff;
      --text: #172033;
      --muted: #697386;
      --line: #d8dee8;
      --accent: #0e7490;
      --accent-dark: #155e75;
      --ok: #16803c;
      --warn: #a16207;
      --bad: #b42318;
      --blue: #1d4ed8;
      --code: #111827;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: linear-gradient(#f7f8fa, var(--bg));
      color: var(--text);
    }
    header {
      height: 64px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
      border-bottom: 1px solid var(--line);
      background: rgba(255,255,255,.92);
      backdrop-filter: blur(10px);
      position: sticky;
      top: 0;
      z-index: 2;
    }
    .brand { display: flex; align-items: center; gap: 10px; }
    .mark {
      width: 30px;
      height: 30px;
      border-radius: 7px;
      display: grid;
      place-items: center;
      background: #083344;
      color: #fff;
      font-weight: 800;
      font-size: 13px;
    }
    header strong { font-size: 17px; letter-spacing: 0; }
    header span { color: var(--muted); font-size: 13px; }
    main {
      display: grid;
      grid-template-columns: 380px minmax(0, 1fr);
      min-height: calc(100vh - 64px);
    }
    aside {
      border-right: 1px solid var(--line);
      background: rgba(255,255,255,.76);
      padding: 22px;
    }
    section { padding: 22px; }
    label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 8px; font-weight: 700; }
    textarea {
      width: 100%;
      min-height: 154px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      font-size: 14px;
      line-height: 1.55;
      color: var(--text);
      background: #fff;
      box-shadow: inset 0 1px 2px rgba(15, 23, 42, .04);
    }
    textarea:focus { outline: 2px solid rgba(14,116,144,.18); border-color: var(--accent); }
    button {
      width: 100%;
      height: 42px;
      margin-top: 14px;
      border: 0;
      border-radius: 8px;
      background: var(--accent);
      color: #fff;
      font-weight: 750;
      cursor: pointer;
      box-shadow: 0 8px 18px rgba(14, 116, 144, .22);
    }
    button:hover { background: var(--accent-dark); }
    button:disabled { opacity: .55; cursor: wait; }
    .hint { margin-top: 12px; color: var(--muted); font-size: 13px; line-height: 1.5; }
    .mode-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 10px;
      font-size: 13px;
    }
    .mode-row label {
      display: flex;
      align-items: center;
      gap: 8px;
      height: 34px;
      margin: 0;
      padding: 0 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--text);
      font-weight: 650;
    }
    .mode-row input { accent-color: var(--accent); }
    .summary {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 14px;
    }
    .metric {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
    }
    .metric span { display: block; color: var(--muted); font-size: 12px; }
    .metric strong { display: block; margin-top: 6px; font-size: 20px; }
    .grid {
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: 14px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      min-width: 0;
      box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
    }
    .span-7 { grid-column: span 7; }
    .span-5 { grid-column: span 5; }
    .span-12 { grid-column: span 12; }
    h2 { font-size: 14px; margin: 0 0 14px; color: #334155; }
    .status {
      display: inline-flex;
      align-items: center;
      height: 24px;
      padding: 0 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      background: #e5f7ef;
      color: var(--ok);
    }
    .status.failed, .status.updating { background: #fee2e2; color: var(--bad); }
    .status.pending { background: #eef2ff; color: var(--blue); }
    .task {
      display: grid;
      grid-template-columns: 76px minmax(0, 1fr);
      gap: 12px;
      padding: 12px 0;
      border-top: 1px solid var(--line);
    }
    .task:first-of-type { border-top: 0; }
    .task code, .trace code {
      color: var(--code);
      background: #f3f4f6;
      border-radius: 4px;
      padding: 2px 4px;
      font-size: 12px;
    }
    .task-title { font-size: 14px; line-height: 1.45; }
    .muted { color: var(--muted); font-size: 12px; margin-top: 4px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { text-align: left; padding: 9px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
    th { color: var(--muted); font-weight: 650; }
    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12px;
      line-height: 1.45;
      color: #e5e7eb;
      background: #111827;
      border-radius: 6px;
      padding: 12px;
      max-height: 420px;
      overflow: auto;
    }
    .trace {
      border-top: 1px solid var(--line);
      padding: 12px 0;
      font-size: 13px;
    }
    .trace:first-of-type { border-top: 0; }
    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; }
      aside { border-right: 0; border-bottom: 1px solid var(--line); }
      .span-7, .span-5 { grid-column: span 12; }
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="mark">店</div>
      <div>
        <strong>1688 AI店长</strong>
        <div><span id="header-status">待选品</span></div>
      </div>
    </div>
    <span id="header-mode">演示数据</span>
  </header>
  <main>
    <aside>
      <label for="goal">想卖什么</label>
      <textarea id="goal"></textarea>
      <div class="mode-row">
        <label><input type="radio" name="mode" value="mock" checked /> 演示数据</label>
        <label><input type="radio" name="mode" value="real" /> 真实1688</label>
      </div>
      <button id="run">开始选品</button>
      <div class="hint">
        真实1688需要先配置 AK。铺货默认只做预检查。
      </div>
      <div class="hint" id="workspace"></div>
    </aside>
    <section>
      <div class="summary">
        <div class="metric"><span>选品状态</span><strong id="metric-state">待开始</strong></div>
        <div class="metric"><span>推荐商品</span><strong id="metric-products">0</strong></div>
        <div class="metric"><span>可用店铺</span><strong id="metric-shops">0</strong></div>
      </div>
      <div class="grid">
        <div class="panel span-7">
          <h2>选品结果</h2>
          <div id="products">输入目标后开始选品。</div>
        </div>
        <div class="panel span-5">
          <h2>铺货预检查</h2>
          <div id="publish">尚未执行。</div>
        </div>
        <div class="panel span-7">
          <h2>店铺状态</h2>
          <div id="shops">尚未查询。</div>
        </div>
        <div class="panel span-5">
          <h2>经营建议</h2>
          <div id="advice">等待选品结果。</div>
        </div>
      </div>
    </section>
  </main>
  <script>
    const defaultGoal = "__DEFAULT_GOAL__";
    const goal = document.getElementById("goal");
    const run = document.getElementById("run");
    const productsEl = document.getElementById("products");
    const publishEl = document.getElementById("publish");
    const shopsEl = document.getElementById("shops");
    const adviceEl = document.getElementById("advice");
    const workspaceEl = document.getElementById("workspace");
    const headerStatus = document.getElementById("header-status");
    const headerMode = document.getElementById("header-mode");
    const metricState = document.getElementById("metric-state");
    const metricProducts = document.getElementById("metric-products");
    const metricShops = document.getElementById("metric-shops");
    goal.value = defaultGoal;

    function esc(value) {
      return String(value ?? "").replace(/[&<>"']/g, ch => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }[ch]));
    }

    function statusClass(state) {
      if (state === "done") return "status";
      if (state === "failed" || state === "updating") return "status failed";
      if (state === "pending") return "status pending";
      return "status pending";
    }

    function currentMode() {
      return document.querySelector("input[name='mode']:checked").value;
    }

    function syncModeLabel() {
      const mode = currentMode();
      headerMode.textContent = mode === "mock" ? "演示数据" : "真实1688";
      run.textContent = "开始选品";
    }

    function updateMetrics(payload) {
      const result = payload.result || {};
      const scratch = result.data?.scratch || {};
      const products = scratch.selected_products || [];
      const shops = scratch.shops || [];
      const stateText = result.state === "done" ? "已完成" : (result.state === "updating" ? "需处理" : result.state || "待开始");
      headerStatus.textContent = stateText;
      metricState.textContent = stateText;
      metricProducts.textContent = String(products.length);
      metricShops.textContent = String(shops.filter(shop => shop.is_authorized).length);
    }

    function renderProducts(result) {
      const products = result.data?.scratch?.selected_products || [];
      if (!products.length) {
        productsEl.textContent = "没有找到可推荐商品。";
        return;
      }
      productsEl.innerHTML = `
        <table>
          <thead><tr><th>商品</th><th>价格</th><th>30天销量</th><th>建议</th></tr></thead>
          <tbody>
            ${products.map(item => `
              <tr>
                <td>${esc(item.title)}<div class="muted">${esc(item.category || item.id)}</div></td>
                <td>¥${esc(item.price)}</td>
                <td>${esc(item.stats?.last30DaysSales || "-")}</td>
                <td>${esc((item.reasons || []).join("、") || "-")}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    }

    function renderShops(result) {
      const shops = result.data?.scratch?.shops || [];
      if (!shops.length) {
        shopsEl.textContent = "没有获取到店铺。";
        return;
      }
      shopsEl.innerHTML = shops.map(shop => `
        <div class="trace">
          <div><span class="${statusClass(shop.is_authorized ? "done" : "failed")}">${shop.is_authorized ? "可用" : "异常"}</span></div>
          <div class="task-title">${esc(shop.name)}</div>
          <div class="muted">${esc(shop.channel)} · ${esc(shop.code)}</div>
        </div>
      `).join("");
    }

    function renderPublish(result) {
      const publish = result.data?.scratch?.publish_dry_run;
      if (!publish) {
        publishEl.textContent = result.state === "updating" ? "预检查未完成，请查看错误状态。" : "尚未执行预检查。";
        return;
      }
      publishEl.innerHTML = `
        <div><span class="${statusClass(publish.success ? "done" : "failed")}">${publish.success ? "通过" : "失败"}</span></div>
        <div class="task-title" style="margin-top:10px">${esc(publish.markdown || "")}</div>
        <div class="muted">dry-run only</div>
      `;
    }

    function renderAdvice(result) {
      const advice = result.data?.scratch?.advice || "";
      if (!advice) {
        adviceEl.textContent = result.markdown || "暂无建议。";
        return;
      }
      adviceEl.innerHTML = `<div class="task-title">${esc(advice)}</div>`;
    }

    run.addEventListener("click", async () => {
      const mode = currentMode();
      run.disabled = true;
      run.textContent = "运行中...";
      headerStatus.textContent = "选品中";
      metricState.textContent = "选品中";
      metricProducts.textContent = "0";
      metricShops.textContent = "0";
      productsEl.textContent = "运行中...";
      publishEl.textContent = "运行中...";
      shopsEl.textContent = "运行中...";
      adviceEl.textContent = "运行中...";
      try {
        const response = await fetch("/api/run", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({goal: goal.value, mock: mode === "mock"})
        });
        const payload = await response.json();
        workspaceEl.textContent = "workspace: " + payload.workspace;
        updateMetrics(payload);
        renderProducts(payload.result);
        renderShops(payload.result);
        renderPublish(payload.result);
        renderAdvice(payload.result);
      } catch (error) {
        productsEl.textContent = "运行失败：" + error;
      } finally {
        run.disabled = false;
        syncModeLabel();
      }
    });
    document.querySelectorAll("input[name='mode']").forEach(input => {
      input.addEventListener("change", syncModeLabel);
    });
    syncModeLabel();
  </script>
</body>
</html>
""".replace("__DEFAULT_GOAL__", DEFAULT_GOAL)


class DemoHandler(BaseHTTPRequestHandler):
    workspace = Path(".agent_data_web")

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("web_demo: " + fmt % args + "\n")

    def do_GET(self) -> None:
        if self.path not in ("/", "/index.html"):
            self._send_json({"error": "not found"}, status=404)
            return
        self._send_html(HTML)

    def do_POST(self) -> None:
        if self.path != "/api/run":
            self._send_json({"error": "not found"}, status=404)
            return
        payload = self._read_json()
        goal = str(payload.get("goal") or DEFAULT_GOAL)
        mock_mode = bool(payload.get("mock", True))
        agent = ShopkeeperAgent(workspace=self.workspace, mock_mode=mock_mode)
        result = agent.run(goal, auto_confirm=True)
        self._send_json(
            {
                "workspace": str(self.workspace.resolve()),
                "mode": "mock" if mock_mode else "real",
                "result": result.to_dict(),
                "subagents": self._load_subagents(),
            }
        )

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _load_subagents(self) -> list[Dict[str, Any]]:
        trace_dir = self.workspace / "subagents"
        if not trace_dir.exists():
            return []
        traces = []
        for path in sorted(trace_dir.glob("subagent_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:12]:
            try:
                traces.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                pass
        return traces

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the 1688 agent web demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--workspace", default=".agent_data_web")
    args = parser.parse_args()

    DemoHandler.workspace = Path(args.workspace)
    server = ThreadingHTTPServer((args.host, args.port), DemoHandler)
    print(f"1688 agent web demo: http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
