// Code.gs 를 가짜 스프레드시트 위에서 돌려 setup → saveAll → getData 왕복을 확인한다.
// 실행: node tools/test-sheet.js   (의존성 없음)
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");
// vm 안에서 만든 객체는 프로토타입이 달라 deepStrictEqual 이 실패하므로 값만 비교한다
const eq = (a, b) => assert.deepStrictEqual(JSON.parse(JSON.stringify(a)), JSON.parse(JSON.stringify(b)));

const root = path.join(__dirname, "..");

function mkSheet(name) {
  const d = [];
  return {
    name, d,
    getName: () => name,
    getLastRow: () => { for (let i = d.length; i > 0; i--) if ((d[i - 1] || []).some((v) => v !== "" && v != null)) return i; return 0; },
    getLastColumn: () => { let m = 0; d.forEach((r) => (r || []).forEach((v, j) => { if (v !== "" && v != null && j + 1 > m) m = j + 1; })); return m; },
    setFrozenRows() {}, setColumnWidth() {},
    getRange(a, b, c, e) {
      if (typeof a === "string") { const m = a.match(/([A-Z])(\d+)/); b = m[1].charCodeAt(0) - 64; a = +m[2]; c = 1; e = 1; }
      const r0 = a, c0 = b, nr = c || 1, nc = e || 1;
      const R = {
        setValues(v) { v.forEach((row, i) => row.forEach((x, j) => { (d[r0 - 1 + i] = d[r0 - 1 + i] || [])[c0 - 1 + j] = x; })); return R; },
        getValues() { return [...Array(nr)].map((_, i) => [...Array(nc)].map((_, j) => { const x = (d[r0 - 1 + i] || [])[c0 - 1 + j]; return x === undefined ? "" : x; })); },
        getValue() { return R.getValues()[0][0]; },
        setValue(v) { return R.setValues([[v]]); },
        clearContent() { for (let i = 0; i < nr; i++) for (let j = 0; j < nc; j++) if (d[r0 - 1 + i]) d[r0 - 1 + i][c0 - 1 + j] = ""; return R; },
        setFontWeight: () => R, setNumberFormat: () => R, setWrap: () => R, setVerticalAlignment: () => R, insertCheckboxes: () => R, removeCheckboxes: () => R,
      };
      return R;
    },
  };
}

load.email = "forsythia1226@gmail.com";
function load() {
  const sheets = [];
  const ss = {
    getSheetByName: (n) => sheets.find((s) => s.name === n) || null,
    insertSheet: (n) => { const s = mkSheet(n); sheets.push(s); return s; },
    getSheets: () => sheets.slice(),
    deleteSheet: (s) => sheets.splice(sheets.indexOf(s), 1),
    getSpreadsheetTimeZone: () => "Asia/Seoul",
    setSpreadsheetTimeZone() {},
  };
  const fmt = (d, tz, f) => { const y = d.getFullYear(), m = ("0" + (d.getMonth() + 1)).slice(-2), dd = ("0" + d.getDate()).slice(-2); return f === "yyyy-MM" ? `${y}-${m}` : `${y}-${m}-${dd}`; };
  const ctx = {
    SpreadsheetApp: { getActiveSpreadsheet: () => ss },
    LockService: { getScriptLock: () => ({ waitLock() {}, releaseLock() {} }) },
    Utilities: { formatDate: fmt },
    HtmlService: {},
    CalendarApp: null,
    Session: { getActiveUser: () => ({ getEmail: () => load.email }) },
    ScriptApp: { getService: () => ({ getUrl: () => "https://script.google.com/macros/s/TEST/exec" }) },
  };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(root, "Saju.gs"), "utf8") + "\n" + fs.readFileSync(path.join(root, "Code.gs"), "utf8"), ctx);
  return { ctx, ss };
}

// 1. 새 시트: 기본값
{
  const { ctx } = load();
  ctx.setup();
  const d = ctx.getData();
  eq(d.goal, { weight: 68, fat: 12, muscle: null }); // 목표 골격근량은 비어 있으면 화면이 추정한다
  eq(d.yearBase, { month: "2026-09", count: 100 });
  assert.ok(d.saju.startsWith("응. 남편분은"), "saju 탭 = 신살 원문");
  assert.strictEqual(d.sajuMonthly.length, 1);
  assert.ok(d.sajuMonthly[0].text.startsWith("채주엽 사주_260903") && d.sajuMonthly[0].date === "2026-09-03", "saju_monthly 첫 행");
  assert.ok(d.vision.startsWith("그를 처음 보았을 때"));
}

