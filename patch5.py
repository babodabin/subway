#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v5 -> v6 : 노선 확장(627역 26노선) + 게임 모드 4종
"""
import sys, json, re

SRC = "/tmp/base_v5.html"
DST = "/tmp/game_v6.html"

s = open(SRC, encoding="utf-8").read()
newD = json.load(open("/tmp/newD.json", encoding="utf-8"))
newDT = json.load(open("/tmp/newDT.json", encoding="utf-8"))
newLL = json.load(open("/tmp/newLL.json", encoding="utf-8"))
meta = json.load(open("/tmp/newMeta.json", encoding="utf-8"))

orig = len(s)
J = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))

# ---------- 1. D 교체 ----------
m = re.search(r'const D=(\{.*?\});\s*\n/\* ---------- 역별 실제 위경도', s, re.S)
if not m:
    print("FAIL: D 블록 못 찾음"); sys.exit(1)
s = s[:m.start(1)] + J(newD) + s[m.end(1):]

# ---------- 2. LL 교체 ----------
m = re.search(r'const LL=(\[.*?\]);\nfunction haversineKm', s, re.S)
if not m:
    print("FAIL: LL 블록 못 찾음"); sys.exit(1)
s = s[:m.start(1)] + J(newLL) + s[m.end(1):]

# ---------- 3. DT(토·일 OD) 교체 ----------
m = re.search(r'const DT=(\{.*?\});\n/\* ---------- 기본값', s, re.S)
if not m:
    print("FAIL: DT 블록 못 찾음"); sys.exit(1)
oldDT = json.loads(m.group(1))
oldDT["sat"] = newDT["sat"]; oldDT["sun"] = newDT["sun"]
s = s[:m.start(1)] + J(oldDT) + s[m.end(1):]

reps = []

# ---------- 4. COL / SPD / ORDER / 노선이름 ----------
COL = {'1':'#0052A4','2':'#00A84D','3':'#EF7C1C','4':'#00A5DE','5':'#996CAC',
       '6':'#CD7C2F','7':'#747F00','8':'#E6186C','9':'#BDB092'}
COL.update(meta["col"])
SPD = {'1':26,'2':32.5,'3':34,'4':35.9,'5':32.8,'6':29.5,'7':32.3,'8':22.4,'9':30.5}
SPD.update(meta["spd"])
NAME = {k: k+"호선" for k in "123456789"}
NAME.update({"신분당":"신분당선","경의중앙":"경의중앙선","경춘":"경춘선","분당":"분당선",
             "수인":"수인선","경강":"경강선","서해":"서해선","우이신설":"우이신설선",
             "신림":"신림선","김포":"김포골드라인","인천1":"인천1호선","인천2":"인천2호선",
             "공항":"공항철도","에버라인":"에버라인","의정부":"의정부경전철",
             "자기부상":"자기부상철도","진접":"진접선"})
NEW_ORDER = ['9','2','5','7','3','4','6','1','8'] + meta["newKeys"]

reps.append((
"""const COL={'1':'#0052A4','2':'#00A84D','3':'#EF7C1C','4':'#00A5DE','5':'#996CAC',
 '6':'#CD7C2F','7':'#747F00','8':'#E6186C','9':'#BDB092'};
const SPD={'1':26,'2':32.5,'3':34,'4':35.9,'5':32.8,'6':29.5,'7':32.3,'8':22.4,'9':30.5};
const EXP9=32; // 9호선 급행 km/h(정차역만)
const ORDER=['9','2','5','7','3','4','6','1','8'];   // 여는 순서""",
f"""const COL={J(COL)};
const SPD={J(SPD)};
const NAME={J(NAME)};                 // 노선 표시 이름
const CORE=['1','2','3','4','5','6','7','8','9'];   // 1~9호선
const EXTRA={J(meta["newKeys"])};     // 확장 노선
const EXP9=32; // 9호선 급행 km/h(정차역만)
const ORDER={J(NEW_ORDER)};   // 여는 순서
let mode='core';   // 'single' 단일노선 | 'core' 1~9호선 | 'all' 전체노선 | 'grow' 한 노선부터 전체확장"""
))

