#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v6 -> v7 : 이벤트 실측 반영 + 폭염/시위 추가
"""
import sys

SRC = "/tmp/game_v6.html"
DST = "/tmp/game_v7.html"
s = open(SRC, encoding="utf-8").read()
orig = len(s)
reps = []

# ---------- 1. CFG.events 교체 ----------
reps.append((
"""  events:[  // 수치는 실측 데이터 없이 정한 설계값. demandMult=수요 배수, capMult=수송력 배수(낮을수록 열차 덜 다니는 효과), days=지속일, chance=매일 발생 확률, line=특정 호선에만 적용
    {type:'비',   emoji:'🌧️', demandMult:1.10, capMult:0.90, days:1, chance:0.08, line:false},
    {type:'눈',   emoji:'❄️', demandMult:1.20, capMult:0.70, days:1, chance:0.02, line:false},
    {type:'명절', emoji:'🏠', demandMult:0.50, capMult:1.00, days:3, chance:0.01, line:false},
    {type:'축제', emoji:'🎉', demandMult:1.30, capMult:1.00, days:1, chance:0.03, line:false},
    {type:'파업', emoji:'✊', demandMult:1.00, capMult:0.40, days:1, chance:0.01, line:true}
  ]""",
"""  // mult = 요일별 수요 배수 {wd:평일, sat:토, sun:일}, cap = 수송력 배수, days = 지속일,
  // chance = 하루 발생 확률, line=true 면 열린 노선 중 하나에만 적용
  // src:'실측' = 공개 통계 근거 있음 / src:'설계' = 근거 자료 없이 정한 값
  events:[
    // 서울교통공사 2025년 실적 분석(2026-06 발표): 일강수량 10mm 이상인 날 이용객 -3.5%,
    // 주말 -5.6%, 일요일 -8.4%. 빈도는 기상청 평년 강수일수 108.8일/년 중 10mm 이상 비율로 추정.
    {type:'비',   emoji:'🌧️', mult:{wd:0.965, sat:0.944, sun:0.916}, cap:0.95, days:1, chance:0.11, line:false, src:'실측'},
    // 같은 분석: 일최고 33도 이상인 날 -3.5%, 토요일 -7.2%.
    {type:'폭염', emoji:'🥵', mult:{wd:0.965, sat:0.928, sun:0.945}, cap:1.00, days:1, chance:0.04, line:false, src:'실측'},
    // 아래는 근거 자료를 찾지 못해 정한 설계값입니다. 언제든 바꾸셔도 됩니다.
    {type:'눈',   emoji:'❄️', mult:{wd:1.05, sat:0.95, sun:0.90}, cap:0.70, days:1, chance:0.02, line:false, src:'설계'},
    {type:'명절', emoji:'🏠', mult:{wd:0.50, sat:0.55, sun:0.55}, cap:1.00, days:3, chance:0.01, line:false, src:'설계'},
    {type:'축제', emoji:'🎉', mult:{wd:1.15, sat:1.30, sun:1.30}, cap:1.00, days:1, chance:0.03, line:false, src:'설계'},
    {type:'파업', emoji:'✊', mult:{wd:1.00, sat:1.00, sun:1.00}, cap:0.40, days:1, chance:0.008, line:true, src:'설계'},
    {type:'시위', emoji:'📢', mult:{wd:1.05, sat:1.10, sun:1.10}, cap:0.85, days:1, chance:0.012, line:true, src:'설계'}
  ]"""
))

# ---------- 2. 수요 배수: 요일별 ----------
reps.append((
"""  const evMult=event?event.demandMult:1;""",
"""  const evMult=eventMult();"""
))
reps.append((
"""function dayRevenueNow(){return servedDaily*(event?event.demandMult:1)*CFG.fare+extraDailyIncome();}""",
"""function eventMult(){return event?(event.mult[dayType]??1):1;}
function dayRevenueNow(){return servedDaily*eventMult()*CFG.fare+extraDailyIncome();}"""
))

# ---------- 3. 수송력 배수: capMult -> cap ----------
reps.append((
"""  if(event&&(!event.line||event.affectedLine===L)) cm=event.capMult;""",
"""  if(event&&(!event.line||event.affectedLine===L)) cm=event.cap;"""
))

# ---------- 4. 혼잡도에도 이벤트 수요 반영 ----------
reps.append((
"""  const load=(linkLoad[L+':'+a+':'+b]||0)*hourW(h)/2;   // 방향 절반""",
"""  const load=(linkLoad[L+':'+a+':'+b]||0)*hourW(h)/2*eventMult();   // 방향 절반"""
))

# ---------- 5. 평판 탭에 현재 이벤트 표시 ----------
reps.append((
"""      <div class="row"><span>역명 병기 (−5)</span><span>${c.namingPenalty.toFixed(1)}</span></div>`;
    P.innerHTML=h;""",
"""      <div class="row"><span>역명 병기 (−5)</span><span>${c.namingPenalty.toFixed(1)}</span></div>`;
    if(event){
      const pct=((eventMult()-1)*100).toFixed(1);
      h+=`<div class="row"><span>${event.emoji} ${event.type}${event.affectedLine?' ('+NAME[event.affectedLine]+')':''}</span>
        <span>수요 ${pct>=0?'+':''}${pct}% · 수송력 ${(event.cap*100).toFixed(0)}% · ${event.daysLeft}일 남음</span></div>`;
    }
    P.innerHTML=h;"""
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
