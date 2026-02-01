#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

REPORT="reports/results.json"
BOLD="\033[1m"
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
CYAN="\033[36m"
RESET="\033[0m"

echo -e "\n${BOLD}${CYAN}Running E2E tests...${RESET}\n"

# Run tests — allow failure so we can report results
set +e
npx playwright test
TEST_EXIT=$?
set -e

# Check report exists
if [ ! -f "$REPORT" ]; then
  echo -e "${RED}No report found at ${REPORT}. Tests may not have run.${RESET}"
  exit 1
fi

# Parse results with node (available since playwright needs it)
node -e "
const fs = require('fs');
const report = JSON.parse(fs.readFileSync('${REPORT}', 'utf8'));

const suites = report.suites || [];
let total = 0, passed = 0, failed = 0, skipped = 0;
const failures = [];
const suiteResults = [];

function walk(suite, path) {
  const name = path ? path + ' > ' + suite.title : suite.title;
  let sPassed = 0, sFailed = 0, sSkipped = 0;

  for (const spec of (suite.specs || [])) {
    for (const test of (spec.tests || [])) {
      total++;
      const status = test.status;
      if (status === 'expected') { passed++; sPassed++; }
      else if (status === 'skipped') { skipped++; sSkipped++; }
      else { failed++; sFailed++; failures.push(spec.title); }
    }
  }

  for (const child of (suite.suites || [])) {
    const sub = walk(child, name);
    sPassed += sub.passed;
    sFailed += sub.failed;
    sSkipped += sub.skipped;
  }

  if (suite.title && (sPassed + sFailed + sSkipped > 0)) {
    suiteResults.push({ name: suite.title, passed: sPassed, failed: sFailed, skipped: sSkipped });
  }
  return { passed: sPassed, failed: sFailed, skipped: sSkipped };
}

for (const s of suites) walk(s, '');

// Print summary
console.log('');
console.log('┌─────────────────────────────────────────────┐');
console.log('│             E2E TEST RESULTS                │');
console.log('├──────────────────────┬──────┬──────┬────────┤');
console.log('│ Suite                │ Pass │ Fail │ Skip   │');
console.log('├──────────────────────┼──────┼──────┼────────┤');

for (const s of suiteResults) {
  const name = s.name.padEnd(20).slice(0, 20);
  const p = String(s.passed).padStart(4);
  const f = String(s.failed).padStart(4);
  const sk = String(s.skipped).padStart(6);
  console.log('│ ' + name + ' │' + p + '  │' + f + '  │' + sk + '  │');
}

console.log('├──────────────────────┼──────┼──────┼────────┤');
const tName = 'TOTAL'.padEnd(20);
console.log('│ ' + tName + ' │' + String(passed).padStart(4) + '  │' + String(failed).padStart(4) + '  │' + String(skipped).padStart(6) + '  │');
console.log('└──────────────────────┴──────┴──────┴────────┘');
console.log('');

if (failures.length > 0) {
  console.log('FAILURES:');
  for (const f of failures) console.log('  ✗ ' + f);
  console.log('');
}

process.exit(failed > 0 ? 1 : 0);
"
PARSE_EXIT=$?

echo ""

if [ "$PARSE_EXIT" -ne 0 ]; then
  echo -e "${RED}${BOLD}✗ Some tests failed. Fix these before pushing.${RESET}"
  echo -e "  Run ${CYAN}npm run report${RESET} to see the full HTML report."
  exit 1
fi

echo -e "${GREEN}${BOLD}✓ All tests passed!${RESET}"
echo ""
read -rp "Push to main? (y/n) " answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
  BRANCH=$(git rev-parse --abbrev-ref HEAD)
  if [ "$BRANCH" = "main" ]; then
    git push origin main
  else
    echo -e "Current branch: ${CYAN}${BRANCH}${RESET}"
    echo "Merging into main and pushing..."
    git checkout main && git merge "$BRANCH" && git push origin main && git checkout "$BRANCH"
  fi
  echo -e "${GREEN}${BOLD}Pushed to main.${RESET}"
else
  echo "Skipped push."
fi
