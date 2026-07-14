import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from agent.core.fsm import PlanModeFSM
from agent_cli import build_runtime, create_planner


HTML = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>1688 Agent Shopkeeper</title>
<style>
body{margin:0;font-family:Arial,"Microsoft YaHei",sans-serif;background:#f6f7f9;color:#18212f}
.shell{max-width:1120px;margin:0 auto;padding:28px}
.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}
h1{font-size:26px;margin:0}.panel{background:#fff;border:1px solid #e1e5ea;border-radius:8px;padding:18px;margin-bottom:14px}
.row{display:flex;gap:10px}.row>*{flex:1}input{height:42px;border:1px solid #cbd3dc;border-radius:6px;padding:0 12px;font-size:15px}
button{height:44px;border:0;border-radius:6px;background:#1677ff;color:#fff;font-weight:600;padding:0 18px;cursor:pointer;flex:0 0 auto}
label{display:flex;align-items:center;gap:8px;flex:0 0 auto}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.card{border:1px solid #e1e5ea;border-radius:8px;padding:12px;background:#fff}.muted{color:#667085}.pill{display:inline-block;background:#eef4ff;color:#175cd3;border-radius:999px;padding:3px 8px;font-size:12px}
pre{white-space:pre-wrap;background:#111827;color:#e5e7eb;border-radius:8px;padding:12px;max-height:260px;overflow:auto}
</style>
</head>
<body>
<main class="shell">
<div class="top"><h1>1688 智能选品铺货台</h1><span class="pill">Agent Runtime</span></div>
<section class="panel">
<div class="row">
<input id="goal" value="帮我找适合抖店卖的夏季连衣裙，挑5个靠谱的并铺货" />
<label><input id="mock" type="checkbox" checked /> Mock</label>
<button onclick="run()">开始</button>
</div>
</section>
<section class="panel"><h2>推荐商品</h2><div id="products" class="grid"></div></section>
<section class="panel"><h2>店铺与铺货结果</h2><div id="publish" class="muted">等待执行</div></section>
<section class="panel"><h2>执行摘要</h2><pre id="trace">暂无</pre></section>
</main>
<script>
async function run(){
  const goal=document.getElementById('goal').value;
  const mock=document.getElementById('mock').checked;
  document.getElementById('trace').textContent='执行中...';
  const res=await fetch('/api/run',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({goal,mock})});
  const data=await res.json();
  const products=((data.tasks||[]).find(t=>t.tool==='search_products')?.result?.products)||[];
  document.getElementById('products').innerHTML=products.map(p=>`<div class="card"><b>${p.title}</b><p class="muted">价格 ¥${p.price} | 销量 ${p.sales||'-'} | 评分 ${p.rating||'-'}</p></div>`).join('');
  const pub=(data.tasks||[]).find(t=>t.tool==='publish_dry_run'||t.tool==='request_publish_approval');
  document.getElementById('publish').textContent=pub&&pub.result?JSON.stringify(pub.result):'未生成铺货结果';
  document.getElementById('trace').textContent=JSON.stringify({plan_id:data.id,status:data.status,tasks:data.tasks.map(t=>({title:t.title,status:t.status,tool:t.tool}))},null,2);
}
</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if urlparse(self.path).path != "/":
            self.send_error(404)
            return
        self._send(200, HTML, "text/html; charset=utf-8")

    def do_POST(self):
        if urlparse(self.path).path != "/api/run":
            self.send_error(404)
            return
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        runtime = build_runtime(".agent_data_web", bool(payload.get("mock", True)))
        plan = create_planner(False).create_plan(payload["goal"], runtime.memory.search(payload["goal"]))
        result = PlanModeFSM(runtime.store, runtime.worker, runtime.hooks).run(plan, auto_confirm=True)
        self._send(200, json.dumps(result.to_dict(), ensure_ascii=False), "application/json; charset=utf-8")

    def _send(self, code, body, content_type):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("Web demo: http://127.0.0.1:8765")
    server.serve_forever()


if __name__ == "__main__":
    main()
