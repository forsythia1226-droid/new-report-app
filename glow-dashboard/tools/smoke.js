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
const shown = (el) => w.getComputedStyle(el).display !== "none"; // 실제로 보이는지 (hidden 속성만으로는 부족)
const check = (name, ok, detail = "") => { if (!ok) errors.push(`${name} ${detail}`); console.log(`${ok ? "✓" : "✗"} ${name}${detail ? " — " + detail : ""}`); };

setTimeout(() => {
  try {
    check("시작 화면 표시", !$("#gate").hidden && text("#gate-status").includes("미리보기"), text("#gate-status"));
    $("#gate-start").click();
    check("시작하기 누르면 화면에서 사라짐", !shown($("#gate")));
    $("[data-tab=saju]").click();
    check("사주 하위 탭: 월별 운세 → 원국·신살 (요약 없음)", [...w.document.querySelectorAll("[data-sub]")].map((b) => b.textContent.trim()).join(",") === "월별 운세,원국 · 신살" && shown($("[data-subview=flow]")) && !shown($("[data-subview=chart]")));
    $("[data-sub=flow]").click();
    check("월별 운세: 원문에서 기간 5개", w.document.querySelectorAll("#timeline .period").length === 5, [...w.document.querySelectorAll("#timeline .period .when span:first-child")].map((e) => e.textContent).join(" "));
    w.document.querySelector("[data-period=\"2026-12\"]").click();
    check("기간 누르면 원문 해당 부분", text("#period-detail").includes("주의해서 볼 달입니다"));
    check("원문 정리: 별점은 막대, 목록은 칩, 소제목", $("#period-detail .sx .sx-rates .rate") && $("#period-detail .sx-chips span") && $("#period-detail .sx-sub") && !text("#period-detail").includes("★"));
    // 새 자료 붙여넣기 → 미리보기 → 저장
    $("#up-paste-btn").click();
    $("#up-paste-text").value = ["새 자료", "", "1. 2026년 10월 — 戊戌", "", "커리어 ★★★☆☆", "", "새 10월 해석입니다.", "", "2. 2026년 11월 — 己亥", "", "재물 ★★★★★", "", "새 11월."].join("\n");
    $("#up-paste-ok").click();
    check("업로드 미리보기에서 기간 인식", text("#up-found").includes("2026.10") && text("#up-found").includes("2026.11"), text("#up-found"));
    $("#up-save").click();
    check("새 자료로 교체", w.document.querySelectorAll("#timeline .period").length === 2 && text("#monthly-hist").includes("사용 중"), text("#monthly-src"));
    check("신살 화면은 그대로", w.document.querySelectorAll("#shinsal .ss-row").length === 10);
    $("[data-tab=career]").click();
    check("3년 로드맵 + 자격증 3종(SQLD 먼저)", w.document.querySelectorAll("#roadmap .ry").length === 3 && $("#certs .cert b").textContent === "SQLD" && w.document.querySelectorAll("#certs .cert").length === 3 && w.document.querySelectorAll("#certs select[data-field=status]").length === 4);
    const sq = $("select[data-stage=sqld][data-field=status]"); sq.value = "합격"; sq.dispatchEvent(new w.Event("change", { bubbles: true }));
    const jw = $("input[data-stage=jcb_w][data-field=date]"); jw.value = "2027-03-01"; jw.dispatchEvent(new w.Event("change", { bubbles: true }));
    check("자격증 합격·시험일 D-day 반영", text("#cert-summary") === "1 / 3 합격 · 6/32학점" && /D-\d+/.test(text("#certs")), text("#cert-summary"));
    const de = $("input[data-degree=earned]"); de.value = "35"; de.dispatchEvent(new w.Event("change", { bubbles: true }));
    check("학위: 자격증 학점 자동 + 수업 학점", text("#degree").startsWith("41 / 140학점") && text("#degree").includes("29%"), text("#degree").slice(0, 30));
    $("input[data-action=cb]").click();
    check("할 일 체크", $("input[data-action=cb]").checked && $(".act.on"));
    $("#log-text").value = "ISMS 인증 심사 대응 자료 준비"; $("#log-form").dispatchEvent(new w.Event("submit", { cancelable: true, bubbles: true }));
    check("경력 문서화 기록", text("#career-log").includes("ISMS 인증 심사") && text("#log-summary").includes("IT 개선 1"), text("#log-summary"));
    $("[data-tab=home]").click();
    check("카테고리 7개 (職 다음 處)", [...w.document.querySelectorAll(".tab")].map((t) => t.textContent.trim()).join(" ") === "◎홈 命사주 身신체 心정신 職커리어 處처세 財투자");
    check("홈 처세 카드", text("#h-cheo").includes("백승 실장") && text("#h-cheo").includes("4분기 사업계획"), text("#h-cheo"));

    // 처세
    $("[data-tab=cheo]").click();
    check("처세 하위 탭: 상황 기록 → 대응 원칙 → 사람", [...w.document.querySelectorAll("[data-csub]")].map((b) => b.textContent.trim()).join(",") === "상황 기록,대응 원칙,사람" && shown($("[data-csubview=log]")) && !shown($("[data-csubview=tactics]")));
    check("처세 하위 탭이 사주 하위 탭과 섞이지 않음", shown($("[data-subview=flow]").closest("section")) === false && $("[data-sub=flow]").getAttribute("aria-selected") === "true");
    check("이번 달 현황 6칸", w.document.querySelectorAll("#cheo-stats > div").length === 6, text("#cheo-stats"));
    $("#case-title").value = "주간보고 수치 정합성";
    $("#case-form input[name=case-risk][value=\"일반\"]").click();
    check("위험도 고르면 추천 대응 + 대응 미리 선택", text("#case-advice").includes("三") && $("#case-form input[name=case-move][value=\"그대로 노출\"]").checked);
    $("#case-form").dispatchEvent(new w.Event("submit", { cancelable: true, bubbles: true }));
    check("상황 기록 추가 (기록 안 남김 경고)", w.document.querySelectorAll("#case-list .case").length === 2 && $("#case-list .case.unlogged") && text("#cheo-stats").includes("기록 안 남긴 건1건"), text("#cheo-stats"));
    check("폼 초기화 (스트레스 3, 대응 비움)", $("#case-title").value === "" && $("#case-form input[name=case-stress][value=\"3\"]").checked && !$("#case-form input[name=case-move]:checked"));
    $("#case-list .case.unlogged input[data-case-logged]").click();
    check("기록 남김 체크하면 경고 해제", !$("#case-list .case.unlogged") && text("#cheo-stats").includes("기록 안 남긴 건0건"));
    $("[data-csub=tactics]").click();
    check("대응 원칙 4개 + 복사 문장 3개", w.document.querySelectorAll("#tactics .tactic").length === 4 && w.document.querySelectorAll("#tactics [data-copy]").length === 3 && shown($("[data-csubview=tactics]")) && !shown($("[data-csubview=log]")));
    $("[data-cheo-raw]").click();
    check("원문 보기 (받은 글 그대로)", $("#reader") && text("#raw-body").includes("배경지 화면일 뿐입니다") && w.document.querySelectorAll("#raw-toc button").length >= 4);
    $("#raw-close").click();
    $("[data-csub=people]").click();
    check("사람: IT혁신팀장 · 백승 실장", [...w.document.querySelectorAll("#people .pn")].map((e) => e.textContent).join(",") === "IT혁신팀장,백승 실장" && $("#cheo-arrive"));
    const nf = $("#people [data-note-form=\"백승 실장\"]"); nf.querySelector("input").value = "숫자 근거부터 묻는다";
    nf.dispatchEvent(new w.Event("submit", { cancelable: true, bubbles: true }));
    check("관찰 메모 남기기", text("#people").includes("숫자 근거부터 묻는다"));
    $("[data-tab=saju]").click();
    check("처세에서 돌아와도 사주 하위 탭 정상", shown($("[data-subview=flow]")) && [...w.document.querySelectorAll("[data-subview]")].filter(shown).length === 1);
    $("[data-tab=home]").click();
    check("사주 하위 탭은 하나만 보임", [...w.document.querySelectorAll("[data-subview]")].filter(shown).length === 1);
    check("홈 지향 묘사", text("#home-vision").startsWith("그를 처음 보았을 때"));

    $("[data-tab=body]").click();
    check("신체 맨 위 = 목표 달성", $("#v-body .grid > .card h2").textContent.includes("목표 달성"));
    check("목표 달성 순서: 체중 → 골격근량 → 체지방률", [...w.document.querySelectorAll("#goal-rings .goal-item .k")].map((e) => e.textContent.split(" ·")[0]).join(",") === "체중,골격근량,체지방률" && !text("#goal-rings").includes("제지방"));
    check("린매스업·커팅 4단계", [...w.document.querySelectorAll("#phases .phase b")].map((e) => e.textContent).join(",") === "1차 린매스업,1차 커팅,2차 린매스업,2차 커팅" && $("#phases .phase.on .ph-n").textContent.includes("지금"));
    w.document.querySelector("[data-phase=\"1\"]").click();
    check("단계 눌러서 지금 단계 변경", $("#phases [data-phase=\"1\"]").classList.contains("on") && $("#phases [data-phase=\"0\"]").classList.contains("done"));
    check("종합 달성률 표시", /\d+%/.test(text("#goal-main")), text("#goal-main"));
    check("달력 일요일 시작", [...w.document.querySelectorAll(".cal .wd")].map((e) => e.textContent).join("") === "일월화수목금토");
    check("오늘 카드", text("#today-card").length > 0, text("#today-card").slice(0, 40));

    const before = text("#tiles").match(/\d+월 운동(\d+)회/)[1];
    $("#today-card .done-btn").click();
    const after = text("#tiles").match(/\d+월 운동(\d+)회/)[1];
    check("오늘 완료 토글로 이번 달 횟수 변화", before !== after, `${before} → ${after}`);

    check("목표 달성 모수 12일", /목표 달성\d+\/ 12일/.test(text("#tiles")), (text("#tiles").match(/\d+월 목표 달성[^%]*%/) || [""])[0]);
    check("부위 카드는 이름만 (값·횟수 없음)", w.document.querySelectorAll("#parts .part").length === 10 && !$("#parts select") && !$("#parts .pcount"));
    check("달력 아래 부위별 횟수 막대 카드", w.document.querySelectorAll("#part-counts .pc-row").length === 10 && w.document.querySelectorAll("#part-counts .pc-row")[0].querySelectorAll(".pc-cells i").length === 6, text("#pc-title"));
    check("패널에 운동 완료 버튼 없음", !$("#sel-done"));
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
