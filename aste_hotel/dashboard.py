"""Dashboard locale: genera dashboard.html con tutti gli alberghi e lo apre nel browser."""
from __future__ import annotations
import json, sqlite3, webbrowser
from datetime import date
from pathlib import Path

DB = Path(__file__).parent.parent / "data.sqlite"
OUT = Path(__file__).parent.parent / "dashboard.html"

def carica():
    if not DB.exists():
        return []
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT source, title, price, city, province, tribunale, "
        "sale_date, url, first_seen FROM listings ORDER BY first_seen DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def genera_html(dati):
    oggi = date.today().isoformat()
    payload = json.dumps(dati, ensure_ascii=False)
    return _T.replace("__DATI__", payload).replace("__OGGI__", oggi).replace("__N__", str(len(dati)))

_T = r"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aste Hotel - Dashboard</title>
<style>
:root{--bg:#0f1116;--card:#1a1d27;--bord:#2a2e3c;--txt:#e6e8ee;--mut:#9aa0b0;--acc:#4da3ff;--green:#36c98d;}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;}
header{padding:24px 28px 8px;}
h1{margin:0;font-size:22px;font-weight:650;}
.sub{color:var(--mut);font-size:13px;margin-top:4px;}
.bar{display:flex;flex-wrap:wrap;gap:10px;padding:16px 28px;align-items:center;}
.bar input,.bar select{background:var(--card);border:1px solid var(--bord);color:var(--txt);padding:8px 10px;border-radius:8px;font-size:13px;}
.bar input[type=text]{min-width:180px;}
.chip{display:flex;align-items:center;gap:6px;color:var(--mut);font-size:13px;}
.wrap{padding:0 28px 40px;}
table{width:100%;border-collapse:collapse;font-size:13px;}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--bord);vertical-align:top;}
th{color:var(--mut);font-weight:600;cursor:pointer;user-select:none;position:sticky;top:0;background:var(--bg);white-space:nowrap;}
th:hover{color:var(--txt);}
tr:hover td{background:#161922;}
.price{font-weight:650;color:var(--green);white-space:nowrap;}
.src{display:inline-block;padding:2px 8px;border-radius:999px;background:var(--card);border:1px solid var(--bord);font-size:11px;color:var(--mut);}
a.det{color:var(--acc);text-decoration:none;}
a.det:hover{text-decoration:underline;}
.muted{color:var(--mut);}
.count{color:var(--mut);font-size:13px;margin-left:auto;}
.title-cell{max-width:520px;}
</style></head>
<body>
<header><h1>🏨 Aste Hotel — Dashboard</h1>
<div class="sub">__N__ lotti raccolti · aggiornato al __OGGI__</div></header>
<div class="bar">
<input type="text" id="q" placeholder="Cerca (titolo, citta, tribunale)...">
<select id="src"><option value="">Tutte le fonti</option></select>
<input type="text" id="pmin" placeholder="Prezzo min" style="width:110px">
<input type="text" id="pmax" placeholder="Prezzo max" style="width:110px">
<label class="chip"><input type="checkbox" id="fut"> Solo aste aperte</label>
<span class="count" id="count"></span>
</div>
<div class="wrap"><table>
<thead><tr>
<th data-k="title">Titolo</th><th data-k="price">Prezzo base</th>
<th data-k="city">Citta</th><th data-k="province">Prov</th>
<th data-k="tribunale">Tribunale</th><th data-k="sale_date">Data vendita</th>
<th data-k="source">Fonte</th><th></th>
</tr></thead><tbody id="tb"></tbody></table></div>
<script>
const DATA=__DATI__; const OGGI="__OGGI__";
let sortK="first_seen",sortDir=-1;
const srcSel=document.getElementById("src");
[...new Set(DATA.map(d=>d.source))].sort().forEach(s=>{const o=document.createElement("option");o.value=s;o.textContent=s;srcSel.appendChild(o);});
function fmtPrice(p){if(p==null)return '<span class="muted">n/d</span>';return '<span class="price">'+p.toLocaleString('it-IT',{maximumFractionDigits:0})+' &euro;</span>';}
function fmtDate(s){if(!s)return '<span class="muted">&mdash;</span>';const d=String(s).slice(0,10);return d.split('-').reverse().join('/');}
function render(){
const q=document.getElementById("q").value.toLowerCase();
const src=srcSel.value;
const pmin=parseFloat(document.getElementById("pmin").value.replace(/\./g,''))||null;
const pmax=parseFloat(document.getElementById("pmax").value.replace(/\./g,''))||null;
const fut=document.getElementById("fut").checked;
let rows=DATA.filter(d=>{
if(src&&d.source!==src)return false;
if(pmin!=null&&(d.price==null||d.price<pmin))return false;
if(pmax!=null&&(d.price==null||d.price>pmax))return false;
if(fut&&d.sale_date&&String(d.sale_date).slice(0,10)<OGGI)return false;
if(q){const b=((d.title||'')+' '+(d.city||'')+' '+(d.tribunale||'')).toLowerCase();if(!b.includes(q))return false;}
return true;});
rows.sort((a,b)=>{let x=a[sortK],y=b[sortK];if(x==null)x='';if(y==null)y='';if(typeof x==='number'||typeof y==='number'){x=+x||0;y=+y||0;}return (x<y?-1:x>y?1:0)*sortDir;});
document.getElementById("count").textContent=rows.length+" lotti";
const tb=document.getElementById("tb");tb.innerHTML="";
for(const d of rows){const tr=document.createElement("tr");
tr.innerHTML='<td class="title-cell">'+(d.title||'')+'</td>'+'<td>'+fmtPrice(d.price)+'</td>'+'<td>'+(d.city||'')+'</td>'+'<td>'+(d.province||'')+'</td>'+'<td>'+(d.tribunale||'<span class="muted">&mdash;</span>')+'</td>'+'<td>'+fmtDate(d.sale_date)+'</td>'+'<td><span class="src">'+d.source+'</span></td>'+'<td>'+(d.url?'<a class="det" href="'+d.url+'" target="_blank">apri &rsaquo;</a>':'')+'</td>';
tb.appendChild(tr);}}
document.querySelectorAll("th[data-k]").forEach(th=>{th.addEventListener("click",()=>{const k=th.dataset.k;if(sortK===k)sortDir*=-1;else{sortK=k;sortDir=1;}render();});});
["q","src","pmin","pmax","fut"].forEach(id=>{document.getElementById(id).addEventListener("input",render);});
render();
</script></body></html>"""

def main():
    dati = carica()
    OUT.write_text(genera_html(dati), encoding="utf-8")
    print(f"Dashboard generata: {OUT}  ({len(dati)} lotti)")
    webbrowser.open(f"file://{OUT}")

if __name__ == "__main__":
    main()
