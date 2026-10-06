// Glow 대시보드 — 이 스프레드시트에 붙은 Apps Script.
// 웹 앱으로 배포하면 index.html 화면을 띄우고, 데이터는 아래 탭들에 읽고 쓴다.

var TABS = {
  inbody: ["측정일", "체중", "골격근량", "체지방률", "기초대사량"],
  workouts: ["날짜", "운동함"],
  plans: ["날짜", "계획 부위"],
  checks: ["날짜", "단단함", "자신감", "여유", "원칙 지킴", "메모"],
  principles: ["순서", "원칙"],
  settings: ["항목", "값"],
  saju: ["원문"],
  saju_monthly: ["올린 날", "제목", "원문"],
  career: ["항목", "상태", "날짜", "값"],
  career_log: ["날짜", "구분", "내용"],
  rm: ["날짜", "부위", "1RM(kg)"],
  cardio: ["날짜", "종목", "시간(분)"],
};
var PARTS = ["chest", "shoulder", "back", "legs", "biceps", "triceps", "forearm", "abs", "walking", "running"];
// 부위 이름 → 키. 예전 workouts 탭의 부위별 열과 plans 탭의 "계획 부위" 글자를 읽을 때 쓴다.
var PART_BY_NAME = { 가슴: "chest", 어깨: "shoulder", 등: "back", 하체: "legs", 이두: "biceps", 삼두: "triceps", 전완근: "forearm", 복근: "abs", 코어: "abs", 워킹: "walking", 러닝: "running" };
var PART_NAMES = { chest: "가슴", shoulder: "어깨", back: "등", legs: "하체", biceps: "이두", triceps: "삼두", forearm: "전완근", abs: "복근", walking: "워킹", running: "러닝" };
// 이 대시보드를 쓸 수 있는 유일한 구글 계정. 웹 앱 접근 권한("나만")에 더해 서버에서 한 번 더 확인한다.
var OWNER_EMAIL = "forsythia1226@gmail.com";
var KR_HOLIDAY_CALENDAR ="ko.south_korea#holiday@group.v.calendar.google.com";
// Saju.gs 의 원문(SAJU_RAW)은 월별 운세 + 신살 해석이 이어져 있다. 이 문장부터가 신살(고정) 부분.
var SAJU_MARK = "응. 남편분은 화면상 원국이";
function splitSaju_(raw) {
  var i = String(raw).indexOf(SAJU_MARK);
  return i < 0 ? { monthly: String(raw).trim(), shinsal: "" } : { monthly: String(raw).slice(0, i).trim(), shinsal: String(raw).slice(i).trim() };
}
var CHECK_KEYS = ["solid", "confidence", "ease", "principle"];
// checks 탭 머리글 → 점검 키. 예전 시트의 "부드러운 태도"는 여유로, "에너지"는 버린다.
var CHECK_BY_HEADER = { 단단함: "solid", 자신감: "confidence", 여유: "ease", "부드러운 태도": "ease", "원칙 지킴": "principle" };
var DEFAULT_VISION = "그를 처음 보았을 때, 나는 그가 다른 이들과 다르다는 것을 느꼈다. 다부진 체구에서는 단단함을, 총명한 눈빛에서는 미래를 아는 듯한 자신감을 부드러운 말투에서는 여유와 편안함이 느껴졌다. 그 사람에게서 나오는 아우라가 그와 함께 있는 공간을 가득채웠다.";

function doGet() {
  return HtmlService.createHtmlOutputFromFile("index")
    .setTitle("Glow")
    .addMetaTag("viewport", "width=device-width, initial-scale=1, viewport-fit=cover");
}

