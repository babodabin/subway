#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v11 -> v12 : 점포(업종) 시스템
 - 역마다 손님 성격이 다르고(생활이동 도착 목적 기준), 업종마다 잘 맞는 성격이 다르다.
 - 잘 맞는 업종을 넣으면 많이 벌고, 안 맞으면 못 번다.
 - 어느 업종이 잘될지 미리 보여주고, 연 뒤에는 실제 매출을 보여준다.
"""
import sys, json

SRC = "/tmp/game_v11.html"
DST = "/tmp/game_v12.html"
s = open(SRC, encoding="utf-8").read()
ch = json.load(open("/tmp/charData.json", encoding="utf-8"))
orig = len(s)
J = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))
reps = []

# ── 1. 역 성격 자료 ───────────────────────────────────
reps.append((
"""/* ---------- 역별 실제 위경도 (노선_역순서_정리.csv, D.names 순서와 매칭) ---------- */""",
"""/* ---------- 역별 손님 성격 ----------
   수도권 생활이동(도착 목적 기준)을 지역_역_배분표로 역에 배분해 만든 값.
   [직장, 학생, 쇼핑, 관광, 병원, 주거] 순서, 전체 평균이 1.00.
   자료가 없는 111개 역은 전부 1.00(평범)으로 뒀다. */
const CHKEY=""" + J(ch["keys"]) + """;
const CH=""" + J(ch["char"]) + """;
/* ---------- 역별 실제 위경도 (노선_역순서_정리.csv, D.names 순서와 매칭) ---------- */"""
))

# ── 2. 업종 정의 ─────────────────────────────────────
reps.append((
"""  retail:{slots:{SS:8,S:8,A:6,B:4,C:3,D:2,E:1}, monthlyShare:0.4},
                                              // 상가: 칸수 등급별, 칸당 월수입=하루수입×0.4""",
"""  retail:{slots:{SS:8,S:8,A:6,B:4,C:3,D:2,E:1}, monthlyShare:0.4},
                                              // 상가: 칸수 등급별, 칸당 월수입=하루수입×0.4
  // 업종. w = [직장,학생,쇼핑,관광,병원,주거] 궁합. 역 성격과 곱해서 매출 배수를 낸다.
  // base 는 업종 자체의 기본 수익성. 수치는 설계값이며 CFG 에서 바꿀 수 있다.
  shops:[
    {n:'편의점',   e:'🏪', base:1.00, w:[1.0,1.0,1.0,1.0,1.0,1.0]},
    {n:'카페',     e:'☕', base:1.05, w:[1.8,1.2,1.1,1.1,0.8,0.7]},
    {n:'분식·간식',e:'🍢', base:0.95, w:[0.9,2.0,1.0,1.1,0.6,1.0]},
    {n:'문구·서점',e:'📚', base:0.85, w:[0.8,2.1,0.7,0.5,0.6,0.9]},
    {n:'화장품',   e:'💄', base:1.10, w:[1.0,1.2,2.0,1.4,0.5,0.6]},
    {n:'빵집',     e:'🥐', base:1.00, w:[1.1,0.9,1.0,0.8,1.5,1.5]},
    {n:'약국',     e:'💊', base:0.95, w:[0.7,0.7,0.6,0.5,2.6,1.2]},
    {n:'기념품·환전',e:'🎁',base:0.90, w:[0.6,0.6,1.3,2.6,0.4,0.4]},
    {n:'반찬가게', e:'🍱', base:0.90, w:[0.7,0.6,0.9,0.4,1.1,2.0]},
    {n:'옷·잡화',  e:'👕', base:1.05, w:[1.0,1.1,2.1,1.2,0.5,0.7]}
  ],
  shopSpan:0.65,   // 궁합이 매출에 얼마나 세게 반영되는지 (0이면 업종 상관없음)"""
))

