// GitHub Pages 모드(구글 로그인 + Sheets API)를 가짜 구글 서버로 확인한다.
// 실행: node tools/test-web.js
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { JSDOM, VirtualConsole } = require("jsdom");

const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8")
  .replace('clientId: "",', 'clientId: "test-client.apps.googleusercontent.com",');
const SHEET_ID = "1IaNAAiPgWUDcVrO2GOd4oCgnGwNsgXjraln5P6rRTeg";

// 가짜 스프레드시트: 탭 이름 → 2차원 배열
function fakeGoogle(store, { email = "forsythia1226@gmail.com", fail401Once = null } = {}) {
  const calls = [];
  const res = (status, body) => ({ ok: status < 300, status, json: async () => body });
  const fetch = async (url, opt = {}) => {
    const u = new URL(url);
    const method = opt.method || "GET";
    calls.push(`${method} ${u.pathname.split("/").pop()}`);
    if (fail401Once && u.pathname.endsWith(fail401Once)) { fail401Once = null; return res(401, { error: { message: "expired" } }); }
    if (u.host === "openidconnect.googleapis.com") return res(200, { email });
    if (u.host === "www.googleapis.com") return res(200, { items: [{ summary: "개천절", description: "공휴일", start: { date: "2026-10-03" }, end: { date: "2026-10-04" } }] });
    assert.ok(u.pathname.includes(SHEET_ID), "spreadsheet id");
    if (method === "GET" && u.searchParams.get("fields")) return res(200, { sheets: Object.keys(store).map((title) => ({ properties: { title } })) });
    if (u.pathname.endsWith("/values:batchUpdate")) {
      for (const { range, values } of JSON.parse(opt.body).data) {
        const [tab, cell] = range.split("!");
        const r0 = +cell.slice(1) - 1;
        values.forEach((row, i) => { store[tab][r0 + i] = row.slice(); });
      }
      return res(200, {});
    }
    if (u.pathname.endsWith(":batchUpdate")) { // 탭 추가 (values:batchUpdate 는 위에서 처리)
      JSON.parse(opt.body).requests.forEach((r) => { store[r.addSheet.properties.title] = []; });
      return res(200, {});
    }
    if (u.pathname.endsWith("/values:batchGet")) {
      const valueRanges = u.searchParams.getAll("ranges").map((r) => {
        const rows = (store[r.split("!")[0]] || []).map((row) => { const c = row.slice(); while (c.length && c[c.length - 1] === "") c.pop(); return c; });
        while (rows.length && !rows[rows.length - 1].length) rows.pop(); // 실제 API처럼 끝의 빈 행은 오지 않는다
        return { values: rows };
      });
      return res(200, { valueRanges });
    }
    throw new Error("unexpected " + method + " " + url);
  };
  const oauth2 = {
    initTokenClient: () => ({ requestAccessToken() { setTimeout(() => this.callback({ access_token: "tok", expires_in: 3600 }), 1); } }),
    revoke: () => {},
  };
  return { calls, install: (w) => { w.fetch = fetch; w.google = { accounts: { oauth2 } }; w.scrollTo = () => {}; } };
}

function open(store, opts) {
  const g = fakeGoogle(store, opts);
  const errors = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => { if (!/scrollTo/.test(e.message)) errors.push(e.message); });
  const dom = new JSDOM(html, { runScripts: "dangerously", url: "https://forsythia1226-droid.github.io/new-report-app/", virtualConsole: vc, beforeParse: g.install });
  dom.window.HTMLElement.prototype.scrollIntoView = () => {};
  const $ = (s) => dom.window.document.querySelector(s);
  return { w: dom.window, $, calls: g.calls, errors, text: (s) => $(s).textContent.replace(/\s+/g, " ").trim() };
}
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const todayKey = (() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; })();