# ---------- 5. 노선 이름 표기: L+'호선' -> NAME[L] ----------
reps.append((
"""    const pills=ls.map(L=>`<span class="pill" style="background:${COL[L]}${open.has(L)?'':';opacity:.3'}">${L}호선</span>`).join('');""",
"""    const pills=ls.map(L=>`<span class="pill" style="background:${COL[L]}${open.has(L)?'':';opacity:.3'}">${NAME[L]}</span>`).join('');"""
))
reps.append((
"""      if(!open.has(L)){h+=`<div class="row"><span>${L}호선 승강장</span><span style="color:var(--soft)">아직 안 열림</span></div>`;continue;}
      if(isBuilt(L,i)){h+=`<div class="row"><span>${L}호선 승강장</span><span style="color:var(--soft)">운행 중</span></div>`;}
      else{const c=cost(i);
        h+=`<div class="row"><span>${L}호선 승강장</span><button class="act" ${cash<c?'disabled':''} onclick="doBuild('${L}',${i})">짓기 ${won(c)}</button></div>`;}""",
"""      if(!open.has(L)){h+=`<div class="row"><span>${NAME[L]} 승강장</span><span style="color:var(--soft)">아직 안 열림</span></div>`;continue;}
      if(isBuilt(L,i)){h+=`<div class="row"><span>${NAME[L]} 승강장</span><span style="color:var(--soft)">운행 중</span></div>`;}
      else{const c=cost(i);
        h+=`<div class="row"><span>${NAME[L]} 승강장</span><button class="act" ${cash<c?'disabled':''} onclick="doBuild('${L}',${i})">짓기 ${won(c)}</button></div>`;}"""
))
reps.append((
"""      h+=`<div class="row" style="border-bottom:0;padding-bottom:0"><span class="pill" style="background:${COL[L]}">${L}호선</span></div>`;""",
"""      h+=`<div class="row" style="border-bottom:0;padding-bottom:0"><span class="pill" style="background:${COL[L]}">${NAME[L]}</span></div>`;"""
))
reps.append((
"""  document.getElementById('sub').textContent=day+'일차'+(event?(' · '+event.emoji+event.type):'')+' · '+[...open].map(L=>L+'호선').join(' ')+' · '+bc+'역';""",
"""  const on=[...open];
  const lineTxt = on.length>4 ? (on.length+'개 노선') : on.map(L=>NAME[L]).join(' ');
  document.getElementById('sub').textContent=day+'일차'+(event?(' · '+event.emoji+event.type):'')+' · '+lineTxt+' · '+bc+'역';"""
))
# 노선 탭: ORDER 전체가 아니라 현재 모드에서 쓰는 노선만
reps.append((
"""    let h='<div class="n1">노선</div><div class="n2">80%를 짓고 대표역을 지으면 다음 호선이 열립니다</div>';
    for(const L of ORDER){""",
"""    let h='<div class="n1">노선</div><div class="n2">80%를 짓고 대표역을 지으면 다음 노선이 열립니다</div>';
    for(const L of activeLines()){"""
))
reps.append((
"""      h+=`<div class="row"><span><span class="pill" style="background:${COL[L]}">${L}</span>${open.has(L)?'':'<span style="color:var(--soft)">잠김</span>'}</span>""",
"""      h+=`<div class="row"><span><span class="pill" style="background:${COL[L]}">${NAME[L]}</span>${open.has(L)?'':'<span style="color:var(--soft)">잠김</span>'}</span>"""
))
# 9호선 급행 토글은 9호선 열렸을 때만
reps.append((
"""      <div class="row"><span>9호선 급행</span><button class="mini ${exp9?'on':''}" onclick="toggleExp()">${exp9?'켜짐 46km/h':'꺼짐 30km/h'}</button></div>""",
"""      ${open.has('9')?`<div class="row"><span>9호선 급행</span><button class="mini ${exp9?'on':''}" onclick="toggleExp()">${exp9?'켜짐 46km/h':'꺼짐 30km/h'}</button></div>`:''}"""
))

