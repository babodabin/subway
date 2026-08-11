# -*- coding: utf-8 -*-
"""게임이 바로 읽을 수 있는 판 데이터를 만든다 → game/board.js

담기는 것
  - 공식 노선도 SVG 전체 (밑그림)
  - 9호선 역 38개: 이름·좌표·환승 여부·등급·하루 이용객
  - 역과 역 사이 선 모양 (노선도 곡선을 그대로 잘라 쓴다)

이용객·등급은 data/ 에 실제 자료가 있으면 그걸 쓰고, 없으면 임시값으로 돈다.
  역별_승하차_시간대별_수도권.csv
  역_등급.csv
넣기만 하면 자동으로 잡힌다. tools/load_ridership.py 참고.

있으면 같이 쓰는 것 (없어도 돈다)
  구간별_승객량.csv    구간마다 실제로 몇 명이 지나가는지 → 혼잡도 보정
  역_외국인비중.csv    단기외국인 비중 → 명물 (점수는 아직 안 매긴다)
"""
import csv
import json
import math
import pathlib
import re

import svgpath
from load_ridership import load_ridership, load_grades

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINE_COLOR = "#a49d87"
LINE_NAME = "9호선"

html = (ROOT / "data" / "공식노선도_환승표시.html").read_text(encoding="utf-8")

# --- 밑그림 SVG ----------------------------------------------------------
m = re.search(r'(<svg id="m".*?</svg>)', html, re.S)
svg = m.group(1)
# 원마다 번호를 달아 게임이 집을 수 있게 한다
n = [0]


def tag_circle(mo):
    s = mo.group(0)[:-1] + ' id="c%d"/>' % n[0]
    n[0] += 1
    return s


svg = re.sub(r"<circle[^>]*/>", tag_circle, svg)

# --- 9호선 역 순서 -------------------------------------------------------
order = [
    r["역명"]
    for r in csv.DictReader((ROOT / "data" / "노선_역순서_정리.csv").open(encoding="utf-8-sig"))
    if r["노선"] in ("서울 도시철도 9호선", "수도권  도시철도 9호선")
]

named = {}
for r in csv.DictReader((ROOT / "data" / "노선도_역이름.csv").open(encoding="utf-8")):
    if LINE_COLOR not in r["색목록"] or not r["역명"]:
        continue
    named.setdefault(r["역명"], []).append(r)

master = {}
for r in csv.DictReader((ROOT / "data" / "역_마스터_수도권.csv").open(encoding="utf-8-sig")):
    master[r["역명"]] = r

# --- 실제 자료가 있으면 쓴다 --------------------------------------------
print("자료 확인")
REAL = load_ridership()
REAL_GRADE = load_grades()
USING_REAL = bool(REAL)


def _opt(name):
    p = ROOT / "data" / name
    if not p.exists():
        print("  %s 없음 (없어도 됩니다)" % name)
        return None
    return list(csv.DictReader(p.open(encoding="utf-8-sig")))


# 구간마다 실제로 지나가는 인원 (하루, 양방향 합)
_rows = _opt("구간별_승객량.csv")
SEG_PAX = {frozenset((r["역A"], r["역B"])): float(r["인원"]) for r in _rows} if _rows else {}
if _rows:
    print("  구간별 승객량: 구간 %d개" % len(SEG_PAX))

# 단기외국인 비중 (%). 명물 판단에 쓴다
_rows = _opt("역_외국인비중.csv")
TOURIST = {r["역명"]: float(r["단기비중"]) for r in _rows} if _rows else {}
if _rows:
    print("  외국인비중: 역 %d개" % len(TOURIST))

# 공항 효과는 관광이 아니다 — 정리 문서 2장이 이 역들을 이름까지 짚어 제외했다.
# (개화 21% · 개화산 15% · 방화 12%). 공항역 자체도 같은 이유로 뺀다.
AIRPORT = {"개화", "개화산", "방화", "김포공항", "공항시장", "공항화물청사",
           "인천공항1터미널", "인천공항2터미널", "영종", "운서"}
LANDMARK_MIN = 10.0        # 관광 명물로 볼 단기외국인 비중 (문서의 6개가 10.5% 이상)

# --- 임시 이용객·등급 ----------------------------------------------------
# 규칙: 환승 노선 수와 '특별역' 여부로만 만든 대용값. 실제 자료가 아니다.
SPECIAL = {"고속터미널": 2.0, "여의도": 1.9, "노량진": 1.5, "당산": 1.4, "신논현": 1.7,
           "종합운동장": 1.3, "김포공항": 1.5, "선정릉": 1.3, "가양": 1.2, "염창": 1.2}
