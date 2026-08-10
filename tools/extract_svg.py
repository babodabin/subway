# -*- coding: utf-8 -*-
"""공식 노선도 SVG에서 역 원(690개)과 환승 호(arc)를 뽑아낸다.

출력: data/노선도_원_추출.csv
  id, x, y, r, colors  (colors 는 '|' 로 구분, 환승역은 여러 색)
"""
import re
import csv
import json
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "공식노선도_환승표시.html"
OUT = ROOT / "data" / "노선도_원_추출.csv"

html = SRC.read_text(encoding="utf-8")


def attr(tag, name):
    m = re.search(r'%s="([^"]*)"' % name, tag)
    return m.group(1) if m else None


# --- 역 원 ---------------------------------------------------------------
circles = []
for i, tag in enumerate(re.findall(r"<circle[^>]*>", html)):
    circles.append(
        {
            "id": i,
            "x": float(attr(tag, "cx")),
            "y": float(attr(tag, "cy")),
            "r": float(attr(tag, "r")),
            "stroke": attr(tag, "stroke"),
            "colors": set(),
        }
    )
    if circles[-1]["stroke"]:
        circles[-1]["colors"].add(circles[-1]["stroke"])

# --- 환승 호: 반원 두 개가 원 하나를 나눠 칠한다 -------------------------
# d="M x1 y1 A r r 0 0 1 x2 y2" → 중심은 두 끝점의 중점
ARC = re.compile(
    r'<path d="M\s*([\d.]+)\s+([\d.]+)A\s*([\d.]+)\s+[\d.]+[^"]*?\s([\d.]+)\s+([\d.]+)"'
    r'[^>]*stroke="(#[0-9a-fA-F]{6})"'
)
arcs = []
for m in ARC.finditer(html):
    x1, y1, r, x2, y2, color = m.groups()
    arcs.append(
        {
            "x1": float(x1),
            "y1": float(y1),
            "x2": float(x2),
            "y2": float(y2),
            "r": float(r),
            "color": color,
        }
    )

# 호를 원에 붙인다. 3분할 호는 두 끝점의 중점이 중심이 아니므로
# "두 끝점에서 모두 반지름 r 만큼 떨어진 점"을 기준으로 고른다.
for a in arcs:
    best, bd = None, 1e9
    for c in circles:
        err = abs(math.hypot(c["x"] - a["x1"], c["y"] - a["y1"]) - a["r"]) + abs(
            math.hypot(c["x"] - a["x2"], c["y"] - a["y2"]) - a["r"]
        )
        if err < bd:
            best, bd = c, err
    if bd < 1.0:
        best["colors"].add(a["color"])

no_color = [c for c in circles if not c["colors"]]

with OUT.open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "x", "y", "r", "colors"])
    for c in circles:
        w.writerow([c["id"], c["x"], c["y"], c["r"], "|".join(sorted(c["colors"]))])

print("원 %d개, 호 %d개" % (len(circles), len(arcs)))
print("환승 원(호 여러 개): %d" % sum(1 for c in circles if len(c["colors"]) > 1))
print("색 못 붙인 원: %d" % len(no_color))
print(json.dumps([[c["id"], c["x"], c["y"]] for c in no_color][:10], ensure_ascii=False))
