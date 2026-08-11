# -*- coding: utf-8 -*-
"""받은 원자료에서 게임이 쓸 두 파일을 뽑는다.

  data/역별_승하차_시간대별_수도권.csv   역명, 시간대, 승차, 하차   (하루 평균)
  data/역_등급.csv                      역명, 등급

쓰는 원자료
  1) 서울시 지하철 시간대별 승하차 (월별, CP949, 139개월 × 600역)  ← 실적. 시간 분포까지 있다
  2) 역 등급표 (역명·시도·호선목록·노선수·이용량·출처·등급, 641역) ← 실적 일평균 승하차 합
  3) 모형 시간대별 (역명·시·승차·하차, 526역)                      ← 1)에 없는 역의 시간 모양만

왜 이렇게 섞는가
  2) 의 '이용량' 은 1) 의 마지막 달 일평균 승하차와 정확히 같다 (서울역 238,194).
  3) 은 생활이동으로 만든 추정치라 큰 역이 6배까지 과소하다 (정리 문서 §5 '큰 역 과소').
  그래서 크기는 실적으로 하고, 실적이 없는 역만 2) 의 이용량으로 채운다.
  시간 모양은 1) 이 있으면 1), 없으면 3) 을 빌리고, 그것도 없으면 평균 모양을 쓴다.

승차만 쓰는 이유
  게임 수입은 통행 1회에 650원이다. 통행 하나는 승차 1 + 하차 1 이므로
  승하차 합을 쓰면 수입이 두 배가 된다. 그래서 riders 는 승차 기준이다.
  ('이용량' 은 승하차 합이므로 절반으로 나눠 승차로 삼는다.)

쓰는 법
  python3 tools/import_ridership.py <서울시월별.csv> <등급표.csv> [<모형시간대.csv>]
"""
import calendar
import collections
import csv
import io
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from load_ridership import variants, _norm  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def master_names():
    with (DATA / "역_마스터_수도권.csv").open(encoding="utf-8-sig") as f:
        return [r["역명"] for r in csv.DictReader(f) if r.get("역명")]


def matcher(names):
    """자료 쪽 역명 → 우리 역명. 변형까지 보고, 겹치면 버린다."""
    exact = {variants(n)[0]: n for n in names}
    index, dup = dict(exact), set()
    for n in names:
        for v in variants(n)[1:]:
            if v in exact:            # 진짜 역명은 변형에 밀리지 않는다
                continue              # ('신촌(경의)' 의 변형이 2호선 '신촌' 을 덮으면 안 된다)
            if v in index and index[v] != n:
                dup.add(v)
            index.setdefault(v, n)
    for v in dup:
        index.pop(v, None)

    def find(raw):
        for v in variants(raw):
            if v in index:
                return index[v]
        return None

    return find


def read_actual(path, find):
    """서울시 월별 실적. 마지막 달만 써서 하루 평균으로 만든다."""
    with io.TextIOWrapper(open(path, "rb"), encoding="cp949", newline="") as f:
        rows = list(csv.DictReader(f))
    fields = rows[0].keys()
    on_cols = [(int(c[:2]) % 24, c) for c in fields if "승차" in c]
    off_cols = [(int(c[:2]) % 24, c) for c in fields if "하차" in c]
    last = max(r["사용월"] for r in rows)
    days = calendar.monthrange(int(last[:4]), int(last[4:]))[1]

    out = collections.defaultdict(lambda: {"on": [0.0] * 24, "off": [0.0] * 24})
    miss = collections.Counter()
    for r in rows:
        if r["사용월"] != last:
            continue
        name = find(r["지하철역"])
        if not name:
            miss[r["지하철역"]] += 1
            continue
        s = out[name]
        for h, c in on_cols:
            s["on"][h] += float(r[c] or 0) / days
        for h, c in off_cols:
            s["off"][h] += float(r[c] or 0) / days
    print("  실적: %s 기준 (%d일) → 역 %d개" % (last, days, len(out)))
    if miss:
        print("    우리 역에 못 붙인 이름 %d개: %s" % (len(miss), ", ".join(sorted(miss))))
    return out


def read_grades(path, find):
    grade, usage = {}, {}
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            name = find(r["역명"]) or r["역명"]
            grade[name] = _norm(r["등급"]).upper()
            usage[name] = float(r["이용량"] or 0)
    print("  등급표: 역 %d개" % len(grade))
    return grade, usage


def read_model(path, find):
    """모형 시간대별. 크기는 안 믿고 시간 모양만 빌린다."""
    shape = collections.defaultdict(lambda: {"on": [0.0] * 24, "off": [0.0] * 24})
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            name = find(r["역명"])
            if not name:
                continue
            h = int(float(r["시"])) % 24
            shape[name]["on"][h] += float(r["승차"] or 0)
            shape[name]["off"][h] += float(r["하차"] or 0)
    print("  모형 시간대: 역 %d개" % len(shape))
    return shape


def normalize(v):
    t = sum(v)
    return [x / t for x in v] if t > 0 else None


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    actual_p, grade_p = sys.argv[1], sys.argv[2]
    model_p = sys.argv[3] if len(sys.argv) > 3 else None

    names = master_names()
    find = matcher(names)
    print("원자료 읽기")
    actual = read_actual(actual_p, find)
    grade, usage = read_grades(grade_p, find)
    model = read_model(model_p, find) if model_p else {}

    # 실적이 있는 역들의 평균 시간 모양. 마지막 대타로 쓴다.
    avg_on = [0.0] * 24
    avg_off = [0.0] * 24
    for s in actual.values():
        for h in range(24):
            avg_on[h] += s["on"][h]
            avg_off[h] += s["off"][h]
    avg_on, avg_off = normalize(avg_on), normalize(avg_off)

    rows = []
    src = collections.Counter()
    zero = []
    for name in names:
        if name in actual:
            s = actual[name]
            src["실적"] += 1
        else:
            # 크기는 등급표 이용량(승하차 합)의 절반을 승차로 본다
            half = usage.get(name, 0.0) / 2.0
            sh = model.get(name)
            on_sh = normalize(sh["on"]) if sh else None
            off_sh = normalize(sh["off"]) if sh else None
            s = {
                "on": [half * x for x in (on_sh or avg_on)],
                "off": [half * x for x in (off_sh or avg_off)],
            }
            src["모형 모양" if sh else "평균 모양"] += 1
            if half <= 0:
                zero.append(name)
        for h in range(24):
            if s["on"][h] or s["off"][h]:
                rows.append([name, h, round(s["on"][h], 1), round(s["off"][h], 1)])

    out = DATA / "역별_승하차_시간대별_수도권.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["역명", "시간대", "승차", "하차"])
        w.writerows(rows)

    gout = DATA / "역_등급.csv"
    with gout.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["역명", "등급"])
        for n in names:
            if n in grade:
                w.writerow([n, grade[n]])

    tot = sum(r[2] for r in rows)
    print("\n%s  %d행 (%.0f KB)" % (out.name, len(rows), out.stat().st_size / 1024))
    print("%s  %d역" % (gout.name, sum(1 for n in names if n in grade)))
    print("  출처: %s" % dict(src))
    print("  하루 총 승차 %s명" % format(int(tot), ","))
    if zero:
        print("  ⚠ 이용량 0 인 역 %d개 (등급표에서 '추정'·미개통): %s"
              % (len(zero), ", ".join(zero[:10]) + (" …" if len(zero) > 10 else "")))


if __name__ == "__main__":
    main()
