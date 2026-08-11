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

역명 표기는 자료마다 다르다. 공공자료는 '서울역'·'잠실(송파구청)'·'총신대입구(이수)'
처럼 쓰고 우리 마스터는 '서울'·'잠실'·'총신대입구' 로 쓴다. 그래서 이름을 그대로
맞추지 않고 표기 변형(괄호 안팎, 끝의 '역', 가운뎃점)까지 같이 본다. Store 참고.
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


_PAREN = r"[（(\[]([^）)\]]*)[）)\]]"


def variants(name):
    """한 역명에서 나올 수 있는 표기들. 믿을 만한 순서로 준다.

    '잠실(송파구청)' → 잠실(송파구청), 잠실, 송파구청
    '서울역'         → 서울역, 서울          (마스터에 '역'으로 끝나는 역명은 없다)
    '시청·용인대'    → 시청·용인대, 시청용인대
    """
    out = []

    def add(s):
        if s and s not in out:
            out.append(s)

    add(_norm(name))
    for s in list(out):
        add(re.sub(_PAREN, "", s))                 # 괄호 밖
        for inner in re.findall(_PAREN, s):        # 괄호 안
            add(_norm(inner))
    for s in list(out):
        if len(s) > 1 and s.endswith("역"):
            add(s[:-1])
    for s in list(out):
        add(re.sub(r"[·・\-~]", "", s))
    return out


class Store(dict):
    """역명을 표기 변형까지 봐 가며 찾아 주는 dict.

    정확한 이름이 먼저다. 변형끼리 겹쳐서 어느 역인지 못 정하면 그 변형은 버린다
    (엉뚱한 역의 승객을 붙이느니 임시값으로 도는 편이 낫다).
    """

    def _build_alias(self):
        alias, dup = {}, set()
        for key in list(self):
            for v in variants(key)[1:]:
                if dict.__contains__(self, v):     # 진짜 역명이 이기게 둔다
                    continue
                if v in alias and alias[v] != key:
                    dup.add(v)
                alias.setdefault(v, key)
        for v in dup:
            alias.pop(v, None)
        self._alias = alias
        self._ambiguous = dup
        return self

    def resolve(self, name):
        """이 이름이 어느 키에 해당하는지. 못 찾으면 None."""
        for v in variants(name):
            if dict.__contains__(self, v):
                return v
        for v in variants(name):
            k = getattr(self, "_alias", {}).get(v)
            if k:
                return k
        return None

    def get(self, name, default=None):
        k = self.resolve(name)
        return dict.get(self, k, default) if k else default

    def __contains__(self, name):
        return self.resolve(name) is not None


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

        # 넓은 모양의 시간 컬럼을 먼저 가려낸다. 이걸 나중에 하면 '04시-05시 승차인원'
        # 이 승차 컬럼으로 먼저 뽑혀 그 한 시간이 통째로 빠진다.
        # 공공자료는 승차/하차가 시간마다 나란히 있으므로 승차 쪽만 남긴다.
        hour_cols = []
        if not c_hour:
            for f2 in fields:
                if f2 == c_name:
                    continue
                h = _hour_of(f2)
                if h is not None and "하차" not in _norm(f2):
                    hour_cols.append((h, f2))
            if any("승차" in _norm(f2) for _, f2 in hour_cols):
                hour_cols = [(h, f2) for h, f2 in hour_cols if "승차" in _norm(f2)]

        taken = {c_name, c_hour} | {f2 for _, f2 in hour_cols}
        rest = [f2 for f2 in fields if f2 not in taken]
        c_on = _pick(rest, "승차", "승차인원", "승차총승객수")
        c_off = _pick(rest, "하차", "하차인원", "하차총승객수")
        c_sum = _pick(rest, "합계", "승하차", "총승객수", "이용객")

        out = Store()

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

    out._build_alias()
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
        out = Store()
        for row in rd:
            g = _norm(row.get(c_grade)).upper().replace("급", "")
            if g in GRADES:
                dict.__setitem__(out, _norm(row.get(c_name)), g)
    out._build_alias()
    if verbose:
        print("  등급: %s → 역 %d개" % (p.name, len(out)))
    return out


def _master_names():
    p = DATA / "역_마스터_수도권.csv"
    if not p.exists():
        return []
    with _open(p) as f:
        return [r["역명"] for r in csv.DictReader(f) if r.get("역명")]


def report():
    """자료가 우리 역 이름에 얼마나 붙는지 본다. 파일을 넣은 뒤 여기부터 돌려 보면 된다."""
    print("자료 확인")
    r = load_ridership()
    g = load_grades()
    if not r and not g:
        print("\n  → 아직 임시값으로 돕니다. 위 파일을 data/ 에 넣으면 자동으로 잡힙니다.")
        return

    if r:
        top = sorted(r.items(), key=lambda kv: -kv[1]["riders"])[:5]
        print("  가장 큰 역:", ", ".join("%s %s명" % (k, format(v["riders"], ",")) for k, v in top))

    names = _master_names()
    if not names:
        return
    for label, store in (("승하차", r), ("등급", g)):
        if not store:
            continue
        hit = {n: store.resolve(n) for n in names}
        miss = [n for n, k in hit.items() if k is None]
        loose = [(n, k) for n, k in hit.items() if k and k != _norm(n)]
        print("\n  [%s] 우리 역 %d개 중 %d개 붙음" % (label, len(names), len(names) - len(miss)))
        if loose:
            print("    표기 달라 맞춘 것 %d개: %s" % (
                len(loose), ", ".join("%s←%s" % (n, k) for n, k in loose[:10])))
        if miss:
            print("    못 붙은 역 %d개: %s" % (len(miss), ", ".join(miss[:15])))
        used = {k for k in hit.values() if k}
        spare = [k for k in store if k not in used]
        if spare:
            print("    자료엔 있는데 우리 역이 아닌 이름 %d개: %s" % (
                len(spare), ", ".join(spare[:15])))
        if getattr(store, "_ambiguous", None):
            print("    어느 역인지 못 정해 버린 표기: %s" % ", ".join(sorted(store._ambiguous)[:10]))


if __name__ == "__main__":
    report()
