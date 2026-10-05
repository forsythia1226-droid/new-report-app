// Glow 대시보드 — 이 스프레드시트에 붙은 Apps Script.
// 웹 앱으로 배포하면 index.html 화면을 띄우고, 데이터는 아래 탭들에 읽고 쓴다.

var TABS = {
  inbody: ["측정일", "체중", "골격근량", "체지방률", "기초대사량"],
  workouts: ["날짜", "가슴", "어깨", "등", "하체", "이두", "삼두", "전완근", "복근", "유산소"],
  checks: ["날짜", "단단함", "자신감", "여유", "원칙 지킴", "메모"],
  principles: ["순서", "원칙"],
  settings: ["항목", "값"],
  saju: ["원문"],
};
var PARTS = ["chest", "shoulder", "back", "legs", "biceps", "triceps", "forearm", "abs", "cardio"];
// workouts 탭 머리글 → 부위 키. 예전 시트의 "코어" 열은 복근으로 읽는다.
var PART_BY_HEADER = { 가슴: "chest", 어깨: "shoulder", 등: "back", 하체: "legs", 이두: "biceps", 삼두: "triceps", 전완근: "forearm", 복근: "abs", 코어: "abs", 유산소: "cardio" };
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
  Object.keys(TABS).forEach(function (name) {
    var head = TABS[name];
    var sh = sheet_(name);
    // 이미 쓰던 탭의 머리글은 건드리지 않는다 (예전 열 구성은 다음 저장 때 데이터와 함께 옮겨진다)
    if (sh.getLastRow() === 0) sh.getRange(1, 1, 1, head.length).setValues([head]).setFontWeight("bold");
    sh.setFrozenRows(1);
  });
  ["inbody", "workouts", "checks"].forEach(function (name) {
    sheet_(name).getRange("A2:A").setNumberFormat("yyyy-mm-dd");
  });

  // 없는 설정 항목만 채운다 (이미 있는 값은 그대로)
  var set = sheet_("settings");
  var have = {};
  rows_("settings").forEach(function (r) { have[String(r[0]).trim()] = true; });
  [
    ["목표 체중", 68],
    ["목표 체지방률", 12],
    ["지향 묘사", DEFAULT_VISION],
    ["정체성 문장", "단단한 몸처럼 흔들리지 않고, 부드러운 태도로 사람을 대한다."],
    ["키워드", "단단함, 자신감, 여유, 편안함, 아우라"],
  ].forEach(function (row) {
    if (!have[row[0]]) set.getRange(set.getLastRow() + 1, 1, 1, 2).setValues([row]);
  });
  set.getRange("B2:B").setWrap(true);
  set.setColumnWidth(2, 480);

  var sj = sheet_("saju");
  if (!sj.getRange("A2").getValue()) sj.getRange("A2").setValue(SAJU_RAW);
  sj.getRange("A2").setWrap(true).setVerticalAlignment("top");
  sj.setColumnWidth(1, 900);

  // 새 스프레드시트에 기본으로 생기는 빈 시트 정리
  ss.getSheets().forEach(function (sh) {
    if (!TABS[sh.getName()] && sh.getLastRow() === 0 && ss.getSheets().length > 1) ss.deleteSheet(sh);
  });
}

/** 화면이 처음 열릴 때 전체 데이터를 읽어 간다. */
function getData() {
  var settings = {};
  rows_("settings").forEach(function (r) { settings[String(r[0]).trim()] = r[1]; });

  var workouts = {};
  var wsh = sheet_("workouts");
  if (wsh.getLastRow() >= 2) {
    var width = wsh.getLastColumn();
    var head = wsh.getRange(1, 1, 1, width).getValues()[0];
    wsh.getRange(2, 1, wsh.getLastRow() - 1, width).getValues().forEach(function (r) {
      if (r[0] === "" || r[0] == null) return;
      var parts = [];
      head.forEach(function (h, i) {
        var key = PART_BY_HEADER[String(h).trim()];
        if (i > 0 && key && isOn_(r[i]) && parts.indexOf(key) < 0) parts.push(key);
      });
      if (parts.length) workouts[day_(r[0])] = parts;
    });
  }

  return {
    goal: { weight: num_(settings["목표 체중"], 68), fat: num_(settings["목표 체지방률"], 12) },
    vision: str_(settings["지향 묘사"]),
    identity: str_(settings["정체성 문장"]),
    keywords: str_(settings["키워드"]).split(",").map(function (s) { return s.trim(); }).filter(String),
    inbody: rows_("inbody")
      .filter(function (r) { return r[1] !== ""; })
      .map(function (r) { return { date: day_(r[0]), w: num_(r[1]), m: num_(r[2]), f: num_(r[3]), bmr: num_(r[4]) }; }),
    workouts: workouts,
    checks: readChecks_(),
    principles: rows_("principles")
      .sort(function (a, b) { return num_(a[0], 0) - num_(b[0], 0); })
      .map(function (r) { return str_(r[1]); })
      .filter(String),
    saju: str_(sheet_("saju").getRange("A2").getValue()),
  };
}

/** 화면에서 바뀐 내용을 통째로 다시 쓴다 (탭마다 수백 행 수준이라 충분히 빠르다). */
function saveAll(s) {
  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    var byDate = function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : 0; };
    write_("inbody", (s.inbody || []).slice().sort(byDate).map(function (r) {
      return [r.date, r.w, r.m, r.f, r.bmr == null ? "" : r.bmr];
    }));

    var days = Object.keys(s.workouts || {}).sort();
    write_("workouts", days.map(function (d) {
      return [d].concat(PARTS.map(function (p) { return s.workouts[d].indexOf(p) >= 0; }));
    }));
    if (days.length) sheet_("workouts").getRange(2, 2, days.length, PARTS.length).insertCheckboxes();

    write_("checks", (s.checks || []).slice().sort(byDate).map(function (c) {
      return [c.date].concat(CHECK_KEYS.map(function (k) { return c.s[k] == null ? "" : c.s[k]; }), [c.note || ""]);
    }));
    write_("principles", (s.principles || []).map(function (p, i) { return [i + 1, p]; }));
    write_("settings", [
      ["목표 체중", s.goal.weight],
      ["목표 체지방률", s.goal.fat],
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
  if (v instanceof Date) return Utilities.formatDate(v, tz, "yyyy-MM-dd");
  var m = String(v).match(/(\d{4})\D+(\d{1,2})\D+(\d{1,2})/);
  if (!m) return String(v);
  return m[1] + "-" + ("0" + m[2]).slice(-2) + "-" + ("0" + m[3]).slice(-2);
}

function num_(v, fallback) {
  if (v === "" || v == null || isNaN(Number(v))) return fallback === undefined ? null : fallback;
  return Number(v);
}

function str_(v) { return v == null ? "" : String(v); }

function isOn_(v) { return v === true || v === 1 || /^(o|y|v|✓|true|1)$/i.test(String(v).trim()); }
