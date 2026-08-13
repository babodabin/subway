#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v9 -> v10
1) 평판이 승객 수를 움직이게 (문서의 '변화 속도 k' 원래 의도 복원)
2) 저장/불러오기 (자동저장 + 파일 내보내기/가져오기)
3) 화면 전환: 오른→왼 슬라이드, 뒤로가기(상단 ‹ · 브라우저 · 왼쪽 가장자리 스와이프)
4) 화면 분리 및 디자인 정리
"""
import sys

SRC = "/tmp/game_v9.html"
DST = "/tmp/game_v10.html"
s = open(SRC, encoding="utf-8").read()
orig = len(s)
reps = []

# ══════════════════════════════════════════════════════════════
# 1. CSS
# ══════════════════════════════════════════════════════════════
reps.append((
"""#toast{position:absolute;left:50%;bottom:14px;transform:translateX(-50%);background:rgba(26,26,26,.92);
color:#F7F5F0;padding:8px 14px;border-radius:3px;font-size:12px;font-weight:700;opacity:0;
transition:opacity .3s;pointer-events:none;white-space:nowrap}
</style>""",
"""#toast{position:fixed;left:50%;bottom:76px;transform:translateX(-50%);background:rgba(26,26,26,.92);
color:#F7F5F0;padding:8px 14px;border-radius:20px;font-size:12px;font-weight:700;opacity:0;
transition:opacity .3s;pointer-events:none;white-space:nowrap;z-index:60}

/* ── 아래 고정 조작줄 ── */
#speed{display:flex;gap:5px;padding:5px 10px 0}
#dock{display:flex;gap:5px;padding:6px 10px;padding-bottom:calc(6px + env(safe-area-inset-bottom))}
.dk{flex:1;padding:9px 2px;border:0;background:#F4F2ED;color:var(--ink);font-size:11px;
font-weight:700;border-radius:9px;cursor:pointer;line-height:1.3}
.dk b{display:block;font-size:13px;font-weight:800}

