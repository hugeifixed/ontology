---
type: Design system guide
title: Institutional color system and static palette
description: Two-tier daisyUI color architecture for the institutional theme, including primitives, semantic roles, UI mixing, favicon alignment, and safe change validation.
tags: [web, theming, daisyui, tailwind, accessibility]
openwiki:
  roles: [architecture, workflow, testing]
  change_kinds: [theming, accessibility, static-assets]
  source_paths: [studio/assets/css/input.css, studio/components/menu_icon/menu_icon.html, studio/templates/studio/base.html, studio/templates/studio/dashboard.html, studio/static/favicon/studio-mark.svg, package.json]
  symbols: [institutional, menu_icon, --color-secondary-content, .menu-icon]
  test_paths: [studio/tests.py]
  invariants: [Components consume semantic daisyUI roles rather than palette primitives., Primary-navigation SVGs inherit the anchor color through currentColor and move from 0.72 to full opacity on hover, focus-visible, and active navigation states., The generated app.css is rebuilt from input.css and is not hand-edited., The favicon uses the same navy, orange, and neutral palette values as the theme.]
  validation_commands: [npm run build:css, .venv/bin/python manage.py test]
---

# Institutional color system and static palette

The `institutional` daisyUI theme in `studio/assets/css/input.css` separates **palette primitives** from the **semantic roles** that components consume. This keeps a visual token change from requiring broad markup rewrites: templates use daisyUI utility classes such as `bg-secondary`, `text-secondary-content`, `bg-base-100`, `text-base-content`, and `border-info`, while the theme maps those roles to named primitives. The workspace uses these roles throughout the server-rendered dashboard; its interaction and accessibility behavior is documented in [the workspace guide](workspace.md).

## Two-tier token contract

The theme declaration disables daisyUI's built-in themes, registers `institutional` as the default light theme, and defines two layers.

| Layer | Tokens in source | Purpose and change rule |
|---|---|---|
| Primitive palette | `--neutral-0`, `--neutral-50`, `--neutral-100`, `--neutral-300`, `--neutral-900`, `--neutral-950`, `--navy-900`, `--orange-500`, `--info-700`, `--success-700`, `--warning-800`, `--danger-700` | Literal color values. The comment in `input.css` says components consume only the semantic roles below; do not couple new component styles to a primitive without a role-level reason. |
| Semantic daisyUI roles | `--color-base-*`, `--color-primary*`, `--color-secondary*`, `--color-accent*`, `--color-neutral*`, `--color-info*`, `--color-success*`, `--color-warning*`, `--color-error*` | The public styling contract for daisyUI/Tailwind component utilities. Change a role mapping when the meaning of a surface or state changes; change a primitive when the shared palette value changes. |

### Current primitive values

| Family | Tokens and literal values |
|---|---|
| Neutral | `--neutral-0: #ffffff`; `--neutral-50: #f7fafc`; `--neutral-100: #f3f6f9`; `--neutral-300: #d9e0e8`; `--neutral-900: #293b51`; `--neutral-950: #17263b` |
| Brand | `--navy-900: #183552`; `--orange-500: #f58025` |
| State foregrounds | `--info-700: #0b7198`; `--success-700: #207a4c`; `--warning-800: #855400`; `--danger-700: #b12a22` |

The current source has no gold primitive or semantic role. In particular, the accent role now maps to `--orange-500`; there is no separate unused gold accent in this theme. Because Git history is unavailable in this checkout, this page records the present source state rather than attributing a historical removal to a particular change.

## Semantic role mapping

| Semantic role | Primitive mapping | UI meaning in the current theme |
|---|---|---|
| Base surfaces | `base-100 → neutral-0`; `base-200 → neutral-100`; `base-300 → neutral-300`; `base-content → neutral-950` | White primary surface, pale neutral secondary surface, borders, and dark readable base text. `base-100` deliberately uses `--neutral-0` (white), not a near-white label. |
| Brand actions | `primary → orange-500`; `primary-content → neutral-950`; `secondary → navy-900`; `secondary-content → neutral-50`; `accent → orange-500`; `accent-content → neutral-950` | Orange primary/accent marks with dark content; navy surfaces with light content. |
| Neutral UI | `neutral → neutral-900`; `neutral-content → neutral-50` | Darker neutral controls/surfaces distinct from the navy brand surface. |
| Status roles | `info → info-700`; `success → success-700`; `warning → warning-800`; `error → danger-700`; every `*-content → neutral-50` | Dark state tokens paired with the light neutral content token. They are the roles used by daisyUI alerts, badges, and related semantic state utilities. |

The state role values are explicit source literals. The repository contains no contrast-ratio calculations, browser accessibility report, or color-specific assertion in `studio/tests.py`; therefore no measured contrast result is claimed here. The README describes a WCAG 2.2 AA target, but a contrast tool check remains required when any foreground, background, opacity, or role pairing changes.

## Surface opacity and OKLab mixing

The theme uses `color-mix(in oklab, ...)` rather than ad hoc precomputed blend hexes for UI overlays and subdued feedback. All known uses are in `studio/assets/css/input.css`:

