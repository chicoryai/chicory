# Chicory E2E Tests

End-to-end testing suite for the Chicory/BrewHub application using Playwright.

## Prerequisites

- Node.js 18+
- The Chicory webapp running on `localhost:3000`
- The Chicory backend API running on `localhost:8000`

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Install Playwright browsers:
   ```bash
   npx playwright install chromium
   ```

3. Create environment file:
   ```bash
   cp .env.example .env.local
   ```

4. Edit `.env.local` with your test credentials:
   ```bash
   TEST_USER_EMAIL=your-test-email@example.com
   TEST_USER_PASSWORD=your-test-password
   BIGQUERY_SERVICE_ACCOUNT_PATH=/path/to/your/service-account.json
   ```

## Running Tests

```bash
# Run all tests
npm test

# Run specific test suites
npm run test:smoke           # Health checks
npm run test:auth            # Authentication tests
npm run test:integrations    # Data source integration tests
npm run test:agents          # Agent tests
npm run test:golden-path     # Full user journey

# Debug mode (step through tests)
npm run test:debug

# UI mode (visual test runner)
npm run test:ui

# Headed mode (see browser)
npm run test:headed

# Generate test code (record actions)
npm run codegen
```

## Test Structure

```
e2e-tests/
├── fixtures/           # Test fixtures and setup
├── pages/              # Page Object Model classes
├── utils/              # Helper utilities
├── tests/
│   ├── smoke/          # Basic health checks
│   ├── auth/           # Authentication tests
│   ├── integrations/   # Data source tests
│   ├── agents/         # Agent CRUD and playground
│   ├── api/            # API execution tests
│   ├── manage/         # Task history tests
│   └── e2e/            # Full journey tests
└── test-data/          # Test files for uploads
```

## Golden Path Tests

The golden path test (`tests/e2e/golden-path.spec.ts`) covers the complete user journey:

1. Login with test credentials
2. Upload a single file (CSV/document)
3. Upload a folder
4. Connect BigQuery data source
5. Run scan/training on data sources
6. Create an agent
7. Configure agent instructions
8. Test agent in playground
9. Deploy agent and get API key
10. Execute agent via API
11. View task history

## Reports

After running tests, view the HTML report:
```bash
npm run report
```

Reports are saved to `reports/playwright-report/`.

## CI/CD

For CI environments, use:
```bash
npm run test:ci
```

This generates GitHub-friendly output and HTML reports.