/* ── 슬라이드 화면 ── */
#screens{position:fixed;inset:0;z-index:40;pointer-events:none}
.scr{position:absolute;inset:0;background:var(--paper);display:flex;flex-direction:column;
transform:translateX(100%);will-change:transform;pointer-events:auto;
box-shadow:-8px 0 24px rgba(0,0,0,.10)}
.scr.anim{transition:transform .28s cubic-bezier(.32,.72,0,1)}
.scr.in{transform:translateX(0)}
.scr.under{transform:translateX(-28%);box-shadow:none}
.scrhd{display:flex;align-items:center;gap:6px;padding:calc(10px + env(safe-area-inset-top)) 12px 10px;
border-bottom:1px solid var(--line);background:var(--paper);flex-shrink:0}
.bk{border:0;background:transparent;font-size:26px;line-height:1;color:var(--ink);
cursor:pointer;padding:0 8px 3px 0;font-weight:300}
.scrttl{font-size:16px;font-weight:800;letter-spacing:-.02em;flex:1}
.scrsub{font-size:11px;color:var(--soft);font-weight:600}
.scrbd{flex:1;overflow-y:auto;-webkit-overflow-scrolling:touch;padding:12px 14px 30px}
.scrbd .row{font-size:12.5px;padding:8px 0}
.scrbd .n1{font-size:15px}
.sect{margin-top:18px;font-size:11px;font-weight:800;color:var(--soft);letter-spacing:.06em}
.sect:first-child{margin-top:0}
.big{font-size:34px;font-weight:800;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
.gauge{height:8px;background:#EFECE4;border-radius:4px;overflow:hidden;margin-top:8px}
.gauge>i{display:block;height:100%;background:var(--ink);transition:width .4s}
</style>"""
))

# ══════════════════════════════════════════════════════════════
# 2. body HTML: 탭/패널 -> 조작줄 + 화면 컨테이너
# ══════════════════════════════════════════════════════════════
reps.append((
"""<div id="tabs">
 <button class="tb on" data-t="stn">역</button>
 <button class="tb" data-t="line">노선</button>
 <button class="tb" data-t="train">열차</button>
 <button class="tb" data-t="jam">혼잡</button>
 <button class="tb" data-t="rep">평판</button>
</div>
<div id="dtype" style="display:flex;gap:6px;padding:6px 12px 0">
 <button class="sp on" data-d="wd" onclick="setDayType('wd')">평일</button>
 <button class="sp" data-d="sat" onclick="setDayType('sat')">토요일</button>
 <button class="sp" data-d="sun" onclick="setDayType('sun')">일요일</button>
</div>
<div id="skip" style="display:flex;gap:6px;padding:6px 12px 0">
 <button class="sp" onclick="skipDays(1)">+하루</button>
 <button class="sp" onclick="skipDays(7)">+일주일</button>
 <button class="sp" onclick="skipDays(30)">+한달</button>
</div>
<div id="panel"></div>
<div id="speed">
 <button class="sp on" data-s="1">1배</button><button class="sp" data-s="8">8배</button>
 <button class="sp" data-s="40">40배</button><button class="sp" data-s="200">하루씩</button>
</div>
</div>""",
"""<div id="speed">
 <button class="sp on" data-s="1">1배</button><button class="sp" data-s="8">8배</button>
 <button class="sp" data-s="40">40배</button><button class="sp" data-s="200">하루씩</button>
</div>
<div id="dock">
 <button class="dk" onclick="go('line')"><b>노선</b>건설</button>
 <button class="dk" onclick="go('train')"><b>열차</b>배차</button>
 <button class="dk" onclick="go('jam')"><b>혼잡</b><span id="dkjam">–</span></button>
 <button class="dk" onclick="go('rep')"><b>평판</b><span id="dkrep">–</span></button>
 <button class="dk" onclick="go('time')"><b>시간</b><span id="dkday">평일</span></button>
 <button class="dk" onclick="go('save')"><b>저장</b>설정</button>
</div>
</div>
<div id="screens"></div>"""
))

# ══════════════════════════════════════════════════════════════
# 3. 평판 -> 승객 수
# ══════════════════════════════════════════════════════════════
reps.append((
"""function changeK(){return Math.max(0.05,Math.min(1,servedDaily/100000));}
function updateRep(){
  const target=repComponents().total, k=changeK();
  repScore = repInit ? repScore+(target-repScore)*k : target;
  repInit=true;
}""",
"""function changeK(){return Math.max(0.05,Math.min(1,servedDaily/100000));}
// 평판이 승객 수를 움직인다. 60점을 기준(1.00배)으로 위아래로 벌어지고,
// 목표치까지 한 번에 가지 않고 변화속도 k 만큼씩 서서히 따라간다.
function repTargetMult(){
  return Math.max(CFG.rep.multMin, Math.min(CFG.rep.multMax,
    1 + (repScore - CFG.rep.neutral) / 100 * CFG.rep.multSpan));
}
function updateRep(){
  const target=repComponents().total, k=changeK();
  repScore = repInit ? repScore+(target-repScore)*k : target;
  const tm=repTargetMult();
  repMult = repInit ? repMult+(tm-repMult)*k : tm;
  repInit=true;
}"""
))
reps.append((
"""  rep:{jamW:40, timeW:25, retailW:20, fameW:15, namingPenalty:5, timeBase:20, timeSpan:40},""",
"""  rep:{jamW:40, timeW:25, retailW:20, fameW:15, namingPenalty:5, timeBase:20, timeSpan:40,
       neutral:60, multSpan:0.5, multMin:0.7, multMax:1.2},
       // 평판 60점이면 승객 그대로(1.00배), 100점이면 1.20배, 20점이면 0.80배까지."""
))
reps.append((
"""let repScore=0, repInit=false, totalTripMinutes=0;  // 평판(0~100), k로 서서히 목표치에 수렴""",
"""let repScore=0, repMult=1, repInit=false, totalTripMinutes=0;  // 평판(0~100)과 그로 인한 승객 배수"""
))
# 수요에 곱하기
reps.append((
"""function eventMult(){return event?(event.mult[dayType]??1):1;}
function dayRevenueNow(){return servedDaily*eventMult()*CFG.fare+extraDailyIncome();}""",
"""function eventMult(){return event?(event.mult[dayType]??1):1;}
function liveMult(){return eventMult()*repMult;}   // 이벤트 × 평판
function dayRevenueNow(){return servedDaily*liveMult()*CFG.fare+extraDailyIncome();}"""
))
reps.append((
"""  const evMult=eventMult();
  const perMin=servedDaily*hourW(h)/60*evMult, extra=extraDailyIncome()/1440;""",
"""  const perMin=servedDaily*hourW(h)/60*liveMult(), extra=extraDailyIncome()/1440;"""
))
reps.append((
"""  const load=(linkLoad[L+':'+a+':'+b]||0)*hourW(h)/2*eventMult();   // 방향 절반""",
"""  const load=(linkLoad[L+':'+a+':'+b]||0)*hourW(h)/2*liveMult();   // 방향 절반"""
))