/** 처음 한 번 실행: 탭과 머리글을 만들고 기본 설정·사주 원문을 넣는다. 다시 실행해도 기존 기록은 지우지 않는다. */
function setup() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (ss.getSpreadsheetTimeZone() !== "Asia/Seoul") ss.setSpreadsheetTimeZone("Asia/Seoul");
  Object.keys(TABS).forEach(function (name) {
    var head = TABS[name];
    var sh = sheet_(name);
    // 이미 쓰던 탭의 머리글은 건드리지 않는다 (예전 열 구성은 다음 저장 때 데이터와 함께 옮겨진다)
    if (sh.getLastRow() === 0) sh.getRange(1, 1, 1, head.length).setValues([head]).setFontWeight("bold");
    sh.setFrozenRows(1);
  });
  ["inbody", "workouts", "plans", "checks", "rm", "cardio"].forEach(function (name) {
    sheet_(name).getRange("A2:A").setNumberFormat("yyyy-mm-dd");
  });

  // 없는 설정 항목만 채운다 (이미 있는 값은 그대로)
  var set = sheet_("settings");
  var have = {};
  rows_("settings").forEach(function (r) { have[String(r[0]).trim()] = true; });
  [
    ["목표 체중", 68],
    ["목표 체지방률", 12],
    ["누적 기준 월", "2026-09"],
    ["누적 기준 횟수", 100],
    ["지향 묘사", DEFAULT_VISION],
    ["정체성 문장", "단단한 몸처럼 흔들리지 않고, 부드러운 태도로 사람을 대한다."],
    ["키워드", "단단함, 자신감, 여유, 편안함, 아우라"],
  ].forEach(function (row) {
    if (!have[row[0]]) set.getRange(set.getLastRow() + 1, 1, 1, 2).setValues([row]);
  });
  set.getRange("B2:B").setWrap(true);
  set.setColumnWidth(2, 480);

  var sj = sheet_("saju");
  var parts = splitSaju_(SAJU_RAW);
  if (!sj.getRange("A2").getValue()) sj.getRange("A2").setValue(parts.shinsal);
  var sm = sheet_("saju_monthly");
  if (sm.getLastRow() < 2) sm.getRange(2, 1, 1, 3).setValues([["2026-09-03", "채주엽 사주_260903", parts.monthly]]);
  sm.getRange("C2:C").setWrap(true);
  sm.setColumnWidth(3, 700);
  sj.getRange("A2").setWrap(true).setVerticalAlignment("top");
  sj.setColumnWidth(1, 900);

  // 새 스프레드시트에 기본으로 생기는 빈 시트 정리
  ss.getSheets().forEach(function (sh) {
    if (!TABS[sh.getName()] && sh.getLastRow() === 0 && ss.getSheets().length > 1) ss.deleteSheet(sh);
  });
}

/** 화면이 처음 열릴 때 전체 데이터를 읽어 간다. */
/** 시작 화면용: 지금 로그인한 구글 계정과 허용 여부, 계정 바꾸기용 웹 앱 주소. */
function whoAmI() {
  var email = activeEmail_();
  return { email: email, owner: OWNER_EMAIL, ok: isOwner_(email), url: ScriptApp.getService().getUrl() };
}