// 2. 저장 → 다시 읽기
{
  const { ctx } = load();
  ctx.setup();
  const d = ctx.getData();
  d.done = { "2026-10-06": true };
  d.plans = { "2026-10-07": ["back", "biceps"], "2026-10-08": ["walking", "running"] };
  d.inbody = [{ date: "2026-10-06", w: 62.5, m: 28, f: 18.2, bmr: null }];
  d.checks = [{ date: "2026-10-06", s: { solid: 4, confidence: 4, ease: 5, principle: null }, note: "메모" }];
  d.principles = ["원칙1"];
  d.sajuMonthly = d.sajuMonthly.concat({ date: "2026-11-01", title: "11월 자료", text: "1. 2026년 11월 — 己亥" });
  d.careerLog = [{ date: "2026-10-20", kind: "보안 감사", text: "내부 감사 대응" }];
  d.careerRows = [["ADsP", "합격", "2026-12-05", ""], ["학위 이수학점", "", "", 35]];
  d.cardio = [{ date: "2026-10-06", part: "running", min: 30 }];
  d.rm = [{ date: "2026-10-06", part: "chest", kg: 60 }, { date: "2026-09-01", part: "triceps", kg: 27.5 }];
  ctx.saveAll(d);
  const e = ctx.getData();
  eq(e.done, d.done);
  eq(e.plans, d.plans);
  eq(e.inbody, d.inbody);
  eq(e.checks, d.checks);
  eq(e.principles, d.principles);
  eq(e.sajuMonthly.map((m) => m.title), ["채주엽 사주_260903", "11월 자료"]);
  eq(e.careerLog, [{ date: "2026-10-20", kind: "보안 감사", text: "내부 감사 대응" }]);
  eq(e.career, [["ADsP", "합격", "2026-12-05", ""], ["학위 이수학점", "", "", 35]]);
  eq(e.cardio, [{ date: "2026-10-06", part: "running", min: 30 }]);
  eq(e.rm, [{ date: "2026-09-01", part: "triceps", kg: 27.5 }, { date: "2026-10-06", part: "chest", kg: 60 }]);
}

// 3. 예전 형식 시트 이전 (부위별 운동 열, 부드러운 태도 점검)
{
  const { ctx, ss } = load();
  ss.insertSheet("workouts").getRange(1, 1, 3, 4).setValues([["날짜", "가슴", "어깨", "코어"], ["2026-10-01", true, false, false], ["2026-10-02", false, false, false]]);
  ss.insertSheet("checks").getRange(1, 1, 2, 6).setValues([["날짜", "자신감", "에너지", "원칙 지킴", "부드러운 태도", "메모"], ["2026-10-01", 4, 2, 5, 3, "예전"]]);
  ctx.setup();
  const d = ctx.getData();
  eq(d.done, { "2026-10-01": true });
  eq(d.checks[0].s, { solid: null, confidence: 4, ease: 3, principle: 5 });
}

// 4. 사람이 시트에 직접 쓴 형식
{
  const { ctx, ss } = load();
  ctx.setup();
  ss.getSheetByName("plans").getRange(2, 1, 1, 2).setValues([["2026.10.9", "어깨·복근"]]);
  ss.getSheetByName("workouts").getRange(2, 1, 1, 2).setValues([[new Date(2026, 9, 5), "O"]]);
  const d = ctx.getData();
  eq(d.plans["2026-10-09"], ["shoulder", "abs"]);
  eq(d.done, { "2026-10-05": true });
}

// 5. 소유자가 아닌 계정은 막는다
{
  const { ctx } = load();
  eq(ctx.whoAmI(), { email: "forsythia1226@gmail.com", owner: "forsythia1226@gmail.com", ok: true, url: "https://script.google.com/macros/s/TEST/exec" });
  load.email = "someone@else.com";
  assert.strictEqual(ctx.whoAmI().ok, false);
  assert.throws(() => ctx.getData(), /forsythia1226@gmail.com 계정만/);
  load.email = "forsythia1226@gmail.com";
}

console.log("test-sheet: all passed");