# ══════════════════════════════════════════════════════════════
# 4. panel() -> 화면별 렌더 함수
# ══════════════════════════════════════════════════════════════
reps.append((
"""/* ---------- 패널 ---------- */
const P=document.getElementById('panel');
function panel(){
  if(tab==='stn'){
    if(sel<0){P.innerHTML='<div class="n1">회색 점을 누르세요</div><div class="n2">아직 짓지 않은 역입니다</div>';return;}
    const i=sel,n=D.names[i],ls=lineOf[i]||[];""",
"""/* ---------- 화면 내용 ---------- */
function scrBody(t){
  if(t==='stn'){
    if(sel<0)return '<div class="n1">역을 고르세요</div><div class="n2">지도에서 점을 누르면 열립니다</div>';
    const i=sel,n=D.names[i],ls=lineOf[i]||[];"""
))
reps.append((
"""      h+=`<div class="row"><span>상가 ${rc}/${rmax}칸</span>${rc<rmax?`<button class="act" onclick="openRetail(${i})">칸 열기 (월 ${won(dayRev(i)*CFG.retail.monthlyShare)})</button>`:`<span style="color:var(--soft)">가득 참</span>`}</div>`;
    }
    P.innerHTML=h;
  }
  else if(tab==='line'){""",
"""      h+=`<div class="row"><span>상가 ${rc}/${rmax}칸</span>${rc<rmax?`<button class="act" onclick="openRetail(${i})">칸 열기 (월 ${won(dayRev(i)*CFG.retail.monthlyShare)})</button>`:`<span style="color:var(--soft)">가득 참</span>`}</div>`;
    }
    return h;
  }
  else if(t==='line'){"""
))
reps.append((
"""      <span class="bar"><i style="width:${(b/a.length*100).toFixed(0)}%"></i></span></span></div>`;}
    P.innerHTML=h;
  }
  else if(tab==='train'){""",
"""      <span class="bar"><i style="width:${(b/a.length*100).toFixed(0)}%"></i></span></span></div>`;}
    return h;
  }
  else if(t==='train'){"""
))
reps.append((
"""        <button class="mini" onclick="chg('${L}',${k},'hw',-1)">＋</button></span></div>`;});
    }
    P.innerHTML=h;
  }
  else if(tab==='jam'){""",
"""        <button class="mini" onclick="chg('${L}',${k},'hw',-1)">＋</button></span></div>`;});
    }
    return h;
  }
  else if(t==='jam'){"""
))
reps.append((
"""      <span style="${j>CFG.jamWarn?'color:var(--hot);font-weight:800':''}">${(j*100).toFixed(0)}%</span></div>`;});
    P.innerHTML=h;
  }
  else if(tab==='rep'){
    const c=repComponents();
    let h=`<div class="n1">평판 ${c.total.toFixed(0)}점</div><div class="n2">100점 만점 · 매일 서서히 반영 (변화속도 k=${changeK().toFixed(2)})</div>
      <div class="row"><span>혼잡 (40점 만점)</span><span>${c.jamScore.toFixed(1)}</span></div>
      <div class="row"><span>소요시간 (25점 만점)</span><span>${c.timeScore.toFixed(1)}</span></div>
      <div class="row"><span>상가 (20점 만점)</span><span>${c.retailScore.toFixed(1)}</span></div>
      <div class="row"><span>명물 (15점 만점)</span><span>${c.fameScore.toFixed(1)}</span></div>
      <div class="row"><span>역명 병기 (−5)</span><span>${c.namingPenalty.toFixed(1)}</span></div>`;
    if(event){
      const pct=((eventMult()-1)*100).toFixed(1);
      h+=`<div class="row"><span>${event.emoji} ${event.type}${event.affectedLine?' ('+NAME[event.affectedLine]+')':''}</span>
        <span>수요 ${pct>=0?'+':''}${pct}% · 수송력 ${(event.cap*100).toFixed(0)}% · ${event.daysLeft}일 남음</span></div>`;
    }
    P.innerHTML=h;
  }
}""",
"""      <span style="${j>CFG.jamWarn?'color:var(--hot);font-weight:800':''}">${(j*100).toFixed(0)}%</span></div>`;});
    return h;
  }
  else if(t==='rep'){
    const c=repComponents();
    const now=((repMult-1)*100), tgt=((repTargetMult()-1)*100);
    let h=`<div class="big">${repScore.toFixed(0)}<span style="font-size:15px;color:var(--soft)"> / 100점</span></div>
      <div class="gauge"><i style="width:${repScore.toFixed(0)}%"></i></div>
      <div class="n2">지금 승객이 <b>${now>=0?'+':''}${now.toFixed(1)}%</b> 늘었습니다 (목표 ${tgt>=0?'+':''}${tgt.toFixed(1)}%).
      평판 ${CFG.rep.neutral}점이 기준이고, 매일 ${(changeK()*100).toFixed(0)}%씩 목표에 다가갑니다.</div>
      <div class="sect">점수 내역</div>
      <div class="row"><span>혼잡 <span style="color:var(--soft)">40점 만점</span></span><span>${c.jamScore.toFixed(1)}</span></div>
      <div class="row"><span>소요시간 <span style="color:var(--soft)">25점 만점</span></span><span>${c.timeScore.toFixed(1)}</span></div>
      <div class="row"><span>상가 <span style="color:var(--soft)">20점 만점</span></span><span>${c.retailScore.toFixed(1)}</span></div>
      <div class="row"><span>명물 <span style="color:var(--soft)">15점 만점</span></span><span>${c.fameScore.toFixed(1)}</span></div>
      <div class="row"><span>역명 병기 <span style="color:var(--soft)">계약 있으면 −5</span></span><span>${c.namingPenalty.toFixed(1)}</span></div>`;
    if(event){
      const pct=((eventMult()-1)*100).toFixed(1);
      h+=`<div class="sect">지금 일어난 일</div>
        <div class="row"><span>${event.emoji} ${event.type}${event.affectedLine?' ('+NAME[event.affectedLine]+')':''}</span>
        <span>수요 ${pct>=0?'+':''}${pct}% · 수송력 ${(event.cap*100).toFixed(0)}% · ${event.daysLeft}일</span></div>`;
    }
    return h;
  }
  else if(t==='time'){
    return `<div class="sect">요일</div>
      <div style="display:flex;gap:6px;margin-top:6px">
        ${['wd','sat','sun'].map((d,k)=>`<button class="sp ${dayType===d?'on':''}" style="flex:1"
          onclick="setDayType('${d}');refresh()">${['평일','토요일','일요일'][k]}</button>`).join('')}
      </div>
      <div class="n2">요일마다 승객 수와 시간대 흐름이 다릅니다. 토요일은 평일의 79%, 일요일은 58%입니다.</div>
      <div class="sect">시간 건너뛰기</div>
      <div style="display:flex;gap:6px;margin-top:6px">
        <button class="sp" style="flex:1" onclick="skipDays(1);refresh()">＋하루</button>
        <button class="sp" style="flex:1" onclick="skipDays(7);refresh()">＋일주일</button>
        <button class="sp" style="flex:1" onclick="skipDays(30);refresh()">＋한달</button>
      </div>
      <div class="n2">건너뛴 날만큼 수입이 들어오고 평판도 갱신됩니다.</div>
      <div class="sect">지금</div>
      <div class="row"><span>날짜</span><span>${day}일차</span></div>
      <div class="row"><span>하루 이용객</span><span>${Math.round(servedDaily*liveMult()).toLocaleString()}명</span></div>
      <div class="row"><span>하루 수입</span><span>${won(dayRevenueNow())}</span></div>`;
  }
  else if(t==='save'){
    const sv=savedInfo();
    return `<div class="sect">저장</div>
      <div class="n2">게임은 이 브라우저에 자동으로 저장됩니다. 창을 닫아도 이어서 할 수 있습니다.</div>
      <div class="row"><span>자동 저장</span><span>${sv?sv:'아직 없음'}</span></div>
      <div class="row"><span>지금 저장</span><button class="act" onclick="saveGame(1)">저장</button></div>
      <div class="row"><span>저장한 데서 이어하기</span><button class="act" ${sv?'':'disabled'} onclick="loadGame()">불러오기</button></div>
      <div class="sect">파일로</div>
      <div class="n2">다른 기기로 옮기거나 백업할 때 쓰세요.</div>
      <div class="row"><span>파일로 내보내기</span><button class="act" onclick="exportGame()">내보내기</button></div>
      <div class="row"><span>파일에서 가져오기</span><button class="act" onclick="importGame()">가져오기</button></div>
      <div class="sect">새로</div>
      <div class="row"><span>처음부터 다시</span><button class="act" style="background:var(--hot)" onclick="resetGame()">새 게임</button></div>`;
  }
  return '';
}
/* ---------- 화면 전환 (오른→왼 슬라이드 · 뒤로가기) ---------- */
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
});
function refresh(){                 // 현재 화면 다시 그리기
  const el=SCR.lastElementChild; if(!el)return;
  el.querySelector('.scrbd').innerHTML=scrBody(stack[stack.length-1]);
  dock();
}
window.refresh=refresh;
function dock(){
  if(!started)return;
  const h0=Math.floor(mins/60)%24; let mx=0;
  for(const L of open) for(const [a,b] of segs(L)){
    if(!isBuilt(L,a)||!isBuilt(L,b))continue;
    const j=jamOf(L,a,b,h0); if(j>mx)mx=j;
  }
  const dj=document.getElementById('dkjam'); if(dj){
    dj.textContent=(mx*100).toFixed(0)+'%';
    dj.style.color = mx>CFG.jamWarn?'var(--hot)':'';
  }
  const dr=document.getElementById('dkrep'); if(dr)dr.textContent=repScore.toFixed(0)+'점';
  const dd=document.getElementById('dkday'); if(dd)dd.textContent={wd:'평일',sat:'토',sun:'일'}[dayType];
}
/* 왼쪽 가장자리에서 오른쪽으로 밀면 뒤로 */
(function(){
  let sx=0,sy=0,dx=0,act=false,el=null,under=null;
  SCR.addEventListener('touchstart',e=>{
    if(!stack.length||e.touches.length!==1)return;
    const t=e.touches[0]; if(t.clientX>28)return;
    sx=t.clientX; sy=t.clientY; dx=0; act=true;
    el=SCR.lastElementChild; under=SCR.children[SCR.children.length-2];
    if(el)el.classList.remove('anim');
    if(under)under.classList.remove('anim');
  },{passive:true});
  SCR.addEventListener('touchmove',e=>{
    if(!act||!el)return;
    const t=e.touches[0]; dx=Math.max(0,t.clientX-sx);
    if(Math.abs(t.clientY-sy)>Math.abs(dx)+30){act=false;el.classList.add('anim');el.style.transform='';return;}
    const w=el.offsetWidth||1;
    el.style.transform=`translateX(${dx}px)`;
    if(under)under.style.transform=`translateX(${-28+28*(dx/w)}%)`;
  },{passive:true});
  const end=()=>{
    if(!act||!el)return; act=false;
    const w=el.offsetWidth||1;
    el.classList.add('anim'); if(under)under.classList.add('anim');
    el.style.transform=''; if(under)under.style.transform='';
    if(dx>w*0.32)history.back();
    dx=0; el=null; under=null;
  };
  SCR.addEventListener('touchend',end,{passive:true});
  SCR.addEventListener('touchcancel',end,{passive:true});
})();"""
))

