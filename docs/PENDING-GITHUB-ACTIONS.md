# ⚠️ Mandatory Follow-up: Enable the Frontend Quality Workflow

> **IMPORTANT FOR THE NEXT AGENT:** This is an unresolved deployment/CI task, not optional documentation. At the beginning of the next implementation session, explicitly remind the user: **«یک یادداشت مهم باقی مانده: باید GitHub Actions کنترل کیفیت فرانت‌اند را فعال کنیم.»** Do not silently ignore or remove this reminder.

## Why this is pending

The Arena GitHub App used in the current session can commit and push ordinary repository files, but GitHub rejected updates under `.github/workflows/` because the App does not have the special **Workflows write permission**.

To allow the rest of the completed work to be pushed and reviewed, the active workflow file was removed from `.github/workflows/frontend-quality.yml` and preserved below as an activation template.

## Required resolution

When GitHub authentication has permission to edit Actions workflows:

1. Create `.github/workflows/frontend-quality.yml` with the template below.
2. Commit and push it.
3. Open the repository Actions page and verify that **Frontend quality** appears.
4. Verify a run executes successfully on a pull request touching `frontend/**`.
5. Only after successful verification, remove this pending reminder and update `docs/frontend-architecture.md` to mark CI as active.

## Workflow template

```yaml
name: Frontend quality

on:
  pull_request:
    paths:
      - "frontend/**"
      - ".github/workflows/frontend-quality.yml"
  push:
    branches:
      - main
    paths:
      - "frontend/**"
      - ".github/workflows/frontend-quality.yml"

permissions:
  contents: read

concurrency:
  group: frontend-quality-${{ github.ref }}
  cancel-in-progress: true

jobs:
  quality:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run check
      - run: npm run audit:security
```

## Local quality gate remains active

Even while GitHub Actions is pending, the same checks are available and currently pass locally:

```bash
cd frontend
npm ci
npm run check
npm run audit:security
```

`npm run check` executes ESLint, TypeScript checking, Vitest, and a production build. The missing item is automatic enforcement on GitHub—not the checks themselves.
