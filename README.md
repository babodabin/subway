# 서울 지하철 건설 게임

실제 서울·수도권 지하철을 직접 깔아나가는 방치형 게임.
규칙과 지금까지의 결정은 **[docs/지하철게임_정리_20260810.md](docs/지하철게임_정리_20260810.md)** 에 다 있습니다.

## 해 보기

```
python3 -m http.server 8000
```
그리고 http://localhost:8000/ 로 들어가면 9호선 판이 열립니다.
(`index.html` 을 파일로 바로 열어도 돌아갑니다. 데이터가 `.js` 안에 들어 있습니다.)

개화·김포공항·공항시장 세 역이 열린 채로 시작합니다. 점을 눌러 이어 지으세요.

## 폴더

```
data/    원자료 + 만들어진 표
tools/   자료를 게임이 읽을 수 있게 바꾸는 파이썬
game/    게임 코드 (board.js 는 tools 가 만든 것이니 직접 고치지 말 것)
docs/    정리 문서
```

## 다시 만들기

`data/` 를 고쳤으면 순서대로 돌리면 됩니다.

```
python3 tools/extract_svg.py      # 노선도 SVG → 원 690개 + 환승 색
python3 tools/name_stations.py    # 원에 역 이름 붙이기 (631/690)
python3 tools/build_board.py      # 9호선 판 → game/board.js
python3 tools/build_single.py     # (선택) 파일 하나로 합치기
```

## ⚠️ 지금 이용객 숫자는 임시값입니다

`역별_승하차_시간대별_수도권.csv` 와 `역_등급.csv` 가 아직 없어서,
노선 수와 도심까지 거리로 만든 대용값을 쓰고 있습니다. 실제 자료가 아닙니다.
`tools/build_board.py` 의 `provisional()` 을 갈아끼우면 됩니다.
