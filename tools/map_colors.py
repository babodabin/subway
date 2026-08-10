# -*- coding: utf-8 -*-
"""OCR 이름표를 원에 붙여서 '색 → 호선' 대응표를 만든다.

OCR 좌표 → SVG 좌표 변환값: x 0.23999 (2557.76 / 10658)
"""
import csv
import math
import pathlib
import collections

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCALE = 2557.76 / 10658.0

circles = []
with (ROOT / "data" / "노선도_원_추출.csv").open(encoding="utf-8") as f:
    for r in csv.DictReader(f):
        circles.append(
            {
                "id": int(r["id"]),
                "x": float(r["x"]),
                "y": float(r["y"]),
                "colors": r["colors"].split("|"),
            }
        )

# 역 마스터: 역명 → 호선 목록
master = {}
with (ROOT / "data" / "역_마스터_수도권.csv").open(encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        master[r["역명"]] = r["호선목록"].split("|")

ocr = []
with (ROOT / "data" / "노선도_역좌표_OCR.csv").open(encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        ocr.append((r["역명"], float(r["x"]) * SCALE, float(r["y"]) * SCALE))

# 이름표는 원 옆에 찍히므로, 가장 가까운 원을 후보로 삼는다
votes = collections.Counter()
pairs = []
for name, x, y in ocr:
    best, bd = None, 1e9
    for c in circles:
        d = math.hypot(c["x"] - x, c["y"] - y)
        if d < bd:
            best, bd = c, d
    pairs.append((name, best, bd))
    if name in master and bd < 40:
        for col in best["colors"]:
            for line in master[name]:
                votes[(col, line)] += 1

# 색마다 가장 표를 많이 받은 호선
by_color = collections.defaultdict(list)
for (col, line), n in votes.items():
    by_color[col].append((n, line))

n_circ = collections.Counter()
for c in circles:
    for col in c["colors"]:
        n_circ[col] += 1

print("색 → 호선 (표수 / 그 색 원 개수)")
print("-" * 52)
for col in sorted(n_circ, key=lambda c: -n_circ[c]):
    cand = sorted(by_color.get(col, []), reverse=True)
    top = cand[0] if cand else (0, "???")
    rest = ", ".join("%s:%d" % (l, n) for n, l in cand[1:4])
    print("%-9s %-14s %3d / %3d   %s" % (col, top[1], top[0], n_circ[col], rest))

d = [p[2] for p in pairs]
d.sort()
print("\n이름표-원 거리: 중앙 %.2f, 90%% %.2f, 최대 %.2f" % (d[len(d) // 2], d[int(len(d) * 0.9)], d[-1]))