# ── 3. 점포 계산 함수 ────────────────────────────────
reps.append((
"""const namingMult=(i)=>CFG.naming.mult[D.grade[i]]??CFG.naming.mult['E'];
const retailMax=(i)=>CFG.retail.slots[D.grade[i]]??CFG.retail.slots['E'];""",
"""const namingMult=(i)=>CFG.naming.mult[D.grade[i]]??CFG.naming.mult['E'];
const retailMax=(i)=>CFG.retail.slots[D.grade[i]]??CFG.retail.slots['E'];
// 업종 궁합: 역 성격과 업종 가중치를 곱해 평균낸 뒤, 1.0 기준으로 벌린다.
function shopFit(i,sid){
  const sh=CFG.shops[sid], c=CH[i]||[1,1,1,1,1,1];
  let num=0,den=0;
  for(let k=0;k<sh.w.length;k++){ num+=c[k]*sh.w[k]; den+=sh.w[k]; }
  const raw=den?num/den:1;                       // 1.0 = 평범한 역
  return Math.max(0.35, Math.min(2.4, 1+(raw-1)*(1+CFG.shopSpan)))*sh.base;
}
function shopRevenue(i,sid){ return dayRev(i)*CFG.retail.monthlyShare*shopFit(i,sid)/30; }
function shopsAt(i){ return retail.get(i)||[]; }
function bestShops(i){
  return CFG.shops.map((sh,k)=>({k,sh,fit:shopFit(i,k)})).sort((a,b)=>b.fit-a.fit);
}
// 역 성격을 말로: 평균보다 뚜렷하게 높은 것만 골라 보여준다
function charText(i){
  const c=CH[i]; if(!c)return '';
  const t=CHKEY.map((k,j)=>({k,v:c[j]})).filter(x=>x.v>=1.35).sort((a,b)=>b.v-a.v);
  return t.length? t.slice(0,3).map(x=>x.k).join('·')+' 손님이 많은 역' : '고른 손님이 오는 역';
}"""
))

# ── 4. 수입 계산: 업종별 ─────────────────────────────
reps.append((
"""  for(const [i,cnt] of retail){ s+=dayRev(i)*CFG.retail.monthlyShare*cnt/30; }""",
"""  for(const [i,arr] of retail){ for(const sid of arr) s+=shopRevenue(i,sid); }"""
))

# ── 5. 평판의 상가 점수: 칸 수 기준 유지 ─────────────
reps.append((
"""  for(let i=0;i<N;i++){ if(!anyBuilt(i))continue; maxSlots+=retailMax(i); openSlots+=(retail.get(i)||0); }""",
"""  for(let i=0;i<N;i++){ if(!anyBuilt(i))continue; maxSlots+=retailMax(i); openSlots+=shopsAt(i).length; }"""
))

# ── 6. 점포 열기 ─────────────────────────────────────
reps.append((
"""window.openRetail=(i)=>{if(!anyBuilt(i))return; const cur=retail.get(i)||0, max=retailMax(i);
  if(cur>=max)return; retail.set(i,cur+1); toast(D.names[i]+' 상가 '+(cur+1)+'/'+max+'칸'); refresh(); saveGame();};""",
"""window.openShop=(i,sid)=>{
  if(!anyBuilt(i))return;
  const arr=shopsAt(i).slice(), max=retailMax(i);
  if(arr.length>=max)return;
  arr.push(sid); retail.set(i,arr);
  const sh=CFG.shops[sid];
  toast(sh.e+' '+sh.n+' 열었습니다 · 월 '+won(shopRevenue(i,sid)*30));
  refresh(); saveGame();
};
window.closeShop=(i,slot)=>{
  const arr=shopsAt(i).slice(); if(slot<0||slot>=arr.length)return;
  const sh=CFG.shops[arr[slot]]; arr.splice(slot,1); retail.set(i,arr);
  toast(sh.n+' 닫았습니다'); refresh(); saveGame();
};
window.pickShop=(i)=>go('shop');"""
))

# ── 7. 역 화면: 상가 줄 교체 ─────────────────────────
reps.append((
"""      const rc=retail.get(i)||0, rmax=retailMax(i);
      h+=`<div class="row"><span>상가 ${rc}/${rmax}칸</span>${rc<rmax?`<button class="act" onclick="openRetail(${i})">칸 열기 (월 ${won(dayRev(i)*CFG.retail.monthlyShare)})</button>`:`<span style="color:var(--soft)">가득 참</span>`}</div>`;
    }
    return h;""",
"""      const arr=shopsAt(i), rmax=retailMax(i);
      h+=`<div class="sect">상가 ${arr.length}/${rmax}칸</div>`;
      if(arr.length){
        arr.forEach((sid,k)=>{
          const sh=CFG.shops[sid], f=shopFit(i,sid);
          h+=`<div class="row"><span>${sh.e} ${sh.n}
            <span style="color:${f>=1.25?'#1B7F4B':(f<0.8?'var(--hot)':'var(--soft)')}">${f>=1.25?'잘 됨':(f<0.8?'안 됨':'보통')}</span></span>
            <span>월 ${won(shopRevenue(i,sid)*30)}
            <button class="mini" onclick="closeShop(${i},${k})">닫기</button></span></div>`;
        });
      }
      if(arr.length<rmax){
        h+=`<div class="row"><span style="color:var(--soft)">빈 칸 ${rmax-arr.length}개</span>
          <button class="act" onclick="pickShop(${i})">업종 고르기</button></div>`;
      }else{
        h+=`<div class="n2">칸이 다 찼습니다. 바꾸려면 닫고 다시 여세요.</div>`;
      }
    }
    return h;"""
))