function getData() {
  assertOwner_();
  // 처음 열 때(탭이 아직 없을 때) 자동으로 설정한다. 이후에는 탭이 있으니 건너뛴다.
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (Object.keys(TABS).some(function (n) { return !ss.getSheetByName(n); })) setup();

  var settings = {};
  rows_("settings").forEach(function (r) { settings[String(r[0]).trim()] = r[1]; });

  // 운동한 날. 예전 형식(부위별 체크 열)이면 한 부위라도 체크된 날을 운동한 날로 본다.
  var done = {};
  var wsh = sheet_("workouts");
  if (wsh.getLastRow() >= 2) {
    var width = wsh.getLastColumn();
    var head = wsh.getRange(1, 1, 1, width).getValues()[0].map(function (h) { return String(h).trim(); });
    wsh.getRange(2, 1, wsh.getLastRow() - 1, width).getValues().forEach(function (r) {
      if (r[0] === "" || r[0] == null) return;
      var on = head.some(function (h, i) { return i > 0 && (h === "운동함" || PART_BY_NAME[h]) && isOn_(r[i]); });
      if (on) done[day_(r[0])] = true;
    });
  }

  var plans = {};
  rows_("plans").forEach(function (r) {
    var parts = partsFromText_(r[1]);
    if (parts.length) plans[day_(r[0])] = parts;
  });

  return {
    goal: { weight: num_(settings["목표 체중"], 68), fat: num_(settings["목표 체지방률"], 12) },
    // 앱 이전 운동 기록: 기준 월까지 N회 (그 다음 달부터 앱 기록을 더한다)
    yearBase: { month: month_(settings["누적 기준 월"]), count: num_(settings["누적 기준 횟수"], 0) },
    vision: str_(settings["지향 묘사"]),
    identity: str_(settings["정체성 문장"]),
    keywords: str_(settings["키워드"]).split(",").map(function (s) { return s.trim(); }).filter(String),
    inbody: rows_("inbody")
      .filter(function (r) { return r[1] !== ""; })
      .map(function (r) { return { date: day_(r[0]), w: num_(r[1]), m: num_(r[2]), f: num_(r[3]), bmr: num_(r[4]) }; }),
    done: done,
    plans: plans,
    checks: readChecks_(),
    principles: rows_("principles")
      .sort(function (a, b) { return num_(a[0], 0) - num_(b[0], 0); })
      .map(function (r) { return str_(r[1]); })
      .filter(String),
    saju: str_(sheet_("saju").getRange("A2").getValue()),
    // 커리어: [항목, 상태, 날짜, 값] 행을 그대로 넘기고 화면(careerFromRows)이 해석한다
    career: rows_("career").length ? rows_("career").map(function (r) { return [str_(r[0]).trim(), str_(r[1]).trim(), r[2] === "" || r[2] == null ? "" : day_(r[2]), r[3]]; }) : null,
    careerLog: rows_("career_log")
      .filter(function (r) { return str_(r[2]).trim(); })
      .map(function (r) { return { date: day_(r[0]), kind: str_(r[1]), text: str_(r[2]) }; }),
    sajuMonthly: rows_("saju_monthly")
      .filter(function (r) { return str_(r[2]).trim(); })
      .map(function (r) { return { date: day_(r[0]), title: str_(r[1]), text: str_(r[2]) }; }),
    cardio: rows_("cardio")
      .map(function (r) { return { date: day_(r[0]), part: PART_BY_NAME[str_(r[1]).trim()], min: num_(r[2]) }; })
      .filter(function (c) { return (c.part === "walking" || c.part === "running") && c.min > 0; }),
    rm: rows_("rm")
      .map(function (r) { return { date: day_(r[0]), part: PART_BY_NAME[str_(r[1]).trim()], kg: num_(r[2]) }; })
      .filter(function (r) { return r.part && r.kg > 0; }),
  };
}

/**
 * 구글 캘린더 "대한민국의 휴일"에서 한 해의 공휴일·기념일을 읽는다.
 * 반환: { "2026-10-03": { name: "개천절", off: true }, ... }  off=false는 쉬지 않는 기념일(어버이날 등).
 * 처음 쓸 때 캘린더 읽기 권한을 한 번 더 묻는다.
 */
function getHolidays(year) {
  assertOwner_();
  var cal;
  try {
    cal = CalendarApp.getCalendarById(KR_HOLIDAY_CALENDAR) || CalendarApp.subscribeToCalendar(KR_HOLIDAY_CALENDAR, { hidden: true });
  } catch (e) {
    return null; // 권한이 없거나 캘린더를 못 열면 화면의 내장 공휴일 표를 쓴다
  }
  if (!cal) return null;
  var tz = SpreadsheetApp.getActiveSpreadsheet().getSpreadsheetTimeZone();
  var out = {};
  cal.getEvents(new Date(year, 0, 1), new Date(year + 1, 0, 1)).forEach(function (ev) {
    var desc = String(ev.getDescription() || "");
    var off = !/기념일|observance/i.test(desc);
    var allDay = ev.isAllDayEvent();
    var end = allDay ? ev.getAllDayEndDate() : ev.getEndTime();
    for (var t = new Date(allDay ? ev.getAllDayStartDate() : ev.getStartTime()); t < end; t.setDate(t.getDate() + 1)) {
      var k = Utilities.formatDate(t, tz, "yyyy-MM-dd");
      if (out[k] && out[k].off && !off) continue; // 공휴일이 겹치면 공휴일 이름을 우선
      out[k] = { name: ev.getTitle(), off: off };
    }
  });
  return out;
}

