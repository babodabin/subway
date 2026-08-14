#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v10 -> v11
1) 뒤로가기가 안 되는 문제
   - 파일을 직접 열면(file://) history.pushState 가 막혀 예외가 나고 화면 전환이 통째로 깨진다.
     → history 사용을 전부 try/catch 로 감싸고, 막히면 자체 스택으로만 동작.
   - ‹ 버튼은 history 가 안 먹어도 항상 닫히도록 안전장치 추가.
2) 게임을 하나 고르면 다른 게임을 못 고르는 문제
   - 시작 화면으로 돌아가는 길을 만든다(홈에서 뒤로가기 · 설정 화면의 버튼).
"""
import sys

SRC = "/tmp/game_v10.html"
DST = "/tmp/game_v11.html"
s = open(SRC, encoding="utf-8").read()
orig = len(s)
reps = []

# ── 1. 화면 전환 코어 교체 ──────────────────────────────
reps.append((
"""/* ---------- 화면 전환 (오른→왼 슬라이드 · 뒤로가기) ---------- */
const TITLE={stn:'역',line:'노선',train:'열차',jam:'혼잡',rep:'평판',time:'시간',save:'저장 · 설정'};
const SCR=document.getElementById('screens');
let stack=[];                       // 쌓인 화면 이름
function go(t){
  if(!started)return;
  if(stack[stack.length-1]===t)return;
  tab=t;
  const el=document.createElement('div');
  el.className='scr';
  el.innerHTML=`<div class="scrhd"><button class="bk" aria-label="뒤로">‹</button>
    <div class="scrttl">${TITLE[t]}</div><div class="scrsub" id="hsub"></div></div>
    <div class="scrbd">${scrBody(t)}</div>`;
  el.querySelector('.bk').onclick=()=>history.back();
  SCR.appendChild(el);
  const under=stack.length?SCR.children[SCR.children.length-2]:null;
  requestAnimationFrame(()=>{
    el.classList.add('anim','in');
    if(under)under.classList.add('anim','under');
  });
  stack.push(t);
  history.pushState({scr:t,depth:stack.length},'','#'+t);
  draw();
}
function closeTop(){
  const el=SCR.lastElementChild; if(!el)return;
  stack.pop();
  const under=SCR.children[SCR.children.length-2];
  el.classList.add('anim'); el.classList.remove('in');
  if(under)under.classList.remove('under');
  setTimeout(()=>el.remove(),290);
  tab=stack[stack.length-1]||'';
  draw();
}
window.go=go;
window.addEventListener('popstate',e=>{
  const want=(e.state&&e.state.depth)||0;
  while(stack.length>want)closeTop();
});""",
"""/* ---------- 화면 전환 (오른→왼 슬라이드 · 뒤로가기) ---------- */
const TITLE={stn:'역',line:'노선',train:'열차',jam:'혼잡',rep:'평판',time:'시간',save:'설정'};
const SCR=document.getElementById('screens');
let stack=[];                       // 쌓인 화면 이름
// 깊이: 0 = 시작 화면, 1 = 지도(홈), 2 이상 = 세부 화면
// file:// 로 열면 pushState 가 막히는 브라우저가 있어 실패하면 자체 스택만으로 돈다.
let histOK=true, popped=false;
try{ history.replaceState({depth:0},''); }catch(err){ histOK=false; }
function pushHist(depth){
  if(!histOK)return;
  try{ history.pushState({depth},''); }catch(err){ histOK=false; }
}
function go(t){
  if(!started)return;
  if(stack[stack.length-1]===t)return;
  tab=t;
  const el=document.createElement('div');
  el.className='scr';
  el.innerHTML=`<div class="scrhd"><button class="bk" aria-label="뒤로">‹</button>
    <div class="scrttl">${TITLE[t]}</div><div class="scrsub" id="hsub"></div></div>
    <div class="scrbd">${scrBody(t)}</div>`;
  el.querySelector('.bk').onclick=goBack;
  SCR.appendChild(el);
  const under=stack.length?SCR.children[SCR.children.length-2]:null;
  requestAnimationFrame(()=>{
    el.classList.add('anim','in');
    if(under)under.classList.add('anim','under');
  });
  stack.push(t);
  pushHist(stack.length+1);
  draw();
}
function closeTop(){
  const el=SCR.lastElementChild; if(!el)return;
  stack.pop();
  const under=SCR.children[SCR.children.length-2];
  el.classList.add('anim'); el.classList.remove('in');
  if(under)under.classList.remove('under');
  setTimeout(()=>el.remove(),290);
  tab=stack[stack.length-1]||'';
  draw();
}
// ‹ 버튼과 가장자리 스와이프가 쓰는 뒤로가기.
// history 가 살아 있으면 브라우저 뒤로가기와 같은 길을 타고,
// 막혀 있으면(파일로 직접 열었을 때 등) 직접 닫는다.
function goBack(){
  if(!histOK){ stack.length?closeTop():toStart(); return; }
  popped=false;
  try{ history.back(); }catch(err){ histOK=false; }
  setTimeout(()=>{ if(!popped){ stack.length?closeTop():toStart(); } },280);
}
window.goBack=goBack;
window.go=go;
window.addEventListener('popstate',e=>{
  popped=true;
  const want=(e.state&&e.state.depth)||0;
  while(stack.length && stack.length+1>want) closeTop();
  if(want===0 && started) toStart();
});
/* 시작 화면으로 (게임은 지워지지 않고 그대로 남아 있음) */
function toStart(){
  while(stack.length)closeTop();
  renderPick();
  const st=document.getElementById('start');
  st.style.display='flex';
  if(histOK){ try{ history.replaceState({depth:0},''); }catch(err){} }
}
window.toStart=toStart;"""
))

# ── 2. 스와이프도 goBack 사용 ──────────────────────────
reps.append((
"""    if(dx>w*0.32)history.back();""",
"""    if(dx>w*0.32)goBack();"""
))

# ── 3. 게임 시작 시 홈 깊이(1) 기록 ────────────────────
reps.append((
"""  fitTo(a); recompute(); updateRep(); dock(); saveGame(1);
}
window.startLine=startLine;""",
"""  fitTo(a); recompute(); updateRep(); dock(); saveGame(1); pushHist(1);
}
window.startLine=startLine;"""
))
reps.append((
"""    toast('완성 · 하루 '+Math.round(servedDaily).toLocaleString()+'명 ('+(Date.now()-t)+'ms)');
    dock(); saveGame(1);},60);""",
"""    toast('완성 · 하루 '+Math.round(servedDaily).toLocaleString()+'명 ('+(Date.now()-t)+'ms)');
    dock(); saveGame(1);},60);
  pushHist(1);"""
))
reps.append((
"""  dock(); draw();
}
window.loadGame=()=>{""",
"""  dock(); draw(); pushHist(1);
}
window.loadGame=()=>{"""
))

# ── 4. 시작 화면에 '돌아가기' + 설정 화면에 '다른 게임' ──
reps.append((
"""function renderPick(){
  const p=document.getElementById('pick'); p.innerHTML='';
  const tabs=document.getElementById('modetab');""",
"""function renderPick(){
  const p=document.getElementById('pick'); p.innerHTML='';
  const back=document.getElementById('sback');
  if(back)back.style.display = started ? 'block' : 'none';
  const tabs=document.getElementById('modetab');"""
))
reps.append((
"""<div class="s2" id="modedesc"></div>
<div id="pick"></div></div></div></div>""",
"""<div class="s2" id="modedesc"></div>
<div id="pick"></div>
<button id="sback" style="display:none;width:100%;margin-top:12px;padding:11px;border:1px solid var(--line);
 background:transparent;border-radius:3px;font-size:12px;font-weight:700;color:var(--soft);cursor:pointer"
 onclick="closeStart()">하던 게임으로 돌아가기</button>
</div></div></div>"""
))
reps.append((
"""      <div class="sect">새로</div>
      <div class="row"><span>처음부터 다시</span><button class="act" style="background:var(--hot)" onclick="resetGame()">새 게임</button></div>`;""",
"""      <div class="sect">게임</div>
      <div class="row"><span>다른 게임 고르기</span><button class="act" onclick="toStart()">고르기</button></div>
      <div class="n2">지금 하던 게임은 저장되어 있어서, 시작 화면에서 '이어하기'로 다시 돌아올 수 있습니다.</div>
      <div class="row"><span>처음부터 다시</span><button class="act" style="background:var(--hot)" onclick="resetGame()">기록 지우고 새로</button></div>`;"""
))

# ── 5. 시작 화면 닫기 ──────────────────────────────────
reps.append((
"""window.resetGame=()=>{""",
"""window.closeStart=()=>{
  if(!started)return;
  document.getElementById('start').style.display='none';
  pushHist(1);
};
window.resetGame=()=>{"""
))

# ── 6. 지도 위에 홈/시작 버튼 (뒤로가기를 몰라도 갈 수 있게) ──
reps.append((
"""<div id="stage"><svg id="m" viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid meet"></svg>
<div id="toast"></div>""",
"""<div id="stage"><svg id="m" viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid meet"></svg>
<button id="menu" onclick="toStart()" title="게임 고르기">≡</button>
<div id="toast"></div>"""
))
reps.append((
"""/* ── 슬라이드 화면 ── */""",
"""#menu{position:absolute;top:8px;right:10px;width:34px;height:34px;border:1px solid var(--line);
background:rgba(255,255,255,.92);border-radius:9px;font-size:17px;line-height:1;cursor:pointer;
color:var(--ink);z-index:4}

/* ── 슬라이드 화면 ── */"""
))

bad=[]
for i,(o,n) in enumerate(reps,1):
    c=s.count(o)
    if c!=1: bad.append((i,c))
    else: s=s.replace(o,n,1)
if bad:
    print("FAILED:",bad); sys.exit(1)

open(DST,"w",encoding="utf-8").write(s)
print(f"OK {orig:,} -> {len(s):,}  ({DST})")
