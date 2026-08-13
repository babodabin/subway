#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
서울지하철 게임 - 노선 확장 데이터 빌드
기존 1~9호선 378역은 그대로 두고, 역_통합표.csv(641역)를 기준으로
신규 17개 노선을 추가한 D 데이터를 만든다.
"""
import csv, json, math, sys
from collections import defaultdict, Counter

B = "/sessions/brave-modest-ramanujan/mnt/지하철/새 폴더/8.11"
LANE_CSV = "/sessions/brave-modest-ramanujan/mnt/uploads/노선_역순서_정리.csv"
OLD_D = "/tmp/oldD.json"

# ---------- 신규 노선: CSV 노선명 -> 게임 노선키 ----------
NEW_LINES = {
    "신분당선": "신분당",
    "경의중앙선": "경의중앙",
    "경춘선": "경춘",
    "분당선": "분당",
    "수인선": "수인",
    "경강선": "경강",
    "서해선": "서해",
    "우이신설선": "우이신설",
    "수도권 경량도시철도 신림선": "신림",
    "김포도시철도": "김포",
    "인천지하철 1호선": "인천1",
    "인천지하철 2호선": "인천2",
    "인천국제공항선": "공항",
    "에버라인": "에버라인",
    "의정부": "의정부",
    "자기부상철도": "자기부상",
    "진접선": "진접",
}
# 노선 색 (실제 노선색 기준)
NEW_COL = {
    "신분당": "#D4003B", "경의중앙": "#77C4A3", "경춘": "#0C8E72", "분당": "#FABE00",
    "수인": "#FABE00", "경강": "#003DA5", "서해": "#8FC31F", "우이신설": "#B0CE18",
    "신림": "#6789CA", "김포": "#A17E46", "인천1": "#7CA8D5", "인천2": "#ED8B00",
    "공항": "#0090D2", "에버라인": "#509F22", "의정부": "#FDA600", "자기부상": "#FFCD12",
    "진접": "#00A5DE",
}
# 표정속도 km/h (공개 자료 기반 근사)
NEW_SPD = {
    "신분당": 45.0, "경의중앙": 45.0, "경춘": 47.0, "분당": 38.0, "수인": 38.0,
    "경강": 55.0, "서해": 42.0, "우이신설": 25.0, "신림": 25.0, "김포": 30.0,
    "인천1": 32.0, "인천2": 30.0, "공항": 55.0, "에버라인": 28.0,
    "의정부": 26.0, "자기부상": 25.0, "진접": 40.0,
}
# 대표역
NEW_REP = {
    "신분당": "판교", "경의중앙": "문산", "경춘": "평내호평", "분당": "서현", "수인": "인천",
    "경강": "여주", "서해": "원시", "우이신설": "북한산우이", "신림": "관악산",
    "김포": "구래", "인천1": "인천대입구", "인천2": "운연", "공항": "인천공항1터미널",
    "에버라인": "전대·에버랜드", "의정부": "탑석", "자기부상": "인천국제공항", "진접": "진접",
}

# ---------- 원본 자료 오류 보정 ----------
# 역_통합표.csv 의 양원역 위경도가 영동선 양원역(경북 봉화) 값으로 잘못 들어가 있어
# 경의중앙선 양원역(서울 중랑구) 실제 좌표로 교정. 망우~양원~구리 구간 190km 오류 수정.
LATLON_FIX = {
    "양원": (37.606500, 127.107800),
}
# 같은 이름 다른 역: 5호선 양평(서울 영등포)과 경의중앙선 양평(경기 양평군)이
# 통합표에 한 역으로 합쳐져 있어, 경의중앙선 쪽을 별도 역으로 분리한다.
SPLIT = {
    ("경의중앙선", "양평"): {
        "새이름": "양평(중앙)", "위도": 37.493500, "경도": 127.489700,
        "등급": "E", "회수일수": 1.0, "하루승차": 1286.0, "관광명물": "", "시도": "경기",
    },
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1); dl = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))

def main():
    master = {r["역명"]: r for r in csv.DictReader(open(f"{B}/역_통합표.csv", encoding="utf-8-sig"))}
    # 위경도 오류 보정
    for n, (la, lo) in LATLON_FIX.items():
        if n in master:
            master[n]["위도"], master[n]["경도"] = str(la), str(lo)
            master[n]["x"], master[n]["y"] = "", ""   # 좌표는 이웃 보간으로 다시 잡음
            print(f"[0] 위경도 보정: {n} -> {la},{lo}")

    lanes = defaultdict(list)
    for r in csv.DictReader(open(LANE_CSV, encoding="utf-8-sig")):
        lanes[r["노선"]].append((int(r["순번"]), r["역명"]))
    for L in lanes: lanes[L].sort()

    # 동명이역 분리
    for (L, orig), spec in SPLIT.items():
        newname = spec["새이름"]
        lanes[L] = [(no, newname if nm == orig else nm) for no, nm in lanes[L]]
        master[newname] = {
            "역명": newname, "시도": spec["시도"], "호선목록": L, "노선수": "1",
            "위도": str(spec["위도"]), "경도": str(spec["경도"]), "x": "", "y": "",
            "등급": spec["등급"], "회수일수": str(spec["회수일수"]),
            "하루승차": str(spec["하루승차"]), "관광명물": spec["관광명물"],
        }
        print(f"[0] 동명이역 분리: {L} 의 {orig} -> {newname}")

    oldD = json.load(open(OLD_D, encoding="utf-8"))
    old_names = oldD["names"]

    # ---------- 1. 역 목록: 기존 378역 먼저(인덱스 보존), 그 뒤 신규역 ----------
    names = list(old_names)
    have = set(names)
    # 신규 노선에 실제로 쓰이는 역만 추가
    used_new = []
    for csvL, key in NEW_LINES.items():
        for _, n in lanes[csvL]:
            if n not in have:
                have.add(n); names.append(n); used_new.append(n)
    N = len(names)
    idx = {n: i for i, n in enumerate(names)}
    print(f"[1] 역 수: 기존 {len(old_names)} + 신규 {len(used_new)} = {N}")

    missing_master = [n for n in names if n not in master]
    if missing_master:
        print("  ! 통합표에 없는 역:", missing_master); sys.exit(1)

    # ---------- 2. 좌표 ----------
    pos = [None]*N
    for i, n in enumerate(names):
        if i < len(old_names):
            pos[i] = oldD["pos"][i]          # 기존역은 기존 좌표 그대로
        else:
            r = master[n]
            if r["x"] and r["y"]:
                pos[i] = [float(r["x"]), float(r["y"])]
    # 좌표 없는 신규역: 같은 노선 이웃 사이 보간
    noxy = [i for i in range(N) if pos[i] is None]
    for _ in range(6):
        fixed = 0
        for i in list(noxy):
            if pos[i] is not None: continue
            cands = []
            for csvL in NEW_LINES:
                seq = [idx[n] for _, n in lanes[csvL] if n in idx]
                if i in seq:
                    k = seq.index(i)
                    prv = next((pos[seq[j]] for j in range(k-1, -1, -1) if pos[seq[j]]), None)
                    nxt = next((pos[seq[j]] for j in range(k+1, len(seq)) if pos[seq[j]]), None)
                    if prv and nxt: cands.append([(prv[0]+nxt[0])/2, (prv[1]+nxt[1])/2])
                    elif prv: cands.append(prv)
                    elif nxt: cands.append(nxt)
            if cands:
                pos[i] = [sum(c[0] for c in cands)/len(cands), sum(c[1] for c in cands)/len(cands)]
                fixed += 1
        if fixed == 0: break
    # 이웃이 전부 없는 노선(예: 자기부상철도)은 위경도->x,y 선형변환으로 대체
    still = [i for i in range(N) if pos[i] is None]
    if still:
        pts = [(float(master[n]["경도"]), float(master[n]["위도"]), pos[i][0], pos[i][1])
               for i, n in enumerate(names) if pos[i] is not None
               and master[n]["위도"] and master[n]["경도"]]
        def fit(xs, ys):
            k = len(xs); mx = sum(xs)/k; my = sum(ys)/k
            b = sum((x-mx)*(y-my) for x, y in zip(xs, ys))/sum((x-mx)**2 for x in xs)
            return my - b*mx, b
        ax, bx = fit([p[0] for p in pts], [p[2] for p in pts])
        ay, by = fit([p[1] for p in pts], [p[3] for p in pts])
        for i in still:
            r = master[names[i]]
            pos[i] = [ax + bx*float(r["경도"]), ay + by*float(r["위도"])]
        print(f"  · 위경도 변환으로 채운 역 {len(still)}개: {[names[i] for i in still]}")
    interp = [names[i] for i in noxy]
    print(f"[2] 좌표: 보간으로 채운 신규역 {len(interp)}개 {interp[:8]}{'...' if len(interp)>8 else ''}")

    # ---------- 3. 등급 / 회수일수 / 하루승차 / 명물 ----------
    E_MEDIAN = 1286.0   # 통합표 E등급 하루승차 중앙값 (하루승차 결측 보정용)
    grade = [None]*N; pay = [0.0]*N; board = [0.0]*N; fame = [""]*N
    imputed = []
    for i, n in enumerate(names):
        r = master[n]
        grade[i] = r["등급"]
        pay[i] = float(r["회수일수"]) if r["회수일수"] else 1.0
        if r["하루승차"]:
            board[i] = float(r["하루승차"])
        else:
            board[i] = E_MEDIAN; imputed.append(n)
        # 명물: 기존 378역은 게임에 있던 이모지를 그대로 보존(통합표는 Y 플래그뿐).
        # 신규역은 통합표가 Y 인 경우만 기본 아이콘.
        if i < len(old_names):
            fame[i] = oldD["fame"][i]
        else:
            fame[i] = "📍" if r["관광명물"].strip() else ""
    use = [b*2 for b in board]
    print(f"[3] 등급/회수일수 완료. 하루승차 결측 보정(E중앙값 {E_MEDIAN:.0f}): {len(imputed)}역")

    # ---------- 4. 노선 ----------
    lines = {}
    for L, arr in oldD["lines"].items():
        lines[L] = list(arr)                  # 기존 1~9호선 그대로
    for csvL, key in NEW_LINES.items():
        lines[key] = [idx[n] for _, n in lanes[csvL] if n in idx]
    loop = list(oldD["loop"])
    print(f"[4] 노선 {len(lines)}개 (기존 9 + 신규 {len(NEW_LINES)})")

    # ---------- 5. 구간 거리 ----------
    km = dict(oldD["km"])
    added = 0
    for key in NEW_LINES.values():
        seq = lines[key]
        for a, b in zip(seq, seq[1:]):
            k1, k2 = f"{a}_{b}", f"{b}_{a}"
            if k1 in km or k2 in km: continue
            ra, rb = master[names[a]], master[names[b]]
            d = haversine(float(ra["위도"]), float(ra["경도"]), float(rb["위도"]), float(rb["경도"]))
            km[k1] = round(max(d, 0.3), 3); added += 1
    print(f"[5] 구간거리: 기존 {len(oldD['km'])} + 신규 {added} = {len(km)}")

    # ---------- 6. OD (평일/토/일) 전체 표에서 재구축 ----------
    def load_od(path):
        flat = []; tot = 0.0; skipped = 0
        with open(path, encoding="utf-8-sig") as f:
            rd = csv.reader(f); next(rd)
            for row in rd:
                if len(row) < 3: continue
                o, d, c = row[0], row[1], row[2]
                if o == d: continue
                if o not in idx or d not in idx: skipped += 1; continue
                try: c = float(c)
                except: continue
                flat += [idx[o], idx[d], round(c, 2)]; tot += c
        return flat, tot, skipped

    od_wd, t_wd, s_wd = load_od(f"{B}/역간_수요표_수도권.csv")
    od_sat, t_sat, s_sat = load_od("/sessions/brave-modest-ramanujan/mnt/uploads/역간_수요표_토요일.csv")
    od_sun, t_sun, s_sun = load_od("/sessions/brave-modest-ramanujan/mnt/uploads/역간_수요표_일요일.csv")
    print(f"[6] OD 평일 {len(od_wd)//3}쌍 합계 {t_wd:,.0f} (제외 {s_wd})")
    print(f"    토요일 {len(od_sat)//3}쌍 합계 {t_sat:,.0f}  비율 {t_sat/t_wd:.3f}")
    print(f"    일요일 {len(od_sun)//3}쌍 합계 {t_sun:,.0f}  비율 {t_sun/t_wd:.3f}")

    # ---------- 7. 대표역 ----------
    rep = dict(oldD["rep"])
    for key, r in NEW_REP.items():
        if r in idx: rep[key] = r
        else:
            seq = lines[key]
            rep[key] = names[seq[len(seq)//2]]
            print(f"    ! 대표역 '{r}' 없음 -> {key}: {rep[key]} 로 대체")

    D = {
        "names": names, "pos": pos, "lines": lines, "loop": loop, "km": km,
        "grade": grade, "use": use, "board": board, "pay": pay, "fame": fame,
        "hour": oldD["hour"], "od": od_wd, "rep": rep, "river": oldD["river"],
    }
    json.dump(D, open("/tmp/newD.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump({"sat": od_sat, "sun": od_sun}, open("/tmp/newDT.json", "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))

    # 위경도 (짧은거리 제외용)
    LL = [[round(float(master[n]["위도"]), 6), round(float(master[n]["경도"]), 6)] for n in names]
    json.dump(LL, open("/tmp/newLL.json", "w", encoding="utf-8"), separators=(",", ":"))

    meta = {"lineKeys": list(lines.keys()), "newKeys": list(NEW_LINES.values()),
            "col": NEW_COL, "spd": NEW_SPD}
    json.dump(meta, open("/tmp/newMeta.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[7] 완료. 총 {N}역, 노선 {len(lines)}개")

if __name__ == "__main__":
    main()