GRADE_DAYS = {"E": 1.0, "D": 1.5, "C": 2.0, "B": 3.0, "A": 5.0, "S": 8.0}


# 도심에 가까울수록 큰 역이 되도록 완만한 기울기를 준다 (임시 규칙)
CORE = (37.5045, 127.0245)  # 신논현 근처


def provisional(name):
    r = master.get(name, {})
    lines = int(r.get("노선수", 1))
    base = 9000 * (lines ** 1.35) * SPECIAL.get(name, 1.0)
    if r:
        d = math.hypot(
            (float(r["위도"]) - CORE[0]) * 111.0,
            (float(r["경도"]) - CORE[1]) * 88.0,
        )
        base *= 1.9 * math.exp(-d / 11.0) + 0.55
    return int(round(base / 100.0) * 100)


def grade_of(riders):
    for g, lo in (("S", 90000), ("A", 55000), ("B", 33000), ("C", 20000), ("D", 12000)):
        if riders >= lo:
            return g
    return "E"


DEFAULT_PEAK = 0.09   # 시간대 자료가 없을 때 쓰는 첨두 1시간 비중


def riders_of(name):
    """(하루 이용객, 첨두비중, 실제자료인가)"""
    if REAL:
        r = REAL.get(name)
        if r and r["riders"] > 0:
            return r["riders"], (r["peak"] or DEFAULT_PEAK), True
    return provisional(name), DEFAULT_PEAK, False


def grade_for(name, riders):
    g = REAL_GRADE.get(name) if REAL_GRADE else None
    return g or grade_of(riders)


# --- 노선 위 위치 --------------------------------------------------------
polys = []
for mo in re.finditer(r"<path([^>]*)>", html):
    a = mo.group(1)
    s = re.search(r'stroke="(%s)"' % LINE_COLOR, a)
    d = re.search(r'\bd="([^"]+)"', a)
    if s and d and len(d.group(1)) > 60:
        polys.extend(p for p in svgpath.flatten(d.group(1)) if len(p) > 1)
poly = max(polys, key=len)

stations = []
missing = []
for name in order:
    rows = named.get(name)
    if not rows:
        raise SystemExit("이름 못 찾음: %s" % name)
    x = sum(float(r["x"]) for r in rows) / len(rows)
    y = sum(float(r["y"]) for r in rows) / len(rows)
    riders, peak, is_real = riders_of(name)
    g = grade_for(name, riders)
    if not is_real:
        missing.append(name)
    stations.append(
        {
            "name": name,
            "x": round(x, 2),
            "y": round(y, 2),
            "ids": [int(r["id"]) for r in rows],
            "xfer": any(r["환승"] == "Y" for r in rows),
            "lines": master.get(name, {}).get("호선목록", LINE_NAME).split("|"),
            "riders": riders,
            "peak": peak,              # 하루 이용객 중 첨두 1시간 비중
            "grade": g,
            "paybackDays": GRADE_DAYS[g],
            "tourist": TOURIST.get(name),   # 단기외국인 비중 %. 점수는 아직 안 매긴다
            "landmark": bool(TOURIST.get(name, 0) >= LANDMARK_MIN and name not in AIRPORT),
            "s": round(svgpath.project(poly, x, y)[0], 2),
        }
    )

# --- 역 사이 선 모양 -----------------------------------------------------
def slice_poly(s0, s1):
    """폴리라인에서 누적거리 s0~s1 구간만 잘라 낸다."""
    out, acc = [], 0.0
    for i in range(len(poly) - 1):
        ax, ay = poly[i]
        bx, by = poly[i + 1]
        seg = math.hypot(bx - ax, by - ay)
        if seg == 0:
            continue
        a0, a1 = acc, acc + seg
        if a1 >= s0 and a0 <= s1:
            t0 = max(0.0, (s0 - a0) / seg)
            t1 = min(1.0, (s1 - a0) / seg)
            p0 = (ax + (bx - ax) * t0, ay + (by - ay) * t0)
            p1 = (ax + (bx - ax) * t1, ay + (by - ay) * t1)
            if not out:
                out.append(p0)
            out.append(p1)
        acc = a1
    return [[round(p[0], 2), round(p[1], 2)] for p in out]


def real_km(n1, n2):
    """노선도는 거리를 왜곡했으므로 실제 위경도로 잰다."""
    r1, r2 = master.get(n1), master.get(n2)
    if not (r1 and r2):
        return 1.0
    dy = (float(r2["위도"]) - float(r1["위도"])) * 111.0
    dx = (float(r2["경도"]) - float(r1["경도"])) * 88.0
    return round(math.hypot(dx, dy) * 1.15, 3)  # 선로는 직선보다 조금 길다


