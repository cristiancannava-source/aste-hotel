"""Dashboard a 3 tab (Alberghi / Roma / Sardegna).
Legge data_hotel.json e data_zone.json e genera dashboard.html (o site/index.html).
Attive in evidenza in cima, scadute in fondo a ogni tab.

Uso locale:   python -m aste_hotel.dashboard
"""
import json, webbrowser
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent.parent
HOTEL_JSON = BASE / "data_hotel.json"
ZONE_JSON = BASE / "data_zone.json"
OUT = BASE / "dashboard.html"

ZONE_NOMI = {
    "pvp_centro_storico": "Centro Storico", "pvp_prati": "Prati",
    "pvp_borgo": "Borgo", "pvp_mazzini": "Mazzini",
    "pvp_della_vittoria": "Della Vittoria", "pvp_degli_eroi": "Degli Eroi",
    "pvp_parioli": "Parioli", "pvp_flaminio": "Flaminio",
    "pvp_trastevere": "Trastevere", "pvp_corso_francia": "Corso Francia",
    "pvp_vigna_clara": "Vigna Clara", "pvp_fleming": "Fleming",
    "pvp_ponte_milvio": "Ponte Milvio", "pvp_trieste": "Trieste",
    "pvp_salario": "Salario", "pvp_bologna": "Bologna",
    "pvp_porto_cervo": "Porto Cervo",
}

def carica_json(path):
    p = Path(path)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []

def prepara(dati, is_zona):
    oggi = date.today().isoformat()
    out = []
    for d in dati:
        sd = str(d.get("sale_date") or "")[:10]
        d["_attiva"] = (not sd) or (sd >= oggi)
        d["_zona"] = ZONE_NOMI.get(d.get("source", ""), "") if is_zona else ""
        out.append(d)
    attive = sorted([x for x in out if x["_attiva"]], key=lambda x: str(x.get("sale_date") or "9999"))
    scadute = sorted([x for x in out if not x["_attiva"]], key=lambda x: str(x.get("sale_date") or ""), reverse=True)
    return attive + scadute

def genera_html(hotel, zone):
    tab_hotel = prepara(hotel, False)
    zone_roma = prepara([d for d in zone if d.get("source") != "pvp_porto_cervo"], True)
    zone_sar = prepara([d for d in zone if d.get("source") == "pvp_porto_cervo"], True)
    html = TEMPLATE
    html = html.replace("__HOTEL__", json.dumps(tab_hotel, ensure_ascii=False))
    html = html.replace("__ROMA__", json.dumps(zone_roma, ensure_ascii=False))
    html = html.replace("__SARDEGNA__", json.dumps(zone_sar, ensure_ascii=False))
    html = html.replace("__OGGI__", date.today().isoformat())
    return html

def main():
    html = genera_html(carica_json(HOTEL_JSON), carica_json(ZONE_JSON))
    OUT.write_text(html, encoding="utf-8")
    print(f"Dashboard generata: {OUT}")
    webbrowser.open(f"file://{OUT}")

