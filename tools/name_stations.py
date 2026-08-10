# -*- coding: utf-8 -*-
"""노선도 원 690개에 역 이름을 붙인다.

방법
  1. 노선 색마다 그 색 path 를 폴리라인으로 펼친다
  2. 그 색 원들을 path 위에 투영해 '노선 위 순서'를 얻는다
  3. 아주 가까이 붙은 원(승강장이 안 합쳐진 것)은 하나로 묶는다
  4. 노선_역순서_정리.csv 의 역 순서와 DP 로 맞춘다
     - 환승 여부(원의 색 개수 vs 역의 호선 수)가 큰 단서
     - OCR 이름표가 못 역할
  5. 방향은 양쪽으로 다 맞춰 보고 점수가 높은 쪽을 쓴다

출력: data/노선도_역이름.csv  (id, x, y, r, 환승, 역명, 노선목록, 확신)
"""
import csv
import math
import pathlib
import re
import collections

import svgpath

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCALE = 2557.76 / 10658.0
MERGE_PX = 20.0  # 이보다 가까운 이웃 원은 같은 역의 승강장으로 본다

# 색 → 그 색으로 그려진 '한 줄로 이어지는 길'들.
# 우리 데이터는 노선을 물리 철도 기준으로 쪼개 놓았고(경원선이 1호선과
# 경의중앙선에 걸쳐 있는 식), 지도는 승객이 타는 노선 기준으로 그려져 있다.
# 그래서 지도 위에서 한 줄로 이어지는 것끼리 다시 붙여 준다.
#   조각 = (노선명, 뒤집기, 시작순번, 끝순번)   순번은 1부터, 끝은 포함. None 이면 끝까지
COLOR_ROUTES = {
    "#a49d87": [[("서울 도시철도 9호선",), ("수도권  도시철도 9호선",)]],
    "#eb6101": [[("일산선", True), ("3호선",)]],
    # 4호선은 북쪽으로 진접선까지 이어진다 (진접 → 불암산 → 남태령 → 선바위 → 오이도)
    "#009bce": [[("진접선",), ("4호선",), ("안산과천선",)]],
    "#eca300": [[("분당선",), ("수인선",)]],
    "#69702e": [[("7호선",), ("도시철도 7호선",)]],
    "#e5006a": [[("수도권 광역철도 8호선",), ("8호선",)]],
    # 5호선은 강동에서 갈라진다. 지도는 마천쪽을 본선처럼 이어 그렸다
    "#794698": [
        [("5호선 마천지선", True), ("5호선 본선", True, 1, 39)],  # 마천 … 강동 … 방화
        [("5호선 본선", False, 40, None)],                      # 길동 … 하남검단산
    ],
    "#00a23f": [
        [("2호선 본선",)],
        [("2호선 성수지선",)],
        [("2호선 신정지선",)],
    ],
    # 1호선 무리. 지도는 세 갈래로 그려져 있다.
    #   run0 인천 → 구로 → 서울역 → 청량리 → 연천
    #   run1 가산디지털단지 → 수원   (광명지선이 금천구청에서 갈라져 여기 붙는다)
    #   run2 세류 → 평택            (서동탄지선이 병점에서 갈라져 여기 붙는다)
    #        run2 아래로는 천안·신창 구간이 더 그려져 있으나 우리 데이터에 없다
    "#004b84": [
        [
            ("경인선",),                       # 인천 … 구일
            ("경부선 본선", True, 1, 8),        # 구로 … 남영
            ("1호선", True),                   # 서울 … 청량리
            ("경원선", False, 8, None),         # 청량리 … 연천
        ],
        [("경부선 본선", False, 9, 22)],        # 가산디지털단지 … 수원
        [("경부선 본선", False, 23, None)],     # 세류 … 평택
    ],
    "#713b1d": [
        [("6호선", False, 1, 34)],             # 신내 … 응암
        [("6호선", False, 35, None)],          # 역촌 … 구산 (응암 순환구간)
    ],
    # 경의중앙선의 용산~왕십리 구간이 우리 데이터에는 '경원선' 앞머리에 들어 있다
    "#6bc2b3": [
        [
            ("경의중앙선", False, 1, 24),       # 임진강 … 서강대
            ("경의중앙선", False, 26, 27),      # 공덕, 효창공원앞
            ("경원선", False, 1, 7),            # 용산 … 왕십리
            ("경의중앙선", False, 29, None),     # 청량리 … 지평
        ],
        [("경의중앙선", False, 25, 25), ("경의중앙선", False, 28, 28)],  # 신촌(경의), 서울 지선
    ],
    "#006390": [[("인천국제공항선",)]],
    "#c12c30": [[("신분당선",)]],
    "#006550": [[("경춘선",)]],
    "#1d2f63": [[("경강선",)]],
    "#4da635": [[("서해선",)]],
    "#86b3e0": [[("인천지하철 1호선",)]],
    "#f4a463": [[("인천지하철 2호선",)]],
    "#df7504": [[("의정부",)]],
    "#71b22d": [[("에버라인",)]],
    "#bacc00": [[("우이신설선",)]],
    "#957326": [[("김포도시철도",)]],
    "#557ec0": [[("수도권 경량도시철도 신림선",)]],
}
# 순환선은 시작점이 정해져 있지 않아 모든 회전을 시험한다
CIRCULAR = {"2호선 본선"}
# 우리 데이터에 없는 노선(GTX-A 등)은 이름 없이 남긴다
UNKNOWN_COLORS = {"#a35e8c", "#9a958c"}

