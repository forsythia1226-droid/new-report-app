// index.html 을 GitHub Pages 용 gh-pages 브랜치에 올린다.
// gh-pages 에는 생성물(index.html, .nojekyll)만 두므로 매번 새로 만들어 강제 푸시한다.
// 실행: npm run pages   → https://forsythia1226-droid.github.io/new-report-app/
const { execSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const root = path.join(__dirname, "..");
const sh = (cmd, cwd) => execSync(cmd, { cwd, stdio: ["ignore", "pipe", "inherit"] }).toString().trim();
const remote = sh("git remote get-url origin", root);
const source = sh("git rev-parse --short HEAD", root);

const dir = fs.mkdtempSync(path.join(os.tmpdir(), "glow-pages-"));
fs.copyFileSync(path.join(root, "index.html"), path.join(dir, "index.html"));
fs.writeFileSync(path.join(dir, ".nojekyll"), "");
sh("git init -q -b gh-pages", dir);
sh("git add -A", dir);
sh(`git -c user.name="${sh("git config user.name", root)}" -c user.email="${sh("git config user.email", root)}" commit -q -m "Publish Glow dashboard (${source})"`, dir);
sh(`git push -q -f "${remote}" gh-pages`, dir);
fs.rmSync(dir, { recursive: true, force: true });
console.log(`published ${source} → gh-pages`);
console.log("https://forsythia1226-droid.github.io/new-report-app/");