| Selector | Mix | Intent |
|---|---|---|
| `.drawer-side .menu a:hover, :focus-visible` | `secondary-content` with `transparent 92%` | A restrained light hover/focus surface on the navy navigation area. |
| `.drawer-side .menu a.menu-active` | `secondary-content` with `transparent 88%` | Slightly stronger selected-nav surface, while the orange primary border identifies selection. |
| `.ontology-node:hover, [open]` | `primary` with `base-300 55%`; `secondary` with `transparent 90%` | Orange-tinted border and low-opacity navy shadow for native disclosure feedback. |
| `.control-hero` grid/diagonal decoration | `primary` with `transparent 92%`; `secondary-content` with `transparent 96%` | Low-contrast decorative marks that preserve the navy hero surface. |
| `.control-route > li::before` | `primary` with `transparent 55%` | Orange route marker halo. |

The navy-surface text treatment uses `--color-secondary-content` (`--neutral-50`) with utility opacity suffixes in `dashboard.html`, including `/85`, `/70`, `/25`, `/15`, and `/10`. Examples are the hero reference label, body copy, outline badge, panel borders, and workflow line items. This is an intentional surface-content relationship: preserve the `text-secondary-content` base token before tuning opacity so text remains tied to the semantic navy surface rather than a one-off neutral value.

### Primary-navigation icon states

The six primary-navigation glyphs are rendered by the reusable `menu_icon` component documented in [the workspace guide](workspace.md). Its SVG declares `stroke="currentColor"`, so the icon inherits the navigation anchor's `--color-secondary-content` color instead of specifying a literal fill or stroke. The component remains decorative; its accessibility contract is owned by that workspace page.

`input.css` deliberately separates color inheritance from emphasis. `.drawer-side .menu a .menu-icon` starts at `opacity: 0.72` and transitions opacity with `--motion-feedback` and `--ease-enter`. The combined hover, `:focus-visible`, and `.menu-active` selector restores `opacity: 1`, while the anchor itself retains semantic secondary-content text and receives its matching hover/focus or active background. Do not change only the icon opacity as a replacement for visible focus or selected-page treatment: keyboard focus remains the anchor's state and uses the orange focus outline described by the workspace/theme rules.

## Favicon alignment

`studio/templates/studio/base.html` loads `favicon/studio-mark.svg`. The SVG uses the same literal values as the theme's brand and neutral primitives:

| Favicon element | Value | Theme primitive |
|---|---|---|
| Rounded background | `#183552` | `--navy-900` |
| Hexagonal mark | `#f58025` | `--orange-500` |
| Inner mark | `#f7fafc` | `--neutral-50` |

When a shared palette value changes, update the favicon in the same change if the corresponding brand/neutral role remains represented there. This asset is a static source file, not generated CSS.

## Change navigation and validation

Consult this page for a palette, role mapping, status color, nav/hero overlay, favicon, or daisyUI theme change.

| Change | Implementation seam | Invariants and focused evidence | Minimal validation |
|---|---|---|---|
| Change a color family or semantic role | `studio/assets/css/input.css`: `@plugin "daisyui/theme"` block | Keep the primitive-to-semantic split; audit all affected semantic pairings in the rendered workspace. No automated palette test exists. | `npm run build:css`; manually inspect affected light and navy surfaces with a contrast tool. |
| Add a new semantic state | Theme role block; the template/component using the daisyUI state utility | Prefer a semantic role over direct primitive use. Pair its content role deliberately; validate the actual foreground/background pairing rather than assuming a token name proves contrast. | `npm run build:css`; `.venv/bin/python manage.py test`; manual contrast check. |
| Tune nav, disclosure, hero, or route overlays | `input.css`: the selector-specific `color-mix(in oklab, ...)` rule | Retain OKLab mixing and the semantic source colors. On navy, retain `secondary-content` as the starting text token before changing opacity. | `npm run build:css`; manually inspect hover, focus-visible, active, and open states. |
| Tune primary-navigation icon treatment | `studio/components/menu_icon/menu_icon.html`: `stroke="currentColor"`; `input.css`: `.drawer-side .menu a .menu-icon` and its state selector | Preserve currentColor inheritance, `0.72` default opacity, full opacity on hover/focus-visible/active, and the anchor's separate visible focus/active treatment. The icon remains decorative; see the [workspace component contract](workspace.md). | `npm run build:css`; `.venv/bin/python manage.py test`; manually inspect hover, keyboard focus, and active section on the navy drawer. |
| Change favicon colors | `studio/static/favicon/studio-mark.svg`; confirm `base.html` link remains `favicon/studio-mark.svg` | Keep brand alignment where the favicon represents theme primitives; avoid editing generated CSS for this change. | Open the dashboard and inspect the browser icon; `npm run build:css` is unnecessary unless theme source also changed. |

`studio/static/studio/css/app.css` is the generated artifact served by `base.html`. Run `npm run build:css` after changes to `input.css` (or template class discovery changes); never hand-edit that output. The [runtime and delivery guide](../operations/runtime-and-delivery.md) documents the subsequent WhiteNoise/`collectstatic` boundary. `collectstatic` is conditional: use it only when validating production static delivery or changing its configuration, not for an ordinary token edit.
