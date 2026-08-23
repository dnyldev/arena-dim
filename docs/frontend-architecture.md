# Frontend Architecture & UI Charter

## Goals

The dashboard is a technical laboratory, but complexity must appear only where it helps. The default workflow stays calm and legible; expert evidence remains one deliberate interaction away. UI behavior must be accessible, testable, modular, and consistent.

## Stack

- React + TypeScript + Vite
- Tailwind CSS for styling
- Radix UI primitives for accessible behavior
- CVA for component variants
- Lucide for consistent icons
- Vitest + Testing Library
- ESLint + TypeScript project checks

Framework changes require a demonstrated product need. Next.js or a large visual kit must not be introduced merely for fashion.

## Module boundaries

```text
src/
├── components/
│   ├── ui/              # domain-free design-system primitives
│   └── layout/          # application shell and global layout
├── features/
│   └── laboratory/      # feature-owned components and public barrel
├── lib/                 # framework-independent shared utilities
├── state/               # application state hooks
└── types/               # API contracts
```

Rules:

1. `components/ui` cannot know about beats, jobs, models, or rules.
2. Feature internals are imported through that feature's `index.ts` public API.
3. Network calls do not live inside visual components.
4. Domain calculations belong in selectors/hooks/utilities, not JSX.
5. A component has one primary responsibility.
6. New ad-hoc buttons, badges, switches, dialogs, tooltips, and tabs are prohibited when a shared primitive exists.
7. Native controls remain preferred when they provide the best mobile/accessibility behavior without advanced interaction needs.

## Progressive disclosure

- Default: summary, primary action, essential status.
- Secondary: tab-specific workspace.
- Technical: explicit inspector/log/details interaction.
- Help: local tooltip for a term and global guide for the complete model.

No evidence is hidden permanently; it is organized by user intent.

## Accessibility requirements

- Keyboard operation for every interactive element.
- Visible focus states.
- Radix focus trapping/restoration for dialogs.
- Icon-only buttons require accessible labels.
- Status cannot be communicated by color alone.
- Reduced-motion preferences are honored.
- Tables use semantic table markup.
- Automated tests query by role/name where possible.

## Design-system rules

Shared variants:

- Buttons: `primary`, `secondary`, `outline`, `ghost`, `danger`.
- Sizes: `sm`, `md`, `lg`, `icon`.
- Badges: `neutral`, `good`, `warn`, `bad`, `info`.

Icons come from Lucide; platform-dependent emoji and text glyphs are not UI controls. Focus, disabled, hover, and loading states are part of the primitive, not reimplemented by features.

## Quality gate

Every frontend change must pass:

```bash
npm run check
npm run audit:security
```

`check` runs lint, TypeScript project checking, tests, and a production build. High/critical dependency vulnerabilities block acceptance.

## Current workspace design

- Sticky application header with concise system status and global help.
- Control column for audio, engine configuration, and primary actions.
- Main workspace with compact pipeline progress.
- Pipeline technical stages and event log are opt-in details.
- Results use keyboard-accessible tabs: Timeline, Beats, Details, Laboratory.
- Laboratory uses a summary, safety guarantees, tracking regions, rule log, and focused decision inspector.

## Next approved expansion

The next major visual capability is an audio workspace with waveform, playback, playhead, zoom, and independently toggleable raw/final/region/issue layers. It must be implemented as a feature module; timing anchors and structural grouping remain separate visual layers.
