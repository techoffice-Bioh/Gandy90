#!/usr/bin/env python
"""Generate standalone interactive HTML viewers from system_gandy90.drawio.

This is an ISOLATED deliverable generator. It only READS the .drawio file and
writes the HTML next to itself. It imports nothing from build.py / sync.py and
never edits the inventory / scratch / diagrams pipeline.

It emits two themed, self-contained files (light + dark). Each embeds a snapshot
of the diagram's <mxGraphModel> XML inline and loads the locally vendored
drawio/mxGraph engine, so they work fully offline by double-clicking (file://).
Re-run to refresh the snapshot after the .drawio changes:

    py interactive/gen_interactive.py
"""

import base64
import sys
import urllib.parse
import zlib
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DRAWIO = PROJECT_ROOT / "diagrams" / "pictorial" / "system_gandy90.drawio"

OUT_LIGHT = SCRIPT_DIR / "system_gandy90.interactive.html"
OUT_DARK = SCRIPT_DIR / "system_gandy90.interactive.dark.html"


def extract_model(text):
    """Return the verbatim <mxGraphModel>...</mxGraphModel> substring.

    The file is plain/uncompressed, so the fast path is a literal slice. The
    compressed fallback (base64 + raw deflate + url-decode) is defensive only.
    """
    start = text.find("<mxGraphModel")
    if start != -1:
        close = text.find("</mxGraphModel>")
        if close != -1:
            return text[start:close + len("</mxGraphModel>")]

    dstart = text.find("<diagram")
    if dstart != -1:
        body_start = text.find(">", dstart) + 1
        body_end = text.find("</diagram>", body_start)
        if body_end != -1:
            payload = text[body_start:body_end].strip()
            try:
                raw = base64.b64decode(payload)
                inflated = zlib.decompress(raw, -15).decode("utf-8")
                xml = urllib.parse.unquote(inflated)
                s = xml.find("<mxGraphModel")
                e = xml.find("</mxGraphModel>")
                if s != -1 and e != -1:
                    return xml[s:e + len("</mxGraphModel>")]
            except Exception as exc:  # pragma: no cover - defensive only
                raise SystemExit("Could not decompress <diagram>: %s" % exc)

    raise SystemExit("Could not locate <mxGraphModel> in %s" % DRAWIO)


# Theme = the CSS custom-property block injected into :root. Everything else
# (layout, behavior) is shared. The diagram canvas (--paper) stays light in both
# themes so the embedded icons (drawn for a light background) remain faithful.
THEME_LIGHT = """    --bg: #eef2f6;
    --surface: #ffffff;
    --hover: #eef2f6;
    --ink: #15212b;
    --ink-soft: #5a6b7b;
    --line: #e3e8ef;
    --brand: #ce0000;
    --brand-tint: #fcebeb;
    --brand-edge: #f3c9c9;
    --brand-glow: rgba(206, 0, 0, .16);
    --dot-off: #cbd5e1;
    --paper: #ffffff;
    --paper-border: #e3e8ef;
    --paper-shadow: 0 1px 3px rgba(15, 23, 42, .06), 0 10px 28px rgba(15, 23, 42, .05);"""

THEME_DARK = """    --bg: #0e151c;
    --surface: #161f29;
    --hover: #1f2c3a;
    --ink: #e6edf3;
    --ink-soft: #93a4b5;
    --line: #263340;
    --brand: #ff3b3b;
    --brand-tint: rgba(255, 59, 59, .14);
    --brand-edge: rgba(255, 59, 59, .38);
    --brand-glow: rgba(255, 59, 59, .28);
    --dot-off: #3a4a5a;
    --paper: #0f1825;
    --paper-border: #243140;
    --paper-shadow: 0 2px 8px rgba(0, 0, 0, .5), 0 16px 44px rgba(0, 0, 0, .55);"""