/** 화면에서 바뀐 내용을 통째로 다시 쓴다 (탭마다 수백 행 수준이라 충분히 빠르다). */
function saveAll(s) {
  assertOwner_();
  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    var byDate = function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : 0; };
    write_("inbody", (s.inbody || []).slice().sort(byDate).map(function (r) {
      return [r.date, r.w, r.m, r.f, r.bmr == null ? "" : r.bmr];
    }));

    var days = Object.keys(s.done || {}).filter(function (d) { return s.done[d]; }).sort();
    write_("workouts", days.map(function (d) { return [d, true]; }));
    if (days.length) sheet_("workouts").getRange(2, 2, days.length, 1).insertCheckboxes();

    var planDays = Object.keys(s.plans || {}).sort();
    write_("plans", planDays.map(function (d) { return [d, partsToText_(s.plans[d])]; }));

    write_("checks", (s.checks || []).slice().sort(byDate).map(function (c) {
      return [c.date].concat(CHECK_KEYS.map(function (k) { return c.s[k] == null ? "" : c.s[k]; }), [c.note || ""]);
    }));
    if (s.sajuShinsal) write_("saju", [[s.sajuShinsal]]);
    if (s.careerRows) write_("career", s.careerRows);
    write_("career_log", (s.careerLog || []).slice()
      .sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : 0; })
      .map(function (l) { return [l.date, l.kind, l.text]; }));
    write_("saju_monthly", (s.sajuMonthly || []).slice()
      .sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : 0; })
      .map(function (m) { return [m.date, m.title, m.text]; }));
    write_("cardio", (s.cardio || []).slice()
      .sort(function (a, b) { var x = a.date + a.part, y = b.date + b.part; return x < y ? -1 : x > y ? 1 : 0; })
      .map(function (r) { return [r.date, PART_NAMES[r.part], r.min]; }));
    write_("rm", (s.rm || []).slice()
      .sort(function (a, b) { var x = a.date + a.part, y = b.date + b.part; return x < y ? -1 : x > y ? 1 : 0; })
      .map(function (r) { return [r.date, PART_NAMES[r.part], r.kg]; }));
    write_("principles", (s.principles || []).map(function (p, i) { return [i + 1, p]; }));
    write_("settings", [
      ["목표 체중", s.goal.weight],
      ["목표 체지방률", s.goal.fat],
      ["누적 기준 월", s.yearBase && s.yearBase.month ? "'" + s.yearBase.month : ""],
      ["누적 기준 횟수", s.yearBase ? s.yearBase.count : ""],
      ["지향 묘사", s.vision || DEFAULT_VISION],
      ["정체성 문장", s.identity || ""],
      ["키워드", (s.keywords || []).join(", ")],
    ]);
  } finally {
    lock.releaseLock();
  }
  return true;
}

/* ---------- helpers ---------- */
function activeEmail_() {
  try { return String(Session.getActiveUser().getEmail() || "").toLowerCase(); } catch (e) { return ""; }
}
// "나만" 배포에서는 구글이 이미 소유자만 들여보내므로, 이메일을 못 읽는 경우(빈 값)는 통과시킨다.
function isOwner_(email) { return !email || email === OWNER_EMAIL; }
function assertOwner_() {
  if (!isOwner_(activeEmail_())) throw new Error("이 대시보드는 " + OWNER_EMAIL + " 계정만 사용할 수 있습니다.");
}