# 노선 이름이 한 색 안에서 이어 붙는 방식.
# 지선은 본선과 다른 subpath 에 있으므로 따로 맞춘다.
html = (ROOT / "data" / "공식노선도_환승표시.html").read_text(encoding="utf-8")

paths_by_color = collections.defaultdict(list)
for m in re.finditer(r"<path([^>]*)>", html):
    a = m.group(1)
    s = re.search(r'stroke="(#[0-9a-fA-F]{6})"', a)
    d = re.search(r'\bd="([^"]+)"', a)
    if not (s and d) or len(d.group(1)) < 60:
        continue
    for poly in svgpath.flatten(d.group(1)):
        if len(poly) > 1:
            paths_by_color[s.group(1)].append(poly)

circles = []
with (ROOT / "data" / "노선도_원_추출.csv").open(encoding="utf-8") as f:
    for r in csv.DictReader(f):
        circles.append(
            {
                "id": int(r["id"]),
                "x": float(r["x"]),
                "y": float(r["y"]),
                "r": float(r["r"]),
                "colors": r["colors"].split("|"),
                "names": set(),
            }
        )

master = {}
with (ROOT / "data" / "역_마스터_수도권.csv").open(encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        master[r["역명"]] = int(r["노선수"])

line_order = collections.OrderedDict()
with (ROOT / "data" / "노선_역순서_정리.csv").open(encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        line_order.setdefault(r["노선"], []).append(r["역명"])

ocr_pts = collections.defaultdict(list)
with (ROOT / "data" / "노선도_역좌표_OCR.csv").open(encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        ocr_pts[r["역명"]].append((float(r["x"]) * SCALE, float(r["y"]) * SCALE))


def ocr_dist(name, node):
    """이름표와 원 사이 거리. 이름표가 없으면 None."""
    if name not in ocr_pts:
        return None
    return min(math.hypot(node["x"] - x, node["y"] - y) for x, y in ocr_pts[name])


def order_along(cands, polys):
    """원들을 (subpath, 그 위 거리) 순으로 세운다. subpath 별로 나눠 돌려준다."""
    runs = collections.defaultdict(list)
    for c in cands:
        best = (1e18, 1e18, 0)
        for pi, poly in enumerate(polys):
            s, d = svgpath.project(poly, c["x"], c["y"])
            if d < best[1]:
                best = (s, d, pi)
        runs[best[2]].append((best[0], c))
    out = []
    for pi in sorted(runs):
        out.append([c for _, c in sorted(runs[pi], key=lambda t: t[0])])
    return out


def collapse(seq):
    """붙어 있는 승강장 원들을 한 덩어리로 묶는다."""
    groups = []
    for c in seq:
        if groups and math.hypot(c["x"] - groups[-1][-1]["x"], c["y"] - groups[-1][-1]["y"]) < MERGE_PX:
            groups[-1].append(c)
        else:
            groups.append([c])
    return groups


def node_of(group):
    return {
        "x": sum(c["x"] for c in group) / len(group),
        "y": sum(c["y"] for c in group) / len(group),
        "xfer": max(len(c["colors"]) for c in group) > 1 or len(group) > 1,
    }


def score(node, name):
    """이 덩어리가 이 역일 법한 정도. 높을수록 좋다."""
    s = 0.0
    d = ocr_dist(name, node)
    if d is not None:
        s += 6.0 if d < 30 else (2.0 if d < 55 else -4.0)
    xfer_real = master.get(name, 1) > 1
    s += 1.2 if node["xfer"] == xfer_real else -1.2
    return s


def align(nodes, names):
    """덩어리 목록과 역 이름 목록을 순서대로 맞춘다 (건너뜀 허용 DP)."""
    m, n = len(nodes), len(names)
    NEG = -1e9
    dp = [[NEG] * (n + 1) for _ in range(m + 1)]
    bk = [[None] * (n + 1) for _ in range(m + 1)]
    dp[0][0] = 0.0
    for i in range(m + 1):
        for j in range(n + 1):
            if dp[i][j] == NEG:
                continue
            if i < m and j < n:  # 짝짓기
                v = dp[i][j] + score(nodes[i], names[j])
                if v > dp[i + 1][j + 1]:
                    dp[i + 1][j + 1], bk[i + 1][j + 1] = v, ("M", i, j)
            if i < m:  # 이 원은 이름 없이 넘어감
                v = dp[i][j] - 2.5
                if v > dp[i + 1][j]:
                    dp[i + 1][j], bk[i + 1][j] = v, ("C", i, j)
            if j < n:  # 이 역은 이 색 위에 원이 없음
                v = dp[i][j] - 2.5
                if v > dp[i][j + 1]:
                    dp[i][j + 1], bk[i][j + 1] = v, ("N", i, j)
    i, j, out = m, n, []
    while bk[i][j]:
        op, pi, pj = bk[i][j]
        if op == "M":
            out.append((pi, pj))
        i, j = (pi, pj) if op == "M" else ((pi, j) if op == "C" else (i, pj))
    out.reverse()
    return dp[m][n], out


def route_names(route):
    """조각 목록을 한 줄짜리 역 이름 목록으로 이어 붙인다."""
    out = []
    for piece in route:
        line = piece[0]
        rev = piece[1] if len(piece) > 1 else False
        lo = piece[2] if len(piece) > 2 else 1
        hi = piece[3] if len(piece) > 3 else None
        seq = line_order.get(line, [])[lo - 1 : hi]
        seq = seq[::-1] if rev else seq
        for nm in seq:
            if out and out[-1] == nm:  # 이음매의 겹치는 역
                continue
            out.append(nm)
    return out


def route_label(route):
    out = []
    for piece in route:
        s = piece[0]
        if len(piece) > 2:
            s += "[%s~%s]" % (piece[2], piece[3] if len(piece) > 3 and piece[3] else "끝")
        out.append(s)
    return " + ".join(out)


# --- 색마다 맞추기 --------------------------------------------------------
rows = []
for color, routes in COLOR_ROUTES.items():
    cands = [c for c in circles if color in c["colors"]]
    runs = order_along(cands, paths_by_color.get(color, []))
    if not runs:
        continue
    groups_runs = [collapse(r) for r in runs]

    # 길 × run 을 모두 채점한 뒤, 겹치지 않게 가장 좋은 짝을 고른다
    cell = {}
    for idx, route in enumerate(routes):
        names = route_names(route)
        if not names:
            continue
        circ = any(p[0] in CIRCULAR for p in route)
        for ri, groups in enumerate(groups_runs):
            nodes = [node_of(g) for g in groups]
            best = None
            for rev in (False, True):
                seq = nodes[::-1] if rev else nodes
                rots = range(len(names)) if circ else [0]
                for rot in rots:
                    nm = names[rot:] + names[:rot] if circ else names
                    sc, pairs = align(seq, nm)
                    sc -= abs(len(seq) - len(nm)) * 0.4
                    if best is None or sc > best[0]:
                        best = (sc, rev, pairs, nm)
            cell[(idx, ri)] = best

    # 길 개수가 적어서 모든 짝짓기를 다 해 본다
    def assign(pending, free, acc):
        if not pending:
            return (sum(cell[k][0] for k in acc), list(acc))
        idx = pending[0]
        best = None
        for ri in list(free):
            if (idx, ri) not in cell:
                continue
            acc.append((idx, ri))
            r = assign(pending[1:], free - {ri}, acc)
            acc.pop()
            if best is None or r[0] > best[0]:
                best = r
        if best is None:  # 붙일 run 이 없으면 이 길은 건너뛴다
            best = assign(pending[1:], free, acc)
        return best

    idxs = [i for i in range(len(routes)) if route_names(routes[i])]
    _, chosen = assign(idxs, set(range(len(groups_runs))), [])

    for idx, ri in chosen:
        sc, rev, pairs, nm = cell[(idx, ri)]
        groups = groups_runs[ri]
        order = list(range(len(groups)))[::-1] if rev else list(range(len(groups)))
        for gi, ni in pairs:
            for c in groups[order[gi]]:
                c["names"].add(nm[ni])
        rows.append((color, route_label(routes[idx]), len(nm), len(pairs), sc))

print("%-9s %-40s %4s %4s %8s" % ("색", "길", "역수", "붙음", "점수"))
print("-" * 72)
for color, label, n, k, sc in rows:
    flag = "" if k == n else "  ← %d개 못 붙임" % (n - k)
    print("%-9s %-40s %4d %4d %8.1f%s" % (color, label, n, k, sc, flag))

# --- 검산: OCR 이름표와 얼마나 맞는가 ------------------------------------
ok = bad = miss = 0
wrong = []
for name, pts in ocr_pts.items():
    x, y = pts[0]
    near = sorted(circles, key=lambda c: math.hypot(c["x"] - x, c["y"] - y))[:3]
    if any(name in c["names"] for c in near):
        ok += 1
    elif not any(c["names"] for c in near):
        miss += 1
    else:
        bad += 1
        wrong.append((name, [sorted(c["names"]) for c in near[:2]]))

named = sum(1 for c in circles if c["names"])
print("\n이름 붙은 원 %d / %d" % (named, len(circles)))
print("OCR 검산: 맞음 %d, 틀림 %d, 근처에 이름 없음 %d" % (ok, bad, miss))
for w in wrong[:20]:
    print("  틀림:", w[0], "→", w[1])

with (ROOT / "data" / "노선도_역이름.csv").open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "x", "y", "r", "환승", "역명", "색목록"])
    for c in circles:
        w.writerow(
            [
                c["id"],
                c["x"],
                c["y"],
                c["r"],
                "Y" if len(c["colors"]) > 1 else "N",
                "|".join(sorted(c["names"])),
                "|".join(sorted(c["colors"])),
            ]
        )
print("\n→ data/노선도_역이름.csv")