# Extra per-theme CSS. The dark theme paints the diagram canvas dark; the
# embedded icons use black strokes (stroke:black) and several pipes are pure
# #000000, which would vanish on a dark background. invert(1) hue-rotate(180deg)
# turns those blacks light while keeping saturated colors (blue stays blue, red
# stays red), yielding a coherent, legible dark schematic.
EXTRA_LIGHT = ""
EXTRA_DARK = "  #graph svg { filter: invert(1) hue-rotate(180deg); }"


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@TITLE@@</title>
<link rel="icon" href="assets/sbsystem-favicon.png">
<style>
  :root {
@@THEME_VARS@@
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%;
    font-family: "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif;
    color: var(--ink); background: var(--bg); }
  #app { display: flex; flex-direction: column; height: 100vh; }

  /* ---- top bar ---------------------------------------------------------- */
  #topbar { display: flex; align-items: center; gap: 16px; flex: 0 0 auto;
    padding: 11px 20px; background: var(--surface);
    border-top: 3px solid var(--brand); border-bottom: 1px solid var(--line);
    box-shadow: 0 1px 2px rgba(0, 0, 0, .14); }
  .brand { display: flex; align-items: center; gap: 11px; }
  .brand img { height: 34px; width: auto; display: block; }
  .brand .wm { line-height: 1.05; }
  .brand .wm b { display: block; font-size: 16px; font-weight: 700;
    letter-spacing: .01em; color: var(--ink); }
  .brand .wm span { display: block; font-size: 10px; font-weight: 600;
    letter-spacing: .08em; text-transform: uppercase; color: var(--ink-soft); }
  .vrule { width: 1px; height: 30px; background: var(--line); }
  .page-title { font-size: 14px; color: var(--ink-soft); }
  .page-title b { color: var(--ink); font-weight: 700; }
  .spacer { margin-left: auto; }
  #reset { background: transparent; color: var(--brand);
    border: 1px solid var(--brand); border-radius: 8px; padding: 7px 14px;
    font: inherit; font-size: 12px; font-weight: 600; cursor: pointer;
    transition: background .15s, color .15s; }
  #reset:hover { background: var(--brand); color: #fff; }

  /* ---- body / canvas ---------------------------------------------------- */
  #body { flex: 1 1 auto; display: flex; min-height: 0; }
  #canvas-wrap { flex: 1 1 auto; min-width: 0; padding: 16px; display: flex;
    position: relative; }
  #graph { flex: 1 1 auto; min-width: 0; min-height: 0; background: var(--paper);
    border: 1px solid var(--paper-border); border-radius: 12px; overflow: auto;
    user-select: none; outline: none; box-shadow: var(--paper-shadow);
    touch-action: pan-x pan-y; opacity: 0; transition: opacity .3s ease; }
  #graph.ready { opacity: 1; }

  /* ---- zoom control (floating, over the canvas) ------------------------- */
  #zoomctl { position: absolute; right: 28px; bottom: 28px; z-index: 5;
    display: flex; flex-direction: column; background: var(--surface);
    border: 1px solid var(--line); border-radius: 10px; overflow: hidden;
    box-shadow: var(--paper-shadow); }
  #zoomctl button { width: 38px; height: 36px; border: none; background: transparent;
    color: var(--ink); font: inherit; font-size: 18px; line-height: 1; font-weight: 600;
    cursor: pointer; border-bottom: 1px solid var(--line); transition: background .12s; }
  #zoomctl button:last-child { border-bottom: none; font-size: 15px; }
  #zoomctl button:hover { background: var(--hover); }

  /* ---- side panel ------------------------------------------------------- */
  #panel { flex: 0 0 292px; width: 292px; background: var(--surface);
    border-left: 1px solid var(--line); display: flex; flex-direction: column; }
  .panel-head { display: flex; align-items: baseline; gap: 9px;
    padding: 15px 16px 11px; border-bottom: 1px solid var(--line); }
  .panel-head .ptitle { font-size: 12px; font-weight: 700; letter-spacing: .06em;
    text-transform: uppercase; color: var(--ink); }
  .panel-head .pcount { background: var(--hover); color: var(--ink-soft);
    border-radius: 999px; padding: 1px 9px; font-size: 11px; font-weight: 600; }
  #list { flex: 1 1 auto; overflow: auto; padding: 7px; }
  .comp { display: flex; align-items: center; gap: 10px; width: 100%;
    text-align: left; background: transparent; border: 1px solid transparent;
    border-radius: 8px; padding: 8px 10px; cursor: pointer; font: inherit;
    font-size: 13px; color: var(--ink-soft); transition: background .12s; }
  .comp:hover { background: var(--hover); }
  .comp .dot { flex: 0 0 auto; width: 9px; height: 9px; border-radius: 50%;
    background: var(--dot-off); transition: background .15s, box-shadow .15s; }
  .comp.on { background: var(--brand-tint); border-color: var(--brand-edge);
    color: var(--ink); font-weight: 600; }
  .comp.on .dot { background: var(--brand); box-shadow: 0 0 0 3px var(--brand-glow); }

  /* ---- active glow + connection flow animation (visible edge path) ------ */
  .comp-glow { filter: drop-shadow(0 0 6px rgba(206, 0, 0, .55)); }
  .conn-strong { stroke-width: 3.4px;
    filter: drop-shadow(0 0 4px var(--glow-conn, #ce0000)); }
  .conn-fwd { stroke-dasharray: 7 5; animation: flowdash .5s linear infinite; }
  .conn-rev { stroke-dasharray: 7 5; animation: flowdash .5s linear infinite reverse; }
  @keyframes flowdash { to { stroke-dashoffset: -12; } }

  /* ---- responsive: stack the panel under the canvas on narrow screens ---- */
  @media (max-width: 760px) {
    #topbar { flex-wrap: wrap; gap: 8px 12px; padding: 9px 13px; }
    .page-title { font-size: 13px; }
    #body { flex-direction: column; }
    #canvas-wrap { padding: 10px; min-height: 0; }
    #panel { flex: 0 0 auto; width: 100%; max-height: 34vh;
      border-left: none; border-top: 1px solid var(--line); }
  }
@@EXTRA_CSS@@
</style>
<script>
  // Must be set before mxClient.js loads so nothing is fetched at runtime.
  window.mxBasePath = "vendor/mxgraph";
  window.mxImageBasePath = "vendor/mxgraph/images";
  window.mxLoadResources = false;
  window.mxLoadStylesheets = false;
  window.mxForceIncludes = false;
</script>
<script src="vendor/mxgraph/mxClient.js"></script>
</head>
<body>
<div id="app">
  <div id="topbar">
    <div class="brand">
      <img src="assets/sbsystem-favicon.png" alt="SB System">
      <div class="wm"><b>SB System</b><span>Water treatment &amp; disinfection</span></div>
    </div>
    <div class="vrule"></div>
    <div class="page-title"><b>Gandy 90</b> &mdash; Interactive hydraulic diagram</div>
    <div class="spacer"></div>
    <button id="reset" type="button">Turn all off</button>
  </div>

  <div id="body">
    <div id="canvas-wrap">
      <div id="graph"></div>
      <div id="zoomctl">
        <button type="button" data-z="in" title="Zoom in" aria-label="Zoom in">&plus;</button>
        <button type="button" data-z="out" title="Zoom out" aria-label="Zoom out">&minus;</button>
        <button type="button" data-z="fit" title="Fit to view" aria-label="Fit to view">&#8862;</button>
      </div>
    </div>
    <div id="panel">
      <div class="panel-head">
        <span class="ptitle">Components</span>
        <span class="pcount" id="count">0</span>
      </div>
      <div id="list"></div>
    </div>
  </div>
</div>

<!-- Snapshot of system_gandy90.drawio (read as raw text, parsed by mxGraph). -->
<script type="application/xml" id="diagram">@@DIAGRAM_XML@@</script>

<script>
(function () {
  function boot() {
    var graphDiv = document.getElementById("graph");
    if (typeof mxGraph === "undefined") {
      graphDiv.textContent = "Failed to load the drawing engine (vendor/mxgraph/mxClient.js).";
      return;
    }

    // Component opacity. Connections are driven entirely via the DOM (below).
    var OP_ON = "100", OP_COMP_OFF = "25";
    var DIM = "0.3";   // "very low contrast" static connection

    var xml = document.getElementById("diagram").textContent;
    var doc = mxUtils.parseXml(xml);
    var graph = new mxGraph(graphDiv);

    // Read-only viewer: render and deliver events, but no editing/selection.
    graph.setEnabled(false);
    graph.setTooltips(false);
    graph.setPanning(false);
    graph.setConnectable(false);
    graph.setCellsLocked(true);
    graph.setCellsSelectable(false);
    graph.setCellsMovable(false);
    graph.setCellsResizable(false);
    graph.setCellsEditable(false);
    graph.foldingEnabled = false;
    graph.setHtmlLabels(true);
    graph.border = 22;

    // Bare mxGraph lacks drawio's base styles, so "group" container cells and
    // "edgeLabel" cells fall back to the default vertex style and render a
    // visible box. Register them as transparent so they draw nothing (as in
    // drawio) while still positioning/transforming their children.
    var sheet = graph.getStylesheet();
    var invisible = {};
    invisible[mxConstants.STYLE_FILLCOLOR] = "none";
    invisible[mxConstants.STYLE_STROKECOLOR] = "none";
    sheet.putCellStyle("group", invisible);
    sheet.putCellStyle("edgeLabel", invisible);

    // Make connections easy to click: the engine builds a hidden, wider
    // "tolerance" hit-path of width (lineWidth + svgStrokeTolerance). Bump that
    // tolerance so the clickable band around each thin edge is generous.
    mxConnector.prototype.svgStrokeTolerance = 20;

    var codec = new mxCodec(doc);
    codec.decode(doc.documentElement, graph.getModel());

    var model = graph.getModel();

    // ---- helpers -----------------------------------------------------------
    function topComponent(cell) {
      var c = cell;
      while (c != null) {
        var p = model.getParent(c);
        if (p == null) return null;
        var pid = p.getId();
        if (pid === "1" || pid === "0") {
          return model.isVertex(c) ? c : null;
        }
        c = p;
      }
      return null;
    }

    function isComponentCell(cell) {
      if (!model.isVertex(cell)) return false;
      var style = cell.getStyle() || "";
      return style.indexOf("group") === 0 || style.indexOf("image=") !== -1
             || style.indexOf("shape=image") !== -1;
    }

    function collectVertices(cell, acc) {
      acc.push(cell);
      var n = model.getChildCount(cell);
      for (var i = 0; i < n; i++) {
        var ch = model.getChildAt(cell, i);
        if (model.isVertex(ch)) collectVertices(ch, acc);
      }
    }

    function prettyName(id) {
      var s = id;
      if (s.slice(-6) === "_group") s = s.slice(0, -6);
      var parts = s.split("_");
      for (var i = 0; i < parts.length; i++) {
        var w = parts[i];
        if (w.length === 0) continue;
        if (w.length === 1) parts[i] = w.toUpperCase();
        else if (w === w.toUpperCase()) parts[i] = w;          // keep acronyms
        else parts[i] = w.charAt(0).toUpperCase() + w.slice(1);
      }
      return parts.join(" ");
    }

    // ---- build indexes -----------------------------------------------------
    var componentIndex = {};   // id -> {cell, on, name, edges:{}, dimCells:[]}
    var cells = model.cells;

    for (var id in cells) {
      var cell = cells[id];
      if (!model.isVertex(cell)) continue;
      var p = model.getParent(cell);
      if (!p || p.getId() !== "1") continue;
      if (!isComponentCell(cell)) continue;
      var dim = [];
      collectVertices(cell, dim);
      var imgs = [];
      for (var di = 0; di < dim.length; di++) {
        var ds = dim[di].getStyle() || "";
        if (ds.indexOf("image=") !== -1 || ds.indexOf("shape=image") !== -1) imgs.push(dim[di]);
      }
      componentIndex[id] = { cell: cell, on: false, name: prettyName(id),
                             edges: {}, dimCells: dim, imageCells: imgs };
    }

    // Connection state: 0 off, 1 dim/static, 2 full/static, 3 flow fwd, 4 flow rev.
    var edgeIndex = {};
    for (var id in cells) {
      var cell = cells[id];
      if (!model.isEdge(cell)) continue;
      var s = model.getTerminal(cell, true);
      var t = model.getTerminal(cell, false);
      if (!s || !t) continue;                    // skip decorative flexArrows
      var sc = topComponent(s), tc = topComponent(t);
      if (!sc || !tc) continue;
      var scId = sc.getId(), tcId = tc.getId();
      if (!componentIndex[scId] || !componentIndex[tcId]) continue;
      edgeIndex[id] = { cell: cell, src: scId, dst: tcId, state: 0 };
      componentIndex[scId].edges[id] = true;
      componentIndex[tcId].edges[id] = true;
    }

    // ---- raise layer-level edges above components (clickable on top) -------
    var layerEdges = [];
    for (var id in edgeIndex) {
      var ec = edgeIndex[id].cell;
      if (model.getParent(ec).getId() === "1") layerEdges.push(ec);
    }
    if (layerEdges.length) graph.orderCells(false, layerEdges);

    // ---- rendering ---------------------------------------------------------
    function powered(e) {
      return componentIndex[e.src].on || componentIndex[e.dst].on;
    }

    function applyEdgeVisual(id) {
      var e = edgeIndex[id];
      var st = graph.view.getState(e.cell);
      if (!st || !st.shape || !st.shape.node) return;
      var node = st.shape.node;
      // Visible line = first path that is NOT the hidden, wide tolerance hit-path
      // (that clone carries visibility="hidden"). Style only the visible line so
      // the wide click band is preserved in every state.
      var line = null, paths = node.getElementsByTagName("path");
      for (var i = 0; i < paths.length; i++) {
        if (paths[i].getAttribute("visibility") !== "hidden") { line = paths[i]; break; }
      }
      if (line) line.classList.remove("conn-strong", "conn-fwd", "conn-rev");
      if (e.state === 0) {                        // off: hidden, not clickable
        node.style.opacity = "0";
        node.style.pointerEvents = "none";
        return;
      }
      node.style.pointerEvents = "";
      if (e.state === 1) { node.style.opacity = DIM; return; }   // dim, static
      node.style.opacity = "1";                                  // full contrast
      if (line) {
        line.style.setProperty("--glow-conn", line.getAttribute("stroke") || "#ce0000");
        line.classList.add("conn-strong");                       // strong + own-color glow
        if (e.state === 3) line.classList.add("conn-fwd");
        else if (e.state === 4) line.classList.add("conn-rev");
      }
    }

    function applyComponentGlow(id) {
      var c = componentIndex[id];
      for (var i = 0; i < c.imageCells.length; i++) {
        var s2 = graph.view.getState(c.imageCells[i]);
        if (s2 && s2.shape && s2.shape.node) {
          if (c.on) s2.shape.node.classList.add("comp-glow");
          else s2.shape.node.classList.remove("comp-glow");
        }
      }
    }

    function render() {
      model.beginUpdate();
      try {
        var onC = [], offC = [];
        for (var id in componentIndex) {
          var c = componentIndex[id];
          var arr = c.on ? onC : offC;
          for (var i = 0; i < c.dimCells.length; i++) arr.push(c.dimCells[i]);
        }
        if (onC.length)  graph.setCellStyles(mxConstants.STYLE_OPACITY, OP_ON, onC);
        if (offC.length) graph.setCellStyles(mxConstants.STYLE_OPACITY, OP_COMP_OFF, offC);
      } finally {
        model.endUpdate();
      }
      for (var id in componentIndex) applyComponentGlow(id);
      for (var id in edgeIndex) applyEdgeVisual(id);
      syncPanel();
    }

    // ---- state transitions -------------------------------------------------
    function setComponent(compId, on) {
      var c = componentIndex[compId];
      if (!c) return;
      c.on = on;
      for (var eid in c.edges) {
        var e = edgeIndex[eid];
        if (powered(e)) { if (e.state === 0) e.state = 1; }   // newly powered -> dim
        else e.state = 0;                                     // both off -> hidden
      }
      render();
    }

    function toggleComponent(compId) {
      var c = componentIndex[compId];
      if (c) setComponent(compId, !c.on);
    }

    // Click loop for a powered connection. The first click leaves the dim
    // entry state for Active (full static); after that it loops
    // Active -> Flow forward -> Flow reverse -> Active, so a click always
    // brings the line back to a clear static state.
    function cycleConnection(edgeId) {
      var e = edgeIndex[edgeId];
      if (!e || e.state === 0) return;            // only a powered connection cycles
      e.state = (e.state === 4) ? 2 : e.state + 1;
      applyEdgeVisual(edgeId);
    }

    function allOff() {
      for (var id in componentIndex) componentIndex[id].on = false;
      for (var id in edgeIndex) edgeIndex[id].state = 0;
      render();
    }

    // ---- click dispatch ----------------------------------------------------
    graph.addListener(mxEvent.CLICK, function (sender, evt) {
      var ne = evt.getProperty("event");
      if (ne) mxEvent.consume(ne);
      var cell = evt.getProperty("cell");
      if (!cell) return;
      if (model.isEdge(cell)) {
        if (edgeIndex[cell.getId()]) cycleConnection(cell.getId());
        return;
      }
      var top = topComponent(cell);
      if (top && componentIndex[top.getId()]) toggleComponent(top.getId());
    });

    // ---- side panel --------------------------------------------------------
    var listEl = document.getElementById("list");
    var rows = {};
    var compIds = Object.keys(componentIndex).sort(function (a, b) {
      return componentIndex[a].name.localeCompare(componentIndex[b].name);
    });
    document.getElementById("count").textContent = String(compIds.length);
    compIds.forEach(function (cid) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "comp";
      var dot = document.createElement("span");
      dot.className = "dot";
      var nm = document.createElement("span");
      nm.className = "cname";
      nm.textContent = componentIndex[cid].name;
      btn.appendChild(dot);
      btn.appendChild(nm);
      btn.addEventListener("click", function () { toggleComponent(cid); });
      listEl.appendChild(btn);
      rows[cid] = btn;
    });
    function syncPanel() {
      for (var id in rows) rows[id].classList.toggle("on", componentIndex[id].on);
    }
    document.getElementById("reset").addEventListener("click", allOff);

    // ---- viewport: geometry-based framing + zoom ---------------------------
    // graph.fit() frames from the RENDERED bounds, which mxGraph inflates with
    // the HTML label boxes (each foreignObject is sized 100%/scale, e.g. 122%),
    // so the diagram ends up off-centre inside a pane far taller than the real
    // content -> phantom empty scroll. We frame from GEOMETRY instead (immune to
    // labels), compute scale + centred translate ourselves, and clamp the pane
    // to max(viewport, content) so scrollbars appear only when zoomed past fit.
    var PAD = graph.border;
    var fitScale = 1;                  // scale at which the whole diagram fits

    function contentBBox() {
      var layer = model.getChildAt(model.getRoot(), 0);
      return graph.getBoundingBoxFromGeometry(model.getChildCells(layer, true, true), true);
    }

    // anchor (optional) = { mx, my, sx, sy }: after rescaling, keep the model
    // point (mx,my) under the container-relative screen point (sx,sy). Without
    // an anchor the view is recentred (used by the buttons and fit).
    function applyScale(s, anchor, bb) {
      bb = bb || contentBBox();
      if (!bb || !bb.width || !bb.height) return;
      var cw = graphDiv.clientWidth, ch = graphDiv.clientHeight;
      s = Math.max(fitScale, Math.min(s, Math.max(fitScale * 4, 2)));
      var paneW = Math.max(cw, Math.ceil(bb.width * s + 2 * PAD));
      var paneH = Math.max(ch, Math.ceil(bb.height * s + 2 * PAD));
      var tx = (paneW / s - bb.width) / 2 - bb.x;   // centre content in the pane
      var ty = (paneH / s - bb.height) / 2 - bb.y;
      graph.view.scaleAndTranslate(s, tx, ty);
      var svg = graphDiv.querySelector("svg");
      if (svg) { svg.style.minWidth = paneW + "px"; svg.style.minHeight = paneH + "px"; }
      if (anchor) {                                 // keep the pinched point put
        graphDiv.scrollLeft = (anchor.mx + tx) * s - anchor.sx;
        graphDiv.scrollTop = (anchor.my + ty) * s - anchor.sy;
      } else {                                      // recentre
        graphDiv.scrollLeft = (graphDiv.scrollWidth - cw) / 2;
        graphDiv.scrollTop = (graphDiv.scrollHeight - ch) / 2;
      }
    }

    function fitView() {
      var bb = contentBBox();
      if (!bb || !bb.width || !bb.height) return;
      var cw = graphDiv.clientWidth, ch = graphDiv.clientHeight;
      fitScale = Math.min((cw - 2 * PAD) / bb.width, (ch - 2 * PAD) / bb.height, 1);
      applyScale(fitScale, null, bb);
    }

    document.getElementById("zoomctl").addEventListener("click", function (e) {
      var z = e.target.getAttribute("data-z");
      if (z === "in") applyScale(graph.view.scale * 1.25);
      else if (z === "out") applyScale(graph.view.scale / 1.25);
      else if (z === "fit") fitView();
    });

    // ---- touch gestures: one-finger pan is native (overflow:auto); two-finger
    // pinch zooms the diagram, anchored on the midpoint between the fingers.
    // touch-action:pan-x pan-y (CSS) keeps native one-finger scroll while
    // letting us own the pinch (we preventDefault only for 2-finger moves).
    var pinch = null;
    function touchDist(a, b) {
      var dx = a.clientX - b.clientX, dy = a.clientY - b.clientY;
      return Math.sqrt(dx * dx + dy * dy);
    }
    graphDiv.addEventListener("touchstart", function (e) {
      if (e.touches.length !== 2) return;
      var r = graphDiv.getBoundingClientRect();
      var sx = (e.touches[0].clientX + e.touches[1].clientX) / 2 - r.left;
      var sy = (e.touches[0].clientY + e.touches[1].clientY) / 2 - r.top;
      var s0 = graph.view.scale, t = graph.view.translate;
      pinch = { d0: touchDist(e.touches[0], e.touches[1]), s0: s0,
                mx: (graphDiv.scrollLeft + sx) / s0 - t.x,
                my: (graphDiv.scrollTop + sy) / s0 - t.y };
      e.preventDefault();
    }, { passive: false });
    graphDiv.addEventListener("touchmove", function (e) {
      if (!pinch || e.touches.length !== 2) return;
      var r = graphDiv.getBoundingClientRect();
      var sx = (e.touches[0].clientX + e.touches[1].clientX) / 2 - r.left;
      var sy = (e.touches[0].clientY + e.touches[1].clientY) / 2 - r.top;
      var d = touchDist(e.touches[0], e.touches[1]);
      if (pinch.d0 > 0) {
        applyScale(pinch.s0 * (d / pinch.d0), { mx: pinch.mx, my: pinch.my, sx: sx, sy: sy });
      }
      e.preventDefault();
    }, { passive: false });
    graphDiv.addEventListener("touchend", function (e) {
      if (e.touches.length < 2) pinch = null;
    });

    // ---- initial layout + state -------------------------------------------
    render();                          // everything off (components dim, edges hidden)
    // Defer the first framing one frame so the container reports its final size.
    // The very first synchronous pass can still carry a transient scrollbar from
    // the raw decode, skewing the fit by ~a scrollbar width.
    window.requestAnimationFrame(function () {
      fitView();
      graphDiv.classList.add("ready");   // fade the canvas in
    });

    // Re-frame on resize so the diagram stays framed through the mobile reflow
    // (panel dropping below the canvas).
    var refitPending = false;
    window.addEventListener("resize", function () {
      if (refitPending) return;
      refitPending = true;
      window.requestAnimationFrame(function () { refitPending = false; fitView(); });
    });
  }

  if (document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
</script>
</body>
</html>
"""


def build(theme_vars, extra_css, title, model_xml):
    return (TEMPLATE
            .replace("@@THEME_VARS@@", theme_vars)
            .replace("@@EXTRA_CSS@@", extra_css)
            .replace("@@TITLE@@", title)
            .replace("@@DIAGRAM_XML@@", model_xml))


# The source .drawio is owned by the pictorial pipeline; this generator only
# READS it and never edits it. A few of its embedded labels are still Italian —
# translate them to English in the snapshot only, so the deliverable is fully
# English while the source stays untouched. Strings are the HTML-entity-encoded
# label values exactly as they appear in the .drawio.
LABEL_TRANSLATIONS = {
    "&gt;INGRESSO&lt;/font&gt;&lt;div&gt;&lt;font style=&quot;color: rgb(255, 255, 255);&quot;&gt;ACQUA&lt;":
        "&gt;WATER&lt;/font&gt;&lt;div&gt;&lt;font style=&quot;color: rgb(255, 255, 255);&quot;&gt;INLET&lt;",
    "&gt;USCITA&lt;br&gt;ACQUA&lt;": "&gt;WATER&lt;br&gt;OUTLET&lt;",
}


def translate_labels(model_xml):
    for italian, english in LABEL_TRANSLATIONS.items():
        model_xml = model_xml.replace(italian, english)
    return model_xml


def main():
    if not DRAWIO.exists():
        raise SystemExit("Source diagram not found: %s" % DRAWIO)
    text = DRAWIO.read_text(encoding="utf-8")
    model_xml = translate_labels(extract_model(text))

    targets = [
        (OUT_LIGHT, THEME_LIGHT, EXTRA_LIGHT, "SB System &middot; Gandy 90 Hydraulic Diagram"),
        (OUT_DARK, THEME_DARK, EXTRA_DARK, "SB System &middot; Gandy 90 Hydraulic Diagram (Dark)"),
    ]
    for out, theme, extra, title in targets:
        html = build(theme, extra, title, model_xml)
        out.write_text(html, encoding="utf-8")
        print("Wrote %s (%d bytes)" % (out.name, len(html)))
    print("Embedded <mxGraphModel> snapshot: %d bytes" % len(model_xml))


if __name__ == "__main__":
    sys.exit(main())
