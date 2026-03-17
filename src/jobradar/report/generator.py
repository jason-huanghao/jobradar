"""HTML report generator — produces a self-contained single-file report.

All CSS and JS are inlined. Job data is embedded as JSON.
No server required — the output file opens directly in any browser.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def generate_report(
    jobs: list[dict[str, Any]],
    *,
    profile_name: str = "",
    generated_at: datetime | None = None,
    output_path: Path | None = None,
) -> Path:
    """Generate a self-contained HTML report from scored jobs.

    Args:
        jobs: List of dicts with keys: id, title, company, location, score,
              source, url, date_posted, reasoning, breakdown (dict)
        profile_name: Candidate name shown in header
        generated_at: Report timestamp (default: now)
        output_path: Where to write the file

    Returns:
        Path to the generated HTML file
    """
    if generated_at is None:
        generated_at = datetime.utcnow()

    if output_path is None:
        report_dir = Path.home() / ".jobradar" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        h = hashlib.sha256(f"{profile_name}{generated_at.date()}".encode()).hexdigest()[:8]
        output_path = report_dir / f"report-{h}.html"

    jobs_json = json.dumps(jobs, ensure_ascii=False, default=str)
    html = _render_html(jobs_json, profile_name, generated_at)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def jobs_from_db(db_path: Path, min_score: float = 0.0) -> list[dict[str, Any]]:
    """Load scored jobs from SQLite DB into report-ready dicts."""
    from sqlmodel import select
    from ..storage.db import get_session, init_db
    from ..storage.models import Job, ScoredJobRecord

    init_db(db_path)
    results = []
    with next(get_session(db_path)) as session:
        scored = session.exec(select(ScoredJobRecord)).all()
        job_map = {j.id: j for j in session.exec(select(Job)).all()}
        for s in scored:
            if s.overall < min_score:
                continue
            j = job_map.get(s.job_id)
            if not j:
                continue
            results.append({
                "id": s.job_id,
                "title": j.title,
                "company": j.company or "",
                "location": j.location or "",
                "score": round(s.overall, 1),
                "source": j.source,
                "url": j.url or "",
                "date_posted": str(j.date_posted or ""),
                "reasoning": s.reasoning or "",
                "breakdown": {
                    "skills_match":    round(s.skills_match or 0, 1),
                    "seniority_fit":   round(s.seniority_fit or 0, 1),
                    "location_fit":    round(s.location_fit or 0, 1),
                    "language_fit":    round(s.language_fit or 0, 1),
                    "visa_friendly":   round(s.visa_friendly or 0, 1),
                    "growth_potential":round(s.growth_potential or 0, 1),
                },
            })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def _render_html(jobs_json: str, profile_name: str, generated_at: datetime) -> str:
    ts = generated_at.strftime("%Y-%m-%d %H:%M UTC")
    title = ("JobRadar \u2014 " + profile_name) if profile_name else "JobRadar Report"
    subtitle = (" \u00b7 " + profile_name) if profile_name else ""
    # Use plain string (not f-string) so JS braces don't need escaping
    return _HTML_TEMPLATE.replace("__TITLE__", title) \
                         .replace("__SUBTITLE__", subtitle) \
                         .replace("__TS__", ts) \
                         .replace("__JOBS_JSON__", jobs_json)


# Static HTML template — substitution tokens: __TITLE__ __SUBTITLE__ __TS__ __JOBS_JSON__
_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f5;color:#1a1a1a;font-size:15px}
header{background:#1a1a1a;color:#fff;padding:20px 32px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
header h1{font-size:20px;font-weight:600;letter-spacing:-.3px}
header .meta{font-size:13px;color:#aaa}
.toolbar{background:#fff;border-bottom:1px solid #e5e5e5;padding:14px 32px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.toolbar input{padding:7px 12px;border:1px solid #ddd;border-radius:6px;font-size:14px;width:220px;outline:none}
.toolbar input:focus{border-color:#555}
.toolbar select{padding:7px 10px;border:1px solid #ddd;border-radius:6px;font-size:14px;background:#fff;cursor:pointer}
.toolbar .count{margin-left:auto;font-size:13px;color:#666}
.summary{padding:20px 32px;display:flex;gap:16px;flex-wrap:wrap}
.stat{background:#fff;border:1px solid #e5e5e5;border-radius:8px;padding:14px 20px;min-width:120px}
.stat .n{font-size:28px;font-weight:700;line-height:1}
.stat .l{font-size:12px;color:#666;margin-top:4px}
.jobs{padding:0 32px 40px;display:grid;gap:12px}
.card{background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:18px 20px;cursor:pointer;transition:box-shadow .15s}
.card:hover{box-shadow:0 2px 12px rgba(0,0,0,.08)}
.card-top{display:flex;align-items:flex-start;gap:12px}
.score-badge{min-width:48px;height:48px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:700;flex-shrink:0}
.score-hi{background:#dcfce7;color:#15803d}
.score-mid{background:#fef9c3;color:#854d0e}
.score-lo{background:#fee2e2;color:#b91c1c}
.card-info{flex:1;min-width:0}
.card-info h3{font-size:15px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.card-info .sub{font-size:13px;color:#555;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tags{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.tag{font-size:11px;padding:2px 8px;border-radius:20px;background:#f0f0f0;color:#444}
.tag.src{background:#e0f2fe;color:#0369a1}
.detail{display:none;margin-top:14px;padding-top:14px;border-top:1px solid #f0f0f0}
.card.open .detail{display:block}
.breakdown{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.dim{font-size:12px;background:#f8f8f8;border:1px solid #eee;border-radius:6px;padding:4px 10px}
.dim span{font-weight:600}
.reasoning{font-size:13px;color:#444;line-height:1.6}
.apply-link{display:inline-block;margin-top:10px;font-size:13px;color:#1d4ed8;text-decoration:none;font-weight:500}
.apply-link:hover{text-decoration:underline}
@media(max-width:600px){
  header,.toolbar,.summary,.jobs{padding-left:16px;padding-right:16px}
  .toolbar input{width:100%}
}
</style>
</head>
<body>
<header>
  <h1>&#x26A1; JobRadar__SUBTITLE__</h1>
  <span class="meta">Generated __TS__</span>
</header>
<div class="toolbar">
  <input type="text" id="q" placeholder="Search title, company, location\u2026" oninput="filter()">
  <select id="src" onchange="filter()"><option value="">All sources</option></select>
  <select id="min" onchange="filter()">
    <option value="0">All scores</option>
    <option value="6">6+ only</option>
    <option value="7" selected>7+ only</option>
    <option value="8">8+ only</option>
    <option value="9">9+ only</option>
  </select>
  <span class="count" id="count"></span>
</div>
<div class="summary" id="summary"></div>
<div class="jobs" id="jobs"></div>
<script>
const JOBS = __JOBS_JSON__;
const DIM_LABELS = {
  skills_match:"Skills",seniority_fit:"Seniority",location_fit:"Location",
  language_fit:"Language",visa_friendly:"Visa",growth_potential:"Growth"
};
function scoreCls(s){return s>=8?"score-hi":s>=6?"score-mid":"score-lo"}
function buildSummary(){
  const el=document.getElementById("summary");
  const hi=JOBS.filter(j=>j.score>=8).length;
  const mid=JOBS.filter(j=>j.score>=6&&j.score<8).length;
  const srcs=new Set(JOBS.map(j=>j.source)).size;
  el.innerHTML=[
    ["Total",JOBS.length],["Score 8+",hi],["Score 6\u20138",mid],["Sources",srcs]
  ].map(([l,n])=>`<div class="stat"><div class="n">${n}</div><div class="l">${l}</div></div>`).join("");
}
function buildSourceFilter(){
  const sel=document.getElementById("src");
  const srcs=[...new Set(JOBS.map(j=>j.source))].sort();
  srcs.forEach(s=>{const o=document.createElement("option");o.value=s;o.textContent=s;sel.appendChild(o);});
}
function renderJobs(jobs){
  const el=document.getElementById("jobs");
  document.getElementById("count").textContent=jobs.length+" jobs";
  el.innerHTML=jobs.map(j=>{
    const bd=Object.entries(j.breakdown||{})
      .map(([k,v])=>`<div class="dim">${DIM_LABELS[k]||k}: <span>${v}</span></div>`).join("");
    return `<div class="card" id="c_${j.id}" onclick="toggle(this)">
      <div class="card-top">
        <div class="score-badge ${scoreCls(j.score)}">${j.score}</div>
        <div class="card-info">
          <h3>${esc(j.title)}</h3>
          <div class="sub">${esc(j.company)}${j.location?" \u00b7 "+esc(j.location):""}</div>
          <div class="tags">
            <span class="tag src">${esc(j.source)}</span>
            ${j.date_posted?`<span class="tag">${j.date_posted.slice(0,10)}</span>`:""}
          </div>
        </div>
      </div>
      <div class="detail">
        ${bd?`<div class="breakdown">${bd}</div>`:""}
        ${j.reasoning?`<div class="reasoning">${esc(j.reasoning)}</div>`:""}
        ${j.url?`<a class="apply-link" href="${j.url}" target="_blank" rel="noopener">View job \u2192</a>`:""}
      </div>
    </div>`;
  }).join("");
}
function toggle(el){el.classList.toggle("open")}
function esc(s){const d=document.createElement("div");d.textContent=s||"";return d.innerHTML}
function filter(){
  const q=document.getElementById("q").value.toLowerCase();
  const src=document.getElementById("src").value;
  const min=parseFloat(document.getElementById("min").value)||0;
  const visible=JOBS.filter(j=>{
    if(j.score<min)return false;
    if(src&&j.source!==src)return false;
    if(q&&![j.title,j.company,j.location].join(" ").toLowerCase().includes(q))return false;
    return true;
  });
  renderJobs(visible);
}
buildSummary();buildSourceFilter();filter();
</script>
</body>
</html>"""