# ---------- 6. activeLines() + 해금 체인 ----------
reps.append((
"""function checkUnlock(){
  for(let k=0;k<ORDER.length-1;k++){
    const L=ORDER[k]; if(!open.has(L))continue;
    const a=D.lines[L],b=a.filter(i=>isBuilt(L,i)).length,rep=idxOf[D.rep[L]];
    if(b/a.length>=CFG.unlockRatio&&isBuilt(L,rep)&&!open.has(ORDER[k+1])){
      open.add(ORDER[k+1]); toast(ORDER[k+1]+'호선이 열렸습니다');}
  }
}""",
"""function activeLines(){
  if(mode==='single') return [...open];
  if(mode==='core')   return ORDER.filter(L=>CORE.includes(L));
  return ORDER;                       // all / grow
}
function checkUnlock(){
  if(mode==='single')return;          // 단일 노선 모드는 해금 없음
  const chain=activeLines();
  for(let k=0;k<chain.length-1;k++){
    const L=chain[k]; if(!open.has(L))continue;
    const a=D.lines[L],b=a.filter(i=>isBuilt(L,i)).length,rep=idxOf[D.rep[L]];
    if(b/a.length>=CFG.unlockRatio&&isBuilt(L,rep)&&!open.has(chain[k+1])){
      open.add(chain[k+1]); toast(NAME[chain[k+1]]+'이(가) 열렸습니다');}
  }
}"""
))

# ---------- 7. startLine / buildAll / 시작화면 ----------
reps.append((
"""function startLine(L){
  open=new Set([L]); started=true;
  ORDER.splice(0,ORDER.length,L,...['9','2','5','7','3','4','6','1','8'].filter(x=>x!==L));
  const a=D.lines[L], mid=Math.floor(a.length/2);
  for(let k=mid-1;k<=mid+1;k++) built.add(L+':'+a[k]);
  cash=CFG.cash0; named.clear(); retail.clear(); repInit=false;
  document.getElementById('start').style.display='none';
  fitTo(a); recompute(); updateRep(); panel();
}
window.startLine=startLine;""",
"""function startLine(L,m){
  mode=m||'core';
  open=new Set([L]); started=true; built.clear();
  const chain = mode==='grow' ? [...CORE,...EXTRA] : (mode==='single' ? [L] : [...CORE]);
  ORDER.splice(0,ORDER.length,L,...chain.filter(x=>x!==L));
  const a=D.lines[L], mid=Math.floor(a.length/2);
  for(let k=Math.max(0,mid-1);k<=Math.min(a.length-1,mid+1);k++) built.add(L+':'+a[k]);
  cash=CFG.cash0; named.clear(); retail.clear(); repInit=false; event=null; day=1; mins=330;
  document.getElementById('start').style.display='none';
  fitTo(a); recompute(); updateRep(); panel();
}
window.startLine=startLine;"""
))
reps.append((
"""(function(){const p=document.getElementById('pick');
  for(const L of ['1','2','3','4','5','6','7','8','9']){
    const b=document.createElement('button'); b.className='pk';
    b.style.background=COL[L];
    b.innerHTML=L+'호선<small>'+D.lines[L].length+'역 · '+D.rep[L]+'</small>';
    b.onclick=()=>startLine(L); p.appendChild(b);}
  const all=document.createElement('button');
  all.className='pk'; all.style.cssText='grid-column:1/-1;background:#1A1A1A';
  all.innerHTML='전부 지어놓고 보기<small>1~9호선 378역 완성 상태</small>';
  all.onclick=buildAll; p.appendChild(all);
})();""",
"""let pickMode='core';
function renderPick(){
  const p=document.getElementById('pick'); p.innerHTML='';
  const tabs=document.getElementById('modetab');
  tabs.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.m===pickMode));
  const desc={
    single:'고른 노선 하나만 짓습니다. 다른 노선은 열리지 않습니다.',
    core:'1~9호선. 80%와 대표역을 지으면 다음 호선이 열립니다.',
    grow:'고른 노선에서 시작해 1~9호선과 확장 노선 전부까지 열립니다.',
    all:'모든 노선이 지어진 상태로 바로 봅니다.'};
  document.getElementById('modedesc').textContent=desc[pickMode];
  if(pickMode==='all'){
    const b1=document.createElement('button');
    b1.className='pk'; b1.style.cssText='grid-column:1/-1;background:#1A1A1A';
    b1.innerHTML='1~9호선 전부<small>'+CORE.reduce((a,L)=>a+D.lines[L].length,0)+'개 승강장</small>';
    b1.onclick=()=>buildAll(CORE); p.appendChild(b1);
    const b2=document.createElement('button');
    b2.className='pk'; b2.style.cssText='grid-column:1/-1;background:#444';
    b2.innerHTML='전체 노선<small>'+D.names.length+'역 · '+(CORE.length+EXTRA.length)+'개 노선</small>';
    b2.onclick=()=>buildAll([...CORE,...EXTRA]); p.appendChild(b2);
    return;
  }
  const list = pickMode==='core' ? CORE : [...CORE,...EXTRA];
  for(const L of list){
    const b=document.createElement('button'); b.className='pk';
    b.style.background=COL[L];
    b.style.fontSize = NAME[L].length>4 ? '11px' : '15px';
    b.innerHTML=NAME[L]+'<small>'+D.lines[L].length+'역 · '+D.rep[L]+'</small>';
    b.onclick=()=>startLine(L,pickMode); p.appendChild(b);}
}
(function(){
  document.getElementById('modetab').querySelectorAll('button').forEach(b=>{
    b.onclick=()=>{pickMode=b.dataset.m; renderPick();};});
  renderPick();
})();"""
))
reps.append((
"""function buildAll(){
  started=true; open=new Set(['1','2','3','4','5','6','7','8','9']);
  for(const L in D.lines) for(const i of D.lines[L]) built.add(L+':'+i);
  cash=0; named.clear(); retail.clear(); repInit=false;
  document.getElementById('start').style.display='none';
  toast('경로 계산 중…');
  setTimeout(()=>{const t=Date.now();recompute(); updateRep();
    fitTo(D.names.map((_,i)=>i));
    toast('완성 · 하루 '+Math.round(servedDaily).toLocaleString()+'명 ('+(Date.now()-t)+'ms)');
    panel();},60);
}""",
"""function buildAll(list){
  const ls=list||[...CORE,...EXTRA];
  mode='all'; started=true; open=new Set(ls); built.clear();
  ORDER.splice(0,ORDER.length,...ls);
  for(const L of ls) for(const i of D.lines[L]) built.add(L+':'+i);
  cash=0; named.clear(); retail.clear(); repInit=false; event=null; day=1; mins=330;
  document.getElementById('start').style.display='none';
  toast('경로 계산 중…');
  setTimeout(()=>{const t=Date.now();recompute(); updateRep();
    const shown=new Set(); for(const L of ls) for(const i of D.lines[L]) shown.add(i);
    fitTo([...shown]);
    toast('완성 · 하루 '+Math.round(servedDaily).toLocaleString()+'명 ('+(Date.now()-t)+'ms)');
    panel();},60);
}"""
))