(async () => {
  const store = {}; // 빈 스프레드시트에서 시작

  // 1. 첫 방문: 로그인 버튼 → 탭 자동 생성 → 대시보드
  let p = open(store);
  await wait(50);
  assert.match(p.text("#gate-start"), /Google 계정으로 로그인/);
  p.$("#gate-start").click();
  await wait(150);
  assert.ok(p.$("#gate").hidden, "로그인 후 시작 화면 닫힘");
  assert.deepStrictEqual(Object.keys(store).sort(), ["checks", "inbody", "plans", "principles", "saju", "settings", "workouts"]);
  assert.ok(String(store.saju[1][0]).startsWith("채주엽 사주_260903"), "사주 원문 저장");
  assert.match(p.text("#sync"), /동기화/);
  assert.ok(p.calls.includes("GET events"), "공휴일 조회");

  // 2. 오늘 운동 완료 + 계획 → 시트에 저장
  p.$("[data-tab=body]").click();
  p.$("#today-card .done-btn").click();
  const cell = p.$(`.cal .day[data-date="${todayKey}"]`);
  cell.click();
  p.$("[data-part=walking]").click();
  await wait(800);
  assert.deepStrictEqual(store.workouts.filter((r) => r[0]).map((r) => r.slice(0, 2)), [["날짜", "운동함"], [todayKey, true]]);
  assert.ok(store.plans.some((r) => r[0] === todayKey && /워킹/.test(r[1])), "계획 저장");
  assert.deepStrictEqual(p.errors, []);
  p.w.close();

  // 3. 다시 열기: 저장한 기록이 그대로
  p = open(store);
  await wait(30);
  p.$("#gate-start").click();
  await wait(150);
  p.$("[data-tab=body]").click();
  assert.match(p.text("#today-card .done-btn"), /완료/);
  p.$("#today-card .done-btn").click(); // 취소 → 시트에서 행이 지워져야 한다
  await wait(800);
  assert.ok(!store.workouts.some((r) => r[0] === todayKey && r[1] === true), "취소하면 시트에서도 지워짐");
  p.w.close();

  // 4. 다른 계정은 막힌다
  p = open(store, { email: "someone@taihan.com" });
  await wait(30);
  p.$("#gate-start").click();
  await wait(100);
  assert.ok(!p.$("#gate").hidden && /전용이에요/.test(p.text("#gate-status")), "다른 계정 차단");
  assert.ok(!p.calls.includes("GET values:batchGet"), "다른 계정은 시트를 읽지 않음");
  p.w.close();

  // 5. 로그인 만료(401) 중 저장 → 다시 로그인하면 이어서 저장
  p = open(store, { fail401Once: "/values:batchUpdate" });
  await wait(30);
  p.$("#gate-start").click();
  await wait(150);
  p.$("[data-tab=body]").click();
  p.w.sessionStorage.clear();
  p.$("#today-card .done-btn").click();
  await wait(800);
  assert.ok(!p.$("#gate").hidden && /다시 로그인/.test(p.text("#gate-start")), "만료 시 다시 로그인 안내");
  p.$("#gate-start").click();
  await wait(150);
  assert.ok(p.$("#gate").hidden, "다시 로그인 후 닫힘");
  assert.ok(store.workouts.some((r) => r[0] === todayKey && r[1] === true), "만료 후 이어서 저장");
  p.w.close();

  // 6. Apps Script 주소(google.script.run)도 그대로 동작한다
  {
    const calls = [];
    const server = {
      whoAmI: () => ({ email: "forsythia1226@gmail.com", owner: "forsythia1226@gmail.com", ok: true, url: "u" }),
      getData: () => ({ goal: { weight: 68, fat: 12 }, yearBase: { month: "2026-09", count: 100 }, vision: "", identity: "", keywords: [], inbody: [], done: { [todayKey]: true }, plans: {}, checks: [], principles: [], saju: "" }),
      getHolidays: () => ({}), saveAll: () => true,
    };
    const dom = new JSDOM(fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8"), { runScripts: "dangerously", url: "https://script.google.com/macros/s/x/exec", beforeParse(w) {
      w.scrollTo = () => {};
      const mk = () => { let ok = () => {}, fail = () => {}; const r = { withSuccessHandler(f) { ok = f; return r; }, withFailureHandler(f) { fail = f; return r; } };
        for (const k of Object.keys(server)) r[k] = (...a) => { calls.push(k); setTimeout(() => { try { ok(server[k](...a)); } catch (e) { fail(e); } }, 1); }; return r; };
      w.google = { script: { get run() { return mk(); } } };
    } });
    await wait(80);
    const $ = (q) => dom.window.document.querySelector(q);
    assert.ok(!$("#gate-start").disabled && /시작하기/.test($("#gate-start").textContent), "Apps Script: 시작하기 활성");
    $("#gate-start").click();
    assert.ok($("#gate").hidden, "Apps Script: 시작 화면 닫힘");
    assert.deepStrictEqual([...new Set(calls)].sort(), ["getData", "getHolidays", "whoAmI"]);
    dom.window.close();
  }

  console.log("test-web: all passed");
})().catch((e) => { console.error(e); process.exitCode = 1; });