# ══════════════════════════════════════════════════════════════
# 5. panel() 호출부 정리
# ══════════════════════════════════════════════════════════════
reps.append((
"""window.doBuild=(L,i)=>{const c=cost(i); if(cash<c)return; cash-=c; built.add(L+':'+i);
  toast(D.names[i]+' 완공'); checkUnlock(); recompute(); panel();};""",
"""window.doBuild=(L,i)=>{const c=cost(i); if(cash<c)return; cash-=c; built.add(L+':'+i);
  toast(D.names[i]+' 완공'); checkUnlock(); recompute(); refresh(); saveGame();};"""
))
reps.append((
"""  named.set(i, day+365*CFG.naming.years); toast(D.names[i]+' 역명 병기 계약 ('+CFG.naming.years+'년)'); panel();};""",
"""  named.set(i, day+365*CFG.naming.years); toast(D.names[i]+' 역명 병기 계약 ('+CFG.naming.years+'년)'); refresh(); saveGame();};"""
))
reps.append((
"""  if(cur>=max)return; retail.set(i,cur+1); toast(D.names[i]+' 상가 '+(cur+1)+'/'+max+'칸'); panel();};""",
"""  if(cur>=max)return; retail.set(i,cur+1); toast(D.names[i]+' 상가 '+(cur+1)+'/'+max+'칸'); refresh(); saveGame();};"""
))
reps.append((
"""window.chg=(L,k,what,d)=>{if(what==='car')cars[L][k]=Math.max(2,Math.min(10,cars[L][k]+d));
  else headway[L][k]=Math.max(2,Math.min(15,headway[L][k]+d)); panel(); draw();};
window.toggleExp=()=>{exp9=!exp9;recompute();panel();};
window.expandDepot=()=>{if(cash<CFG.depotCost)return;cash-=CFG.depotCost;depot+=CFG.depotStep;panel();};""",
"""window.chg=(L,k,what,d)=>{if(what==='car')cars[L][k]=Math.max(2,Math.min(10,cars[L][k]+d));
  else headway[L][k]=Math.max(2,Math.min(15,headway[L][k]+d)); refresh(); draw(); saveGame();};
window.toggleExp=()=>{exp9=!exp9;recompute();refresh();saveGame();};
window.expandDepot=()=>{if(cash<CFG.depotCost)return;cash-=CFG.depotCost;depot+=CFG.depotStep;refresh();saveGame();};"""
))
reps.append((
"""window.setDayType=(t)=>{if(dayType===t)return; dayType=t; recompute(); panel();};""",
"""window.setDayType=(t)=>{if(dayType===t)return; dayType=t; recompute(); dock(); saveGame();};"""
))
reps.append((
"""  for(let i=0;i<n;i++){cash+=dayRevenueNow(); day++; rollEvent(); updateRep();}
  pax=0; recompute(); draw(); panel();
  toast(n+'일 건너뜀 · '+day+'일차');""",
"""  for(let i=0;i<n;i++){cash+=dayRevenueNow(); day++; rollEvent(); updateRep();}
  pax=0; recompute(); draw(); dock(); saveGame(1);
  toast(n+'일 건너뜀 · '+day+'일차');"""
))
reps.append((
"""  fitTo(a); recompute(); updateRep(); panel();
}
window.startLine=startLine;""",
"""  fitTo(a); recompute(); updateRep(); dock(); saveGame(1);
}
window.startLine=startLine;"""
))
reps.append((
"""    toast('완성 · 하루 '+Math.round(servedDaily).toLocaleString()+'명 ('+(Date.now()-t)+'ms)');
    panel();},60);""",
"""    toast('완성 · 하루 '+Math.round(servedDaily).toLocaleString()+'명 ('+(Date.now()-t)+'ms)');
    dock(); saveGame(1);},60);"""
))
# 지도 클릭 -> 역 화면
reps.append((
"""S.addEventListener('click',e=>{if(moved)return;const i=e.target.dataset&&e.target.dataset.i;if(i===undefined)return;
  sel=+i;tab='stn';document.querySelectorAll('.tb').forEach(x=>x.classList.toggle('on',x.dataset.t==='stn'));
  panel();draw();});""",
"""S.addEventListener('click',e=>{if(moved)return;const i=e.target.dataset&&e.target.dataset.i;if(i===undefined)return;
  sel=+i; draw();
  if(stack[stack.length-1]==='stn')refresh(); else go('stn');});"""
))
# 탭 핸들러 제거 (탭이 없어짐)
reps.append((
"""document.querySelectorAll('.tb').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('.tb').forEach(x=>x.classList.remove('on'));b.classList.add('on');
  tab=b.dataset.t;panel();draw();});
document.querySelectorAll('.sp').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('.sp').forEach(x=>x.classList.remove('on'));b.classList.add('on');speed=+b.dataset.s;});""",
"""document.querySelectorAll('#speed .sp').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('#speed .sp').forEach(x=>x.classList.remove('on'));b.classList.add('on');speed=+b.dataset.s;});"""
))
# 마지막 초기화
reps.append((
"""window.buildAll=buildAll;
draw(); panel();
</script>""",
"""window.buildAll=buildAll;

/* ---------- 저장 · 불러오기 ---------- */
const SAVEKEY='seoul-subway-save-v1';
function snapshot(){
  return {v:1, t:Date.now(), mode, order:[...ORDER], open:[...open], built:[...built],
    cash, pax, mins, day, dayType, depot, exp9, speed,
    named:[...named], retail:[...retail], cars, headway,
    repScore, repMult, repInit,
    event: event?{type:event.type, daysLeft:event.daysLeft, affectedLine:event.affectedLine||null}:null};
}
function saveGame(loud){
  if(!started)return;
  try{
    localStorage.setItem(SAVEKEY, JSON.stringify(snapshot()));
    if(loud)toast('저장했습니다');
  }catch(err){ if(loud)toast('저장 실패 — 브라우저 저장공간을 쓸 수 없습니다'); }
}
function savedInfo(){
  try{
    const r=localStorage.getItem(SAVEKEY); if(!r)return '';
    const o=JSON.parse(r); const d=new Date(o.t);
    return `${o.day}일차 · ${String(d.getMonth()+1)}/${d.getDate()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
  }catch(err){ return ''; }
}
function applySnapshot(o){
  mode=o.mode||'core';
  ORDER.splice(0,ORDER.length,...(o.order||[]));
  open=new Set(o.open||[]);
  built.clear(); (o.built||[]).forEach(k=>built.add(k));
  cash=o.cash||0; pax=o.pax||0; mins=o.mins||330; day=o.day||1;
  dayType=o.dayType||'wd'; depot=o.depot||CFG.depot0; exp9=!!o.exp9; speed=o.speed||1;
  named.clear(); (o.named||[]).forEach(([k,v])=>named.set(+k,v));
  retail.clear(); (o.retail||[]).forEach(([k,v])=>retail.set(+k,v));
  for(const L in cars){ if(o.cars&&o.cars[L])cars[L]=o.cars[L].slice();
                        if(o.headway&&o.headway[L])headway[L]=o.headway[L].slice(); }
  repScore=o.repScore||0; repMult=o.repMult||1; repInit=!!o.repInit;
  event=null;
  if(o.event){
    const base=CFG.events.find(e=>e.type===o.event.type);
    if(base)event=Object.assign({},base,{daysLeft:o.event.daysLeft,affectedLine:o.event.affectedLine});
  }
  started=true;
  document.getElementById('start').style.display='none';
  document.querySelectorAll('#speed .sp').forEach(x=>x.classList.toggle('on',+x.dataset.s===speed));
  recompute();
  const shown=new Set(); for(const L of open) for(const i of D.lines[L]) shown.add(i);
  if(shown.size)fitTo([...shown]);
  dock(); draw();
}
window.loadGame=()=>{
  try{
    const r=localStorage.getItem(SAVEKEY); if(!r){toast('저장된 게임이 없습니다');return;}
    while(stack.length)closeTop();
    applySnapshot(JSON.parse(r)); toast('불러왔습니다');
  }catch(err){ toast('불러오기 실패'); }
};
window.exportGame=()=>{
  if(!started){toast('먼저 게임을 시작하세요');return;}
  const blob=new Blob([JSON.stringify(snapshot())],{type:'application/json'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download=`지하철_${day}일차.json`;
  a.click(); setTimeout(()=>URL.revokeObjectURL(a.href),1000);
  toast('파일로 내보냈습니다');
};
window.importGame=()=>{
  const inp=document.createElement('input');
  inp.type='file'; inp.accept='.json,application/json';
  inp.onchange=()=>{
    const f=inp.files&&inp.files[0]; if(!f)return;
    const rd=new FileReader();
    rd.onload=()=>{ try{
      const o=JSON.parse(rd.result);
      while(stack.length)closeTop();
      applySnapshot(o); saveGame(); toast('가져왔습니다');
    }catch(err){ toast('파일을 읽지 못했습니다'); } };
    rd.readAsText(f);
  };
  inp.click();
};
window.resetGame=()=>{
  try{ localStorage.removeItem(SAVEKEY); }catch(err){}
  location.reload();
};
// 자동 저장: 하루 넘어갈 때 + 창 닫을 때
window.addEventListener('beforeunload',()=>saveGame());
setInterval(()=>saveGame(), 30000);

// 저장된 게임이 있으면 시작 화면에 '이어하기'
(function(){
  const info=savedInfo(); if(!info)return;
  const p=document.getElementById('pick');
  const b=document.createElement('button');
  b.className='pk'; b.style.cssText='grid-column:1/-1;background:#2E7D5B;margin-bottom:4px';
  b.innerHTML='이어하기<small>'+info+'</small>';
  b.onclick=()=>window.loadGame();
  p.parentNode.insertBefore(b, p);
})();

draw();
</script>"""
))
# 하루 넘어갈 때 자동저장 + 독 갱신
reps.append((
"""  if(mins>=1440){mins-=1440;day++;pax=0;rollEvent();updateRep();}""",
"""  if(mins>=1440){mins-=1440;day++;pax=0;rollEvent();updateRep();dock();saveGame();}"""
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