# ---------- 8. 시작화면 UI ----------
reps.append((
"""<div id="start"><div class="sbox"><div class="s1">어느 호선부터 만들까요?</div>
<div class="s2">고른 호선의 가운데 세 역에서 시작합니다.<br>80%를 짓고 대표역을 지으면 다음 호선이 열립니다.</div>
<div id="pick"></div></div></div></div>""",
"""<div id="start"><div class="sbox"><div class="s1">어떤 게임을 할까요?</div>
<div id="modetab" style="display:flex;gap:5px;margin-top:12px">
 <button class="tb" data-m="single">단일 노선</button>
 <button class="tb on" data-m="core">1~9호선</button>
 <button class="tb" data-m="grow">전체 확장</button>
 <button class="tb" data-m="all">전부 보기</button>
</div>
<div class="s2" id="modedesc"></div>
<div id="pick"></div></div></div></div>"""
))

# ---------- 적용 ----------
bad = []
for i, (o, n) in enumerate(reps, 1):
    c = s.count(o)
    if c != 1: bad.append((i, c))
    else: s = s.replace(o, n, 1)
if bad:
    print("FAILED:", bad); sys.exit(1)

open(DST, "w", encoding="utf-8").write(s)
print(f"OK {orig:,} -> {len(s):,}  ({DST})")
