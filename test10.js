const { JSDOM } = require("jsdom");
const fs = require("fs");
const errors = [];
const dom = new JSDOM(fs.readFileSync("/tmp/game_v10.html", "utf-8"), {
  runScripts: "dangerously", resources: "usable", pretendToBeVisual: true,
  url: "https://example.com/index.html",
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
const doc = window.document;

(async () => {
  await wait(700);
  if (errors.length) { console.log("LOAD ERRORS:", errors); process.exit(1); }

  window.startLine("2", "core");
  await wait(500);
  console.log("시작 OK · servedDaily =", Math.round(ev("servedDaily")), "· 건설", ev("built.size"), "역");

  // ── 평판 → 승객 ──
  console.log("\n=== 평판이 승객에 미치는 영향 ===");
  console.log("  repScore:", ev("repScore").toFixed(1), "repMult:", ev("repMult").toFixed(4),
    "목표:", ev("repTargetMult()").toFixed(4));
  ev("repScore=100; repInit=true;");
  for (let i = 0; i < 40; i++) ev("updateRep()");
  console.log("  평판 100점 유지 40일 후 repMult:", ev("repMult").toFixed(3), "(상한 1.2)");
  ev("repScore=0; repInit=true;");
  for (let i = 0; i < 60; i++) ev("updateRep()");
  console.log("  평판 0점 유지 60일 후 repMult:", ev("repMult").toFixed(3), "(하한 0.7)");
  ev("repScore=60; repMult=1; repInit=true;");
  console.log("  liveMult (이벤트x평판):", ev("liveMult()").toFixed(3));

  // ── 화면 전환 ──
  console.log("\n=== 화면 전환 ===");
  const scrCount = () => doc.querySelectorAll("#screens .scr").length;
  console.log("  초기 stack:", ev("stack").length, "화면수:", scrCount());
  window.go("line"); await wait(60);
  console.log("  go(line) → stack:", ev("stack"), "화면수:", scrCount(), "제목:", doc.querySelector(".scrttl").textContent);
  console.log("  transform 클래스:", doc.querySelector("#screens .scr").className);
  window.go("train"); await wait(60);
  const scrs = [...doc.querySelectorAll("#screens .scr")];
  console.log("  go(train) → stack:", ev("stack"), "화면수:", scrCount());
  console.log("  아래 화면 under 클래스:", scrs[0].classList.contains("under") ? "적용됨" : "안됨");
  console.log("  history length:", window.history.length, "hash:", window.location.hash);

  window.history.back(); await wait(400);
  console.log("  뒤로 → stack:", ev("stack"), "화면수:", scrCount());
  window.history.back(); await wait(400);
  console.log("  뒤로 → stack:", ev("stack"), "화면수:", scrCount());

  // 모든 화면 렌더 확인
  console.log("\n=== 화면별 렌더 ===");
  for (const t of ["stn", "line", "train", "jam", "rep", "time", "save"]) {
    ev(`sel=${ev("[...built][0].split(':')[1]")};`);
    const html = ev(`scrBody('${t}')`);
    console.log(`  ${t}: ${html.length}자 ${html.length < 30 ? "⚠️ 너무짧음" : ""}`);
  }

  // ── 저장 / 불러오기 ──
  console.log("\n=== 저장 · 불러오기 ===");
  ev("cash=777000000; day=42; dayType='sat'; depot=99; exp9=true;");
  ev("named.set(5, 500); retail.set(5, 3);");
  ev("saveGame(1)");
  console.log("  저장정보:", ev("savedInfo()"));
  const snap = ev("JSON.stringify(snapshot()).length");
  console.log("  스냅샷 크기:", snap, "바이트");

  // 값 망가뜨린 뒤 복구
  ev("cash=1; day=1; dayType='wd'; depot=1; exp9=false; named.clear(); retail.clear();");
  window.loadGame(); await wait(400);
  console.log("  복구 cash:", ev("cash"), "day:", ev("day"), "dayType:", ev("dayType"),
    "depot:", ev("depot"), "exp9:", ev("exp9"));
  console.log("  named:", ev("[...named]"), "retail:", ev("[...retail]"));
  console.log("  건설역 수 복구:", ev("built.size"), "open:", [...ev("open")]);

  // dock 갱신
  ev("dock()");
  console.log("\n  dock 혼잡:", doc.getElementById("dkjam").textContent,
    "· 평판:", doc.getElementById("dkrep").textContent,
    "· 요일:", doc.getElementById("dkday").textContent);

  if (errors.length) { console.log("\nERRORS:", errors); process.exit(1); }
  console.log("\nNO ERRORS");
  process.exit(0);
})().catch(e => { console.error("THREW:", e); process.exit(1); });
