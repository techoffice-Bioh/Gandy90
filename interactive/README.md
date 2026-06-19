# SB System — Interactive hydraulic diagram (Gandy 90)

A **standalone, offline** interactive viewer built from
[`diagrams/pictorial/system_gandy90.drawio`](../diagrams/pictorial/system_gandy90.drawio),
styled as a premium SB System clinical dashboard. Two themes are shipped:

- **`system_gandy90.interactive.html`** — light dashboard.
- **`system_gandy90.interactive.dark.html`** — dark dashboard (same diagram on a light "paper"
  card so the icons stay faithful and readable).

This folder is **fully isolated**: it does not modify or depend on the project pipeline
(`sync.py`, `build.py`, `diagrams/`, `inventory/`, `scratch/`). It only *reads* the `.drawio`.

## How to open

Double-click either HTML file (opens in any modern browser). No server, no internet — the diagram,
the rendering engine, and the SB System branding are all bundled locally.

## How to use

- **Click a component** (on the canvas or in the **Components** list) to power it on. It lights to
  full opacity and **its connections appear at low contrast** (powered, static). Click again to
  power it off.
- A connection is **powered** while **at least one** endpoint is on; when **both** are off it is
  hidden again (and its state resets).
- **Click a powered connection** to step through its states:

  | State | Appearance | Reached by |
  |-------|------------|-----------|
  | **Off** | hidden — not clickable | both endpoints off |
  | **Powered** | very low contrast, static | powering a component it touches |
  | **Active** | full contrast, static | clicking the connection |
  | **Flow →** | dashes animating forward | clicking again |
  | **Flow ←** | dashes animating in reverse | clicking again |

  Clicking a powered connection **loops**: the first click leaves *Powered* for *Active*, then it
  cycles **Active → Flow → → Flow ← → Active → …**, so a click always brings the line back to a
  clear **Active (static)** state — you can stop the flow at any time.

- **Turn all off** (top-right) resets everything.

Connections are drawn **on top** of the icons so they are always clickable; a powered-off connection
lets clicks pass through to the component beneath.

## Branding

The header uses the SB System crest (`assets/sbsystem-favicon.png`) and the company red on a clean
clinical surface (light: `#ce0000`; dark: a brightened `#ff3b3b`). Assets are stored locally so the
pages are fully self-contained. (Source: [sbsystem.it](https://sbsystem.it/) — Nuova SB System Srl /
BIOH Group Filtrazione.)

In the dark theme the **whole diagram canvas is dark too** (not just the frame). Because the
embedded icons use black outlines (`stroke:black`) and several pipes are pure `#000000` — which
would vanish on a dark background — the dark theme applies an `invert(1) hue-rotate(180deg)` filter
to the diagram: black lines become light while saturated colors are largely preserved (blue stays
blue, red stays red). The light theme renders the original colors unchanged; the dark theme is a
remapped, legible dark schematic.

## Rendering fidelity

The diagram is rendered by the **real drawio/mxGraph engine** (vendored locally in
`vendor/mxgraph/`), so component transformations (rotations, flips), edge routing and waypoints, and
the embedded SVG icons match the `.drawio` exactly.

**Known minor difference:** line **jumps** at edge crossings (drawio's `jumpStyle=arc`) are a drawio
editor extension and are not drawn by the bundled engine — crossing lines render as plain crossings.

Tip: the full system is large; use the browser zoom (**Ctrl** + mouse wheel, or **Ctrl** +/–) to
zoom in for precise clicking.

## Regenerating after the diagram changes

The HTML embeds a **snapshot** of the diagram's XML. To refresh both themes from the current
`.drawio`:

```
py interactive/gen_interactive.py
```

This re-reads `diagrams/pictorial/system_gandy90.drawio` and rewrites both HTML files. It changes
nothing outside this folder.

## Files

| File | Role |
|------|------|
| `system_gandy90.interactive.html` | Light deliverable (open this). Inlined diagram XML + page. |
| `system_gandy90.interactive.dark.html` | Dark deliverable. Same diagram + 5-state logic. |
| `gen_interactive.py` | Read-only generator: shared template + light/dark themes + XML injector. |
| `assets/sbsystem-favicon.png` | SB System crest (header logo + favicon). |
| `vendor/mxgraph/mxClient.js` | Vendored drawio/mxGraph 4.2.2 engine (offline). |
