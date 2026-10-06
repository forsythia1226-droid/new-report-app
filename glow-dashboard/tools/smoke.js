// index.html 을 jsdom 에서 예시 데이터(미리보기 모드)로 띄워 주요 동작을 눌러 본다.
// 실행: npm install (처음 한 번) → node tools/smoke.js
const fs = require("fs");
const path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom");

const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const errors = [];
const vc = new VirtualConsole();
vc.on("jsdomError", (e) => { if (!/scrollTo/.test(e.message)) errors.push(e.message); }); // jsdom 미구현 API는 무시

const dom = new JSDOM(html, { runScripts: "dangerously", url: "https://preview.test/", virtualConsole: vc, pretendToBeVisual: true });
const w = dom.window;
w.HTMLElement.prototype.scrollIntoView = () => {};
const $ = (s) => w.document.querySelector(s);
const text = (s) => $(s).textContent.replace(/\s+/g, " ").trim();
const check = (name, ok, detail = "") => { if (!ok) errors.push(`${name} ${detail}`); console.log(`${ok ? "✓" : "✗"} ${name}${detail ? " — " + detail : ""}`); };

setTimeout(() => {
  try {
    check("카테고리 6개", w.document.querySelectorAll(".tab").length === 6, [...w.document.querySelectorAll(".tab")].map((t) => t.textContent.trim()).join(" "));
    check("홈 지향 묘사", text("#home-vision").startsWith("그를 처음 보았을 때"));

    $("[data-tab=body]").click();
    check("신체 맨 위 = 목표 달성", $("#v-body .grid > .card h2").textContent.includes("목표 달성"));
    check("종합 달성률 표시", /\d+%/.test(text("#goal-main")), text("#goal-main"));
    check("달력 일요일 시작", [...w.document.querySelectorAll(".cal .wd")].map((e) => e.textContent).join("") === "일월화수목금토");
    check("오늘 카드", text("#today-card").length > 0, text("#today-card").slice(0, 40));

    const before = text("#tiles").match(/\d+월 운동(\d+)회/)[1];
    $("#today-card .done-btn").click();
    const after = text("#tiles").match(/\d+월 운동(\d+)회/)[1];
    check("오늘 완료 토글로 이번 달 횟수 변화", before !== after, `${before} → ${after}`);

    const free = [...w.document.querySelectorAll(".cal .day[data-date]")].find((b) => !b.classList.contains("other") && !b.querySelector(".plan"));
    free.click();
    $("[data-part=legs]").click();
    check("날짜 계획 저장", text("#sel-sub").includes("하체"), text("#sel-sub"));

    $("#clear-examples").click();
    $("[data-tab=body]").click();
    check("예시 지우기 후 빈 목표 안내", text("#goal-main").includes("인바디"));
  } catch (e) {
    errors.push("test: " + e.message);
  }
  console.log(errors.length ? `\nFAILED:\n- ${errors.join("\n- ")}` : "\nsmoke: all passed");
  w.close();
  process.exitCode = errors.length ? 1 : 0;
}, 300);
