# -*- coding: utf-8 -*-
"""흩어져 있는 역 자료를 한 파일로 합친다 → data/역_통합표.csv

한 줄에 한 역. 마스터 641역이 모두 들어간다 (값이 없으면 빈 칸).

  역명 시도 호선목록 노선수 위도 경도
  x y 원수 원id          ← 공식 노선도 좌표계 (viewBox 2557.76 × 2556.96)
  등급 회수일수 하루승차 첨두비중
  단기외국인비중 관광명물
  승하차출처                ← 실적 / 추정

노선도 좌표에 대하여
  환승역은 승강장마다 원이 따로 있다. 그 원들의 평균을 역 위치로 쓴다.
  이름이 'A|B' 로 남은 원 5개는 색으로 가린다 —
  원의 색이 가리키는 호선을 다 가진 역이 그 원의 주인이다.
  아무도 못 가지면 두 역이 12px 규칙에 걸려 한 원으로 합쳐진 것이므로 둘 다에 준다.
"""
import collections
import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from load_ridership import load_ridership, load_grades  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

GRADE_DAYS = {"E": 1.0, "D": 1.5, "C": 2.0, "B": 3.0, "A": 5.0, "S": 8.0}
AIRPORT = {"개화", "개화산", "방화", "김포공항", "공항시장", "공항화물청사",
           "인천공항1터미널", "인천공항2터미널", "영종", "운서"}
LANDMARK_MIN = 10.0


def read(name, **kw):
    p = DATA / name
    if not p.exists():
        return None
    return list(csv.DictReader(p.open(encoding=kw.get("enc", "utf-8-sig"))))


master = read("역_마스터_수도권.csv")
circles = read("노선도_역이름.csv", enc="utf-8")
tourist = {r["역명"]: float(r["단기비중"]) for r in (read("역_외국인비중.csv") or [])}

M = {r["역명"]: r for r in master}

# --- 색 → 호선 (단색 원들에서 거꾸로 뽑는다) -----------------------------
c2l = collections.defaultdict(collections.Counter)
for r in circles:
    n = r["역명"]
    if not n or "|" in n or n not in M:
        continue
    cols = r["색목록"].split("|")
    if len(cols) != 1:
        continue
    for line in M[n]["호선목록"].split("|"):
        c2l[cols[0]][line] += 1
CMAP = {c: k.most_common(1)[0][0] for c, k in c2l.items()}

# --- 원을 역에 나눠 준다 -------------------------------------------------
owned = collections.defaultdict(list)
merged, resolved = [], []
for r in circles:
    n = r["역명"]
    if not n:
        continue
    if "|" not in n:
        owned[n].append(r)
        continue
    cand = n.split("|")
    lines = {CMAP.get(c) for c in r["색목록"].split("|")} - {None}
    fit = [c for c in cand if lines <= set(M.get(c, {}).get("호선목록", "").split("|"))]
    if len(fit) == 1:
        owned[fit[0]].append(r)
        resolved.append("%s → %s" % (n, fit[0]))
    else:                      # 아무도 못 가짐 = 두 역이 한 원으로 합쳐진 것
        for c in cand:
            owned[c].append(r)
        merged.append(n)

print("이름표가 두 역에 걸렸던 원 %d개" % (len(resolved) + len(merged)))
for s in resolved:
    print("  가림: %s" % s)
for s in merged:
    print("  합쳐진 원 (두 역이 같은 자리): %s" % s)

# --- 승하차·등급 --------------------------------------------------------
print("\n자료 확인")
RIDE = load_ridership() or {}
GRADE = load_grades() or {}

rows = []
for r in master:
    n = r["역명"]
    cs = owned.get(n, [])
    x = round(sum(float(c["x"]) for c in cs) / len(cs), 2) if cs else ""
    y = round(sum(float(c["y"]) for c in cs) / len(cs), 2) if cs else ""
    rd = RIDE.get(n) or {}
    g = GRADE.get(n, "")
    t = tourist.get(n)
    rows.append({
        "역명": n,
        "시도": r["시도"],
        "호선목록": r["호선목록"],
        "노선수": r["노선수"],
        "위도": r["위도"],
        "경도": r["경도"],
        "x": x,
        "y": y,
        "원수": len(cs),
        "원id": "|".join(c["id"] for c in cs),
        "등급": g,
        "회수일수": GRADE_DAYS.get(g, ""),
        "하루승차": rd.get("riders", ""),
        "첨두비중": round(rd["peak"], 4) if rd.get("peak") else "",
        "단기외국인비중": t if t is not None else "",
        "관광명물": "Y" if (t is not None and t >= LANDMARK_MIN and n not in AIRPORT) else "",
        "승하차출처": "실적" if rd.get("riders") else "",
    })

out = DATA / "역_통합표.csv"
with out.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

no_xy = [r["역명"] for r in rows if r["x"] == ""]
no_ride = [r["역명"] for r in rows if r["하루승차"] == ""]
print("\n%s  %d역 (%.0f KB)" % (out.name, len(rows), out.stat().st_size / 1024))
print("  노선도 좌표 있음 %d / 없음 %d" % (len(rows) - len(no_xy), len(no_xy)))
if no_xy:
    print("    좌표 없는 역: %s" % ", ".join(no_xy))
print("  하루승차 있음 %d / 없음 %d" % (len(rows) - len(no_ride), len(no_ride)))
print("  관광 명물 %d역" % sum(1 for r in rows if r["관광명물"]))
