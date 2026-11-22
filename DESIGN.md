# Atmosphere360 — Design System

Mode: **Operate** (task-focused dashboard). The established dark command-center world is preserved;
this document records the tokens and rules that now govern it.

## Tokens

Defined once in `theme.py` (`COLORS`) and exposed as CSS custom properties on `:root`:

| Token | Value | Role |
|---|---|---|
| `--cp-bg` | `#0B1220` | App background |
| `--cp-surface` | `#162235` | Cards, panels, status bar |
| `--cp-surface-2` | `#1C2B42` | Raised surfaces, inputs, nested blocks |
| `--cp-surface-3` | `#223552` | Hover state |
| `--cp-border` | `#24364F` | 1px structural borders, dividers |
| `--cp-focus` | `#2DD4BF` | Focus rings and active controls |
| `--cp-text` | `#F1F5F9` | Primary text |
| `--cp-text-muted` | `#A9B8CC` | Secondary text (AA on surface) |
| `--cp-accent` | `#2DD4BF` | Primary actions, selection, active state |
| `--cp-warning` / `--cp-critical` / `--cp-success` | `#F59E0B` / `#EF4444` / `#10B981` | Semantic status only |

AQI and priority palettes remain domain tokens in `theme.py` and are never used for decoration.

- **Spacing:** 4px base — 4 / 8 / 12 / 16 / 20 / 24 / 32 / 40px.
- **Radii:** 8px controls, 12px cards, 16px hero cards.
- **Elevation:** `0 4px 16px rgba(2,6,23,.35)` for cards, `0 8px 28px …` for overlays.
- **Type:** Inter 400 / 500 / 700. Scale: 12px labels, 14px UI/body, 16px section heads,
  18px headings, 24px page title, 44px hero figures. Headings: more space above than below.
- **Motion:** 180ms ease-out, used only for state changes (tabs, buttons, nav hover).
  Honours `prefers-reduced-motion`.

## Rules

1. Components consume tokens through CSS classes (`.cp-kpi-card`, `.cp-hero-card`, …).
   Per-instance colour is passed with `--cp-card-accent`; no inline magic numbers in new markup.
2. Icons come from `icons.py` (`:material/...:`). No emoji as interface icons.
3. No eyebrow/kicker above a heading; the heading carries the hierarchy.
4. Cards use 1px structural borders and a 2px accent rule on top. No heavy coloured side borders.
5. Non-interactive cards do not move on hover — no false affordances.
6. Numerical values use tabular figures; browser surfaces (selection, caret, scrollbar,
   focus rings, underline offset) are themed from the palette.
7. Missing values render as an em dash or nothing — never `nan`.
8. Structural breakpoints at 1100 / 860 / 640px; the native header stays visible so the
   sidebar toggle remains reachable on small screens.

## Verification

Run `streamlit run app.py`, then check at 1440px and 390px: all three modes render without
exceptions, no horizontal overflow, contrast holds, keyboard focus is visible, and no
baseline delta shows `nan`.