# ── 8. 역 화면 머리에 성격 한 줄 ─────────────────────
reps.append((
"""      <div class="n2">등급 ${D.grade[i]} · 하루 ${D.use[i].toLocaleString()}명 · 수입 ${won(dayRev(i))}/일</div>`;""",
"""      <div class="n2">등급 ${D.grade[i]} · 하루 ${D.use[i].toLocaleString()}명 · 수입 ${won(dayRev(i))}/일</div>
      <div class="n2">${charText(i)}</div>`;"""
))

# ── 9. 업종 고르기 화면 ──────────────────────────────
reps.append((
"""  else if(t==='time'){""",
"""  else if(t==='shop'){
    const i=sel;
    if(i<0||!anyBuilt(i))return '<div class="n1">역을 먼저 고르세요</div>';
    const arr=shopsAt(i), rmax=retailMax(i);
    const c=CH[i]||[1,1,1,1,1,1];
    let h=`<div class="n1">${D.names[i]}</div>
      <div class="n2">${charText(i)} · 빈 칸 ${rmax-arr.length}개</div>
      <div class="sect">이 역 손님</div>`;
    CHKEY.forEach((k,j)=>{
      const v=c[j], pc=Math.min(100,v/3*100);
      h+=`<div class="row" style="border:0;padding:3px 0"><span style="width:44px">${k}</span>
        <span class="bar" style="flex:1;width:auto"><i style="width:${pc}%;background:${v>=1.35?'#1B7F4B':'var(--ink)'}"></i></span>
        <span style="width:34px;text-align:right">${v.toFixed(1)}</span></div>`;
    });
    h+=`<div class="sect">업종 (잘 맞는 순서)</div>`;
    if(arr.length>=rmax) h+=`<div class="n2">칸이 다 찼습니다.</div>`;
    for(const {k,sh,fit} of bestShops(i)){
      const rev=shopRevenue(i,k)*30;
      const tag = fit>=1.25?'<span style="color:#1B7F4B">잘 됨</span>'
                : fit<0.8 ?'<span style="color:var(--hot)">안 됨</span>'
                :          '<span style="color:var(--soft)">보통</span>';
      h+=`<div class="row"><span>${sh.e} ${sh.n} ${tag}</span>
        <span>월 ${won(rev)}
        <button class="act" ${arr.length>=rmax?'disabled':''} onclick="openShop(${i},${k})">열기</button></span></div>`;
    }
    return h;
  }
  else if(t==='time'){"""
))
reps.append((
"""const TITLE={stn:'역',line:'노선',train:'열차',jam:'혼잡',rep:'평판',time:'시간',save:'설정'};""",
"""const TITLE={stn:'역',line:'노선',train:'열차',jam:'혼잡',rep:'평판',time:'시간',save:'설정',shop:'업종 고르기'};"""
))

# ── 10. 저장 형식: retail 값이 배열 ──────────────────
reps.append((
"""  retail.clear(); (o.retail||[]).forEach(([k,v])=>retail.set(+k,v));""",
"""  retail.clear();
  (o.retail||[]).forEach(([k,v])=>retail.set(+k, Array.isArray(v)?v : Array(v).fill(0)));
  // 예전 저장(숫자 칸수)은 편의점으로 채워 넣는다"""
))

# ── 11. 노선 화면에 전체 진행률 ──────────────────────
reps.append((
"""    let h='<div class="n1">노선</div><div class="n2">80%를 짓고 대표역을 지으면 다음 노선이 열립니다</div>';""",
"""    let tb=0,tt=0;
    for(const L of activeLines()){ tt+=D.lines[L].length; tb+=D.lines[L].filter(i=>isBuilt(L,i)).length; }
    const bc=new Set([...built].map(x=>+x.split(':')[1])).size;
    let h=`<div class="big">${tt?(tb/tt*100).toFixed(0):0}<span style="font-size:15px;color:var(--soft)">%</span></div>
      <div class="gauge"><i style="width:${tt?(tb/tt*100):0}%"></i></div>
      <div class="n2">승강장 ${tb.toLocaleString()} / ${tt.toLocaleString()} · 역 ${bc.toLocaleString()}곳</div>
      <div class="n2">80%를 짓고 대표역을 지으면 다음 노선이 열립니다</div><div class="sect">노선</div>`;"""
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
