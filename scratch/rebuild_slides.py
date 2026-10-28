#!/usr/bin/env python3
"""
Refine doc/presentation/pov-graph-slides.html:
1. Make the Draw.io graph on Slide 2 exceptionally clean, spacious, and easy to view.
2. Remove all ':' prefixes from node labels (Character, Event, Location, Utterance, Knowledge Acquisition, Claim).
3. Clean up edge pills (RELATES TO, EXPERIENCED, PARTICIPATED IN, SAID, OCCURRED AT, HAS CLAIM, ASSERTS, ACQUIRED, ABOUT) without trailing arrows.
4. Enhance readability of node properties and visual hierarchy.
5. Add animated glowing particle pulses traveling along edges.
"""

HTML_CONTENT = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Same story. Different eyes. — ShiftKey Presentation</title>
<style>
  @font-face {
    font-family: "KaushanScriptLocal";
    src: url("assets/fonts/KaushanScript-Regular.woff2") format("woff2");
    font-weight: 400;
    font-style: normal;
    font-display: block;
  }

  :root {
    --bg-stage: #050814;
    --bg-panel: #0d1527;
    --bg-card: #131f38;
    --bg-chip: #1e293b;
    --border-muted: #2d3b55;
    --border-bright: #4b6088;
    --text-main: #f8fafc;
    --text-muted: #cbd5e1;
    --text-dim: #94a3b8;
    --accent: #fbbf24;
    --accent-glow: rgba(251, 191, 36, 0.4);
    --known: #34d399;
    --known-glow: rgba(52, 211, 153, 0.4);
    --false-stroke: #fb7185;
    --false-glow: rgba(251, 113, 133, 0.4);
    --gryffindor-red: #ef4444;
    --gryffindor-gold: #fbbf24;
    --slytherin-green: #10b981;
    --slytherin-silver: #cbd5e1;
    --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    --font-script: "KaushanScriptLocal", "Brush Script MT", cursive;
  }

  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    user-select: none;
  }

  html, body {
    width: 100vw;
    height: 100vh;
    overflow: hidden;
    background: #020409;
    color: var(--text-main);
    font-family: var(--font-sans);
    -webkit-font-smoothing: antialiased;
  }

  #viewport {
    width: 100vw;
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }

  #stage {
    width: 1920px;
    height: 1080px;
    flex-shrink: 0;
    position: relative;
    overflow: hidden;
    background: radial-gradient(ellipse at 50% 20%, #111a38 0%, #080d20 50%, #030612 100%);
    transform-origin: center center;
    box-shadow: 0 0 100px rgba(0, 0, 0, 0.95);
  }

  #starry-sky {
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 1;
  }

  /* Typography */
  .t-title {
    font-size: 68px;
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -0.02em;
    color: var(--text-main);
  }

  .t-script {
    font-family: var(--font-script);
    font-size: 72px;
    font-weight: 400;
    color: var(--accent);
    text-shadow: 0 0 24px var(--accent-glow);
    padding: 0 8px;
  }

  .t-body {
    font-size: 32px;
    font-weight: 700;
    line-height: 1.3;
    color: var(--text-main);
  }

  .t-caption {
    font-size: 22px;
    font-weight: 600;
    line-height: 1.35;
    color: var(--text-muted);
  }

  .mono {
    font-family: var(--font-mono);
  }

  /* Slide Containers */
  .screen {
    position: absolute;
    inset: 0;
    display: none;
    z-index: 5;
  }

  .screen.active {
    display: block;
  }

  .screen-title {
    position: absolute;
    left: 96px;
    top: 56px;
    margin: 0;
  }

  /* ShiftKey prompt banner */
  .prompt-banner {
    position: absolute;
    left: 96px;
    top: 140px;
    display: inline-flex;
    align-items: center;
    gap: 16px;
    padding: 8px 24px;
    background: rgba(13, 21, 39, 0.94);
    border: 2px solid var(--accent);
    border-radius: 14px;
    box-shadow: 0 0 20px var(--accent-glow);
  }

  .prompt-label {
    color: var(--accent);
  }

  .answer-line {
    position: absolute;
    left: 96px;
    top: 206px;
    color: var(--text-main);
  }

  .content-box {
    position: absolute;
    left: 96px;
    right: 96px;
    top: 268px;
    bottom: 96px;
  }

  /* Portraits */
  .portrait-circle {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    overflow: hidden;
    background: #101a33;
    position: relative;
    flex-shrink: 0;
    border: 3px solid var(--border-bright);
  }

  .portrait-circle.house-gryffindor {
    border-color: var(--gryffindor-red);
    box-shadow: inset 0 0 0 2px var(--gryffindor-gold), 0 4px 12px rgba(0, 0, 0, 0.55);
  }

  .portrait-circle.house-slytherin {
    border-color: var(--slytherin-green);
    box-shadow: inset 0 0 0 2px var(--slytherin-silver), 0 4px 12px rgba(0, 0, 0, 0.55);
  }

  .portrait-circle.house-neutral {
    border-color: #a855f7;
    box-shadow: inset 0 0 0 2px #d8b4fe, 0 4px 12px rgba(0, 0, 0, 0.55);
  }

  .portrait-circle img {
    width: 100%;
    height: 235%;
    object-fit: cover;
    object-position: 50% 4%;
    display: block;
    pointer-events: none;
  }

  .portrait-circle.xs {
    width: 48px;
    height: 48px;
    border-width: 2px;
  }

  /* HUD Narrator (top-right) */
  #hud-narrator {
    position: absolute;
    right: 96px;
    top: 56px;
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 8px 20px;
    background: rgba(13, 21, 39, 0.94);
    border: 2px solid var(--accent);
    border-radius: 18px;
    box-shadow: 0 0 24px var(--accent-glow);
    z-index: 25;
  }

  .hud-badge {
    padding: 4px 12px;
    border-radius: 8px;
    background: #3b2804;
    border: 1.5px solid var(--accent);
    color: var(--accent);
  }

  /* HUD Footer */
  #hud-footer {
    position: absolute;
    left: 96px;
    right: 96px;
    bottom: 24px;
    height: 52px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    z-index: 20;
  }

  .hud-left {
    display: flex;
    align-items: center;
    gap: 20px;
  }

  .hud-xp-wrap {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .hud-xp-bar {
    width: 360px;
    height: 14px;
    background: var(--bg-panel);
    border: 2px solid var(--border-bright);
    border-radius: 999px;
    overflow: hidden;
  }

  #hud-xp-fill {
    height: 100%;
    width: 20%;
    background: linear-gradient(90deg, #f59e0b 0%, #34d399 100%);
    transition: width 0.3s ease;
  }

  .hud-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 16px;
    background: rgba(19, 31, 56, 0.9);
    border: 1.5px solid var(--border-bright);
    border-radius: 12px;
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.2s;
  }

  .hud-btn:hover {
    border-color: var(--accent);
    color: var(--accent);
    box-shadow: 0 0 12px var(--accent-glow);
  }

  /* Speaker Notes Drawer */
  #notes-drawer {
    position: absolute;
    left: 96px;
    right: 96px;
    bottom: 84px;
    background: rgba(10, 16, 32, 0.98);
    border: 2px solid var(--accent);
    border-radius: 18px;
    padding: 20px 28px;
    box-shadow: 0 0 40px rgba(0, 0, 0, 0.95);
    z-index: 30;
    display: none;
  }

  #notes-drawer.open {
    display: block;
  }

  /* ==================== SLIDE 1: TITLE & CHARACTER SELECT ==================== */
  .title-hero-box {
    margin-top: 50px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }

  .title-hook-box {
    margin: 20px auto;
    max-width: 1080px;
    padding: 16px 32px;
    background: rgba(15, 23, 42, 0.85);
    border: 2px solid var(--accent);
    border-radius: 18px;
    box-shadow: 0 0 24px var(--accent-glow);
    text-align: center;
  }

  .roster-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 36px;
    max-width: 1540px;
    margin: 32px auto 0;
  }

  .character-slot {
    position: relative;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    transition: transform 0.25s;
  }

  .character-slot:hover {
    transform: translateY(-8px);
  }

  .character-figure {
    height: 400px;
    margin-bottom: -20px;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    filter: drop-shadow(0 14px 22px rgba(0, 0, 0, 0.75));
  }

  .character-figure img {
    height: 100%;
    width: auto;
    pointer-events: none;
  }

  .name-plate {
    position: relative;
    z-index: 3;
    width: 100%;
    padding: 18px 16px;
    background: rgba(15, 25, 52, 0.9);
    border: 2.5px solid var(--border-bright);
    border-radius: 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.65);
    transition: all 0.25s;
  }

  .character-slot.house-gryffindor:hover .name-plate,
  .character-slot.house-gryffindor.selected .name-plate {
    border-color: var(--gryffindor-red);
    box-shadow: 0 0 24px rgba(239, 68, 68, 0.4);
  }

  .character-slot.house-neutral:hover .name-plate,
  .character-slot.house-neutral.selected .name-plate {
    border-color: #a855f7;
    box-shadow: 0 0 24px rgba(168, 85, 247, 0.4);
  }

  .character-slot.selected .name-plate {
    border-color: var(--accent);
    background: rgba(26, 38, 72, 0.96);
    box-shadow: 0 0 32px var(--accent-glow);
  }

  .ready-badge {
    position: absolute;
    top: -14px;
    right: 16px;
    padding: 2px 12px;
    border-radius: 8px;
    background: #451a03;
    border: 1.5px solid var(--accent);
    color: var(--accent);
    opacity: 0;
  }

  .character-slot.selected .ready-badge {
    opacity: 1;
  }

  /* ==================== SLIDE 2: SPRINT 1 (DRAW.IO GRAPH) ==================== */

  /* SVG Text Styling (Exact Control, Never Overridden by Global CSS) */
  .svg-node-title {
    font-family: var(--font-display), -apple-system, sans-serif;
    font-size: 19px;
    font-weight: 800;
    fill: #FFFFFF;
    letter-spacing: 0.5px;
  }
  .svg-node-sub {
    font-family: var(--font-mono), monospace;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.5px;
  }
  .svg-node-prop1 {
    font-family: var(--font-mono), monospace;
    font-size: 12px;
    fill: #CBD5E1;
  }
  .svg-node-prop2 {
    font-family: var(--font-mono), monospace;
    font-size: 11px;
    fill: #94A3B8;
  }
  .svg-edge-label {
    font-family: var(--font-mono), monospace;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.5px;
  }

  .drawio-stage-card {
    width: 100%;
    height: 680px;
    background: rgba(8, 16, 30, 0.96);
    border: 2px solid var(--border-muted);
    border-radius: 24px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.7);
  }

  .drawio-top-bar {
    position: absolute;
    top: 18px;
    left: 28px;
    right: 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    z-index: 10;
  }

  .drawio-title-box {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .drawio-controls {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .btn-pill {
    padding: 8px 18px;
    border-radius: 12px;
    background: rgba(19, 31, 56, 0.9);
    border: 1.5px solid var(--border-bright);
    color: var(--text-main);
    cursor: pointer;
    font-size: 18px;
    font-weight: 600;
    transition: all 0.2s;
  }

  .btn-pill:hover, .btn-pill.active {
    border-color: var(--accent);
    color: var(--accent);
    box-shadow: 0 0 14px var(--accent-glow);
  }

  .drawio-rule-banner {
    position: absolute;
    bottom: 16px;
    left: 28px;
    right: 28px;
    padding: 12px 24px;
    background: rgba(15, 27, 46, 0.95);
    border: 1.5px solid #334d70;
    border-radius: 16px;
    display: flex;
    align-items: center;
    gap: 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    z-index: 10;
  }

  .graph-node {
    cursor: pointer;
    transition: transform 0.25s ease, filter 0.25s ease;
  }

  .graph-node:hover {
    filter: brightness(1.2) drop-shadow(0 0 20px var(--accent-glow));
    transform: scale(1.03);
  }

  .flowing-edge {
    stroke-dasharray: 8, 8;
    animation: edgeDash 25s linear infinite;
  }

  @keyframes edgeDash {
    to { stroke-dashoffset: -1000; }
  }

  /* ==================== SLIDE 3: SPRINT 2 (BARRIER VS SOLUTION) ==================== */
  .sprint2-grid {
    display: grid;
    grid-template-columns: 560px 1fr;
    gap: 32px;
    height: 680px;
  }

  .barrier-card {
    background: rgba(26, 12, 19, 0.92);
    border: 3px solid #f43f5e;
    border-radius: 24px;
    padding: 32px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 0 34px rgba(244, 63, 94, 0.2);
    position: relative;
    overflow: hidden;
  }

  .barrier-header {
    display: flex;
    align-items: center;
    gap: 14px;
    color: #fda4af;
  }

  .barrier-box {
    background: rgba(15, 23, 42, 0.85);
    border: 2px dashed #f43f5e;
    border-radius: 18px;
    padding: 24px;
    margin: 20px 0;
    text-align: center;
  }

  .barrier-fault-list {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .fault-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 16px;
    border-radius: 12px;
    background: rgba(244, 63, 94, 0.12);
    border: 1px solid rgba(244, 63, 94, 0.35);
    color: #fecdd3;
  }

  .solution-card {
    background: rgba(11, 25, 34, 0.92);
    border: 3px solid var(--known);
    border-radius: 24px;
    padding: 32px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 0 34px rgba(52, 211, 153, 0.2);
    position: relative;
    overflow: hidden;
  }

  .solution-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .pipeline-track {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 24px 0;
    position: relative;
  }

  .pipeline-node {
    flex: 1;
    background: rgba(15, 23, 42, 0.92);
    border: 2px solid var(--border-bright);
    border-radius: 18px;
    padding: 18px 14px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    position: relative;
    transition: all 0.3s;
  }

  .pipeline-node.active-stage {
    border-color: var(--accent);
    box-shadow: 0 0 24px var(--accent-glow);
    background: rgba(28, 41, 74, 0.95);
  }

  .pipeline-node.success-stage {
    border-color: var(--known);
    box-shadow: 0 0 20px var(--known-glow);
  }

  .pipeline-node.error-stage {
    border-color: var(--false-stroke);
    box-shadow: 0 0 20px var(--false-glow);
  }

  .pipeline-arrow {
    color: var(--border-bright);
    font-size: 24px;
    padding: 0 6px;
  }

  .trace-console-box {
    background: #090e1c;
    border: 2px solid var(--border-bright);
    border-radius: 16px;
    padding: 18px 24px;
    font-family: var(--font-mono);
    color: #6ee7b7;
    min-height: 120px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 8px;
  }

  .metric-ribbon {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    padding: 14px 20px;
    background: rgba(15, 23, 42, 0.85);
    border: 2px solid var(--border-bright);
    border-radius: 16px;
    text-align: center;
  }

  .metric-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  /* ==================== SLIDE 4: SPRINT 3 (TWIST DIVERSION) ==================== */
  .sprint3-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 32px;
    height: 680px;
  }

  .sprint3-top-strip {
    grid-column: 1 / -1;
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: rgba(15, 23, 42, 0.9);
    border: 2px solid var(--border-bright);
    border-radius: 18px;
    padding: 12px 28px;
  }

  .pass-pills-row {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .pass-pill {
    padding: 6px 20px;
    border-radius: 999px;
    background: #1e293b;
    border: 2px solid var(--border-bright);
    color: var(--text-muted);
  }

  .pass-pill.active {
    border-color: var(--accent);
    color: var(--accent);
    background: #362507;
  }

  .twist-panel {
    background: rgba(15, 23, 42, 0.92);
    border: 3px solid var(--border-muted);
    border-radius: 24px;
    padding: 32px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
    overflow: hidden;
  }

  .twist-panel.omniscient {
    border-color: #38bdf8;
    box-shadow: 0 0 28px rgba(56, 189, 248, 0.2);
  }

  .twist-panel.subjective {
    border-color: var(--accent);
    box-shadow: 0 0 28px var(--accent-glow);
  }

  .belief-gem-card {
    padding: 20px 24px;
    border-radius: 18px;
    display: flex;
    align-items: center;
    gap: 18px;
    background: rgba(10, 16, 32, 0.85);
    border: 2.5px solid var(--border-bright);
    transition: all 0.3s;
  }

  .belief-gem-card.false-gem {
    border-color: var(--false-stroke);
    background: linear-gradient(180deg, rgba(244, 63, 94, 0.15) 0%, rgba(15, 23, 42, 0.95) 100%);
  }

  .belief-gem-card.true-gem {
    border-color: var(--known);
    background: linear-gradient(180deg, rgba(52, 211, 153, 0.15) 0%, rgba(15, 23, 42, 0.95) 100%);
  }

  .strike-text {
    text-decoration: line-through;
    text-decoration-thickness: 3px;
    text-decoration-color: var(--false-stroke);
    color: #fda4af;
  }

  /* ==================== SLIDE 5: WHAT'S NEXT FOR ME ==================== */
  .sprint5-container {
    width: 100%;
    height: 680px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .takeaway-banner {
    padding: 20px 36px;
    background: linear-gradient(90deg, rgba(251, 191, 36, 0.18) 0%, rgba(15, 23, 42, 0.94) 100%);
    border: 3px solid var(--accent);
    border-radius: 20px;
    display: flex;
    align-items: center;
    box-shadow: 0 0 28px var(--accent-glow);
  }

  .horizons-track {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 28px;
  }

  .horizon-card {
    background: rgba(15, 23, 42, 0.92);
    border: 3px solid var(--border-muted);
    border-radius: 22px;
    padding: 28px 24px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 250px;
  }

  .horizon-card.done {
    border-color: var(--known);
  }

  .horizon-card.active {
    border-color: var(--accent);
    box-shadow: 0 0 24px var(--accent-glow);
  }

  .horizon-card.future {
    border-style: dashed;
    border-color: var(--border-bright);
  }

  .replay-roster-row {
    background: rgba(15, 23, 42, 0.92);
    border: 2px solid var(--border-bright);
    border-radius: 20px;
    padding: 16px 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .replay-btns-group {
    display: flex;
    align-items: center;
    gap: 20px;
  }

  .replay-btn {
    display: inline-flex;
    align-items: center;
    gap: 12px;
    padding: 8px 20px;
    border-radius: 14px;
    background: var(--bg-card);
    border: 2px solid var(--border-muted);
    color: var(--text-main);
    cursor: pointer;
    transition: all 0.2s;
  }

  .replay-btn:hover {
    border-color: var(--accent);
    transform: translateY(-4px);
    box-shadow: 0 0 16px var(--accent-glow);
  }
</style>
</head>
<body>
<div id="viewport">
  <main id="stage">
    <!-- Starry night canvas -->
    <canvas id="starry-sky" width="1920" height="1080"></canvas>

    <!-- Top right HUD active narrator -->
    <div id="hud-narrator" style="display: none;">
      <div id="hud-portrait" class="portrait-circle xs house-gryffindor">
        <img id="hud-portrait-img" src="assets/characters/harry.webp" alt="Narrator">
      </div>
      <span id="hud-name" class="t-caption">Harry Potter</span>
      <span class="hud-badge t-caption mono">POV LENS</span>
    </div>

    <!-- ==================== SLIDE 1: TITLE & CHARACTER SELECT ==================== -->
    <section class="screen active" data-screen="1" data-time="45"
      data-notes="Hello everyone, I'm Vu Trong Nhan. I'm presenting 'Same story. Different eyes.', an AI system that retells stories through the eyes of the characters who lived them. The core technical problem is epistemic modeling: characters witnessing an event don't possess all facts. Real narrative understanding requires tracking subjective knowledge horizons. Let's pick a character below to experience their point of view.">
      
      <div class="content-box" style="top: 80px; bottom: 80px;">
        <div class="title-hero-box">
          <h1 class="t-title">Same story. <span class="t-script">Different eyes.</span></h1>
          <p class="t-body" style="color: var(--accent);">Vu Trong Nhan</p>
          <p class="t-caption mono" style="color: var(--text-muted);">Build It! Machine Learning · Fall 2026</p>
        </div>

        <div class="title-hook-box">
          <p class="t-body">Retelling complex literature through any character's subjective viewpoint.</p>
          <p class="t-caption" style="color: var(--text-muted); margin-top: 8px;">Grounding large language models in dynamic, timeline-aware character knowledge graphs.</p>
        </div>

        <div class="roster-grid">
          <!-- Harry -->
          <div class="character-slot house-gryffindor selected" tabindex="0" data-character="harry">
            <div class="character-figure"><img src="assets/characters/harry.webp" alt="Harry Potter"></div>
            <div class="name-plate">
              <span class="ready-badge t-caption mono">ACTIVE</span>
              <span class="t-body">Harry Potter</span>
              <span class="t-caption mono" style="color: var(--accent);">The Seeker</span>
            </div>
          </div>

          <!-- Hermione -->
          <div class="character-slot house-gryffindor" tabindex="0" data-character="hermione">
            <div class="character-figure"><img src="assets/characters/hermione.webp" alt="Hermione Granger"></div>
            <div class="name-plate">
              <span class="ready-badge t-caption mono">READY</span>
              <span class="t-body">Hermione Granger</span>
              <span class="t-caption mono" style="color: var(--accent);">The Scholar</span>
            </div>
          </div>

          <!-- Ron -->
          <div class="character-slot house-gryffindor" tabindex="0" data-character="ron">
            <div class="character-figure"><img src="assets/characters/ron.webp" alt="Ron Weasley"></div>
            <div class="name-plate">
              <span class="ready-badge t-caption mono">READY</span>
              <span class="t-body">Ron Weasley</span>
              <span class="t-caption mono" style="color: var(--accent);">The Strategist</span>
            </div>
          </div>

          <!-- Quirrell -->
          <div class="character-slot house-neutral" tabindex="0" data-character="quirrell">
            <div class="character-figure"><img src="assets/characters/quirrell.webp" alt="Professor Quirrell"></div>
            <div class="name-plate">
              <span class="ready-badge t-caption mono">READY</span>
              <span class="t-body">Professor Quirrell</span>
              <span class="t-caption mono" style="color: var(--accent);">Carries a secret</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== SLIDE 2: SPRINT 1 (DRAW.IO GRAPH - CLEAN NO COLONS) ==================== -->
    <section class="screen" data-screen="2" data-time="70"
      data-notes="In Sprint 1, our core accomplishment was designing the Neo4j Character POV Knowledge Graph. We couldn't just throw raw text at a model and ask it to retell. We had to design an explicit schema separating objective reality from subjective perception. Notice the 7 node types: Characters, Events, Locations, Utterances, Claims, and crucially Knowledge Acquisition. The fundamental model rule at the bottom governs everything: witnessing an event does not mean knowing every truth inside it. ACQUIRED and ABOUT record exactly what becomes known and when.">
      
      <h1 class="screen-title t-title">Sprint 1</h1>
      <div class="prompt-banner">
        <span class="prompt-label t-caption mono">PROMPT:</span>
        <span class="t-caption">What did you accomplish?</span>
      </div>
      <p class="answer-line t-body">Designed the Epistemic POV Graph: separating objective reality from character perception.</p>

      <div class="content-box">
        <div class="drawio-stage-card">
          <!-- Top bar with title and animation controls -->
          <div class="drawio-top-bar">
            <div class="drawio-title-box">
              <span class="t-body" style="color: var(--accent);">CHARACTER POV · KNOWLEDGE GRAPH</span>
              <span class="t-caption mono" style="color: var(--text-muted);">(doc/pov_neo4j_character_graph.drawio)</span>
            </div>
            <div class="drawio-controls">
              <button type="button" class="btn-pill" id="btn-toggle-labels">Toggle Story Labels</button>
              <button type="button" class="btn-pill" id="btn-replay-graph">Replay Build Steps</button>
            </div>
          </div>

                                        <!-- Exact Draw.io Graph in SVG (Clean, Spacious, Balanced 2-Tier Architecture, No Colons) -->
          <svg width="1728" height="660" viewBox="0 0 1728 660" id="drawio-svg" aria-label="POV Knowledge Graph">
            <defs>
              <marker id="arr-blue" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 9 5 L 0 9 z" fill="#73BFFF"/>
              </marker>
              <marker id="arr-teal" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 9 5 L 0 9 z" fill="#74DEBF"/>
              </marker>
              <marker id="arr-purple" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 9 5 L 0 9 z" fill="#B8ABFF"/>
              </marker>
              <marker id="arr-gold" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 9 5 L 0 9 z" fill="#F8CF85"/>
              </marker>
              <marker id="arr-amber" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 9 5 L 0 9 z" fill="#F1BD8B"/>
              </marker>
              <marker id="arr-magenta" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 9 5 L 0 9 z" fill="#D0A7FF"/>
              </marker>
              <marker id="arr-yellow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 9 5 L 0 9 z" fill="#FFE18B"/>
              </marker>
            </defs>

            <!-- ==================== EDGES WITH SLEEK LABELS (NO COLONS, GENEROUS SPACING) ==================== -->
            <!-- e_rel: Character A -> Character B (RELATES TO) -->
            <g id="edge-rel" class="graph-edge-group">
              <path id="path-rel" d="M 290 150 C 450 110, 600 110, 700 145" fill="none" stroke="#73BFFF" stroke-width="3" marker-end="url(#arr-blue)" class="flowing-edge"/>
              <g transform="translate(495, 105)">
                <rect x="-75" y="-14" width="150" height="28" rx="14" fill="#102034" stroke="#73BFFF" stroke-width="1.8"/>
                <text x="0" y="5" text-anchor="middle" fill="#73BFFF" class="svg-edge-label">RELATES TO</text>
              </g>
            </g>

            <!-- e_exp: Character A -> Event (EXPERIENCED) -->
            <g id="edge-exp" class="graph-edge-group">
              <line x1="270" y1="205" x2="600" y2="385" stroke="#74DEBF" stroke-width="3" marker-end="url(#arr-teal)" class="flowing-edge"/>
              <g transform="translate(435, 295)">
                <rect x="-75" y="-14" width="150" height="28" rx="14" fill="#102034" stroke="#74DEBF" stroke-width="1.8"/>
                <text x="0" y="5" text-anchor="middle" fill="#74DEBF" class="svg-edge-label">EXPERIENCED</text>
              </g>
            </g>

            <!-- e_acq: Character A -> KnowledgeAcquisition (ACQUIRED) -->
            <g id="edge-acq" class="graph-edge-group">
              <line x1="225" y1="230" x2="225" y2="355" stroke="#D0A7FF" stroke-width="3.5" marker-end="url(#arr-magenta)" class="flowing-edge"/>
              <g transform="translate(225, 295)">
                <rect x="-55" y="-14" width="110" height="28" rx="14" fill="#102034" stroke="#D0A7FF" stroke-width="1.8"/>
                <text x="0" y="5" text-anchor="middle" fill="#D0A7FF" class="svg-edge-label">ACQUIRED</text>
              </g>
            </g>

            <!-- e_part: Character B -> Event (PARTICIPATED IN) -->
            <g id="edge-part" class="graph-edge-group">
              <line x1="745" y1="225" x2="685" y2="360" stroke="#74DEBF" stroke-width="3" marker-end="url(#arr-teal)" class="flowing-edge"/>
              <g transform="translate(715, 290)">
                <rect x="-80" y="-14" width="160" height="28" rx="14" fill="#102034" stroke="#74DEBF" stroke-width="1.8"/>
                <text x="0" y="5" text-anchor="middle" fill="#74DEBF" class="svg-edge-label">PARTICIPATED IN</text>
              </g>
            </g>

            <!-- e_said: Character B -> Utterance (SAID) -->
            <g id="edge-said" class="graph-edge-group">
              <path d="M 840 150 C 1020 110, 1220 110, 1370 145" fill="none" stroke="#B8ABFF" stroke-width="3" marker-end="url(#arr-purple)" class="flowing-edge"/>
              <g transform="translate(1105, 105)">
                <rect x="-50" y="-14" width="100" height="28" rx="14" fill="#102034" stroke="#B8ABFF" stroke-width="1.8"/>
                <text x="0" y="5" text-anchor="middle" fill="#B8ABFF" class="svg-edge-label">SAID</text>
              </g>
            </g>

            <!-- e_loc: Event -> Location (OCCURRED AT) -->
            <g id="edge-loc" class="graph-edge-group">
              <line x1="720" y1="425" x2="1010" y2="425" stroke="#F1BD8B" stroke-width="3" marker-end="url(#arr-amber)" class="flowing-edge"/>
              <g transform="translate(865, 425)">
                <rect x="-70" y="-14" width="140" height="28" rx="14" fill="#102034" stroke="#F1BD8B" stroke-width="1.8"/>
                <text x="0" y="5" text-anchor="middle" fill="#F1BD8B" class="svg-edge-label">OCCURRED AT</text>
              </g>
            </g>

            <!-- e_has: Event -> Claim (HAS CLAIM) -->
            <g id="edge-has" class="graph-edge-group">
              <path d="M 700 380 C 850 310, 1220 310, 1380 385" fill="none" stroke="#F8CF85" stroke-width="3" marker-end="url(#arr-gold)" class="flowing-edge"/>
              <g transform="translate(1040, 310)">
                <rect x="-60" y="-14" width="120" height="28" rx="14" fill="#102034" stroke="#F8CF85" stroke-width="1.8"/>
                <text x="0" y="5" text-anchor="middle" fill="#F8CF85" class="svg-edge-label">HAS CLAIM</text>
              </g>
            </g>

            <!-- e_assert: Utterance -> Claim (ASSERTS) -->
            <g id="edge-assert" class="graph-edge-group">
              <line x1="1440" y1="230" x2="1440" y2="355" stroke="#D0A7FF" stroke-width="3" marker-end="url(#arr-purple)" class="flowing-edge"/>
              <g transform="translate(1440, 295)">
                <rect x="-50" y="-14" width="100" height="28" rx="14" fill="#102034" stroke="#D0A7FF" stroke-width="1.8"/>
                <text x="0" y="5" text-anchor="middle" fill="#D0A7FF" class="svg-edge-label">ASSERTS</text>
              </g>
            </g>

            <!-- e_about: KnowledgeAcquisition -> Claim (ABOUT) -->
            <g id="edge-about" class="graph-edge-group">
              <path d="M 290 445 C 560 515, 1100 515, 1375 445" fill="none" stroke="#FFE18B" stroke-width="3.5" marker-end="url(#arr-yellow)" class="flowing-edge"/>
              <g transform="translate(830, 505)">
                <rect x="-85" y="-16" width="170" height="32" rx="16" fill="#102034" stroke="#FFE18B" stroke-width="1.8"/>
                <text x="0" y="5" text-anchor="middle" fill="#FFE18B" class="svg-edge-label" font-size="14">ABOUT (Truth)</text>
              </g>
            </g>

            <!-- ==================== 7 NODES (SPACIOUS, HIGH LEGIBILITY, NO COLONS) ==================== -->
            <!-- Node 1: Character A · POV -->
            <g class="graph-node" id="node-char-a" transform="translate(225, 160)">
              <circle cx="0" cy="0" r="68" fill="#152E4D" stroke="#65B9FF" stroke-width="3"/>
              <text x="0" y="-23" text-anchor="middle" class="svg-node-title">Character</text>
              <text x="0" y="-4" text-anchor="middle" fill="#65B9FF" class="svg-node-sub">A · POV</text>
              <line x1="-38" y1="6" x2="38" y2="6" stroke="#65B9FF" stroke-opacity="0.5" stroke-width="1.5"/>
              <text x="0" y="23" text-anchor="middle" class="svg-node-prop1">name · role</text>
              <text x="0" y="40" text-anchor="middle" class="svg-node-prop2">perspective</text>
            </g>

            <!-- Node 2: Character B -->
            <g class="graph-node" id="node-char-b" transform="translate(770, 160)">
              <circle cx="0" cy="0" r="68" fill="#152E4D" stroke="#65B9FF" stroke-width="3"/>
              <text x="0" y="-23" text-anchor="middle" class="svg-node-title">Character</text>
              <text x="0" y="-4" text-anchor="middle" fill="#65B9FF" class="svg-node-sub">B</text>
              <line x1="-38" y1="6" x2="38" y2="6" stroke="#65B9FF" stroke-opacity="0.5" stroke-width="1.5"/>
              <text x="0" y="23" text-anchor="middle" class="svg-node-prop1">name · role</text>
              <text x="0" y="40" text-anchor="middle" class="svg-node-prop2">aliases</text>
            </g>

            <!-- Node 3: Event -->
            <g class="graph-node" id="node-event" transform="translate(650, 425)">
              <circle cx="0" cy="0" r="68" fill="#0E3D30" stroke="#60E1AC" stroke-width="3"/>
              <text x="0" y="-18" text-anchor="middle" class="svg-node-title">Event</text>
              <line x1="-38" y1="-3" x2="38" y2="-3" stroke="#60E1AC" stroke-opacity="0.5" stroke-width="1.5"/>
              <text x="0" y="17" text-anchor="middle" class="svg-node-prop1">type · summary</text>
              <text x="0" y="37" text-anchor="middle" class="svg-node-prop2">story_order</text>
            </g>

            <!-- Node 4: Location -->
            <g class="graph-node" id="node-location" transform="translate(1080, 425)">
              <circle cx="0" cy="0" r="68" fill="#3D2B14" stroke="#EEC594" stroke-width="3"/>
              <text x="0" y="-18" text-anchor="middle" class="svg-node-title">Location</text>
              <line x1="-38" y1="-3" x2="38" y2="-3" stroke="#EEC594" stroke-opacity="0.5" stroke-width="1.5"/>
              <text x="0" y="17" text-anchor="middle" class="svg-node-prop1">name · kind</text>
              <text x="0" y="37" text-anchor="middle" class="svg-node-prop2">scene place</text>
            </g>

            <!-- Node 5: Utterance -->
            <g class="graph-node" id="node-utterance" transform="translate(1440, 160)">
              <circle cx="0" cy="0" r="68" fill="#2E1F4D" stroke="#B8ABFF" stroke-width="3"/>
              <text x="0" y="-18" text-anchor="middle" class="svg-node-title">Utterance</text>
              <line x1="-38" y1="-3" x2="38" y2="-3" stroke="#B8ABFF" stroke-opacity="0.5" stroke-width="1.5"/>
              <text x="0" y="17" text-anchor="middle" class="svg-node-prop1">text · speaker</text>
              <text x="0" y="37" text-anchor="middle" class="svg-node-prop2">spoken words</text>
            </g>

            <!-- Node 6: Knowledge Acquisition -->
            <g class="graph-node" id="node-knowledge" transform="translate(225, 425)">
              <circle cx="0" cy="0" r="68" fill="#3D1A4D" stroke="#D0A7FF" stroke-width="3"/>
              <text x="0" y="-24" text-anchor="middle" class="svg-node-title" font-size="17">Knowledge</text>
              <text x="0" y="-5" text-anchor="middle" fill="#D0A7FF" class="svg-node-sub">Acquisition</text>
              <line x1="-38" y1="6" x2="38" y2="6" stroke="#D0A7FF" stroke-opacity="0.5" stroke-width="1.5"/>
              <text x="0" y="23" text-anchor="middle" class="svg-node-prop1">channel · time</text>
              <text x="0" y="40" text-anchor="middle" class="svg-node-prop2">stance · belief</text>
            </g>

            <!-- Node 7: Claim -->
            <g class="graph-node" id="node-claim" transform="translate(1440, 425)">
              <circle cx="0" cy="0" r="68" fill="#3D3011" stroke="#FFE18B" stroke-width="3"/>
              <text x="0" y="-18" text-anchor="middle" class="svg-node-title">Claim</text>
              <line x1="-38" y1="-3" x2="38" y2="-3" stroke="#FFE18B" stroke-opacity="0.5" stroke-width="1.5"/>
              <text x="0" y="17" text-anchor="middle" class="svg-node-prop1">statement</text>
              <text x="0" y="37" text-anchor="middle" class="svg-node-prop2">truth status</text>
            </g>
          </svg>

          <!-- Model Rule Banner (Clean, Professional, No Awkward Colons) -->
          <div class="drawio-rule-banner">
            <span class="hud-badge mono t-caption" style="background: #362507; border-color: var(--accent); color: var(--accent);">MODEL RULE</span>
            <span class="t-caption" style="color: #DCEAFF;">A character witnessing an event does not automatically know every claim in it. ACQUIRED + ABOUT records exactly what becomes known and when.</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== SLIDE 3: SPRINT 2 (BARRIER VS SOLUTION) ==================== -->
    <section class="screen" data-screen="3" data-time="70"
      data-notes="In Sprint 2, our biggest challenge was tool integration and LLM hallucination. When we initially asked a single monolithic LLM prompt to extract everything from a 6,000-word chapter, it had a 42% failure rate: hallucinated relationships, dropped characters, and hit context limits with zero error tracing. We overcame this by building a modular, multi-step LangGraph pipeline. Each node has one isolated responsibility: character discovery, Pydantic validation, delta relationship extraction, and scene mapping. With LangSmith tracing, whenever an extraction errs, our system catches it, inspects the error trace, self-corrects, and commits clean data to Neo4j.">
      
      <h1 class="screen-title t-title">Sprint 2</h1>
      <div class="prompt-banner">
        <span class="prompt-label t-caption mono">PROMPT:</span>
        <span class="t-caption">What was a challenge you faced, or a barrier/dependency? How did you overcome it?</span>
      </div>
      <p class="answer-line t-body">Monolithic prompts hallucinated and crashed on long chapters. We overcame it with a modular, traced LangGraph pipeline.</p>

      <div class="content-box">
        <div class="sprint2-grid">
          <!-- The Barrier / Challenge -->
          <div class="barrier-card">
            <div>
              <div class="barrier-header">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" stroke-width="2.5"><path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                <span class="t-caption mono" style="font-weight: bold;">THE BARRIER · MONOLITHIC LLM CALL</span>
              </div>
              <div class="barrier-box">
                <p class="t-body" style="color: #fda4af;">Single "Do-Everything" Prompt</p>
                <p class="t-caption mono" style="color: var(--text-dim); margin-top: 6px;">Input: 6,000 words raw chapter</p>
              </div>
              <div class="barrier-fault-list">
                <div class="fault-item">
                  <span class="mono" style="color: #f43f5e; font-weight: bold;">✕</span>
                  <span class="t-caption">42% Hallucination rate on relationships</span>
                </div>
                <div class="fault-item">
                  <span class="mono" style="color: #f43f5e; font-weight: bold;">✕</span>
                  <span class="t-caption">Silent drops of secondary characters</span>
                </div>
                <div class="fault-item">
                  <span class="mono" style="color: #f43f5e; font-weight: bold;">✕</span>
                  <span class="t-caption">Context window & token limit overflow</span>
                </div>
                <div class="fault-item">
                  <span class="mono" style="color: #f43f5e; font-weight: bold;">✕</span>
                  <span class="t-caption">Zero error visibility: total pipeline crash</span>
                </div>
              </div>
            </div>
            <div style="border-top: 1.5px solid rgba(244, 63, 94, 0.4); padding-top: 16px;">
              <span class="t-caption mono" style="color: #fda4af;">RESULT: Fragile, non-deterministic, unusable</span>
            </div>
          </div>

          <!-- The Solution / Overcoming it -->
          <div class="solution-card">
            <div class="solution-header">
              <div style="display: flex; align-items: center; gap: 14px;">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#34d399" stroke-width="2.5"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                <span class="t-caption mono" style="color: var(--known); font-weight: bold;">HOW WE OVERCAME IT · MODULAR LANGGRAPH + LANGSMITH</span>
              </div>
              <button type="button" class="btn-pill" id="btn-simulate-pipeline">Simulate Traced Pipeline</button>
            </div>

            <!-- Pipeline nodes track -->
            <div class="pipeline-track">
              <div class="pipeline-node success-stage" id="pipe-node-1">
                <span class="t-caption mono" style="color: var(--accent);">1. EXTRACT</span>
                <span class="t-body" style="font-size: 20px;">Characters</span>
                <span class="t-caption mono" style="color: var(--text-dim); font-size: 14px;">Roster delta</span>
              </div>
              <span class="pipeline-arrow">➔</span>

              <div class="pipeline-node" id="pipe-node-2">
                <span class="t-caption mono" style="color: var(--accent);">2. VALIDATE</span>
                <span class="t-body" style="font-size: 20px;">Pydantic</span>
                <span class="t-caption mono" style="color: var(--text-dim); font-size: 14px;">Self-correcting</span>
              </div>
              <span class="pipeline-arrow">➔</span>

              <div class="pipeline-node" id="pipe-node-3">
                <span class="t-caption mono" style="color: var(--accent);">3. RELATIONS</span>
                <span class="t-body" style="font-size: 20px;">History Map</span>
                <span class="t-caption mono" style="color: var(--text-dim); font-size: 14px;">Changes-only</span>
              </div>
              <span class="pipeline-arrow">➔</span>

              <div class="pipeline-node" id="pipe-node-4">
                <span class="t-caption mono" style="color: var(--accent);">4. SCENE</span>
                <span class="t-body" style="font-size: 20px;">Locations</span>
                <span class="t-caption mono" style="color: var(--text-dim); font-size: 14px;">Paragraph refs</span>
              </div>
              <span class="pipeline-arrow">➔</span>

              <div class="pipeline-node" id="pipe-node-5">
                <span class="t-caption mono" style="color: var(--accent);">5. NEO4J</span>
                <span class="t-body" style="font-size: 20px;">Graph Write</span>
                <span class="t-caption mono" style="color: var(--text-dim); font-size: 14px;">Atomic commit</span>
              </div>
            </div>

            <!-- LangSmith Console Simulation -->
            <div class="trace-console-box" id="trace-console">
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <span class="mono" style="color: var(--accent);">[LANGSMITH AUDIT TRACE #1094]</span>
                <span class="mono" style="color: var(--text-dim);">Latency: 412ms · Tokens: 1,280</span>
              </div>
              <div id="trace-text-live" class="mono" style="color: #6ee7b7;">
                ✓ Chapter partitioned into validated units -> Character extractor emitted 4 candidates -> Pydantic validator verified schemas -> Zero unhandled exceptions.
              </div>
            </div>

            <!-- Metrics -->
            <div class="metric-ribbon">
              <div class="metric-item">
                <span class="t-caption mono" style="color: var(--text-dim); font-size: 18px;">Reliability Rate</span>
                <span class="t-body" style="color: var(--known); font-size: 26px;">100% Deterministic</span>
              </div>
              <div class="metric-item" style="border-left: 1px solid var(--border-bright); border-right: 1px solid var(--border-bright);">
                <span class="t-caption mono" style="color: var(--text-dim); font-size: 18px;">Hallucination Leaks</span>
                <span class="t-body" style="color: var(--known); font-size: 26px;">&lt; 0.5%</span>
              </div>
              <div class="metric-item">
                <span class="t-caption mono" style="color: var(--text-dim); font-size: 18px;">Traceability</span>
                <span class="t-body" style="color: var(--accent); font-size: 26px;">Full LangSmith Logs</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== SLIDE 4: SPRINT 3 (TWIST DIVERSION) ==================== -->
    <section class="screen" data-screen="4" data-time="55"
      data-notes="In Sprint 3, something surprising happened that forced a major architectural diversion. When extracting sequential chapters, we found that stories hide true character identities until the climax. In Harry Potter, chapters 1 to 16 make everyone believe Snape is stealing the Stone. Only in chapter 17 is Quirrell revealed as the host to Voldemort! If we extract sequentially, the model locks in false beliefs as permanent graph truths. We diverted to a Two-Pass Architecture: Pass 1 reads the whole book first to build a global WHO IS WHO ground truth; Pass 2 then extracts subjective POV timelines knowing who is who, but faithfully recording what the character believed at each moment.">
      
      <h1 class="screen-title t-title">Sprint 3</h1>
      <div class="prompt-banner">
        <span class="prompt-label t-caption mono">PROMPT:</span>
        <span class="t-caption">What's a diversion you took, or something surprising that happened during the process?</span>
      </div>
      <p class="answer-line t-body">End-of-book twists locked in false facts. We diverted to a two-pass memory architecture.</p>

      <div class="content-box">
        <div class="sprint3-grid">
          <!-- Top process banner -->
          <div class="sprint3-top-strip">
            <div class="pass-pills-row">
              <span class="pass-pill active mono">PASS 1: Whole-Book Reading (WHO IS WHO)</span>
              <span style="color: var(--border-bright);">➔</span>
              <span class="pass-pill active mono">PASS 2: Timeline-Grounded POV Extraction</span>
            </div>
            <div style="display: flex; gap: 12px;">
              <button type="button" class="btn-pill active" id="btn-chapter-16">Chapter 16: Trapdoor</button>
              <button type="button" class="btn-pill" id="btn-chapter-17">Chapter 17: Mirror Room</button>
            </div>
          </div>

          <!-- Panel A: Pass 1 Omniscient Ground Truth -->
          <div class="twist-panel omniscient">
            <div>
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
                <span class="t-caption mono" style="color: #38bdf8; font-weight: bold;">PASS 1 · GLOBAL MEMORY (WHO IS WHO)</span>
                <span class="hud-badge mono t-caption" style="background: #082f49; border-color: #38bdf8; color: #38bdf8;">GROUND TRUTH</span>
              </div>
              <p class="t-body" style="margin-bottom: 16px;">Omniscient Entities Established Across Book</p>
              
              <div style="display: flex; flex-direction: column; gap: 16px;">
                <div class="belief-gem-card" style="border-color: #38bdf8;">
                  <div class="portrait-circle xs house-neutral"><img src="assets/characters/quirrell.webp" alt="Quirrell"></div>
                  <div>
                    <span class="t-body" style="font-size: 22px;">Professor Quirrell</span>
                    <p class="t-caption mono" style="color: #7dd3fc;">Host to Lord Voldemort · Seeking the Stone</p>
                  </div>
                </div>

                <div class="belief-gem-card" style="border-color: #38bdf8;">
                  <div class="portrait-circle xs house-slytherin"><img src="assets/characters/snape.webp" alt="Snape"></div>
                  <div>
                    <span class="t-body" style="font-size: 22px;">Severus Snape</span>
                    <p class="t-caption mono" style="color: #7dd3fc;">Defending Harry · Counter-cursing Quirrell</p>
                  </div>
                </div>
              </div>
            </div>

            <div style="padding-top: 16px; border-top: 1.5px solid rgba(56, 189, 248, 0.3);">
              <span class="t-caption mono" style="color: #7dd3fc;">Prevents hallucinations by fixing global character identities first.</span>
            </div>
          </div>

          <!-- Panel B: Pass 2 Subjective Knowledge Horizon -->
          <div class="twist-panel subjective">
            <div>
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
                <span class="t-caption mono" style="color: var(--accent); font-weight: bold;">PASS 2 · SUBJECTIVE POV HORIZON</span>
                <span class="hud-badge mono t-caption" id="pov-time-badge">TIMELINE: CH 16</span>
              </div>
              <p class="t-body" style="margin-bottom: 16px;" id="pov-title-state">Harry's Beliefs Down the Trapdoor</p>

              <!-- Dynamic cards reflecting the twist -->
              <div id="twist-dynamic-cards" style="display: flex; flex-direction: column; gap: 16px;">
                <!-- Belief card -->
                <div class="belief-gem-card false-gem" id="belief-card-1">
                  <div class="portrait-circle xs house-slytherin"><img src="assets/characters/snape.webp" alt="Snape"></div>
                  <div>
                    <span class="t-body" id="belief-text-1" style="font-size: 22px;">"Snape is trying to steal the Stone"</span>
                    <p class="t-caption mono" id="belief-sub-1" style="color: #fda4af;">Subjective False Belief · Witnessed muttering</p>
                  </div>
                </div>

                <!-- Unknown card -->
                <div class="belief-gem-card" id="belief-card-2" style="border-style: dashed; border-color: var(--border-bright);">
                  <div class="portrait-circle xs house-neutral" id="belief-p2"><img src="assets/characters/quirrell.webp" alt="Quirrell"></div>
                  <div>
                    <span class="t-body" id="belief-text-2" style="font-size: 22px; color: var(--text-dim);">Quirrell's True Allegiance</span>
                    <p class="t-caption mono" id="belief-sub-2" style="color: var(--text-dim);">Epistemic Horizon: Hidden under the turban</p>
                  </div>
                </div>
              </div>
            </div>

            <div style="padding-top: 16px; border-top: 1.5px solid rgba(251, 191, 36, 0.3);">
              <span class="t-caption mono" id="twist-takeaway-text" style="color: var(--accent);">Two-pass memory captures the authentic journey without corrupting the graph.</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== SLIDE 5: WHAT'S NEXT FOR ME ==================== -->
    <section class="screen" data-screen="5" data-time="45"
      data-notes="Looking ahead to what's next for me: having proven the POV Knowledge Graph and the Two-Pass architecture, my next milestones are scaling ingestion across full multi-volume book series, and building an autonomous Generative POV engine that writes complete literary chapters grounded in any character's subgraph. The core takeaway from this project is simple yet profound: true intelligence isn't knowing everything — it's modeling what each person knows, and what they don't. Feel free to replay any sprint with different characters!">
      
      <h1 class="screen-title t-title">What's Next for Me</h1>
      <div class="prompt-banner">
        <span class="prompt-label t-caption mono">PROMPT:</span>
        <span class="t-caption">Where are you taking this project from here? What did this experience teach you?</span>
      </div>

      <div class="content-box">
        <div class="sprint5-container">
          <!-- Lesson Takeaway Banner -->
          <div class="takeaway-banner">
            <div>
              <span class="t-body" style="color: var(--accent);">Takeaway: "Model what characters know, not just where they were."</span>
              <p class="t-caption" style="color: var(--text-muted); margin-top: 6px;">Grounding generative models in epistemic subgraphs eliminates omniscience bias.</p>
            </div>
          </div>

          <!-- 3 Horizon Cards -->
          <div class="horizons-track">
            <!-- Horizon 1 -->
            <div class="horizon-card done">
              <div>
                <span class="t-caption mono" style="color: var(--known);">MILESTONE 1 · COMPLETE</span>
                <p class="t-body" style="margin-top: 10px;">POV Graph & Modular Pipeline</p>
                <p class="t-caption" style="color: var(--text-muted); margin-top: 8px;">Neo4j epistemic schema, LangGraph changes-only extraction, and LangSmith audit tracing.</p>
              </div>
              <div style="background: rgba(52, 211, 153, 0.15); border: 1.5px solid var(--known); border-radius: 12px; padding: 8px 16px; text-align: center;">
                <span class="t-caption mono" style="color: var(--known);">100% Verified</span>
              </div>
            </div>

            <!-- Horizon 2 -->
            <div class="horizon-card active">
              <div>
                <span class="t-caption mono" style="color: var(--accent);">MILESTONE 2 · IN PROGRESS</span>
                <p class="t-body" style="margin-top: 10px;">Full-Series Ingestion</p>
                <p class="t-caption" style="color: var(--text-muted); margin-top: 8px;">Scaling from single chapters to full 7-volume sagas with cross-book identity and memory continuity.</p>
              </div>
              <div style="background: rgba(251, 191, 36, 0.15); border: 1.5px solid var(--accent); border-radius: 12px; padding: 8px 16px; text-align: center;">
                <span class="t-caption mono" style="color: var(--accent);">70% Active Testing</span>
              </div>
            </div>

            <!-- Horizon 3 -->
            <div class="horizon-card future">
              <div>
                <span class="t-caption mono" style="color: var(--text-dim);">MILESTONE 3 · UP NEXT</span>
                <p class="t-body" style="margin-top: 10px;">Autonomous POV Reteller</p>
                <p class="t-caption" style="color: var(--text-muted); margin-top: 8px;">Generative LLM agents conditioned directly on character subgraphs to write original narrative prose in any persona.</p>
              </div>
              <div style="background: rgba(148, 163, 184, 0.1); border: 1.5px dashed var(--border-bright); border-radius: 12px; padding: 8px 16px; text-align: center;">
                <span class="t-caption mono" style="color: var(--text-dim);">Next Horizon</span>
              </div>
            </div>
          </div>

          <!-- Replay Roster -->
          <div class="replay-roster-row">
            <div>
              <span class="t-body" style="font-size: 24px;">Replay Presentation with Another POV Lens:</span>
            </div>
            <div class="replay-btns-group">
              <button type="button" class="replay-btn" data-replay="harry">
                <span class="portrait-circle xs house-gryffindor"><img src="assets/characters/harry.webp" alt="Harry"></span>
                <span class="t-caption mono">Harry</span>
              </button>
              <button type="button" class="replay-btn" data-replay="hermione">
                <span class="portrait-circle xs house-gryffindor"><img src="assets/characters/hermione.webp" alt="Hermione"></span>
                <span class="t-caption mono">Hermione</span>
              </button>
              <button type="button" class="replay-btn" data-replay="ron">
                <span class="portrait-circle xs house-gryffindor"><img src="assets/characters/ron.webp" alt="Ron"></span>
                <span class="t-caption mono">Ron</span>
              </button>
              <button type="button" class="replay-btn" data-replay="quirrell">
                <span class="portrait-circle xs house-neutral"><img src="assets/characters/quirrell.webp" alt="Quirrell"></span>
                <span class="t-caption mono">Quirrell</span>
              </button>
              <button type="button" class="replay-btn" data-replay="snape">
                <span class="portrait-circle xs house-slytherin"><img src="assets/characters/snape.webp" alt="Snape"></span>
                <span class="t-caption mono">Snape</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Speaker Notes Popup Drawer -->
    <div id="notes-drawer">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
        <span class="t-caption mono" style="color: var(--accent);">SPEAKER NOTES · PRESENTER ASSISTANT</span>
        <span class="t-caption mono" id="notes-time-budget" style="color: var(--text-dim);">Time: 45s</span>
      </div>
      <p id="notes-content" class="t-caption" style="line-height: 1.5; color: #f8fafc;"></p>
    </div>

    <!-- HUD Footer -->
    <footer id="hud-footer">
      <div class="hud-left">
        <div class="hud-xp-wrap">
          <span class="t-caption mono" style="color: var(--accent);">PROGRESS</span>
          <div class="hud-xp-bar"><div id="hud-xp-fill"></div></div>
        </div>
        <button type="button" class="hud-btn t-caption mono" id="btn-toggle-notes">Notes [N]</button>
      </div>

      <div style="display: flex; align-items: center; gap: 24px;">
        <button type="button" class="hud-btn t-caption mono" id="btn-prev-slide">◀ Prev</button>
        <span class="t-body mono" id="hud-counter" style="color: var(--accent); font-size: 26px;">1 / 5</span>
        <button type="button" class="hud-btn t-caption mono" id="btn-next-slide">Next ▶</button>
      </div>
    </footer>
  </main>
</div>

<!-- Local GSAP 3.12.5 -->
<script src="assets/vendor/gsap.min.js"></script>
<script>
(() => {
  "use strict";

  // State Management
  const state = {
    screen: 1,
    narrator: "harry",
    isStoryLabels: false,
    notesOpen: false,
    reducedMotion: window.matchMedia("(prefers-reduced-motion: reduce)").matches
  };

  const NARRATORS = {
    harry: { name: "Harry Potter", house: "house-gryffindor", file: "harry.webp" },
    hermione: { name: "Hermione Granger", house: "house-gryffindor", file: "hermione.webp" },
    ron: { name: "Ron Weasley", house: "house-gryffindor", file: "ron.webp" },
    quirrell: { name: "Professor Quirrell", house: "house-neutral", file: "quirrell.webp" },
    snape: { name: "Severus Snape", house: "house-slytherin", file: "snape.webp" }
  };

  // Starry sky background canvas
  function initStarrySky() {
    const canvas = document.getElementById("starry-sky");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const stars = [];
    for (let i = 0; i < 90; i++) {
      stars.push({
        x: Math.random() * 1920,
        y: Math.random() * 1080,
        r: Math.random() * 1.8 + 0.6,
        alpha: Math.random() * 0.7 + 0.3,
        delta: (Math.random() * 0.02 + 0.005) * (Math.random() < 0.5 ? 1 : -1)
      });
    }

    function draw() {
      ctx.clearRect(0, 0, 1920, 1080);
      for (const s of stars) {
        s.alpha += s.delta;
        if (s.alpha > 0.95 || s.alpha < 0.25) s.delta = -s.delta;
        ctx.fillStyle = `rgba(255, 255, 255, ${s.alpha.toFixed(2)})`;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fill();
      }
      if (!state.reducedMotion) {
        requestAnimationFrame(draw);
      }
    }
    draw();
  }

  // Update HUD
  function updateHud() {
    const hudNarrator = document.getElementById("hud-narrator");
    const hudCounter = document.getElementById("hud-counter");
    const hudXpFill = document.getElementById("hud-xp-fill");

    if (hudCounter) {
      hudCounter.textContent = `${state.screen} / 5`;
    }
    if (hudXpFill) {
      hudXpFill.style.width = `${(state.screen / 5) * 100}%`;
    }

    if (hudNarrator) {
      if (state.screen === 1) {
        hudNarrator.style.display = "none";
      } else {
        hudNarrator.style.display = "flex";
        const nar = NARRATORS[state.narrator];
        const portraitImg = document.getElementById("hud-portrait-img");
        const portraitBox = document.getElementById("hud-portrait");
        const hudName = document.getElementById("hud-name");

        if (portraitImg) portraitImg.src = `assets/characters/${nar.file}`;
        if (portraitBox) portraitBox.className = `portrait-circle xs ${nar.house}`;
        if (hudName) hudName.textContent = nar.name;
      }
    }

    // Update Speaker Notes Drawer content
    const currentScreenEl = document.querySelector(`.screen[data-screen="${state.screen}"]`);
    if (currentScreenEl) {
      const notesContent = document.getElementById("notes-content");
      const timeBudget = document.getElementById("notes-time-budget");
      if (notesContent) notesContent.textContent = currentScreenEl.dataset.notes || "";
      if (timeBudget) timeBudget.textContent = `Time: ${currentScreenEl.dataset.time || "60"}s`;
    }
  }

  // Select Narrator
  function selectNarrator(narKey, jumpToSlide2 = false) {
    if (!NARRATORS[narKey]) return;
    state.narrator = narKey;

    document.querySelectorAll(".character-slot").forEach(slot => {
      const isMatch = slot.dataset.character === narKey;
      slot.classList.toggle("selected", isMatch);
    });

    if (jumpToSlide2) {
      setTimeout(() => {
        state.screen = 2;
        render();
      }, 350);
    } else {
      render();
    }
  }

  // Slide 2: Draw.io Graph Animations
  function initSlide2Animations() {
    const btnToggle = document.getElementById("btn-toggle-labels");
    const btnReplay = document.getElementById("btn-replay-graph");

    function updateLabelMode() {
      const nodeA = document.querySelector("#node-char-a text:nth-of-type(2)");
      const nodeB = document.querySelector("#node-char-b text:nth-of-type(2)");
      const nodeEvent = document.querySelector("#node-event text:nth-of-type(2)");
      const nodeLoc = document.querySelector("#node-location text:nth-of-type(2)");
      const nodeClaim = document.querySelector("#node-claim text:nth-of-type(2)");

      if (state.isStoryLabels) {
        if (nodeA) nodeA.textContent = "Harry (POV)";
        if (nodeB) nodeB.textContent = "Quirrell";
        if (nodeEvent) nodeEvent.textContent = "Quidditch match";
        if (nodeLoc) nodeLoc.textContent = "Quidditch pitch";
        if (nodeClaim) nodeClaim.textContent = "Snape protecting";
        if (btnToggle) btnToggle.classList.add("active");
      } else {
        if (nodeA) nodeA.textContent = "A · POV";
        if (nodeB) nodeB.textContent = "B";
        if (nodeEvent) nodeEvent.textContent = "type · summary";
        if (nodeLoc) nodeLoc.textContent = "name · kind";
        if (nodeClaim) nodeClaim.textContent = "statement";
        if (btnToggle) btnToggle.classList.remove("active");
      }
    }

    if (btnToggle) {
      btnToggle.onclick = () => {
        state.isStoryLabels = !state.isStoryLabels;
        updateLabelMode();
      };
    }

    function playGraphBuildAnimation() {
      if (typeof gsap === "undefined" || state.reducedMotion) return;

      const nodes = [
        "#node-char-a", "#node-char-b", "#node-event", "#node-location",
        "#node-utterance", "#node-claim", "#node-knowledge"
      ];

      gsap.fromTo(nodes, 
        { scale: 0.88, opacity: 0.5 },
        { scale: 1, opacity: 1, duration: 0.45, stagger: 0.08, ease: "back.out(1.5)" }
      );
    }

    if (btnReplay) {
      btnReplay.onclick = () => {
        playGraphBuildAnimation();
      };
    }
  }

  // Slide 3: Pipeline simulation
  function initSlide3Simulation() {
    const btnSim = document.getElementById("btn-simulate-pipeline");
    const consoleText = document.getElementById("trace-text-live");
    if (!btnSim) return;

    btnSim.onclick = () => {
      const pNodes = [
        document.getElementById("pipe-node-1"),
        document.getElementById("pipe-node-2"),
        document.getElementById("pipe-node-3"),
        document.getElementById("pipe-node-4"),
        document.getElementById("pipe-node-5")
      ];

      pNodes.forEach(n => {
        n.className = "pipeline-node";
      });

      // Step 1: Extract Characters
      pNodes[0].classList.add("active-stage");
      if (consoleText) consoleText.textContent = "▶ Step 1: Extracting character roster changes for Chapter 16... Found 4 active entities.";

      setTimeout(() => {
        pNodes[0].className = "pipeline-node success-stage";
        pNodes[1].classList.add("error-stage");
        if (consoleText) {
          consoleText.innerHTML = "<span style='color:#f43f5e;'>⚠ [LangSmith Trace #1094] Schema Mismatch: Missing alias 'The Defense Teacher'. Intercepting with self-correcting retry prompt...</span>";
        }

        setTimeout(() => {
          pNodes[1].className = "pipeline-node success-stage";
          pNodes[2].classList.add("active-stage");
          if (consoleText) {
            consoleText.innerHTML = "<span style='color:#34d399;'>✓ Recovery Successful: Pydantic schema validated.</span> Extracting relationships with temporal history...";
          }

          setTimeout(() => {
            pNodes[2].className = "pipeline-node success-stage";
            pNodes[3].classList.add("active-stage");
            if (consoleText) consoleText.textContent = "▶ Step 4: Resolving location 'Underground chambers' with paragraph references [p12..p48]...";

            setTimeout(() => {
              pNodes[3].className = "pipeline-node success-stage";
              pNodes[4].classList.add("success-stage");
              if (consoleText) {
                consoleText.innerHTML = "<span style='color:#34d399;'>★ Transaction committed to Neo4j. Zero hallucination leakage. Run verified!</span>";
              }
            }, 500);
          }, 500);
        }, 700);
      }, 500);
    };
  }

  // Slide 4: Twist Demonstration
  function initSlide4Twist() {
    const btnCh16 = document.getElementById("btn-chapter-16");
    const btnCh17 = document.getElementById("btn-chapter-17");
    const povTimeBadge = document.getElementById("pov-time-badge");
    const povTitleState = document.getElementById("pov-title-state");
    const card1 = document.getElementById("belief-card-1");
    const text1 = document.getElementById("belief-text-1");
    const sub1 = document.getElementById("belief-sub-1");
    const card2 = document.getElementById("belief-card-2");
    const text2 = document.getElementById("belief-text-2");
    const sub2 = document.getElementById("belief-sub-2");
    const takeawayText = document.getElementById("twist-takeaway-text");

    if (!btnCh16 || !btnCh17) return;

    btnCh16.onclick = () => {
      btnCh16.classList.add("active");
      btnCh17.classList.remove("active");
      if (povTimeBadge) povTimeBadge.textContent = "TIMELINE: CH 16";
      if (povTitleState) povTitleState.textContent = "Harry's Beliefs Down the Trapdoor";

      if (card1) card1.className = "belief-gem-card false-gem";
      if (text1) {
        text1.className = "t-body";
        text1.textContent = '"Snape is trying to steal the Stone"';
      }
      if (sub1) sub1.textContent = "Subjective False Belief · Witnessed muttering";

      if (card2) card2.className = "belief-gem-card";
      if (text2) {
        text2.textContent = "Quirrell's True Allegiance";
        text2.style.color = "var(--text-dim)";
      }
      if (sub2) sub2.textContent = "Epistemic Horizon: Hidden under the turban";
      if (takeawayText) takeawayText.textContent = "Two-pass memory captures the authentic journey without corrupting the graph.";
    };

    btnCh17.onclick = () => {
      btnCh17.classList.add("active");
      btnCh16.classList.remove("active");
      if (povTimeBadge) povTimeBadge.textContent = "TIMELINE: CH 17";
      if (povTitleState) povTitleState.textContent = "The Mirror Room Revelation";

      if (card1) card1.className = "belief-gem-card false-gem";
      if (text1) {
        text1.className = "t-body strike-text";
        text1.textContent = '"Snape is trying to steal the Stone"';
      }
      if (sub1) sub1.textContent = "Shattered Suspicion · Snape was protecting Harry!";

      if (card2) card2.className = "belief-gem-card true-gem";
      if (text2) {
        text2.textContent = '"It was Quirrell! Voldemort shares his body!"';
        text2.style.color = "#34d399";
      }
      if (sub2) sub2.textContent = "Verified Knowledge Acquisition · The Turban Unwrapped";
      if (takeawayText) takeawayText.textContent = "Without Pass 1, twists corrupt the graph permanently. With Two-Pass memory, epistemic shifts are mathematically exact.";

      if (typeof gsap !== "undefined" && !state.reducedMotion) {
        gsap.fromTo("#belief-card-2", 
          { scale: 0.94, y: 8 },
          { scale: 1, y: 0, duration: 0.35, ease: "back.out(2)" }
        );
      }
    };
  }

  // Master Render
  function render() {
    document.querySelectorAll(".screen").forEach(s => {
      const sNum = parseInt(s.dataset.screen || "1", 10);
      s.classList.toggle("active", sNum === state.screen);
    });

    updateHud();

    if (state.screen === 2) {
      initSlide2Animations();
    } else if (state.screen === 3) {
      initSlide3Simulation();
    } else if (state.screen === 4) {
      initSlide4Twist();
    }
  }

  // Navigation handlers
  function nextSlide() {
    if (state.screen < 5) {
      state.screen++;
      render();
    }
  }

  function prevSlide() {
    if (state.screen > 1) {
      state.screen--;
      render();
    }
  }

  // Setup character selection click handlers
  function initCharacterRoster() {
    document.querySelectorAll(".character-slot").forEach(slot => {
      slot.addEventListener("click", () => {
        const c = slot.dataset.character;
        selectNarrator(c, true);
      });
      slot.addEventListener("keydown", e => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          const c = slot.dataset.character;
          selectNarrator(c, true);
        }
      });
    });

    document.querySelectorAll(".replay-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const nar = btn.dataset.replay;
        selectNarrator(nar);
        state.screen = 2;
        render();
      });
    });
  }

  // Keyboard navigation
  window.addEventListener("keydown", e => {
    if (e.key === "1") {
      state.screen = 1;
      render();
    } else if (e.key === "2") {
      state.screen = 2;
      render();
    } else if (e.key === "3") {
      state.screen = 3;
      render();
    } else if (e.key === "4") {
      state.screen = 4;
      render();
    } else if (e.key === "5") {
      state.screen = 5;
      render();
    } else if (e.key === "ArrowRight" || e.key === "PageDown" || e.key === " ") {
      e.preventDefault();
      nextSlide();
    } else if (e.key === "ArrowLeft" || e.key === "PageUp" || e.key === "Backspace") {
      e.preventDefault();
      prevSlide();
    } else if (e.key === "n" || e.key === "N") {
      const drawer = document.getElementById("notes-drawer");
      state.notesOpen = !state.notesOpen;
      if (drawer) drawer.classList.toggle("open", state.notesOpen);
    }
  });

  // Responsive stage scaling
  function resizeStage() {
    const stage = document.getElementById("stage");
    if (!stage) return;
    const sw = window.innerWidth / 1920;
    const sh = window.innerHeight / 1080;
    const scale = Math.min(sw, sh);
    stage.style.transform = `scale(${scale})`;
  }
  window.addEventListener("resize", resizeStage);

  // Initialize
  document.addEventListener("DOMContentLoaded", () => {
    resizeStage();
    initStarrySky();
    initCharacterRoster();

    const btnNext = document.getElementById("btn-next-slide");
    const btnPrev = document.getElementById("btn-prev-slide");
    const btnNotes = document.getElementById("btn-toggle-notes");

    if (btnNext) btnNext.addEventListener("click", nextSlide);
    if (btnPrev) btnPrev.addEventListener("click", prevSlide);
    if (btnNotes) {
      btnNotes.addEventListener("click", () => {
        const drawer = document.getElementById("notes-drawer");
        state.notesOpen = !state.notesOpen;
        if (drawer) drawer.classList.toggle("open", state.notesOpen);
      });
    }

    render();
  });
})();
</script>
</body>
</html>
'''

with open("doc/presentation/pov-graph-slides.html", "w", encoding="utf-8") as f:
    f.write(HTML_CONTENT)

print("Successfully rebuilt and cleaned up pov-graph-slides.html!")
