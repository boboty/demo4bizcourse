"""生成 demo-backup.html：把关键帧按顺序编进一个自包含（无外部依赖）的单文件页面，
现场演示失败时可以直接切过去，不依赖 demo-evidence/ 目录仍然存在。
"""

import base64
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EV = PROJECT_ROOT / "demo-evidence"

FRAMES = [
    {
        "src": EV / "page30" / "counterfactual" / "service-diff.png",
        "title": "反证实验 · 第 1 步：注入的 BUG",
        "caption": "检测到优惠券就跳过 GOLD 判断，直接按券给 200——14 行改动，其余原样。",
    },
    {
        "src": EV / "page30" / "counterfactual" / "generated-suite-output.png",
        "title": "反证实验 · 第 2 步：generated 套件的反应",
        "caption": "同一份 BUG 下，tests/generated/ 四条测试全绿——自洽错误的直接实证。",
    },
    {
        "src": EV / "page30" / "counterfactual" / "verified-suite-output.png",
        "title": "反证实验 · 第 3 步：verified 套件的反应",
        "caption": "同一份 BUG 下，tests/verified/ 挂在 AC-004 那条断言上：assert 0 == 100。",
    },
    {
        "src": EV / "page35" / "independent-review-rejection.png",
        "title": "独立验收 · 驳回过程",
        "caption": "REJECTED，判据可见：AC-004 缺少有效测试证据；独立验收不重跑 pytest，是另一条判断路径。",
    },
]


def data_uri(path: Path) -> str:
    b = path.read_bytes()
    return "data:image/png;base64," + base64.b64encode(b).decode("ascii")


def build():
    slides_html = []
    for i, f in enumerate(FRAMES):
        uri = data_uri(f["src"])
        active = " active" if i == 0 else ""
        slides_html.append(f"""
    <section class="frame{active}" data-index="{i}">
      <div class="frame-head">
        <h2>{f['title']}</h2>
        <p>{f['caption']}</p>
      </div>
      <img src="{uri}" alt="{f['title']}">
    </section>""")

    html = f"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>demo-backup · 关键帧备份</title>
<style>
  :root {{ --bg:#0D1B2E; --fg:#F2F0EA; --accent:#0D8B76; --dim:#8A97A8; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg); font-family: system-ui,-apple-system,'Segoe UI','Microsoft YaHei','PingFang SC',sans-serif; height:100vh; overflow:hidden; }}
  .frame {{ display:none; height:100vh; flex-direction:column; align-items:center; justify-content:center; padding:24px; }}
  .frame.active {{ display:flex; }}
  .frame-head {{ text-align:center; max-width:1100px; margin-bottom:16px; }}
  .frame-head h2 {{ margin:0 0 6px; font-size:22px; color:var(--fg); }}
  .frame-head p {{ margin:0; font-size:15px; color:var(--dim); }}
  .frame img {{ max-width:92vw; max-height:74vh; border-radius:10px; box-shadow:0 20px 60px rgba(0,0,0,.45); }}
  .nav {{ position:fixed; bottom:18px; left:0; right:0; display:flex; align-items:center; justify-content:center; gap:16px; }}
  .nav button {{ background:#16273E; color:var(--fg); border:1px solid #2A3B52; border-radius:8px; padding:8px 16px; font-size:14px; cursor:pointer; }}
  .nav button:hover {{ border-color: var(--accent); }}
  .counter {{ font-size:13px; color:var(--dim); min-width:60px; text-align:center; }}
  .hint {{ position:fixed; top:14px; right:18px; font-size:12px; color:var(--dim); }}
</style>
</head>
<body>
{''.join(slides_html)}
<div class="hint">← → 或点击按钮切换 · 共 {len(FRAMES)} 帧</div>
<div class="nav">
  <button id="prev">← 上一帧</button>
  <span class="counter" id="counter">1 / {len(FRAMES)}</span>
  <button id="next">下一帧 →</button>
</div>
<script>
  var frames = document.querySelectorAll('.frame');
  var idx = 0;
  function show(i) {{
    idx = (i + frames.length) % frames.length;
    frames.forEach(function(f, j) {{ f.classList.toggle('active', j === idx); }});
    document.getElementById('counter').textContent = (idx+1) + ' / ' + frames.length;
  }}
  document.getElementById('prev').onclick = function() {{ show(idx - 1); }};
  document.getElementById('next').onclick = function() {{ show(idx + 1); }};
  document.addEventListener('keydown', function(e) {{
    if (e.key === 'ArrowRight') show(idx + 1);
    if (e.key === 'ArrowLeft') show(idx - 1);
  }});
</script>
</body>
</html>
"""
    out = PROJECT_ROOT / "demo-backup.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({len(html)} chars, {len(FRAMES)} frames)")


if __name__ == "__main__":
    build()
