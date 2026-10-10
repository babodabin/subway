"""'구 안에 역을' 게임의 자료(game_data.js)를 만든다.

data/역_승객자료.json 의 실제 역 자료(이름·위경도·하루 승차·역간 이동)에서
고른 구 안의 역만 뽑아, 눈에 보이지 않는 '수요 점'으로 쓴다.
구 경계: data/서울_자치구_경계.json (southkorea/seoul-maps, 통계청 2013)

    python3 tools/build_free.py            # 강남구 서초구 송파구
    python3 tools/build_free.py 관악구 동작구 영등포구
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUS = sys.argv[1:] or ['강남구', '서초구', '송파구']

D = json.loads((ROOT / 'data/역_승객자료.json').read_text(encoding='utf-8'))
LL = D['ll']
geo = json.loads((ROOT / 'data/서울_자치구_경계.json').read_text(encoding='utf-8'))


def rings(g):
    return [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']


def inside(lon, lat, polys):
    c = False
    for poly in polys:
        for r in poly:
            for k in range(len(r)):
                x1, y1 = r[k]; x2, y2 = r[k - 1]
                if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
                    c = not c
    return c


gu = {f['properties']['name']: rings(f['geometry']) for f in geo['features']}
miss = [g for g in GUS if g not in gu]
if miss:
    sys.exit('없는 구: ' + ', '.join(miss))

pick = [i for i, (la, lo) in enumerate(LL) if any(inside(lo, la, gu[g]) for g in GUS)]
idx = {i: k for k, i in enumerate(pick)}
od = D['od']
trips = []
for k in range(0, len(od), 3):
    a, b, v = od[k], od[k + 1], od[k + 2]
    if a in idx and b in idx and a != b and v > 0:
        trips += [idx[a], idx[b], round(v, 1)]

r5 = lambda v: round(v, 5)
out = {
    'gus': GUS,
    'area': {g: [[[[r5(x), r5(y)] for x, y in r] for r in p] for p in gu[g]] for g in GUS},
    'around': {n: [[[[r5(x), r5(y)] for x, y in r] for r in p] for p in ps]
               for n, ps in gu.items() if n not in GUS},
    'names': [D['names'][i] for i in pick],
    'll': [LL[i] for i in pick],
    'board': [round(D['board'][i]) for i in pick],
    'trips': trips,
    # '전체 보기'에서 보여 줄 실제 지하철역 전부 (서울·수도권)
    'all': [[D['names'][i], round(la, 5), round(lo, 5)] for i, (la, lo) in enumerate(LL)],
}
js = 'const FREE=' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n'
(ROOT / 'game_data.js').write_text(js, encoding='utf-8')
print(f'{"·".join(GUS)}: 수요 점 {len(pick)}곳 · 이동 {len(trips)//3}쌍 '
      f'하루 {sum(trips[2::3]):,.0f}건 → game_data.js {len(js)//1024}KB')
