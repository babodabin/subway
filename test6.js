const { JSDOM } = require("jsdom");
const fs = require("fs");
const errors = [];
const dom = new JSDOM(fs.readFileSync("/tmp/game_v6.html", "utf-8"), {
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

  console.log("역 수:", ev("D.names.length"), "노선 수:", ev("Object.keys(D.lines).length"));
  console.log("시작화면 모드탭:", [...window.document.querySelectorAll("#modetab button")].map(b => b.dataset.m).join(","));

  // --- 모드1: 단일 노선 (신분당선) ---
  ev("pickMode='single'; renderPick();");
  console.log("\n[single] 버튼 수:", window.document.querySelectorAll("#pick .pk").length);
  window.startLine("신분당", "single");
  await wait(400);
  console.log("[single] mode=", ev("mode"), "open=", [...ev("open")], "servedDaily=", ev("servedDaily"));
  ev("checkUnlock()");
  console.log("[single] 해금 후 open(변화없어야):", [...ev("open")]);

  // --- 모드2: 1~9호선 ---
  window.startLine("9", "core");
  await wait(400);
  console.log("\n[core] open=", [...ev("open")], "activeLines=", ev("activeLines()").length, "개");

  // --- 모드3: 전체 확장 ---
  window.startLine("9", "grow");
  await wait(400);
  console.log("[grow] activeLines=", ev("activeLines()").length, "개  ORDER 마지막:", ev("ORDER").slice(-3));

  // --- 모드4: 전부 보기 (1~9호선) ---
  window.buildAll(ev("CORE"));
  await wait(2500);
  const coreServed = ev("servedDaily");
  console.log("\n[all-core] 노선", [...ev("open")].length, "servedDaily=", Math.round(coreServed), "건설역=", ev("built.size"));

  // --- 모드4: 전부 보기 (전체) ---
  window.buildAll([...ev("CORE"), ...ev("EXTRA")]);
  await wait(6000);
  const allServed = ev("servedDaily");
  console.log("[all-full] 노선", [...ev("open")].length, "servedDaily=", Math.round(allServed), "건설역=", ev("built.size"));
  console.log("  전체/1~9호선 배수:", (allServed / coreServed).toFixed(2));

  // 요일 전환
  window.setDayType("sat"); await wait(4000);
  console.log("  토요일:", Math.round(ev("servedDaily")), "비율", (ev("servedDaily") / allServed).toFixed(3));
  window.setDayType("wd"); await wait(4000);

  // 패널 렌더 확인
  for (const t of ["stn", "line", "train", "jam", "rep"]) {
    ev(`tab='${t}'; sel=500; panel();`);
    const len = window.document.getElementById("panel").innerHTML.length;
    console.log(`  panel[${t}] len=${len}`);
  }
  console.log("  역패널 샘플:", window.document.getElementById("panel").innerHTML.slice(0, 0));
  ev("tab='stn'; sel=500; panel();");
  console.log("  역 500:", ev("D.names[500]"), "->", window.document.getElementById("panel").innerHTML.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").slice(0, 160));

  console.log("\nsub:", window.document.getElementById("sub").textContent);

  if (errors.length) { console.log("ERRORS:", errors); process.exit(1); }
  console.log("\nNO ERRORS");
  process.exit(0);
})().catch(e => { console.error("THREW:", e); process.exit(1); });