// "가슴, 삼두" ↔ ["chest", "triceps"]
function partsFromText_(v) {
  var keys = [];
  String(v == null ? "" : v).split(/[,·\/\s]+/).forEach(function (n) {
    var k = PART_BY_NAME[n.trim()];
    if (k && keys.indexOf(k) < 0) keys.push(k);
  });
  return PARTS.filter(function (k) { return keys.indexOf(k) >= 0; });
}
function partsToText_(keys) {
  return PARTS.filter(function (k) { return (keys || []).indexOf(k) >= 0; }).map(function (k) { return PART_NAMES[k]; }).join(", ");
}

// 머리글 이름으로 열을 찾아 읽는다 (열 순서·구성이 바뀐 예전 시트도 읽힘)
function readChecks_() {
  var sh = sheet_("checks");
  if (sh.getLastRow() < 2) return [];
  var width = sh.getLastColumn();
  var head = sh.getRange(1, 1, 1, width).getValues()[0].map(function (h) { return String(h).trim(); });
  var noteCol = head.indexOf("메모");
  return sh.getRange(2, 1, sh.getLastRow() - 1, width).getValues()
    .filter(function (r) { return r[0] !== "" && r[0] != null; })
    .map(function (r) {
      var s = {};
      CHECK_KEYS.forEach(function (k) { s[k] = null; });
      head.forEach(function (h, i) { if (CHECK_BY_HEADER[h]) s[CHECK_BY_HEADER[h]] = num_(r[i]); });
      return { date: day_(r[0]), s: s, note: noteCol >= 0 ? str_(r[noteCol]) : "" };
    });
}

function sheet_(name) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  return ss.getSheetByName(name) || ss.insertSheet(name);
}

function rows_(name) {
  var sh = sheet_(name);
  var n = sh.getLastRow();
  if (n < 2) return [];
  return sh.getRange(2, 1, n - 1, TABS[name].length).getValues().filter(function (r) { return r[0] !== "" && r[0] != null; });
}

// 머리글까지 다시 써서, 열 구성이 바뀐 예전 시트도 저장할 때 새 구성으로 맞춘다.
function write_(name, rows) {
  var sh = sheet_(name);
  var head = TABS[name];
  var width = Math.max(head.length, sh.getLastColumn());
  var last = sh.getLastRow();
  if (last > 1) {
    if (name === "workouts") sh.getRange(2, 2, last - 1, width - 1).removeCheckboxes();
    sh.getRange(2, 1, last - 1, width).clearContent();
  }
  sh.getRange(1, 1, 1, width).clearContent();
  sh.getRange(1, 1, 1, head.length).setValues([head]).setFontWeight("bold");
  if (rows.length) sh.getRange(2, 1, rows.length, head.length).setValues(rows);
}

// 시트에 직접 입력한 "2026.10.5", "2026/10/05" 같은 날짜도 받아준다.
function day_(v) {
  var tz = SpreadsheetApp.getActiveSpreadsheet().getSpreadsheetTimeZone();
  if (isDate_(v)) return Utilities.formatDate(v, tz, "yyyy-MM-dd");
  var m = String(v).match(/(\d{4})\D+(\d{1,2})\D+(\d{1,2})/);
  if (!m) return String(v);
  return m[1] + "-" + ("0" + m[2]).slice(-2) + "-" + ("0" + m[3]).slice(-2);
}

// "2026-09", "2026.9", 날짜로 바뀐 셀 모두 "2026-09"로
function month_(v) {
  if (isDate_(v)) return Utilities.formatDate(v, SpreadsheetApp.getActiveSpreadsheet().getSpreadsheetTimeZone(), "yyyy-MM");
  var m = String(v == null ? "" : v).match(/(\d{4})\D+(\d{1,2})/);
  return m ? m[1] + "-" + ("0" + m[2]).slice(-2) : "";
}

function isDate_(v) { return Object.prototype.toString.call(v) === "[object Date]"; }

function num_(v, fallback) {
  if (v === "" || v == null || isNaN(Number(v))) return fallback === undefined ? null : fallback;
  return Number(v);
}

function str_(v) { return v == null ? "" : String(v); }

function isOn_(v) { return v === true || v === 1 || /^(o|y|v|✓|true|1)$/i.test(String(v).trim()); }
