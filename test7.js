const { JSDOM } = require("jsdom");
const fs = require("fs");
const errors = [];
const dom = new JSDOM(fs.readFileSync("/tmp/game_v7.html", "utf-8"), {
  runScripts: "dangerously", resources: "usable", pretendToBeVisual: true,
  virtualConsole: (() => {
    const { VirtualConsole } = require("jsdom");
    const vc = new VirtualConsole();
    vc.on("jsdomError", e => errors.push("jsdomError: " + e.message));
    return vc;
  })(),
});
const { window } = dom;
const wait = ms => new Promise(r => setTimeout(r, ms));
const ev = x => window.eval(x);

(async () => {
  await wait(600);
  if (errors.length) { console.log("LOAD ERRORS:", errors); process.exit(1); }

  window.startLine("2", "core");
  await wait(500);
  const base = ev("servedDaily");
  console.log("2호선 기준 servedDaily:", Math.round(base));

  console.log("\n=== 이벤트별 요일 수요배수 / 수송력 ===");
  const evs = ev("CFG.events.map(e=>({t:e.type,src:e.src,wd:e.mult.wd,sat:e.mult.sat,sun:e.mult.sun,cap:e.cap,ch:e.chance,line:e.line}))");
  for (const e of evs) console.log(`  ${e.t}(${e.src}) 평일x${e.wd} 토x${e.sat} 일x${e.sun} 수송력x${e.cap} 확률${(e.ch*100).toFixed(1)}%${e.line?" 노선한정":""}`);
  console.log("  확률 합계:", (evs.reduce((a, e) => a + e.ch, 0) * 100).toFixed(1) + "%/일");

  // 비 이벤트 요일별 배수 확인
  ev("event=Object.assign({},CFG.events.find(e=>e.type==='비'),{daysLeft:1});");
  for (const d of ["wd", "sat", "sun"]) {
    ev(`dayType='${d}';`);
    console.log(`  비 · ${d}: eventMult=${ev("eventMult()").toFixed(3)}`);
  }
  ev("dayType='wd';");

  // 수송력 감소 확인 (파업)
  const capNormal = (ev("event=null"), ev("capacity('2',8)"));
  ev("event=Object.assign({},CFG.events.find(e=>e.type==='파업'),{daysLeft:1,affectedLine:'2'});");
  console.log("\n  파업 시 2호선 수송력:", ev("capacity('2',8)"), "/ 평시", capNormal, "=", (ev("capacity('2',8)") / capNormal).toFixed(2));
  console.log("  파업 시 다른노선(9) 영향:", ev("capacity('9',8)") === capNormal ? "없음(정상)" : "있음(오류)");

  // 평판 탭에 이벤트 표시
  ev("tab='rep'; panel();");
  const rep = window.document.getElementById("panel").innerHTML.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
  console.log("\n  평판탭:", rep.slice(0, 200));
  ev("event=null;");

  // rollEvent 빈도 검증
  let cnt = {}, total = 0;
  for (let i = 0; i < 2000; i++) {
    ev("rollEvent();");
    if (ev("event") !== null) { const t = ev("event.type"); cnt[t] = (cnt[t] || 0) + 1; total++; ev("event=null;"); }
  }
  console.log("\n=== 2000일 시뮬레이션 ===");
  for (const [t, c] of Object.entries(cnt).sort((a, b) => b[1] - a[1])) {
    const exp = evs.find(e => e.t === t).ch * 2000;
    console.log(`  ${t}: ${c}회 (기대 ${exp.toFixed(0)}회)`);
  }
  console.log("  합계:", total, "/2000 =", (total / 2000 * 100).toFixed(1) + "%");

  // 하루 스킵 동작
  ev("event=null;");
  const c0 = ev("cash");
  window.skipDays(30);
  console.log("\n  30일 건너뛰기: cash", Math.round(c0), "->", Math.round(ev("cash")), "day=", ev("day"));

  if (errors.length) { console.log("ERRORS:", errors); process.exit(1); }
  console.log("\nNO ERRORS");
  process.exit(0);
})().catch(e => { console.error("THREW:", e); process.exit(1); });