TEMPLATE = r"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aste - Dashboard</title>
<style>
:root{--bg:#ffffff;--card:#f5f6f8;--bord:#e2e5ea;--txt:#1a1d26;--mut:#6b7280;--acc:#1558d6;--green:#0a7d4b;--amber:#b45309;}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;}
header{padding:22px 28px 6px;}
h1{margin:0;font-size:21px;font-weight:650;}
.sub{color:var(--mut);font-size:13px;margin-top:3px;}
.tabs{display:flex;gap:4px;padding:14px 28px 0;border-bottom:1px solid var(--bord);flex-wrap:wrap;}
.tab{padding:10px 18px;cursor:pointer;font-size:14px;font-weight:600;color:var(--mut);border-bottom:2px solid transparent;user-select:none;}
.tab:hover{color:var(--txt);}
.tab.active{color:var(--acc);border-bottom-color:var(--acc);}
.tab .badge{display:inline-block;margin-left:6px;padding:1px 7px;border-radius:999px;background:var(--card);font-size:11px;color:var(--mut);}
.bar{display:flex;flex-wrap:wrap;gap:10px;padding:14px 28px;align-items:center;}
.bar input{background:var(--card);border:1px solid var(--bord);color:var(--txt);padding:8px 10px;border-radius:8px;font-size:13px;}
.wrap{padding:0 28px 40px;overflow-x:auto;}
table{width:100%;border-collapse:collapse;font-size:13px;}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--bord);vertical-align:top;}
th{color:var(--mut);font-weight:600;cursor:pointer;position:sticky;top:0;background:var(--bg);white-space:nowrap;}
tr:hover td{background:#f0f2f5;}
.price{font-weight:650;color:var(--green);white-space:nowrap;}
.src,.zona{display:inline-block;padding:2px 8px;border-radius:999px;background:var(--card);border:1px solid var(--bord);font-size:11px;color:var(--mut);}
.zona{color:var(--acc);border-color:var(--acc);}
a.det{color:var(--acc);text-decoration:none;}
a.det:hover{text-decoration:underline;}
.muted{color:var(--mut);}
.scaduta td{opacity:.5;}
.sep td{background:#f0f2f5;color:var(--amber);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;padding:8px 12px;}
.count{color:var(--mut);font-size:13px;margin-left:auto;}
.title-cell{max-width:480px;}
</style></head>
<body>
<header><h1>Aste — Dashboard</h1>
<div class="sub">aggiornata al __OGGI__</div></header>
<div class="tabs">
  <div class="tab active" data-tab="hotel">Aste Alberghi<span class="badge" id="b-hotel"></span></div>
  <div class="tab" data-tab="roma">Aste Roma<span class="badge" id="b-roma"></span></div>
  <div class="tab" data-tab="sardegna">Aste Sardegna<span class="badge" id="b-sardegna"></span></div>
</div>
<div class="bar">
  <input type="text" id="q" placeholder="Cerca...">
  <input type="text" id="pmin" placeholder="Prezzo min" style="width:110px">
  <input type="text" id="pmax" placeholder="Prezzo max" style="width:110px">
  <span class="count" id="count"></span>
</div>
<div class="wrap"><table>
<thead><tr id="thead"></tr></thead>
<tbody id="tb"></tbody></table></div>
<script>
const DATA = {hotel: __HOTEL__, roma: __ROMA__, sardegna: __SARDEGNA__};
let tab = "hotel", sortK = null, sortDir = 1;
document.getElementById("b-hotel").textContent = DATA.hotel.length;
document.getElementById("b-roma").textContent = DATA.roma.length;
document.getElementById("b-sardegna").textContent = DATA.sardegna.length;
function cols(){
  const base = [["title","Titolo"],["price","Prezzo base"],["city","Citta"]];
  if(tab!=="hotel") base.push(["_zona","Zona"]);
  base.push(["tribunale","Tribunale"],["sale_date","Vendita"],["source","Fonte"],["",""]);
  return base;
}
function fmtPrice(p){if(p==null)return '<span class="muted">n/d</span>';return '<span class="price">'+Number(p).toLocaleString('it-IT',{maximumFractionDigits:0})+' &euro;</span>';}
function fmtDate(s){if(!s)return '<span class="muted">&mdash;</span>';const d=String(s).slice(0,10);return d.split('-').reverse().join('/');}
function render(){
  const q=document.getElementById("q").value.toLowerCase();
  const pmin=parseFloat(document.getElementById("pmin").value.replace(/\./g,''))||null;
  const pmax=parseFloat(document.getElementById("pmax").value.replace(/\./g,''))||null;
  let rows=DATA[tab].filter(d=>{
    if(pmin!=null&&(d.price==null||d.price<pmin))return false;
    if(pmax!=null&&(d.price==null||d.price>pmax))return false;
    if(q){const b=((d.title||'')+' '+(d.city||'')+' '+(d.tribunale||'')+' '+(d._zona||'')).toLowerCase();if(!b.includes(q))return false;}
    return true;
  });
  if(sortK){rows=[...rows].sort((a,b)=>{let x=a[sortK],y=b[sortK];if(x==null)x='';if(y==null)y='';if(typeof x==='number'||typeof y==='number'){x=+x||0;y=+y||0;}return(x<y?-1:x>y?1:0)*sortDir;});}
  const co=cols();
  document.getElementById("thead").innerHTML=co.map(c=>'<th data-k="'+c[0]+'">'+c[1]+'</th>').join('');
  document.querySelectorAll("#thead th").forEach(th=>{th.onclick=()=>{const k=th.dataset.k;if(!k)return;if(sortK===k)sortDir*=-1;else{sortK=k;sortDir=1;}render();};});
  const attive=rows.filter(r=>r._attiva), scadute=rows.filter(r=>!r._attiva);
  document.getElementById("count").textContent=rows.length+" lotti ("+attive.length+" attivi)";
  const tb=document.getElementById("tb");tb.innerHTML="";
  function riga(d){
    const tr=document.createElement("tr");if(!d._attiva)tr.className="scaduta";
    let h='<td class="title-cell">'+(d.title||'')+'</td>'+'<td>'+fmtPrice(d.price)+'</td>'+'<td>'+(d.city||'')+'</td>';
    if(tab!=="hotel")h+='<td>'+(d._zona?'<span class="zona">'+d._zona+'</span>':'')+'</td>';
    h+='<td>'+(d.tribunale||'<span class="muted">&mdash;</span>')+'</td>'+'<td>'+fmtDate(d.sale_date)+'</td>'+'<td><span class="src">'+(d.source||'').replace('pvp_','')+'</span></td>'+'<td>'+(d.url?'<a class="det" href="'+d.url+'" target="_blank">apri &rsaquo;</a>':'')+'</td>';
    tr.innerHTML=h;return tr;
  }
  attive.forEach(d=>tb.appendChild(riga(d)));
  if(scadute.length){
    const sep=document.createElement("tr");sep.className="sep";
    sep.innerHTML='<td colspan="'+co.length+'">Aste scadute ('+scadute.length+')</td>';
    tb.appendChild(sep);scadute.forEach(d=>tb.appendChild(riga(d)));
  }
}
document.querySelectorAll(".tab").forEach(t=>{t.onclick=()=>{
  document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
  t.classList.add("active");tab=t.dataset.tab;sortK=null;render();
};});
["q","pmin","pmax"].forEach(id=>document.getElementById(id).addEventListener("input",render));
render();
</script></body></html>"""

if __name__ == "__main__":
    main()
