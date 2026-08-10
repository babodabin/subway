// 9호선 판 — 시간·돈·건설·열차
// 규칙은 docs/지하철게임_정리_20260810.md 를 따른다.
(function () {
  "use strict";

  var B = window.BOARD;
  var N = B.stations.length;
  var SVGNS = "http://www.w3.org/2000/svg";

  // ── 게임 상태 ───────────────────────────────────────────────────────
  var S = {
    money: 2000000,         // 시작 자금 200만원
    t: 5 * 60,              // 게임 속 시각(분). 05:00 부터
    day: 1,
    speed: 1,               // 실제 1초 = 10 * speed 게임분
    builtSet: new Set(),
    cars: 6,
    headway: 6,             // 분
    depot: 8,               // 열차 상한 (차량기지)
    depotBuys: 0,
    sel: -1,
  };

  var CAR_CAP = 160;        // 한 칸 정원
  var SPEED_KMH = 30;       // 완행 표정속도
  var PEAK = 0.09;          // 첨두 비율 기본값. 역마다 실제 시간대 자료가 있으면 그걸 쓴다
  var DEPOT_BASE = 500000000;   // 차량기지 늘리는 값. 살수록 비싸진다
  var DEPOT_STEP = 6;           // 한 번에 늘어나는 열차 수

  // ── 지도 밑그림 ─────────────────────────────────────────────────────
  var base = document.getElementById("base");
  base.innerHTML = window.MAP_SVG;
  var baseSvg = base.querySelector("svg");
  baseSvg.removeAttribute("id");
  baseSvg.querySelector("#r").classList.add("dim");

  var over = document.getElementById("over");
  var gRoot = mk("g");
  over.appendChild(gRoot);
  var gSeg = mk("g"), gDot = mk("g"), gTrain = mk("g"), gLabel = mk("g");
  gRoot.appendChild(gSeg); gRoot.appendChild(gDot);
  gRoot.appendChild(gTrain); gRoot.appendChild(gLabel);
  var baseRoot = baseSvg.querySelector("#r");

  function mk(n) { return document.createElementNS(SVGNS, n); }

  // 구간 선
  var segEls = B.segments.map(function (sg) {
    var p = mk("polyline");
    p.setAttribute("points", sg.pts.map(function (q) { return q[0] + "," + q[1]; }).join(" "));
    p.setAttribute("fill", "none");
    p.setAttribute("stroke-width", "4.2");
    p.setAttribute("stroke-linecap", "round");
    p.setAttribute("stroke-linejoin", "round");
    gSeg.appendChild(p);
    return p;
  });

  // 역 점
  var dotEls = B.stations.map(function (st, i) {
    var c = mk("circle");
    c.setAttribute("cx", st.x); c.setAttribute("cy", st.y);
    c.setAttribute("r", st.xfer ? 7.6 : 5.8);
    c.setAttribute("stroke-width", "2.4");
    gDot.appendChild(c);
    return c;
  });

  // 대표역 이름표 (여의도 = 9호선 대표역)
  B.stations.forEach(function (st, i) {
    if (st.name !== "여의도" && !st.xfer) return;
    var t = mk("text");
    t.setAttribute("x", st.x + 9.5); t.setAttribute("y", st.y - 8);
    t.setAttribute("font-size", "13");
    t.setAttribute("font-weight", st.name === "여의도" ? "800" : "600");
    t.setAttribute("fill", "#1D1B16");
    t.setAttribute("stroke", "#F7F5F0"); t.setAttribute("stroke-width", "3.2");
    t.setAttribute("paint-order", "stroke");
    t.textContent = st.name;
    t.style.display = "none";
    t.dataset.i = i;
    gLabel.appendChild(t);
  });

  // ── 연결 요소: 이어져 있는 지어진 역 덩어리 ─────────────────────────
  function components() {
    var comp = new Array(N).fill(-1), out = [], k = 0;
    for (var i = 0; i < N; i++) {
      if (!S.builtSet.has(i) || comp[i] >= 0) continue;
      var run = [];
      var j = i;
      while (j < N && S.builtSet.has(j)) { comp[j] = k; run.push(j); j++; }
      out.push(run); k++;
    }
    return { comp: comp, runs: out };
  }

  // ── 돈 ──────────────────────────────────────────────────────────────
  // 갈 수 있는 곳이 늘어야 그 역이 돈을 번다.
  // 닿는 정도 = (이어진 역들의 이용객 합 - 자기 자신) / (전체 이용객 - 자기 자신)
  // 역 수가 아니라 이용객으로 재기 때문에, 여의도·고속터미널에 닿는 순간 확 뛴다.
  var TOTAL_RIDERS = B.stations.reduce(function (a, s) { return a + s.riders; }, 0);

  function reachFactor(i, run) {
    var st = B.stations[i], sum = 0;
    run.forEach(function (j) { sum += B.stations[j].riders; });
    var denom = TOTAL_RIDERS - st.riders;
    return denom > 0 ? (sum - st.riders) / denom : 0;
  }

  function stationRevenue(i, run) {
    return B.stations[i].riders * B.fare * reachFactor(i, run);
  }

  function dailyRevenue() {
    var cs = components(), sum = 0;
    cs.runs.forEach(function (run) {
      run.forEach(function (i) { sum += stationRevenue(i, run); });
    });
    return sum;
  }

  // 옆 역이 이미 있어야 이어 지을 수 있다 (노선을 깔아 나가는 게임이므로)
  function canBuild(i) {
    if (S.builtSet.has(i)) return false;
    return S.builtSet.has(i - 1) || S.builtSet.has(i + 1);
  }

  // 지었을 때 생길 덩어리
  function runIfBuilt(i) {
    var lo = i, hi = i;
    while (lo - 1 >= 0 && S.builtSet.has(lo - 1)) lo--;
    while (hi + 1 < N && S.builtSet.has(hi + 1)) hi++;
    var run = [];
    for (var k = lo; k <= hi; k++) run.push(k);
    return run;
  }

  // 건설비 = 그 역이 (지어진 뒤) 하루 벌 돈 × 회수일수
  // 노선이 길어질수록 남은 역의 값이 같이 오른다.
  function buildCost(i) {
    return Math.round(stationRevenue(i, runIfBuilt(i)) * B.stations[i].paybackDays);
  }

  // ── 혼잡 ────────────────────────────────────────────────────────────
  // 열차가 모자라면 원하는 배차를 못 지킨다. 실제 배차로 수송력을 잰다.
  function roundTripMin(run) {
    var km = 0;
    for (var k = 0; k < run.length - 1; k++) km += B.segments[run[k]].km;
    return (2 * km / SPEED_KMH) * 60 + 6;   // 종점 회차 6분
  }

  // 덩어리마다 열차를 몇 대 굴릴 수 있는지 (차량기지 한도를 나눠 쓴다)
  function allocation() {
    var runs = components().runs.filter(function (r) { return r.length > 1; });
    var want = runs.map(function (r) { return Math.ceil(roundTripMin(r) / S.headway); });
    var total = want.reduce(function (a, b) { return a + b; }, 0);
    var out = new Map();
    runs.forEach(function (r, k) {
      var got = total <= S.depot ? want[k]
              : Math.max(1, Math.floor(S.depot * want[k] / total));
      out.set(r[0], { want: want[k], got: got, rt: roundTripMin(r) });
    });
    return { map: out, want: total };
  }

  function effHeadway(run, alloc) {
    var a = (alloc || allocation()).map.get(run[0]);
    if (!a) return S.headway;
    return Math.max(S.headway, a.rt / a.got);
  }

  function capacityFor(run, alloc) {
    return CAR_CAP * S.cars * (60 / effHeadway(run, alloc));
  }

  // 구간 통과 승객: 양쪽 덩어리 크기를 곱한 중력식. 가운데가 가장 붐빈다.
  // 첨두 비율은 그 덩어리 역들의 이용객 가중평균을 쓴다.
  function segFlowPerHour(run, idxInRun) {
    var tot = 0, left = 0, pk = 0;
    run.forEach(function (i) {
      var st = B.stations[i];
      tot += st.riders;
      pk += st.riders * (st.peak || PEAK);
    });
    for (var k = 0; k <= idxInRun; k++) left += B.stations[run[k]].riders;
    var right = tot - left;
    if (tot <= 0) return 0;
    return (2 * left * right / tot) * (pk / tot);
  }

  // ── 열차 ────────────────────────────────────────────────────────────
  var trains = [];
  function rebuildTrains() {
    gTrain.innerHTML = "";
    trains = [];
    var cs = components(), alloc = allocation();
    cs.runs.forEach(function (run) {
      if (run.length < 2) return;
      // 덩어리 전체를 잇는 폴리라인
      var pts = [];
      for (var k = 0; k < run.length - 1; k++) {
        var sg = B.segments[run[k]];
        sg.pts.forEach(function (q, qi) { if (qi || !pts.length) pts.push(q); });
      }
      var acc = [0], km = 0;
      for (var k2 = 1; k2 < pts.length; k2++) {
        acc.push(acc[k2 - 1] + Math.hypot(pts[k2][0] - pts[k2 - 1][0], pts[k2][1] - pts[k2 - 1][1]));
      }
      for (var k3 = 0; k3 < run.length - 1; k3++) km += B.segments[run[k3]].km;
      var a = alloc.map.get(run[0]);
      var want = a ? a.got : 1;
      for (var n = 0; n < want; n++) {
        var el = mk("rect");
        el.setAttribute("width", 8.6); el.setAttribute("height", 5.0);
        el.setAttribute("rx", 1.7); el.setAttribute("fill", B.color);
        el.setAttribute("stroke", "#fff"); el.setAttribute("stroke-width", 1.2);
        gTrain.appendChild(el);
        trains.push({ el: el, pts: pts, acc: acc, total: acc[acc.length - 1],
                      km: km, u: (n / want), dir: n % 2 ? -1 : 1 });
      }
    });
  }

  function moveTrains(dtMin) {
    trains.forEach(function (T) {
      var perMin = (SPEED_KMH / 60) / T.km;      // 노선 길이 대비 비율/분
      T.u += T.dir * perMin * dtMin;
      if (T.u > 1) { T.u = 1; T.dir = -1; }
      if (T.u < 0) { T.u = 0; T.dir = 1; }
      var d = T.u * T.total, lo = 0, hi = T.acc.length - 1;
      while (lo < hi) { var mid = (lo + hi) >> 1; if (T.acc[mid] < d) lo = mid + 1; else hi = mid; }
      var i = Math.max(1, lo);
      var a = T.pts[i - 1], b = T.pts[i];
      var span = T.acc[i] - T.acc[i - 1] || 1;
      var t = (d - T.acc[i - 1]) / span;
      T.el.setAttribute("x", a[0] + (b[0] - a[0]) * t - 4.3);
      T.el.setAttribute("y", a[1] + (b[1] - a[1]) * t - 2.5);
    });
  }

  // ── 그리기 ──────────────────────────────────────────────────────────
  function paint() {
    var cs = components(), alloc = allocation();
    B.stations.forEach(function (st, i) {
      var on = S.builtSet.has(i);
      dotEls[i].setAttribute("fill", on ? "#fff" : "#EDE9E0");
      dotEls[i].setAttribute("stroke", on ? B.color : "#A9A294");
      dotEls[i].setAttribute("stroke-width", on ? 3.4 : 2.0);
      dotEls[i].setAttribute("opacity", on ? 1 : .85);
    });
    B.segments.forEach(function (sg, k) {
      var on = S.builtSet.has(sg.a) && S.builtSet.has(sg.b);
      segEls[k].setAttribute("stroke", on ? B.color : "#BDB6A6");
      segEls[k].setAttribute("opacity", on ? 1 : .75);
      if (!on) { segEls[k].setAttribute("stroke-dasharray", "3 4"); }
      else {
        segEls[k].removeAttribute("stroke-dasharray");
        var run = cs.runs[cs.comp[sg.a]];
        var flow = segFlowPerHour(run, run.indexOf(sg.a));
        var load = flow / capacityFor(run, alloc);
        // 100%까지는 노선색, 150%부터 평판이 깎이므로 빨강
        var col = load >= 1.5 ? "#C0432F" : (load >= 1.0 ? "#D9902B" : B.color);
        segEls[k].setAttribute("stroke", col);
        segEls[k].setAttribute("stroke-width", load >= 1.5 ? 5.6 : 4.2);
      }
    });
    gLabel.querySelectorAll("text").forEach(function (t) {
      t.style.display = S.builtSet.has(+t.dataset.i) ? "" : "none";
    });
  }

  // ── 정보 카드 ───────────────────────────────────────────────────────
  var card = document.getElementById("card");
  // 카드는 지도 위에 얹혀 있으므로, 카드 위 조작이 지도로 새지 않게 막는다
  ["pointerdown", "pointermove", "pointerup"].forEach(function (v) {
    card.addEventListener(v, function (e) { e.stopPropagation(); });
  });

  function won(v) {
    if (v >= 100000000) return (v / 100000000).toFixed(v >= 1000000000 ? 0 : 1) + "억원";
    if (v >= 10000) return Math.round(v / 10000).toLocaleString() + "만원";
    return Math.round(v).toLocaleString() + "원";
  }

  function select(i) {
    S.sel = i;
    var st = B.stations[i], on = S.builtSet.has(i);
    document.getElementById("cTitle").textContent = st.name;
    document.getElementById("cBadge").textContent = st.grade + "급";
    document.getElementById("cLines").textContent = st.lines.join(" · ");

    var cs = components();
    var full = st.riders * B.fare;
    var prov = B.provisional && (B.provisionalStations || []).indexOf(st.name) >= 0;
    var rows = [
      ["하루 이용객", st.riders.toLocaleString() + "명" + (prov ? "  (임시값)" : "")],
      ["다 이어졌을 때 하루 수입", won(full)],
    ];
    var ok = canBuild(i), cost = 0;
    if (on) {
      var run = cs.runs[cs.comp[i]];
      var f = reachFactor(i, run);
      rows.push(["지금 하루 수입", won(full * f) + "  (" + Math.round(f * 100) + "%)"]);
      if (run.length > 1) {
        var k = Math.min(run.indexOf(i), run.length - 2);
        var flow = segFlowPerHour(run, k);
        var load = flow / capacityFor(run);
        rows.push(["옆 구간 혼잡도", Math.round(load * 100) + "%" + (load >= 1.5 ? "  평판 깎임" : "")]);
      }
    } else if (ok) {
      cost = buildCost(i);
      var f2 = reachFactor(i, runIfBuilt(i));
      rows.push(["지으면 하루 수입", won(full * f2) + "  (" + Math.round(f2 * 100) + "%)"]);
      rows.push(["건설비 (회수 " + st.paybackDays + "일)", won(cost)]);
    }
    document.getElementById("cRows").innerHTML = rows.map(function (r) {
      return "<div><span>" + r[0] + "</span><b>" + r[1] + "</b></div>";
    }).join("");

    var btn = document.getElementById("cBuild");
    btn.textContent = on ? "이미 지음" : (ok ? "짓기 · " + won(cost) : "아직 못 지음");
    btn.disabled = on || !ok || S.money < cost;
    document.getElementById("note").textContent = on
      ? "이어진 역이 늘수록 이 역의 수입도 같이 오릅니다."
      : !ok
        ? "노선은 이어서만 깔 수 있습니다. 이미 지은 역 옆부터 지으세요."
        : (S.money < cost ? "돈이 모자랍니다. 조금 기다리면 모입니다." : "");
    card.classList.add("show");
    paint();
  }

  document.getElementById("cClose").onclick = function () { card.classList.remove("show"); S.sel = -1; };
  document.getElementById("cBuild").onclick = function () {
    var i = S.sel;
    if (i < 0 || S.builtSet.has(i)) return;
    if (!canBuild(i)) return;
    var c = buildCost(i);
    if (S.money < c) return;
    S.money -= c;
    S.builtSet.add(i);
    rebuildTrains();
    select(i);
    hud();
  };

  // ── 조작줄 ──────────────────────────────────────────────────────────
  document.querySelectorAll("#bar button[data-sp]").forEach(function (b) {
    b.onclick = function () {
      S.speed = +b.dataset.sp;
      document.querySelectorAll("#bar button[data-sp]").forEach(function (o) {
        o.classList.toggle("on", o === b);
      });
    };
  });
  var cars = document.getElementById("cars"), head = document.getElementById("head");
  cars.oninput = function () {
    S.cars = +cars.value; document.getElementById("carsV").textContent = S.cars;
    paint(); hud(); if (S.sel >= 0) select(S.sel);
  };
  head.oninput = function () {
    S.headway = +head.value; document.getElementById("headV").textContent = S.headway + "분";
    rebuildTrains(); paint(); hud(); if (S.sel >= 0) select(S.sel);
  };
  function depotCost() { return DEPOT_BASE * (S.depotBuys + 1); }
  document.getElementById("depot").onclick = function () {
    if (S.money < depotCost()) return;
    S.money -= depotCost(); S.depot += DEPOT_STEP; S.depotBuys++;
    rebuildTrains(); paint(); hud(); if (S.sel >= 0) select(S.sel);
  };

  // ── 위쪽 정보줄 ─────────────────────────────────────────────────────
  function hud() {
    document.getElementById("money").textContent = won(S.money);
    var h = Math.floor(S.t / 60) % 24, m = Math.floor(S.t % 60);
    document.getElementById("clock").textContent =
      S.day + "일차 " + String(h).padStart(2, "0") + ":" + String(m).padStart(2, "0");
    var rev = dailyRevenue();
    document.getElementById("rate").textContent = rev > 0 ? "하루 " + won(rev) : "";
    document.getElementById("built").textContent = S.builtSet.size + " / " + N;
    var al = allocation(), runs = components().runs;
    var use = 0; al.map.forEach(function (a) { use += a.got; });
    var short = al.want > S.depot;
    var eff = runs.length && runs[0].length > 1 ? effHeadway(runs[0], al) : S.headway;
    document.getElementById("fleet").textContent =
      "열차 " + use + "/" + S.depot + " · 실배차 " + eff.toFixed(1) + "분" + (short ? " · 모자람" : "");
    document.getElementById("depot").disabled = S.money < depotCost();
    document.getElementById("depot").textContent = "차량기지 +" + DEPOT_STEP + " · " + won(depotCost());
  }

  // ── 시간 ────────────────────────────────────────────────────────────
  var last = performance.now();
  function tick(now) {
    var dt = Math.min(0.25, (now - last) / 1000); last = now;
    var dtMin = dt * 10 * S.speed;           // 실제 1초 = 10분 × 배속
    if (dtMin > 0) {
      S.t += dtMin;
      while (S.t >= 1440) { S.t -= 1440; S.day++; }
      S.money += dailyRevenue() * (dtMin / 1440);
      moveTrains(dtMin);
      hud();
    }
    requestAnimationFrame(tick);
  }

  // ── 지도 밀고 넓히기 ────────────────────────────────────────────────
  // 변환은 SVG 좌표계에서 한다. 화면 픽셀 ↔ SVG 단위는 sc 로 오간다.
  var VB = 2557.76, VBH = 2556.957;
  var stage = document.getElementById("stage");
  var Z = 1, vx = 0, vy = 0, pts = new Map(), lastD = 0, dragged = false;
  var sc = 1, offX = 0, offY = 0;

  function measure() {
    var r = stage.getBoundingClientRect();
    sc = Math.min(r.width / VB, r.height / VBH);     // 화면픽셀 / SVG단위
    offX = (r.width - VB * sc) / 2;
    offY = (r.height - VBH * sc) / 2;
    return r;
  }
  function toSvg(cx, cy) {                            // 화면 좌표 → SVG 좌표
    var r = stage.getBoundingClientRect();
    return [((cx - r.left - offX) / sc - vx) / Z, ((cy - r.top - offY) / sc - vy) / Z];
  }
  function apply() {
    var tr = "translate(" + vx + " " + vy + ") scale(" + Z + ")";
    baseRoot.setAttribute("transform", tr);
    gRoot.setAttribute("transform", tr);
  }
  function zoomAt(cx, cy, nz) {
    nz = Math.min(14, Math.max(1, nz));
    var p = toSvg(cx, cy);
    vx += p[0] * Z - p[0] * nz;
    vy += p[1] * Z - p[1] * nz;
    Z = nz; apply();
  }

  stage.addEventListener("pointerdown", function (e) {
    pts.set(e.pointerId, { x: e.clientX, y: e.clientY }); dragged = false;
    stage.setPointerCapture(e.pointerId);
  });
  stage.addEventListener("pointermove", function (e) {
    if (!pts.has(e.pointerId)) return;
    var pr = pts.get(e.pointerId);
    pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
    var a = [...pts.values()];
    if (a.length === 1) {
      var dx = e.clientX - pr.x, dy = e.clientY - pr.y;
      if (Math.abs(dx) + Math.abs(dy) > 2) dragged = true;
      vx += dx / sc; vy += dy / sc; apply();
    } else if (a.length === 2) {
      dragged = true;
      var d = Math.hypot(a[0].x - a[1].x, a[0].y - a[1].y);
      if (lastD) zoomAt((a[0].x + a[1].x) / 2, (a[0].y + a[1].y) / 2, Z * (d / lastD));
      lastD = d;
    }
  });
  ["pointerup", "pointercancel"].forEach(function (v) {
    stage.addEventListener(v, function (e) {
      // 밀지 않고 그냥 눌렀으면 가까운 역을 고른다.
      // 점이 작으니 화면 기준 18px 안쪽이면 잡아 준다.
      if (v === "pointerup" && !dragged && pts.size === 1) {
        var p = toSvg(e.clientX, e.clientY);
        var lim = 18 / (sc * Z), best = -1, bd = lim;
        B.stations.forEach(function (st, i) {
          var d = Math.hypot(st.x - p[0], st.y - p[1]);
          if (d < bd) { bd = d; best = i; }
        });
        if (best >= 0) select(best);
        else if (!card.contains(e.target)) { card.classList.remove("show"); S.sel = -1; }
      }
      pts.delete(e.pointerId);
      if (pts.size < 2) lastD = 0;
    });
  });
  stage.addEventListener("wheel", function (e) {
    e.preventDefault();
    zoomAt(e.clientX, e.clientY, Z * (e.deltaY < 0 ? 1.12 : 1 / 1.12));
  }, { passive: false });

  // ── 시작 ────────────────────────────────────────────────────────────
  // 9호선 판은 개화부터. 서쪽 끝 세 역은 그냥 열어 준다.
  // (역 하나만으로는 갈 데가 없어 수입이 0이라 게임이 시작되지 않는다)
  [0, 1, 2].forEach(function (i) { S.builtSet.add(i); });
  rebuildTrains(); paint(); hud();

  // 9호선이 화면 가운데 오도록 맞춘다
  function fit() {
    var r = measure();
    var xs = B.stations.map(function (s) { return s.x; });
    var ys = B.stations.map(function (s) { return s.y; });
    var minx = Math.min.apply(null, xs), maxx = Math.max.apply(null, xs);
    var miny = Math.min.apply(null, ys), maxy = Math.max.apply(null, ys);
    var pad = 70;
    Z = Math.max(1, Math.min(14,
      (r.width - pad * 2) / sc / Math.max(1, maxx - minx),
      (r.height - pad * 2) / sc / Math.max(1, maxy - miny)));
    vx = (r.width / 2 - offX) / sc - ((minx + maxx) / 2) * Z;
    vy = (r.height / 2 - offY) / sc - ((miny + maxy) / 2) * Z;
    apply();
  }
  fit();
  window.addEventListener("resize", function () { measure(); apply(); });

  requestAnimationFrame(tick);
})();
