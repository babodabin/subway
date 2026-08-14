#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
역별 '성격' 만들기 — 점포 업종 궁합에 쓴다.

수도권 생활이동(행정동 단위) 자료의 이동목적별 인원을
지역_역_배분표로 역에 배분해서, 역마다 어떤 손님이 오는지 지표를 만든다.
목적 코드: 1 출근 · 2 등교 · 3 귀가 · 4 쇼핑 · 5 관광 · 6 병원 · 7 기타
(출처: 서울시 빅데이터 캠퍼스 '수도권 생활이동' 자료안내서)

★ 도착지(d_admdong_cd) 기준으로 센다.
  출발지로 세면 '출근하러 떠나는 동네'가 직장으로 잡혀 뜻이 뒤집힌다.
  어디로 가는가가 그 동네의 성격이다 — 출근이 몰리는 곳이 직장가,
  귀가가 몰리는 곳이 주거지, 병원이 몰리는 곳이 병원가.

결과: /tmp/charData.json  = { 역이름: [직장, 학생, 쇼핑, 관광, 병원, 주거] }
      각 값은 전체 평균을 1.0 으로 놓은 상대값(0.2~3.0).
"""
import csv, glob, json, statistics
from collections import defaultdict

BASE = "/sessions/brave-modest-ramanujan/mnt/지하철/새 폴더/8.11"
ALLOC = f"{BASE}/지역_역_배분표_최종.csv"
MOVE_GLOB = f"{BASE}/수도권 생활이동 (출발-도착지 기준)/*final*.csv"

# 성격 6가지 <- 도착 이동목적
#  직장 = 출근(1) 도착, 학생 = 등교(2) 도착, 쇼핑 = 쇼핑(4) 도착,
#  관광 = 관광(5) 도착 + 외국인비중, 병원 = 병원(6) 도착, 주거 = 귀가(3) 도착
KEYS = ["직장", "학생", "쇼핑", "관광", "병원", "주거"]


def main():
    # ---------- 1. 행정동별 목적 인원 (여러 날 합산) ----------
    dong = defaultdict(lambda: defaultdict(float))
    forn = defaultdict(lambda: [0.0, 0.0])
    files = sorted(glob.glob(MOVE_GLOB))
    print(f"[1] 생활이동 파일 {len(files)}개")
    for f in files:
        n = 0
        with open(f, encoding="utf-8") as fh:
            r = csv.reader(fh); next(r, None)
            for row in r:
                if len(row) < 10: continue
                try: c = float(row[9])
                except ValueError: continue
                dong[row[1]][row[6]] += c          # row[1] = 도착 행정동
                forn[row[1]][0 if row[4] == "내국인" else 1] += c
                n += 1
        print(f"    {f.split('/')[-1]}: {n:,}행")
    print(f"    도착 행정동 {len(dong):,}개")

    # ---------- 2. 역에 배분 ----------
    stn = defaultdict(lambda: defaultdict(float))
    stnf = defaultdict(lambda: [0.0, 0.0])
    for r in csv.DictReader(open(ALLOC, encoding="utf-8-sig")):
        d, s, w = r["지역코드"], r["역명"], float(r["가중치"])
        if d not in dong: continue
        for p, c in dong[d].items(): stn[s][p] += c * w
        stnf[s][0] += forn[d][0] * w
        stnf[s][1] += forn[d][1] * w
    print(f"[2] 목적 자료가 붙은 역 {len(stn)}개")

    # ---------- 3. 비중 -> 평균 1.0 상대값 ----------
    raw = {}
    for s, t in stn.items():
        tot = sum(t.values()) or 1.0
        f = stnf[s]; fr = f[1] / (f[0] + f[1]) if (f[0] + f[1]) else 0.0
        raw[s] = {
            "직장": t.get("1", 0) / tot,
            "학생": t.get("2", 0) / tot,
            "쇼핑": t.get("4", 0) / tot,
            "관광": t.get("5", 0) / tot + fr * 0.05,   # 관광은 표본이 작아 외국인비중을 섞는다
            "병원": t.get("6", 0) / tot,
            "주거": t.get("3", 0) / tot,
        }
    means = {k: statistics.mean(v[k] for v in raw.values()) or 1e-9 for k in KEYS}
    print("[3] 평균 비중:", {k: f"{means[k]*100:.2f}%" for k in KEYS})

    out = {}
    for s, v in raw.items():
        out[s] = [round(min(3.0, max(0.2, v[k] / means[k])), 2) for k in KEYS]

    # ---------- 4. 게임 역 목록에 맞추기 ----------
    D = json.load(open("/tmp/newD.json", encoding="utf-8"))
    names = D["names"]
    arr, miss = [], []
    for n in names:
        if n in out: arr.append(out[n])
        else:
            arr.append([1.0] * len(KEYS)); miss.append(n)
    print(f"[4] 게임 {len(names)}역 중 자료 있음 {len(names)-len(miss)}, 없음 {len(miss)} (평균값으로 채움)")

    json.dump({"keys": KEYS, "char": arr}, open("/tmp/charData.json", "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))

    # ---------- 5. 확인 ----------
    idx = {n: i for i, n in enumerate(names)}
    print("\n[5] 성격이 뚜렷한 역 (평균 1.0 기준)")
    for k in KEYS:
        j = KEYS.index(k)
        top = sorted(((arr[idx[n]][j], n) for n in names if n in out), reverse=True)[:5]
        print(f"    {k}: " + ", ".join(f"{n}({v:.1f})" for v, n in top))
    print("\n    예시 역")
    for n in ["강남", "명동", "혜화", "흑석", "잠실", "상계", "여의도"]:
        if n in idx:
            print(f"      {n}: " + " ".join(f"{k}{arr[idx[n]][i]:.1f}" for i, k in enumerate(KEYS)))


if __name__ == "__main__":
    main()
