# -*- coding: utf-8 -*-
"""실제 승하차·등급 자료를 읽어 온다.

기다리는 파일 (data/ 에 넣으면 자동으로 잡힌다)
  역별_승하차_시간대별_수도권.csv   역별 시간대별 승차/하차
  역_등급.csv                      역명, 등급 (S~E)

컬럼 이름이 조금 달라도 잡히도록 만들었다. 세 가지 모양을 다 받는다.
  긴 모양   역명, 시간대, 승차, 하차
  넓은 모양 역명, 00시, 01시, …            (또는 0,1,…,23)
  간단      역명, 승차          (또는 승하차 / 합계)

돌려주는 것: {역명: {"riders": 하루 승차, "peak": 첨두 1시간 비중, "hours": [24개]}}
파일이 없으면 None 을 돌려준다. 그러면 build_board.py 가 임시값으로 돌아간다.
"""
import csv
import pathlib
import re
import unicodedata

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"

RIDE_NAMES = ["역별_승하차_시간대별_수도권.csv", "역별_승하차_시간대별.csv", "역별_승하차.csv"]
GRADE_NAMES = ["역_등급.csv", "역등급.csv"]

GRADES = ["S", "A", "B", "C", "D", "E"]


def _norm(s):
    return unicodedata.normalize("NFKC", (s or "")).replace(" ", "").strip()


def _find(names):
    for n in names:
        p = DATA / n
        if p.exists():
            return p
    return None


def _open(p):
    """BOM 이 있든 없든 읽는다."""
    return p.open(encoding="utf-8-sig", newline="")


def _pick(fields, *wants):
    """헤더에서 원하는 컬럼을 찾는다. 없으면 None."""
    for w in wants:
        for f in fields:
            if _norm(f) == _norm(w):
                return f
    for w in wants:                      # 부분 일치까지 봐준다
        for f in fields:
            if _norm(w) in _norm(f):
                return f
    return None


def _hour_of(field):
    """'07시', 'H07', '7', '07~08' 같은 이름에서 시(0~23)를 뽑는다."""
    m = re.search(r"(\d{1,2})", _norm(field))
    if not m:
        return None
    h = int(m.group(1))
    return h if 0 <= h <= 23 else None


def load_ridership(verbose=True):
    p = _find(RIDE_NAMES)
    if not p:
        if verbose:
            print("  승하차 자료 없음 (%s)" % " / ".join(RIDE_NAMES))
        return None

    with _open(p) as f:
        rd = csv.DictReader(f)
        fields = rd.fieldnames or []
        c_name = _pick(fields, "역명", "지하철역", "역이름", "station")
        if not c_name:
            raise SystemExit("%s: 역명 컬럼을 못 찾았습니다. 헤더=%s" % (p.name, fields))

        c_hour = _pick(fields, "시간대", "시간", "hour")
        c_on = _pick(fields, "승차", "승차인원", "승차총승객수")
        c_off = _pick(fields, "하차", "하차인원", "하차총승객수")
        c_sum = _pick(fields, "합계", "승하차", "총승객수", "이용객")

        hour_cols = []
        if not c_hour:
            for f2 in fields:
                if f2 in (c_name, c_on, c_off, c_sum):
                    continue
                h = _hour_of(f2)
                if h is not None:
                    hour_cols.append((h, f2))

        out = {}

        def slot(name):
            return out.setdefault(_norm(name), {"hours": [0.0] * 24, "riders": 0.0})

        def num(v):
            v = (v or "").replace(",", "").strip()
            try:
                return float(v)
            except ValueError:
                return 0.0

        for row in rd:
            name = row.get(c_name)
            if not name:
                continue
            s = slot(name)
            if c_hour:                                    # 긴 모양
                h = _hour_of(row.get(c_hour))
                v = num(row.get(c_on)) if c_on else num(row.get(c_sum))
                if h is not None:
                    s["hours"][h] += v
                s["riders"] += v
            elif hour_cols:                               # 넓은 모양
                for h, col in hour_cols:
                    v = num(row.get(col))
                    s["hours"][h] += v
                    s["riders"] += v
            else:                                         # 간단
                s["riders"] += num(row.get(c_on)) if c_on else num(row.get(c_sum))

    for name, s in out.items():
        tot = s["riders"]
        s["riders"] = int(round(tot))
        # 첨두 1시간 비중. 시간대 자료가 없으면 None 으로 두고 기본값을 쓰게 한다
        s["peak"] = round(max(s["hours"]) / tot, 4) if (tot > 0 and max(s["hours"]) > 0) else None

    if verbose:
        got = sum(1 for v in out.values() if v["riders"] > 0)
        has_hours = sum(1 for v in out.values() if v["peak"])
        print("  승하차: %s → 역 %d개 (시간대 있는 역 %d개)" % (p.name, got, has_hours))
    return out


def load_grades(verbose=True):
    p = _find(GRADE_NAMES)
    if not p:
        if verbose:
            print("  등급 자료 없음 (%s)" % " / ".join(GRADE_NAMES))
        return None
    with _open(p) as f:
        rd = csv.DictReader(f)
        fields = rd.fieldnames or []
        c_name = _pick(fields, "역명", "지하철역", "역이름")
        c_grade = _pick(fields, "등급", "grade", "급")
        if not (c_name and c_grade):
            raise SystemExit("%s: 역명/등급 컬럼을 못 찾았습니다. 헤더=%s" % (p.name, fields))
        out = {}
        for row in rd:
            g = _norm(row.get(c_grade)).upper().replace("급", "")
            if g in GRADES:
                out[_norm(row.get(c_name))] = g
    if verbose:
        print("  등급: %s → 역 %d개" % (p.name, len(out)))
    return out


if __name__ == "__main__":
    print("자료 확인")
    r = load_ridership()
    g = load_grades()
    if r:
        top = sorted(r.items(), key=lambda kv: -kv[1]["riders"])[:5]
        print("  가장 큰 역:", ", ".join("%s %s명" % (k, format(v["riders"], ",")) for k, v in top))
    if not r and not g:
        print("\n  → 아직 임시값으로 돕니다. 위 파일을 data/ 에 넣으면 자동으로 잡힙니다.")
