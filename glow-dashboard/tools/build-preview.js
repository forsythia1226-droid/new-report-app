// index.html 에서 문서 뼈대(doctype/html/head/body/base)를 걷어낸 미리보기용 파일을 만든다.
// claude.ai 아티팩트는 뼈대를 스스로 씌우기 때문에 이 형태로 올려야 한다.
// 실행: node tools/build-preview.js [출력 경로]   (기본: preview.html)
const fs = require("fs");
const path = require("path");

const src = path.join(__dirname, "..", "index.html");
const out = process.argv[2] || path.join(__dirname, "..", "preview.html");
let h = fs.readFileSync(src, "utf8");
for (const t of [
  "<!DOCTYPE html>\n", '<html lang="ko">\n', "<head>\n", '<base target="_top">\n', '<meta charset="utf-8">\n',
  '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n', "</head>\n", "<body>\n", "</body>\n", "</html>\n",
]) {
  if (!h.includes(t)) throw new Error("index.html 뼈대가 예상과 다름: " + t.trim());
  h = h.replace(t, "");
}
fs.writeFileSync(out, h);
console.log("preview →", out);