segments = []
for i in range(len(stations) - 1):
    a, b = stations[i], stations[i + 1]
    pts = slice_poly(min(a["s"], b["s"]), max(a["s"], b["s"]))
    if a["s"] > b["s"]:
        pts.reverse()
    segments.append(
        {
            "a": i,
            "b": i + 1,
            "pts": pts,
            "len": round(abs(b["s"] - a["s"]), 2),
            "km": real_km(a["name"], b["name"]),
        }
    )

# --- 혼잡도 보정 ---------------------------------------------------------
# 게임은 역을 하나씩 지으므로 구간 승객량을 그때그때 다시 만들어야 한다.
# 그래서 중력식(양쪽 덩어리 크기의 곱)을 쓰되, 다 이어졌을 때 실제 값과 맞도록
# 구간마다 보정계수를 미리 재 둔다.  현재 통과량 = 중력식(지금) × k
TOT = sum(s["riders"] for s in stations)


def gravity_full(i):
    """다 이어졌을 때 이 구간을 지나는 하루 승객 (중력식)"""
    left = sum(s["riders"] for s in stations[: i + 1])
    return 2.0 * left * (TOT - left) / TOT if TOT else 0.0


seg_missing = []
for i, g in enumerate(segments):
    key = frozenset((stations[g["a"]]["name"], stations[g["b"]]["name"]))
    pax = SEG_PAX.get(key)
    if pax is None and SEG_PAX:
        # 원본에 빠진 구간은 이웃 구간의 평균으로 메운다
        near = [SEG_PAX.get(frozenset((stations[j]["name"], stations[j + 1]["name"])))
                for j in (i - 1, i + 1) if 0 <= j < len(segments)]
        near = [v for v in near if v]
        if near:
            pax = sum(near) / len(near)
            seg_missing.append("%s~%s" % (stations[g["a"]]["name"], stations[g["b"]]["name"]))
    gf = gravity_full(i)
    g["pax"] = round(pax, 1) if pax else None
    g["k"] = round(pax / gf, 4) if (pax and gf > 0) else 1.0

board = {
    "line": LINE_NAME,
    "color": LINE_COLOR,
    "fare": 650,
    "stations": stations,
    "segments": segments,
    "provisional": bool(missing),
    "provisionalStations": missing,
    "realSegments": bool(SEG_PAX),
}

out = ROOT / "game" / "board.js"
out.parent.mkdir(exist_ok=True)
out.write_text(
    "// tools/build_board.py 가 만든 파일. 직접 고치지 말 것.\n"
    "window.BOARD = %s;\n"
    "window.MAP_SVG = %s;\n"
    % (json.dumps(board, ensure_ascii=False), json.dumps(svg, ensure_ascii=False)),
    encoding="utf-8",
)
print("역 %d개, 구간 %d개 → game/board.js (%.0f KB)" % (len(stations), len(segments), out.stat().st_size / 1024))
print("총 하루 이용객 %s명, 등급 분포 %s" % (
    format(sum(s["riders"] for s in stations), ","),
    {g: sum(1 for s in stations if s["grade"] == g) for g in "SABCDE"},
))
if SEG_PAX:
    ks = [g["k"] for g in segments if g["pax"]]
    worst = max(segments, key=lambda g: g["pax"] or 0)
    print("  구간 승객량: 보정계수 %.2f~%.2f (1.0 이면 중력식이 맞았다는 뜻)" % (min(ks), max(ks)))
    print("  가장 붐비는 구간: %s~%s 하루 %s명" % (
        stations[worst["a"]]["name"], stations[worst["b"]]["name"],
        format(int(worst["pax"]), ",")))
    if seg_missing:
        print("  ⚠ 원본에 없어 이웃 평균으로 메운 구간: %s" % ", ".join(seg_missing))
if TOURIST:
    lm = [s for s in stations if s["landmark"]]
    tp = sorted((s for s in stations if s["tourist"]), key=lambda s: -s["tourist"])[:3]
    print("  단기외국인 비중 상위: %s" % ", ".join("%s %.1f%%" % (s["name"], s["tourist"]) for s in tp))
    print("  관광 명물 (%.0f%% 이상, 공항 효과 제외): %s" % (
        LANDMARK_MIN, ", ".join(s["name"] for s in lm) or "없음 — 9호선엔 관광 명물이 없습니다"))
if missing:
    print("\n  ⚠ 임시값으로 채운 역 %d개: %s" % (len(missing), ", ".join(missing[:8]) + (" …" if len(missing) > 8 else "")))
    print("     data/ 에 역별_승하차_시간대별_수도권.csv 와 역_등급.csv 를 넣으면 실제값으로 바뀝니다.")
else:
    print("\n  ✓ 38역 모두 실제 자료를 씁니다.")
