# TestGap Miner Web

Frontend-local Next.js application foundation for TestGap Miner, with an MUI
theme, App Router SSR styling, responsive navigation, and an accessibility
baseline.

## Commands

```bash
npm ci
npm run dev
npm test
npm run test:watch
npm run lint
npm run typecheck
npm run build
npm run start
```

The Vitest suite uses jsdom and React Testing Library to cover the current
application shell and Overview page. These tests verify semantic and interactive
regressions, but not visual breakpoints or full browser accessibility behavior.

Auth, API integration, run management, Evidence, review actions, and benchmark
data remain intentionally unimplemented.
