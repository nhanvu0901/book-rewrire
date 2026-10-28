import os

HTML_CONTENT = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Epistemic POV Graph — ShiftKey Academy Build It! Machine Learning</title>
  <style>
    /* ==================== DESIGN TOKENS & RESET ==================== */
    :root {
      --bg-space: #070c14;
      --bg-card: rgba(13, 24, 43, 0.92);
      --bg-card-hover: rgba(22, 38, 68, 0.95);
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --border-bright: #38bdf8;
      --border-muted: #1e3a5f;
      --accent: #facc15;
      --accent-glow: rgba(250, 204, 21, 0.35);
      --danger: #f43f5e;
      --danger-bg: rgba(244, 63, 94, 0.12);
      --danger-border: rgba(244, 63, 94, 0.4);
      --success: #34d399;
      --success-bg: rgba(52, 211, 153, 0.12);
      --success-border: rgba(52, 211, 153, 0.4);
      --purple: #c084fc;
      --purple-bg: rgba(192, 132, 252, 0.12);
      --purple-border: rgba(192, 132, 252, 0.4);
      --font-display: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
      --font-mono: "SF Mono", "Fira Code", Menlo, Monaco, Consolas, monospace;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--bg-space);
      color: var(--text-main);
      font-family: var(--font-display);
      overflow: hidden;
      width: 100vw;
      height: 100vh;
      user-select: none;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      position: relative;
    }

    /* Ambient Space Dust */
    body::before {
      content: "";
      position: absolute;
      inset: 0;
      background-image: 
        radial-gradient(1.5px 1.5px at 15% 20%, rgba(255, 255, 255, 0.45), transparent),
        radial-gradient(1.5px 1.5px at 70% 15%, rgba(56, 189, 248, 0.4), transparent),
        radial-gradient(2px 2px at 40% 75%, rgba(250, 204, 21, 0.3), transparent),
        radial-gradient(1px 1px at 85% 80%, rgba(255, 255, 255, 0.4), transparent),
        radial-gradient(1.5px 1.5px at 25% 60%, rgba(192, 132, 252, 0.35), transparent);
      background-size: 800px 800px;
      pointer-events: none;
      z-index: 0;
    }

    /* Typography Hierarchy */
    .t-title {
      font-size: 48px;
      font-weight: 900;
      letter-spacing: -1px;
      line-height: 1.1;
      color: var(--text-main);
    }

    .t-subtitle {
      font-size: 24px;
      font-weight: 500;
      color: var(--text-muted);
      line-height: 1.4;
    }

    .t-body {
      font-size: 20px;
      line-height: 1.5;
      color: var(--text-main);
    }

    .t-caption {
      font-size: 15px;
      line-height: 1.4;
      color: var(--text-muted);
    }

    .mono {
      font-family: var(--font-mono);
    }

    /* Slide Container */
    .screen {
      position: absolute;
      inset: 0;
      padding: 40px 60px 85px 60px;
      display: none;
      flex-direction: column;
      z-index: 1;
      opacity: 0;
      transition: opacity 0.3s ease;
    }

    .screen.active {
      display: flex;
      opacity: 1;
    }

    /* Top HUD Bar */
    .top-hud {
      position: absolute;
      top: 24px;
      right: 60px;
      display: flex;
      align-items: center;
      gap: 16px;
      z-index: 100;
    }

    .hud-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      border-radius: 999px;
      background: rgba(13, 24, 43, 0.85);
      border: 1px solid var(--border-muted);
      font-size: 13px;
      font-weight: 600;
      color: var(--text-muted);
      backdrop-filter: blur(8px);
    }

    .hud-badge.accent {
      border-color: var(--accent);
      color: var(--accent);
      box-shadow: 0 0 12px var(--accent-glow);
    }

    .hud-lens-avatar {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      object-fit: cover;
      border: 1.5px solid var(--accent);
    }

    /* Bottom HUD Bar */
    .bottom-hud {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 70px;
      padding: 0 60px;
      background: rgba(7, 12, 20, 0.95);
      border-top: 1px solid var(--border-muted);
      display: flex;
      align-items: center;
      justify-content: space-between;
      z-index: 100;
      backdrop-filter: blur(12px);
    }

    .progress-bar-container {
      display: flex;
      align-items: center;
      gap: 16px;
      flex: 1;
      max-width: 480px;
    }

    .progress-track {
      flex: 1;
      height: 6px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 3px;
      overflow: hidden;
    }

    .progress-fill {
      height: 100%;
      width: 12.5%;
      background: linear-gradient(90deg, #38bdf8, var(--accent));
      transition: width 0.3s ease;
      box-shadow: 0 0 10px var(--accent-glow);
    }

    .hud-nav-buttons {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .btn-nav {
      padding: 8px 18px;
      border-radius: 8px;
      background: rgba(19, 31, 56, 0.8);
      border: 1px solid var(--border-muted);
      color: var(--text-main);
      cursor: pointer;
      font-size: 14px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s;
    }

    .btn-nav:hover:not(:disabled) {
      border-color: var(--border-bright);
      background: rgba(30, 58, 95, 0.9);
      color: #fff;
      box-shadow: 0 0 12px rgba(56, 189, 248, 0.3);
    }

    .btn-nav:disabled {
      opacity: 0.35;
      cursor: not-allowed;
    }

    /* Common Slide Elements */
    .prompt-banner {
      display: inline-flex;
      align-items: center;
      gap: 12px;
      padding: 6px 16px;
      background: rgba(250, 204, 21, 0.08);
      border: 1px solid rgba(250, 204, 21, 0.3);
      border-radius: 8px;
      margin-top: 10px;
      margin-bottom: 8px;
      width: fit-content;
    }

    .prompt-label {
      color: var(--accent);
      font-weight: 700;
      font-size: 13px;
      letter-spacing: 1px;
    }

    .answer-line {
      font-size: 26px;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 16px;
    }

    /* ==================== SLIDE 1: TITLE SLIDE ==================== */
    .title-screen-layout {
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: center;
      max-width: 1400px;
      margin: 0 auto;
      width: 100%;
    }

    .title-program-badge {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 8px 18px;
      background: rgba(56, 189, 248, 0.1);
      border: 1px solid rgba(56, 189, 248, 0.4);
      border-radius: 999px;
      color: var(--border-bright);
      font-size: 15px;
      font-weight: 700;
      letter-spacing: 0.5px;
      width: fit-content;
      margin-bottom: 24px;
    }

    .title-h1 {
      font-size: 72px;
      font-weight: 900;
      letter-spacing: -2px;
      line-height: 1.05;
      margin-bottom: 14px;
      background: linear-gradient(135deg, #ffffff 40%, var(--border-bright) 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .title-subheading {
      font-size: 32px;
      font-weight: 600;
      color: var(--accent);
      margin-bottom: 32px;
      text-shadow: 0 0 24px var(--accent-glow);
    }

    .title-hook-card {
      background: rgba(13, 24, 43, 0.85);
      border: 1.5px solid var(--border-muted);
      border-radius: 20px;
      padding: 28px 36px;
      margin-bottom: 32px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
      position: relative;
      overflow: hidden;
    }

    .title-hook-card::before {
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      width: 6px;
      height: 100%;
      background: linear-gradient(180deg, var(--border-bright), var(--accent));
    }

    .title-hook-text {
      font-size: 23px;
      line-height: 1.6;
      color: #e2e8f0;
      margin-bottom: 16px;
    }

    .title-hook-text strong {
      color: var(--accent);
      font-weight: 700;
    }

    .title-meta-grid {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-top: 16px;
      border-top: 1px solid rgba(255, 255, 255, 0.1);
    }

    .title-meta-item {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .title-meta-label {
      font-size: 13px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 1px;
    }

    .title-meta-val {
      font-size: 18px;
      font-weight: 700;
      color: #fff;
    }

    .btn-hero-start {
      display: inline-flex;
      align-items: center;
      gap: 12px;
      padding: 16px 36px;
      background: linear-gradient(135deg, #0284c7, #0369a1);
      border: 1px solid var(--border-bright);
      border-radius: 12px;
      color: #fff;
      font-size: 20px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 10px 25px rgba(2, 132, 199, 0.4);
      transition: all 0.25s;
      width: fit-content;
    }

    .btn-hero-start:hover {
      transform: translateY(-2px);
      box-shadow: 0 14px 30px rgba(2, 132, 199, 0.6), 0 0 20px rgba(56, 189, 248, 0.5);
      border-color: #fff;
    }

    
    /* ==================== SLIDE 2: MARVEL RIVALS CINEMATIC SELECTION (PARTING LINEUP) ==================== */
    .cinematic-select-stage {
      position: absolute;
      top: 110px;
      left: 96px;
      right: 96px;
      bottom: 60px;
      display: flex;
      flex-direction: column;
      z-index: 10;
    }

    .cinematic-header {
      margin-bottom: 4px;
    }

    .cinematic-title {
      font-size: 68px;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #ffffff;
      line-height: 1.1;
      text-shadow: 0 4px 24px rgba(0, 0, 0, 0.7);
    }

    .cinematic-sub {
      font-size: 22px;
      color: #94a3b8;
      margin-top: 6px;
      font-weight: 500;
    }

    /* Ambient atmospheric floating magic motes */
    .magic-motes-container {
      position: absolute;
      inset: 0;
      pointer-events: none;
      overflow: hidden;
      z-index: 1;
    }

    .magic-mote {
      position: absolute;
      width: 4px;
      height: 4px;
      border-radius: 50%;
      background: rgba(251, 191, 36, 0.6);
      box-shadow: 0 0 10px rgba(251, 191, 36, 0.8);
      animation: floatMote 8s ease-in-out infinite;
    }

    @keyframes floatMote {
      0%, 100% { transform: translateY(0) translateX(0); opacity: 0.2; }
      50% { transform: translateY(-40px) translateX(20px); opacity: 0.7; }
    }

    /* Lineup Stage Container with absolute child coordinates */
    .cinematic-lineup-area {
      position: relative;
      flex: 1;
      width: 100%;
      height: 720px;
      margin-top: 10px;
    }

    /* Ambient floor lighting */
    .stage-floor-light {
      position: absolute;
      bottom: 40px;
      left: 0;
      right: 0;
      height: 150px;
      background: radial-gradient(ellipse at 50% 100%, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.3) 50%, transparent 80%);
      pointer-events: none;
      z-index: 1;
    }

    /* Standee hero container (Positioned absolutely via GSAP coordinates) */
    .cinematic-hero {
      position: absolute;
      bottom: 30px;
      width: 260px;
      height: 640px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: flex-end;
      cursor: pointer;
      outline: none;
      z-index: 15;
      transition: opacity 0.35s ease, filter 0.35s ease;
      transform-origin: 50% 90%;
    }

    /* Ground shadow */
    .hero-ground-shadow {
      position: absolute;
      bottom: 80px;
      left: 50%;
      transform: translateX(-50%);
      width: 220px;
      height: 40px;
      border-radius: 50%;
      background: radial-gradient(ellipse at center, rgba(0, 0, 0, 0.92) 0%, rgba(0, 0, 0, 0.45) 45%, transparent 75%);
      pointer-events: none;
      z-index: 2;
      transition: transform 0.35s ease, opacity 0.35s ease;
    }

    /* Magical summoning floor ring */
    .hero-magic-ring {
      position: absolute;
      bottom: 65px;
      left: 50%;
      transform: translateX(-50%) rotateX(68deg);
      width: 250px;
      height: 250px;
      border-radius: 50%;
      border: 2px dashed var(--char-accent, #fbbf24);
      box-shadow: 0 0 28px var(--char-glow, rgba(251, 191, 36, 0.3)), inset 0 0 16px var(--char-glow, rgba(251, 191, 36, 0.2));
      opacity: 0;
      pointer-events: none;
      z-index: 3;
      transition: opacity 0.4s ease;
    }

    .cinematic-hero.is-focused .hero-magic-ring {
      opacity: 0.9;
      animation: spinMagicRing 14s linear infinite;
    }

    @keyframes spinMagicRing {
      0% { transform: translateX(-50%) rotateX(68deg) rotate(0deg); }
      100% { transform: translateX(-50%) rotateX(68deg) rotate(360deg); }
    }

    /* Ambient aura */
    .hero-ambient-aura {
      position: absolute;
      bottom: 90px;
      left: 50%;
      transform: translateX(-50%);
      width: 280px;
      height: 440px;
      border-radius: 50%;
      background: radial-gradient(ellipse at center, var(--char-glow, rgba(251, 191, 36, 0.25)) 0%, transparent 70%);
      opacity: 0;
      pointer-events: none;
      z-index: 3;
      transition: opacity 0.4s ease;
      filter: blur(14px);
    }

    .cinematic-hero.is-focused .hero-ambient-aura {
      opacity: 1;
    }

    /* Character figure wrap */
    .hero-figure-wrap {
      position: relative;
      z-index: 6;
      height: 440px;
      display: flex;
      align-items: flex-end;
      justify-content: center;
      transform-origin: 50% 95%;
      transition: transform 0.35s cubic-bezier(0.2, 0.9, 0.3, 1), filter 0.35s ease;
      pointer-events: none;
    }

    .hero-figure-wrap img {
      height: 100%;
      width: auto;
      display: block;
      filter: drop-shadow(0 14px 24px rgba(0, 0, 0, 0.75));
      pointer-events: none;
      user-select: none;
    }

    /* Focus & Hover states on standees */
    .cinematic-hero:not(.is-focused) {
      opacity: 0.32;
      filter: brightness(0.65) saturate(0.55);
    }

    .cinematic-hero.is-focused {
      opacity: 1;
      filter: none;
      z-index: 25;
    }

    .cinematic-hero.is-focused .hero-figure-wrap {
      transform: translateY(-16px) scale(1.1);
      filter: drop-shadow(0 24px 38px rgba(0, 0, 0, 0.88)) drop-shadow(0 0 24px var(--char-glow, rgba(251, 191, 36, 0.45)));
    }

    .cinematic-hero.is-focused .hero-ground-shadow {
      transform: translateX(-50%) scale(1.2);
      opacity: 0.95;
    }

    /* Minimal floating typography beneath feet (No Card / No Box) */
    .hero-label-wrap {
      position: relative;
      z-index: 8;
      margin-top: 12px;
      margin-bottom: 12px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 3px;
      pointer-events: none;
      text-align: center;
      width: 100%;
    }

    .hero-name-text {
      font-size: 24px;
      font-weight: 800;
      letter-spacing: 0.03em;
      color: #f1f5f9;
      text-transform: uppercase;
      text-shadow: 0 3px 12px rgba(0, 0, 0, 0.9);
      transition: color 0.3s ease, text-shadow 0.3s ease;
      white-space: nowrap;
    }

    .cinematic-hero.is-focused .hero-name-text {
      color: #ffffff;
      text-shadow: 0 0 18px var(--char-glow, rgba(251, 191, 36, 0.6)), 0 4px 14px rgba(0, 0, 0, 0.9);
    }

    .hero-role-text {
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.14em;
      color: var(--char-accent, #fbbf24);
      text-shadow: 0 0 10px var(--char-glow, rgba(251, 191, 36, 0.3));
      white-space: nowrap;
    }

    .hero-status-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 800;
      color: #fbbf24;
      background: rgba(251, 191, 36, 0.14);
      border: 1px solid rgba(251, 191, 36, 0.45);
      box-shadow: 0 0 12px rgba(251, 191, 36, 0.3);
      padding: 2px 10px;
      border-radius: 999px;
      margin-top: 3px;
      opacity: 0;
      transform: translateY(-4px);
      transition: opacity 0.3s ease, transform 0.3s ease;
    }

    .cinematic-hero.selected .hero-status-pill {
      opacity: 1;
      transform: translateY(0);
    }

    /* ==================== FLOATING HUD GAME OVERLAY PANEL ==================== */
    .floating-hud {
      position: absolute;
      top: 24px;
      width: 440px;
      background: linear-gradient(145deg, rgba(12, 19, 38, 0.96) 0%, rgba(6, 10, 22, 0.98) 100%);
      border: 1.5px solid var(--hud-border, rgba(251, 191, 36, 0.45));
      border-radius: 20px;
      padding: 22px 26px;
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.9), 0 0 38px var(--hud-glow, rgba(251, 191, 36, 0.28));
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      z-index: 40;
      pointer-events: none;
      opacity: 0;
      transition: box-shadow 0.3s ease, border-color 0.3s ease;
    }

    .hud-top-meta {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 4px;
    }

    .hud-house-badge {
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.12em;
      color: var(--hud-accent, #fbbf24);
      text-transform: uppercase;
    }

    .hud-role-badge {
      font-size: 11px;
      font-weight: 700;
      color: #94a3b8;
      letter-spacing: 0.08em;
    }

    .hud-name {
      font-size: 32px;
      font-weight: 800;
      letter-spacing: -0.01em;
      color: #ffffff;
      line-height: 1.15;
    }

    .hud-title-sub {
      font-size: 14px;
      color: var(--hud-accent, #fbbf24);
      font-weight: 700;
      margin-top: 2px;
      margin-bottom: 12px;
    }

    /* Tag badges row */
    .hud-tags-row {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      margin-bottom: 14px;
    }

    .hud-tag-pill {
      font-size: 12px;
      font-weight: 700;
      color: #e2e8f0;
      background: rgba(255, 255, 255, 0.07);
      border: 1px solid rgba(255, 255, 255, 0.15);
      padding: 4px 10px;
      border-radius: 8px;
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }

    .hud-divider {
      height: 1px;
      background: linear-gradient(90deg, var(--hud-border, rgba(251, 191, 36, 0.4)) 0%, transparent 100%);
      margin: 12px 0;
    }

    .hud-section-label {
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.14em;
      color: #94a3b8;
      margin-bottom: 8px;
    }

    /* Animated Stat Bars */
    .hud-stats-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .hud-stat-item {
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    .hud-stat-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
    }

    .hud-stat-label {
      color: #cbd5e1;
      font-weight: 600;
    }

    .hud-stat-val {
      font-family: var(--font-mono);
      font-weight: 800;
      color: var(--hud-accent, #fbbf24);
    }

    .hud-bar-track {
      height: 6px;
      width: 100%;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 999px;
      overflow: hidden;
      position: relative;
    }

    .hud-bar-fill {
      height: 100%;
      width: 0%;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--hud-accent, #fbbf24) 0%, #ffffff 100%);
      box-shadow: 0 0 10px var(--hud-glow, rgba(251, 191, 36, 0.5));
      transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
    }

    /* Active Belief & Quote */
    .hud-belief-box {
      background: rgba(0, 0, 0, 0.35);
      border-left: 3px solid var(--hud-accent, #fbbf24);
      padding: 8px 12px;
      border-radius: 0 8px 8px 0;
      margin-bottom: 8px;
    }

    .hud-belief-title {
      font-size: 10px;
      font-weight: 800;
      letter-spacing: 0.12em;
      color: var(--hud-accent, #fbbf24);
      margin-bottom: 3px;
    }

    .hud-belief-text {
      font-size: 12px;
      color: #e2e8f0;
      line-height: 1.35;
    }

    .hud-quote-text {
      font-size: 12px;
      font-style: italic;
      color: #94a3b8;
      line-height: 1.4;
      margin-top: 6px;
    }

    .hud-footer {
      margin-top: 12px;
      padding-top: 8px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .hud-action-hint {
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.1em;
      color: var(--hud-accent, #fbbf24);
    }
/* ==================== SLIDE 3: SPRINT 1 (DRAW.IO GRAPH) ==================== */
    .drawio-stage-card {
      flex: 1;
      background: rgba(8, 16, 30, 0.96);
      border: 2px solid var(--border-muted);
      border-radius: 24px;
      position: relative;
      overflow: hidden;
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.7);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 16px 24px;
    }

    .drawio-top-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      z-index: 10;
    }

    .btn-pill {
      padding: 6px 16px;
      border-radius: 10px;
      background: rgba(19, 31, 56, 0.9);
      border: 1.5px solid var(--border-bright);
      color: var(--text-main);
      cursor: pointer;
      font-size: 15px;
      font-weight: 600;
      transition: all 0.2s;
    }

    .btn-pill:hover, .btn-pill.active {
      border-color: var(--accent);
      color: var(--accent);
      box-shadow: 0 0 14px var(--accent-glow);
    }

    .drawio-rule-banner {
      padding: 12px 24px;
      background: rgba(15, 27, 46, 0.95);
      border: 1.5px solid #334d70;
      border-radius: 14px;
      display: flex;
      align-items: center;
      gap: 20px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
      z-index: 10;
      margin-top: 8px;
    }

    /* SVG Text Styling */
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

    .graph-node {
      cursor: pointer;
      transition: transform 0.25s ease, filter 0.25s ease;
    }

    .graph-node:hover {
      filter: brightness(1.2) drop-shadow(0 0 20px var(--accent-glow));
      transform: scale(1.03);
    }

    .flowing-edge {
      stroke-dasharray: 8 6;
      animation: edgeFlow 2.5s linear infinite;
    }

    @keyframes edgeFlow {
      to {
        stroke-dashoffset: -28;
      }
    }

    /* ==================== SPRINT 2 (PART 1): THE BARRIER ==================== */
    .barrier-screen-layout {
      flex: 1;
      display: grid;
      grid-template-columns: 520px 1fr;
      gap: 40px;
      align-items: center;
    }

    .barrier-core-card {
      background: var(--danger-bg);
      border: 2px solid var(--danger-border);
      border-radius: 24px;
      padding: 36px;
      box-shadow: 0 16px 40px rgba(244, 63, 94, 0.15);
      position: relative;
    }

    .barrier-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      background: rgba(244, 63, 94, 0.2);
      border: 1px solid var(--danger);
      border-radius: 6px;
      color: #fda4af;
      font-weight: 700;
      font-size: 13px;
      margin-bottom: 20px;
    }

    .monolithic-prompt-box {
      background: rgba(8, 12, 20, 0.9);
      border: 2px dashed rgba(244, 63, 94, 0.6);
      border-radius: 16px;
      padding: 24px;
      text-align: center;
      margin-bottom: 24px;
    }

    .prompt-box-title {
      font-size: 26px;
      font-weight: 800;
      color: #fff;
      margin-bottom: 8px;
    }

    .barrier-fault-list {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .fault-card {
      background: rgba(13, 24, 43, 0.85);
      border: 1.5px solid var(--border-muted);
      border-radius: 16px;
      padding: 20px 24px;
      display: flex;
      align-items: flex-start;
      gap: 18px;
      transition: all 0.2s;
    }

    .fault-card:hover {
      border-color: var(--danger);
      transform: translateX(6px);
      box-shadow: 0 8px 24px rgba(244, 63, 94, 0.15);
    }

    .fault-icon {
      width: 44px;
      height: 44px;
      border-radius: 10px;
      background: rgba(244, 63, 94, 0.15);
      border: 1px solid var(--danger);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--danger);
      font-weight: 900;
      font-size: 20px;
      flex-shrink: 0;
    }

    .fault-title {
      font-size: 20px;
      font-weight: 800;
      color: #fff;
      margin-bottom: 6px;
    }

    .fault-desc {
      font-size: 16px;
      color: #cbd5e1;
      line-height: 1.5;
    }

    /* ==================== SPRINT 2 (PART 2): THE SOLUTION ==================== */
    .solution-screen-layout {
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 24px;
    }

    .pipeline-stage-card {
      background: rgba(10, 22, 38, 0.95);
      border: 2px solid var(--success-border);
      border-radius: 24px;
      padding: 28px 36px;
      box-shadow: 0 16px 40px rgba(52, 211, 153, 0.12);
    }

    .pipeline-bar-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 24px;
    }

    .pipeline-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr); gap: 24px;
      gap: 16px;
      position: relative;
    }

    .pipeline-step {
      background: rgba(14, 28, 48, 0.9);
      border: 1.5px solid var(--border-muted);
      border-radius: 16px;
      padding: 20px 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      position: relative;
      transition: all 0.3s;
    }

    .pipeline-step.active-pulse {
      border-color: var(--success);
      box-shadow: 0 0 24px rgba(52, 211, 153, 0.5);
      transform: translateY(-4px);
    }

    .pipeline-step-num {
      font-size: 13px;
      font-weight: 800;
      color: var(--accent);
      font-family: var(--font-mono);
      margin-bottom: 6px;
    }

    .pipeline-step-title {
      font-size: 18px;
      font-weight: 800;
      color: #fff;
      margin-bottom: 6px;
    }

    .pipeline-step-desc {
      font-size: 13px;
      color: var(--text-muted);
      font-family: var(--font-mono);
    }

    .langsmith-audit-box {
      background: rgba(6, 11, 20, 0.95);
      border: 1.5px solid #1e3a5f;
      border-radius: 16px;
      padding: 20px 28px;
      font-family: var(--font-mono);
      font-size: 14px;
      line-height: 1.6;
      color: #94a3b8;
    }

    .langsmith-header-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: var(--accent);
      font-weight: 700;
      margin-bottom: 10px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      padding-bottom: 6px;
    }

    .solution-metrics-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
    }

    .metric-card {
      background: rgba(13, 24, 43, 0.85);
      border: 1.5px solid var(--border-muted);
      border-radius: 16px;
      padding: 18px 24px;
      text-align: center;
    }

    .metric-val {
      font-size: 32px;
      font-weight: 900;
      color: var(--success);
      font-family: var(--font-mono);
      margin-bottom: 4px;
    }

    .metric-label {
      font-size: 14px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    /* ==================== SPRINT 3 (PART 1): THE SURPRISE ==================== */
    .twist-screen-layout {
      flex: 1;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 32px;
      align-items: stretch;
      min-height: 0;
    }

    .twist-side-card {
      background: rgba(13, 24, 43, 0.85);
      border-radius: 20px;
      padding: 28px 32px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      border: 2px solid var(--border-muted);
      position: relative;
    }

    .twist-side-card.red-herring {
      border-color: rgba(250, 204, 21, 0.4);
      background: rgba(250, 204, 21, 0.05);
    }

    .twist-side-card.revelation {
      border-color: var(--purple-border);
      background: var(--purple-bg);
      box-shadow: 0 16px 40px rgba(192, 132, 252, 0.12);
    }

    .twist-side-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 700;
      font-family: var(--font-mono);
      margin-bottom: 16px;
      width: fit-content;
    }

    .evidence-item-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin: 18px 0;
    }

    .evidence-pill-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 16px;
      background: rgba(8, 14, 24, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 10px;
      font-size: 15px;
    }

    /* ==================== SPRINT 3 (PART 2): THE DIVERSION ==================== */
    .diversion-screen-layout {
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 24px;
    }

    .two-pass-stage-card {
      background: rgba(10, 20, 36, 0.95);
      border: 2px solid var(--purple-border);
      border-radius: 24px;
      padding: 28px 36px;
      box-shadow: 0 16px 40px rgba(192, 132, 252, 0.15);
    }

    .two-pass-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 28px;
      margin: 20px 0;
    }

    .pass-column-card {
      background: rgba(15, 27, 48, 0.8);
      border: 1.5px solid var(--border-muted);
      border-radius: 16px;
      padding: 22px 26px;
    }

    .pass-col-header {
      font-size: 18px;
      font-weight: 800;
      color: var(--accent);
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .timeline-toggle-box {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 24px;
      background: rgba(8, 14, 26, 0.9);
      border: 1px solid var(--border-muted);
      border-radius: 14px;
    }

    .btn-timeline-choice {
      padding: 8px 20px;
      border-radius: 10px;
      background: rgba(22, 38, 68, 0.8);
      border: 1.5px solid var(--border-muted);
      color: var(--text-muted);
      cursor: pointer;
      font-size: 15px;
      font-weight: 700;
      transition: all 0.2s;
    }

    .btn-timeline-choice.active {
      border-color: var(--purple);
      color: #fff;
      background: rgba(192, 132, 252, 0.25);
      box-shadow: 0 0 16px rgba(192, 132, 252, 0.4);
    }

    /* ==================== SLIDE 8: WHAT'S NEXT FOR ME ==================== */
    .next-screen-layout {
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 24px;
    }

    .takeaway-banner {
      background: linear-gradient(135deg, rgba(250, 204, 21, 0.12), rgba(56, 189, 248, 0.08));
      border: 2px solid var(--accent);
      border-radius: 20px;
      padding: 24px 36px;
      box-shadow: 0 12px 30px var(--accent-glow);
    }

    .takeaway-quote {
      font-size: 26px;
      font-weight: 800;
      color: #fff;
      margin-bottom: 8px;
    }

    .takeaway-sub {
      font-size: 17px;
      color: #e2e8f0;
      line-height: 1.5;
    }

    .roadmap-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 24px;
    }

    .roadmap-card {
      background: rgba(13, 24, 43, 0.85);
      border: 1.5px solid var(--border-muted);
      border-radius: 18px;
      padding: 24px 28px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      position: relative;
    }

    .roadmap-card.active-lane {
      border-color: var(--border-bright);
      box-shadow: 0 12px 30px rgba(56, 189, 248, 0.15);
    }

    .roadmap-status-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 800;
      font-family: var(--font-mono);
      margin-bottom: 14px;
      width: fit-content;
    }

    .speaker-notes-drawer {
      position: absolute;
      bottom: 70px;
      left: 0;
      right: 0;
      max-height: 180px;
      background: rgba(6, 11, 20, 0.98);
      border-top: 2px solid var(--accent);
      padding: 16px 60px;
      color: #cbd5e1;
      font-size: 15px;
      line-height: 1.6;
      display: none;
      z-index: 90;
      overflow-y: auto;
      box-shadow: 0 -10px 30px rgba(0, 0, 0, 0.7);
    }

    .speaker-notes-drawer.open {
      display: block;
    }
  </style>
</head>
<body>

  <!-- TOP HUD BAR (PERSISTENT) -->
  <div class="top-hud">
    <div class="hud-badge accent" id="current-lens-badge">
      <img src="assets/characters/harry.webp" alt="Harry" class="hud-lens-avatar" id="hud-avatar">
      <span id="hud-lens-name">HARRY POTTER</span> · POV LENS
    </div>
  </div>

  <!-- ========================================================
       SLIDE 1: TITLE SLIDE (Clean, Minimalist, Elegant)
       ======================================================== -->
  <section class="screen active" data-screen="1" data-notes="Hello everyone! My name is Nhan Vu, presenting the Epistemic POV Graph for the ShiftKey Academy UP Build It! Machine Learning program. Standard generative LLMs suffer from Omniscience Bias—they know how the entire book ends and leak future twists into character voices. We built an epistemic knowledge graph in Neo4j that mathematically restricts AI memory to only what a character actually witnessed, heard, or believed at that exact timeline horizon.">
    <div class="title-screen-layout">
      <div class="title-program-badge">
        <span>⚡</span> ShiftKey Academy · UP Build It! Machine Learning · Fall 2026
      </div>
      <h1 class="title-h1">POV Graph</h1>
      <div class="title-subheading">AI Storytelling from Every Perspective</div>

      <div class="title-hook-card" style="margin-top: 10px; margin-bottom: 36px; padding: 24px 32px;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <div>
            <div class="mono" style="font-size: 13px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">Presenter / Builder</div>
            <div style="font-size: 26px; font-weight: 800; color: #fff;">Nhan Vu</div>
          </div>
          <div style="text-align: right;">
            <div class="mono" style="font-size: 13px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">Track & Focus</div>
            <div style="font-size: 20px; font-weight: 700; color: var(--accent);">Machine Learning & Generative Graphs</div>
          </div>
        </div>
      </div>

      <button type="button" class="btn-hero-start" onclick="goToScreen(2)">
        <span>Start Presentation</span>
        <span>→</span>
      </button>
    </div>
  </section>

  <!-- ========================================================
       SLIDE 2: MARVEL RIVALS CINEMATIC CHARACTER SELECTION (PARTING LINEUP)
       ======================================================== -->
  <section class="screen" data-screen="2" data-notes="Instead of treating a story as one single global timeline, our project models it as multiple subjective realities. Notice our four characters standing freely on stage. When you hover over each hero, the lineup gracefully parts and an elegant floating game HUD reveals their perspective, epistemic bias, and cognitive attributes. Harry's view is driven by intense gut suspicion, Hermione by causal logic, Ron by strategic loyalty, and Quirrell by calculated deception. Click any character to lock in their point of view.">
    <div class="cinematic-select-stage">
      <div class="cinematic-header">
        <h1 class="cinematic-title">Choose Your Character</h1>
        <p class="cinematic-sub">Hover over any character to reveal their perspective and abilities. Click to lock in their point of view.</p>
      </div>

      <div class="cinematic-lineup-area" id="cinematic-lineup" onmouseleave="onLineupLeave()">
        <div class="magic-motes-container">
          <div class="magic-mote" style="top: 20%; left: 15%; animation-delay: 0s;"></div>
          <div class="magic-mote" style="top: 40%; left: 35%; animation-delay: 2s;"></div>
          <div class="magic-mote" style="top: 15%; left: 60%; animation-delay: 4s;"></div>
          <div class="magic-mote" style="top: 50%; left: 80%; animation-delay: 1s;"></div>
          <div class="magic-mote" style="top: 30%; left: 90%; animation-delay: 3s;"></div>
        </div>

        <div class="stage-floor-light"></div>

        <!-- 1. Harry -->
        <div class="cinematic-hero is-focused selected" id="hero-slot-harry" data-hero="harry" tabindex="0"
             style="--char-accent: #facc15; --char-glow: rgba(250, 204, 21, 0.45);"
             onmouseenter="onHeroHover('harry')"  onclick="onHeroClick('harry')">
          <div class="hero-ambient-aura"></div>
          <div class="hero-magic-ring"></div>
          <div class="hero-ground-shadow"></div>
          <div class="hero-figure-wrap">
            <img src="assets/characters/harry.webp" alt="Harry Potter">
          </div>
          <div class="hero-label-wrap">
            <span class="hero-name-text">Harry Potter</span>
            <span class="hero-role-text mono">GRYFFINDOR · THE SEEKER</span>
            <span class="hero-status-pill mono">● ACTIVE LENS</span>
          </div>
        </div>

        <!-- 2. Hermione -->
        <div class="cinematic-hero" id="hero-slot-hermione" data-hero="hermione" tabindex="0"
             style="--char-accent: #60a5fa; --char-glow: rgba(96, 165, 250, 0.45);"
             onmouseenter="onHeroHover('hermione')"  onclick="onHeroClick('hermione')">
          <div class="hero-ambient-aura"></div>
          <div class="hero-magic-ring"></div>
          <div class="hero-ground-shadow"></div>
          <div class="hero-figure-wrap">
            <img src="assets/characters/hermione.webp" alt="Hermione Granger">
          </div>
          <div class="hero-label-wrap">
            <span class="hero-name-text">Hermione Granger</span>
            <span class="hero-role-text mono">GRYFFINDOR · THE SCHOLAR</span>
            <span class="hero-status-pill mono">● ACTIVE LENS</span>
          </div>
        </div>

        <!-- 3. Ron -->
        <div class="cinematic-hero" id="hero-slot-ron" data-hero="ron" tabindex="0"
             style="--char-accent: #fb923c; --char-glow: rgba(251, 146, 60, 0.45);"
             onmouseenter="onHeroHover('ron')"  onclick="onHeroClick('ron')">
          <div class="hero-ambient-aura"></div>
          <div class="hero-magic-ring"></div>
          <div class="hero-ground-shadow"></div>
          <div class="hero-figure-wrap">
            <img src="assets/characters/ron.webp" alt="Ron Weasley">
          </div>
          <div class="hero-label-wrap">
            <span class="hero-name-text">Ron Weasley</span>
            <span class="hero-role-text mono">GRYFFINDOR · THE STRATEGIST</span>
            <span class="hero-status-pill mono">● ACTIVE LENS</span>
          </div>
        </div>

        <!-- 4. Quirrell -->
        <div class="cinematic-hero" id="hero-slot-quirrell" data-hero="quirrell" tabindex="0"
             style="--char-accent: #c084fc; --char-glow: rgba(192, 132, 252, 0.5);"
             onmouseenter="onHeroHover('quirrell')"  onclick="onHeroClick('quirrell')">
          <div class="hero-ambient-aura"></div>
          <div class="hero-magic-ring"></div>
          <div class="hero-ground-shadow"></div>
          <div class="hero-figure-wrap">
            <img src="assets/characters/quirrell.webp" alt="Professor Quirrell">
          </div>
          <div class="hero-label-wrap">
            <span class="hero-name-text">Prof. Quirrell</span>
            <span class="hero-role-text mono">DARK CONDUIT · THE HOST</span>
            <span class="hero-status-pill mono">● ACTIVE LENS</span>
          </div>
        </div>

        <!-- FLOATING CINEMATIC GAME HUD OVERLAY (Beside active character) -->
        <div class="floating-hud" id="floating-hud">
          <div class="hud-top-meta">
            <span class="hud-house-badge mono" id="hud-house">🦁 GRYFFINDOR</span>
            <span class="hud-role-badge mono" id="hud-role">POV LEAD</span>
          </div>
          <div class="hud-name" id="hud-name">HARRY POTTER</div>
          <div class="hud-title-sub" id="hud-title-sub">The Intuitive Seeker</div>

          <div class="hud-tags-row" id="hud-tags">
            <!-- Staggered badges -->
          </div>

          <div class="hud-divider"></div>

          <div class="hud-section-label mono">EPISTEMIC ATTRIBUTES & STATS</div>
          <div class="hud-stats-list" id="hud-stats">
            <!-- Animated progress bars -->
          </div>

          <div class="hud-divider"></div>

          <div class="hud-belief-box">
            <div class="hud-belief-title mono">ACTIVE BELIEF & BIAS (CH 1–16)</div>
            <div class="hud-belief-text" id="hud-belief"></div>
          </div>

          <div class="hud-quote-text" id="hud-quote"></div>

          <div class="hud-footer">
            <span class="hud-action-hint mono" id="hud-action-hint">✓ ACTIVE POV LENS LOCKED</span>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ========================================================
       SLIDE 3: SPRINT 1 (DRAW.IO GRAPH - CLEAN NO COLONS)
       ======================================================== -->
  <section class="screen" data-screen="3" data-notes="In Sprint 1, our core accomplishment was designing the Neo4j Character POV Knowledge Graph. We couldn't just throw raw text at an LLM; we had to design an explicit schema separating objective reality from subjective perception. Notice the 7 node types: Characters, Events, Locations, Utterances, Claims, and crucially Knowledge Acquisition. The fundamental model rule at the bottom governs everything: witnessing an event does not mean knowing every truth inside it. ACQUIRED and ABOUT record exactly what becomes known and when.">
    <h1 class="t-title">Sprint 1</h1>
    <div class="prompt-banner">
      <span class="prompt-label mono">PROMPT:</span>
      <span class="t-caption">What did you accomplish?</span>
    </div>
    <p class="answer-line">Designed the Epistemic POV Graph: separating objective reality from character perception.</p>

    <div class="drawio-stage-card">
      <div class="drawio-top-bar">
        <div style="display: flex; align-items: center; gap: 16px;">
          <span class="t-body" style="color: var(--accent); font-weight: 800;">CHARACTER POV · KNOWLEDGE GRAPH</span>
          <span class="t-caption mono">(doc/pov_neo4j_character_graph.drawio)</span>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <button type="button" class="btn-pill" id="btn-toggle-labels" onclick="toggleStoryLabels()">Toggle Story Labels</button>
          <button type="button" class="btn-pill" id="btn-replay-graph" onclick="replayBuildSteps()">Replay Build Steps</button>
        </div>
      </div>

      <!-- Exact Draw.io Graph in SVG (Clean, Spacious, Balanced 2-Tier Architecture, No Colons) -->
      <svg width="1728" height="540" viewBox="0 0 1728 540" id="drawio-svg" aria-label="POV Knowledge Graph">
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

        <!-- Edges with clean pill labels (no colons) -->
        <g id="edge-rel" class="graph-edge-group">
          <path id="path-rel" d="M 290 140 C 450 100, 600 100, 700 135" fill="none" stroke="#73BFFF" stroke-width="3" marker-end="url(#arr-blue)" class="flowing-edge"/>
          <g transform="translate(495, 95)">
            <rect x="-75" y="-14" width="150" height="28" rx="14" fill="#102034" stroke="#73BFFF" stroke-width="1.8"/>
            <text x="0" y="5" text-anchor="middle" fill="#73BFFF" class="svg-edge-label">RELATES TO</text>
          </g>
        </g>

        <g id="edge-exp" class="graph-edge-group">
          <line x1="270" y1="190" x2="600" y2="355" stroke="#74DEBF" stroke-width="3" marker-end="url(#arr-teal)" class="flowing-edge"/>
          <g transform="translate(435, 270)">
            <rect x="-75" y="-14" width="150" height="28" rx="14" fill="#102034" stroke="#74DEBF" stroke-width="1.8"/>
            <text x="0" y="5" text-anchor="middle" fill="#74DEBF" class="svg-edge-label">EXPERIENCED</text>
          </g>
        </g>

        <g id="edge-acq" class="graph-edge-group">
          <line x1="225" y1="215" x2="225" y2="325" stroke="#D0A7FF" stroke-width="3.5" marker-end="url(#arr-magenta)" class="flowing-edge"/>
          <g transform="translate(225, 270)">
            <rect x="-55" y="-14" width="110" height="28" rx="14" fill="#102034" stroke="#D0A7FF" stroke-width="1.8"/>
            <text x="0" y="5" text-anchor="middle" fill="#D0A7FF" class="svg-edge-label">ACQUIRED</text>
          </g>
        </g>

        <g id="edge-part" class="graph-edge-group">
          <line x1="745" y1="210" x2="685" y2="330" stroke="#74DEBF" stroke-width="3" marker-end="url(#arr-teal)" class="flowing-edge"/>
          <g transform="translate(715, 265)">
            <rect x="-80" y="-14" width="160" height="28" rx="14" fill="#102034" stroke="#74DEBF" stroke-width="1.8"/>
            <text x="0" y="5" text-anchor="middle" fill="#74DEBF" class="svg-edge-label">PARTICIPATED IN</text>
          </g>
        </g>

        <g id="edge-said" class="graph-edge-group">
          <path d="M 840 140 C 1020 100, 1220 100, 1370 135" fill="none" stroke="#B8ABFF" stroke-width="3" marker-end="url(#arr-purple)" class="flowing-edge"/>
          <g transform="translate(1105, 95)">
            <rect x="-50" y="-14" width="100" height="28" rx="14" fill="#102034" stroke="#B8ABFF" stroke-width="1.8"/>
            <text x="0" y="5" text-anchor="middle" fill="#B8ABFF" class="svg-edge-label">SAID</text>
          </g>
        </g>

        <g id="edge-loc" class="graph-edge-group">
          <line x1="720" y1="390" x2="1010" y2="390" stroke="#F1BD8B" stroke-width="3" marker-end="url(#arr-amber)" class="flowing-edge"/>
          <g transform="translate(865, 390)">
            <rect x="-70" y="-14" width="140" height="28" rx="14" fill="#102034" stroke="#F1BD8B" stroke-width="1.8"/>
            <text x="0" y="5" text-anchor="middle" fill="#F1BD8B" class="svg-edge-label">OCCURRED AT</text>
          </g>
        </g>

        <g id="edge-has" class="graph-edge-group">
          <path d="M 700 350 C 850 280, 1220 280, 1380 350" fill="none" stroke="#F8CF85" stroke-width="3" marker-end="url(#arr-gold)" class="flowing-edge"/>
          <g transform="translate(1040, 280)">
            <rect x="-60" y="-14" width="120" height="28" rx="14" fill="#102034" stroke="#F8CF85" stroke-width="1.8"/>
            <text x="0" y="5" text-anchor="middle" fill="#F8CF85" class="svg-edge-label">HAS CLAIM</text>
          </g>
        </g>

        <g id="edge-assert" class="graph-edge-group">
          <line x1="1440" y1="215" x2="1440" y2="325" stroke="#D0A7FF" stroke-width="3" marker-end="url(#arr-purple)" class="flowing-edge"/>
          <g transform="translate(1440, 270)">
            <rect x="-50" y="-14" width="100" height="28" rx="14" fill="#102034" stroke="#D0A7FF" stroke-width="1.8"/>
            <text x="0" y="5" text-anchor="middle" fill="#D0A7FF" class="svg-edge-label">ASSERTS</text>
          </g>
        </g>

        <g id="edge-about" class="graph-edge-group">
          <path d="M 290 410 C 560 475, 1100 475, 1375 410" fill="none" stroke="#FFE18B" stroke-width="3.5" marker-end="url(#arr-yellow)" class="flowing-edge"/>
          <g transform="translate(830, 465)">
            <rect x="-85" y="-16" width="170" height="32" rx="16" fill="#102034" stroke="#FFE18B" stroke-width="1.8"/>
            <text x="0" y="5" text-anchor="middle" fill="#FFE18B" class="svg-edge-label" font-size="14">ABOUT (Truth)</text>
          </g>
        </g>

        <!-- 7 Nodes (No Colons, Clean Typography) -->
        <g class="graph-node" id="node-char-a" transform="translate(225, 150)">
          <circle cx="0" cy="0" r="66" fill="#152E4D" stroke="#65B9FF" stroke-width="3"/>
          <text x="0" y="-23" text-anchor="middle" class="svg-node-title">Character</text>
          <text x="0" y="-4" text-anchor="middle" fill="#65B9FF" class="svg-node-sub">A · POV</text>
          <line x1="-38" y1="6" x2="38" y2="6" stroke="#65B9FF" stroke-opacity="0.5" stroke-width="1.5"/>
          <text x="0" y="23" text-anchor="middle" class="svg-node-prop1">name · role</text>
          <text x="0" y="40" text-anchor="middle" class="svg-node-prop2">perspective</text>
        </g>

        <g class="graph-node" id="node-char-b" transform="translate(770, 150)">
          <circle cx="0" cy="0" r="66" fill="#152E4D" stroke="#65B9FF" stroke-width="3"/>
          <text x="0" y="-23" text-anchor="middle" class="svg-node-title">Character</text>
          <text x="0" y="-4" text-anchor="middle" fill="#65B9FF" class="svg-node-sub">B</text>
          <line x1="-38" y1="6" x2="38" y2="6" stroke="#65B9FF" stroke-opacity="0.5" stroke-width="1.5"/>
          <text x="0" y="23" text-anchor="middle" class="svg-node-prop1">name · role</text>
          <text x="0" y="40" text-anchor="middle" class="svg-node-prop2">aliases</text>
        </g>

        <g class="graph-node" id="node-event" transform="translate(650, 390)">
          <circle cx="0" cy="0" r="66" fill="#0E3D30" stroke="#60E1AC" stroke-width="3"/>
          <text x="0" y="-18" text-anchor="middle" class="svg-node-title">Event</text>
          <line x1="-38" y1="-3" x2="38" y2="-3" stroke="#60E1AC" stroke-opacity="0.5" stroke-width="1.5"/>
          <text x="0" y="17" text-anchor="middle" class="svg-node-prop1">type · summary</text>
          <text x="0" y="37" text-anchor="middle" class="svg-node-prop2">story_order</text>
        </g>

        <g class="graph-node" id="node-location" transform="translate(1080, 390)">
          <circle cx="0" cy="0" r="66" fill="#3D2B14" stroke="#EEC594" stroke-width="3"/>
          <text x="0" y="-18" text-anchor="middle" class="svg-node-title">Location</text>
          <line x1="-38" y1="-3" x2="38" y2="-3" stroke="#EEC594" stroke-opacity="0.5" stroke-width="1.5"/>
          <text x="0" y="17" text-anchor="middle" class="svg-node-prop1">name · kind</text>
          <text x="0" y="37" text-anchor="middle" class="svg-node-prop2">scene place</text>
        </g>

        <g class="graph-node" id="node-utterance" transform="translate(1440, 150)">
          <circle cx="0" cy="0" r="66" fill="#2E1F4D" stroke="#B8ABFF" stroke-width="3"/>
          <text x="0" y="-18" text-anchor="middle" class="svg-node-title">Utterance</text>
          <line x1="-38" y1="-3" x2="38" y2="-3" stroke="#B8ABFF" stroke-opacity="0.5" stroke-width="1.5"/>
          <text x="0" y="17" text-anchor="middle" class="svg-node-prop1">text · speaker</text>
          <text x="0" y="37" text-anchor="middle" class="svg-node-prop2">spoken words</text>
        </g>

        <g class="graph-node" id="node-knowledge" transform="translate(225, 390)">
          <circle cx="0" cy="0" r="66" fill="#3D1A4D" stroke="#D0A7FF" stroke-width="3"/>
          <text x="0" y="-24" text-anchor="middle" class="svg-node-title" font-size="17">Knowledge</text>
          <text x="0" y="-5" text-anchor="middle" fill="#D0A7FF" class="svg-node-sub">Acquisition</text>
          <line x1="-38" y1="6" x2="38" y2="6" stroke="#D0A7FF" stroke-opacity="0.5" stroke-width="1.5"/>
          <text x="0" y="23" text-anchor="middle" class="svg-node-prop1">channel · time</text>
          <text x="0" y="40" text-anchor="middle" class="svg-node-prop2">stance · belief</text>
        </g>

        <g class="graph-node" id="node-claim" transform="translate(1440, 390)">
          <circle cx="0" cy="0" r="66" fill="#3D3011" stroke="#FFE18B" stroke-width="3"/>
          <text x="0" y="-18" text-anchor="middle" class="svg-node-title">Claim</text>
          <line x1="-38" y1="-3" x2="38" y2="-3" stroke="#FFE18B" stroke-opacity="0.5" stroke-width="1.5"/>
          <text x="0" y="17" text-anchor="middle" class="svg-node-prop1">statement</text>
          <text x="0" y="37" text-anchor="middle" class="svg-node-prop2">truth status</text>
        </g>
      </svg>

      <div class="drawio-rule-banner">
        <span class="hud-badge mono" style="background: #362507; border-color: var(--accent); color: var(--accent);">MODEL RULE</span>
        <span class="t-caption" style="color: #DCEAFF; font-size: 15px;">A character witnessing an event does not automatically know every claim in it. ACQUIRED + ABOUT records exactly what becomes known and when.</span>
      </div>
    </div>
  </section>

  <!-- ========================================================
       SLIDE 4: SPRINT 2 (PART 1) — THE BARRIER / CHALLENGE
       ======================================================== -->
  <section class="screen" data-screen="4" data-notes="In Sprint 2, our biggest barrier was tool reliability. We initially attempted a monolithic approach: passing an entire 6,000-word chapter into a single LLM prompt asking it to extract characters, events, quotes, and relationships. It was a disaster. We measured a 42% hallucination rate on relationships. The LLM silently dropped secondary characters due to context saturation, and when errors occurred, the entire call crashed without any diagnostic trace. Probabilistic guesswork simply cannot build a rigorous knowledge graph.">
    <h1 class="t-title">Sprint 2 · The Barrier</h1>
    <div class="prompt-banner">
      <span class="prompt-label mono">PROMPT:</span>
      <span class="t-caption">What was a challenge you faced, or a barrier/dependency?</span>
    </div>
    <p class="answer-line">Monolithic LLM prompts hallucinated on 6,000-word chapters with zero failure visibility.</p>

    <div class="barrier-screen-layout">
      <!-- Left: The Monolithic Trap Visual -->
      <div class="barrier-core-card">
        <div class="barrier-badge">⚠️ ARCHITECTURAL BREAKDOWN</div>
        <div class="monolithic-prompt-box">
          <div class="prompt-box-title">Single "Do-Everything" Prompt</div>
          <div class="t-caption mono" style="color: #fda4af;">Input: 6,000 words raw chapter text</div>
          <div style="margin: 16px 0; font-size: 40px;">💥</div>
          <p class="t-caption" style="color: #cbd5e1;">Prompt asks LLM to identify characters, infer emotions, track room movements, and extract typed graph edges all in one shot.</p>
        </div>
        <div style="padding: 14px; background: rgba(0,0,0,0.4); border-radius: 12px; border: 1px solid rgba(244, 63, 94, 0.3);">
          <span class="t-caption mono" style="color: #fca5a5;">RESULT: Fragile, non-deterministic, completely un-debuggable.</span>
        </div>
      </div>

      <!-- Right: 3 Critical Breakdown Points -->
      <div class="barrier-fault-list">
        <div class="fault-card">
          <div class="fault-icon">42%</div>
          <div>
            <div class="fault-title">Hallucinated Graph Relationships</div>
            <div class="fault-desc">The LLM invented interactions between characters who were in different rooms, confusing narrative summary with active dialogue.</div>
          </div>
        </div>

        <div class="fault-card">
          <div class="fault-icon">📉</div>
          <div>
            <div class="fault-title">Silent Drops of Secondary Characters</div>
            <div class="fault-desc">Context window saturation caused minor entities (e.g. Neville, Madam Hooch, Fluffy) to be silently dropped from the entity roster.</div>
          </div>
        </div>

        <div class="fault-card">
          <div class="fault-icon">🚫</div>
          <div>
            <div class="fault-title">Token Limit Overflow & Zero Traceability</div>
            <div class="fault-desc">A single formatting error in a 1,000-line JSON output corrupted the entire batch, with zero visibility into which paragraph caused the fault.</div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ========================================================
       SLIDE 5: SPRINT 2 (PART 2) — HOW WE OVERCAME IT
       ======================================================== -->
  <section class="screen" data-screen="5" data-notes="Here is how we overcame the barrier: we completely abandoned monolithic prompts and engineered a 5-stage modular LangGraph pipeline with LangSmith tracing. Each node in the state graph has a single isolated job. Step 1 extracts candidate rosters. Step 2 validates types with Pydantic schemas. Step 3 maps atomic relationships with paragraph references. Step 4 pins physical locations. Step 5 commits an atomic Cypher transaction to Neo4j. If any validation fails, LangGraph catches it, re-prompts the specific failed node, and LangSmith records the full audit trace.">
    <h1 class="t-title">Sprint 2 · The Solution</h1>
    <div class="prompt-banner">
      <span class="prompt-label mono">PROMPT:</span>
      <span class="t-caption">How did you overcome it?</span>
    </div>
    <p class="answer-line">Engineered a 5-stage modular LangGraph pipeline backed by LangSmith audit tracing.</p>

    <div class="solution-screen-layout">
      <!-- 5-Step Pipeline Card -->
      <div class="pipeline-stage-card">
        <div class="pipeline-bar-header">
          <div style="display: flex; align-items: center; gap: 12px;">
            <span class="hud-badge mono" style="background: var(--success-bg); border-color: var(--success); color: var(--success);">STATE GRAPH</span>
            <span class="t-body" style="font-size: 19px; font-weight: 700;">Deterministic Multi-Agent Workflow</span>
          </div>
          <button type="button" class="btn-pill" id="btn-simulate-pipeline" onclick="simulatePipeline()">
            ▶ Simulate Traced Execution
          </button>
        </div>

        <div class="pipeline-grid">
          <div class="pipeline-step" id="p-step-1">
            <div class="pipeline-step-num">STEP 1</div>
            <div class="pipeline-step-title">Roster Delta</div>
            <div class="pipeline-step-desc">Extract candidate entities per paragraph chunk</div>
          </div>

          <div class="pipeline-step" id="p-step-2">
            <div class="pipeline-step-num">STEP 2</div>
            <div class="pipeline-step-title">Pydantic Guard</div>
            <div class="pipeline-step-desc">Self-correcting schema validator with strict types</div>
          </div>

          <div class="pipeline-step" id="p-step-3">
            <div class="pipeline-step-num">STEP 3</div>
            <div class="pipeline-step-title">Relations Map</div>
            <div class="pipeline-step-desc">Atomic delta extraction with evidence grounding</div>
          </div>

          <div class="pipeline-step" id="p-step-4">
            <div class="pipeline-step-num">STEP 4</div>
            <div class="pipeline-step-title">Scene Pinning</div>
            <div class="pipeline-step-desc">Link to validated Location and story order</div>
          </div>

          <div class="pipeline-step" id="p-step-5">
            <div class="pipeline-step-num">STEP 5</div>
            <div class="pipeline-step-title">Neo4j Commit</div>
            <div class="pipeline-step-desc">Idempotent Cypher merge with atomic rollback</div>
          </div>
        </div>
      </div>

      <!-- LangSmith Audit Output -->
      <div class="langsmith-audit-box">
        <div class="langsmith-header-row">
          <span>LANGSMITH TRACE INSPECTOR [RUN_ID: #lg-89241]</span>
          <span>LATENCY: 412ms · TOKENS: 1,280 · ERRORS: 0</span>
        </div>
        <div id="pipeline-trace-log">
          [10:42:01] 🟢 LangGraph runner initialized. Chapter partitioned into 8 validated chunks.<br>
          [10:42:02] 🟢 Step 1: Character extractor discovered 4 entities: [Harry, Hermione, Quirrell, Snape].<br>
          [10:42:03] 🟢 Step 2: Pydantic verified strict type constraints. 0 schema violations.<br>
          [10:42:04] 🟢 Step 5: Neo4j Cypher transaction committed. 14 edges merged successfully.
        </div>
      </div>

      <!-- 3 Key Metric Badges -->
      <div class="solution-metrics-row">
        <div class="metric-card">
          <div class="metric-val">100%</div>
          <div class="metric-label">Schema Compliance</div>
        </div>
        <div class="metric-card">
          <div class="metric-val">&lt; 0.5%</div>
          <div class="metric-label">Hallucination Leak Rate</div>
        </div>
        <div class="metric-card">
          <div class="metric-val">Full</div>
          <div class="metric-label">LangSmith Audit Traceability</div>
        </div>
      </div>
    </div>
  </section>

  <!-- ========================================================
       SLIDE 6: SPRINT 3 (PART 1) — THE SURPRISE
       ======================================================== -->
  <section class="screen" data-screen="6" data-notes="In Sprint 3, our biggest surprise was the profound technical challenge posed by mystery narratives and plot twists. In Harry Potter, everything in Chapters 1 through 16 points to Snape being the villain. Harry saw Snape's leg bleeding from Fluffy, heard him confronting Quirrell, and saw him staring intently at Harry's broomstick. But in Chapter 17, the entire premise flips: Quirrell unwraps his turban to reveal Voldemort, and Snape was secretly counter-cursing to save Harry's life. If you update a knowledge graph naively, Chapter 17 permanently corrupts Chapter 16! Characters would suffer from omniscience leakage.">
    <h1 class="t-title">Sprint 3 · The Surprise</h1>
    <div class="prompt-banner">
      <span class="prompt-label mono">PROMPT:</span>
      <span class="t-caption">What's something surprising that happened during the process?</span>
    </div>
    <p class="answer-line">End-of-book twists completely shattered conventional graph assumptions.</p>

    <div class="twist-screen-layout">
      <!-- Left: Chapter 1-16 Red Herring -->
      <div class="twist-side-card red-herring">
        <div>
          <div class="twist-side-badge" style="background: rgba(250, 204, 21, 0.15); color: var(--accent); border: 1px solid var(--accent);">
            CHAPTERS 1 – 16 · THE RED HERRING
          </div>
          <h2 style="font-size: 28px; font-weight: 800; color: #fff; margin-bottom: 8px;">The Snape Suspicion Consensus</h2>
          <p class="t-body" style="font-size: 17px; color: #cbd5e1;">Every clue, witness, and protagonist belief points to Severus Snape as the thief trying to steal the Stone.</p>

          <div class="evidence-item-list">
            <div class="evidence-pill-item">
              <span>🩸</span> Witnessed Snape's leg mauled by Fluffy on Halloween night
            </div>
            <div class="evidence-pill-item">
              <span>🧹</span> Hermione saw Snape making eye-contact during the Quidditch match
            </div>
            <div class="evidence-pill-item">
              <span>🌲</span> Harry eavesdropped on Snape cornering Quirrell in the Forbidden Forest
            </div>
          </div>
        </div>

        <div style="padding: 14px; background: rgba(0,0,0,0.5); border-radius: 12px; border: 1px solid rgba(250, 204, 21, 0.3);">
          <span class="t-caption mono" style="color: var(--accent);">NAIVE GRAPH RESULT: Snape permanently marked as antagonist.</span>
        </div>
      </div>

      <!-- Right: Chapter 17 Mirror Revelation -->
      <div class="twist-side-card revelation">
        <div>
          <div class="twist-side-badge" style="background: var(--purple-bg); color: var(--purple); border: 1px solid var(--purple);">
            CHAPTER 17 · THE MIRROR TWIST
          </div>
          <h2 style="font-size: 28px; font-weight: 800; color: #fff; margin-bottom: 8px;">The Turban Unwrapped</h2>
          <p class="t-body" style="font-size: 17px; color: #cbd5e1;">Harry steps through the trapdoor expecting Snape—only to find stammering Professor Quirrell smiling in front of the Mirror.</p>

          <div class="evidence-item-list">
            <div class="evidence-pill-item">
              <span>🎭</span> Quirrell reveals his stutter was a calculated distraction
            </div>
            <div class="evidence-pill-item">
              <span>🛡️</span> Snape was murmuring counter-curses to save Harry's life
            </div>
            <div class="evidence-pill-item">
              <span>🐍</span> Lord Voldemort is living in the back of Quirrell's head
            </div>
          </div>
        </div>

        <div style="padding: 14px; background: rgba(0,0,0,0.5); border-radius: 12px; border: 1px solid var(--purple);">
          <span class="t-caption mono" style="color: #e9d5ff;">THE EPISTEMIC CRISIS: How do we record the twist without retroactively destroying Harry's earlier authentic memories?</span>
        </div>
      </div>
    </div>
  </section>

  <!-- ========================================================
       SLIDE 7: SPRINT 3 (PART 2) — THE DIVERSION
       ======================================================== -->
  <section class="screen" data-screen="7" data-notes="To solve the surprise of narrative twists, we took a major architectural diversion: we engineered a Two-Pass Epistemic Ingestion architecture. In Pass 1, we read the entire book from an omniscient global perspective to establish canonical entity identities—knowing that Quirrell is the true villain and Snape is the protector. Then in Pass 2, we re-read the saga chronologically, anchoring each character's beliefs to temporal horizons. Toggle the timeline buttons below: notice how in Chapter 16, Harry's active claim is that Snape is the thief. In Chapter 17, that suspicion is marked as shattered, and the true Quirrell acquisition is committed. Both facts coexist in Neo4j with explicit temporal bounds.">
    <h1 class="t-title">Sprint 3 · The Diversion</h1>
    <div class="prompt-banner">
      <span class="prompt-label mono">PROMPT:</span>
      <span class="t-caption">What's a diversion you took, or something surprising that happened?</span>
    </div>
    <p class="answer-line">Pivoted to a Two-Pass Memory Architecture to ground subjective timeline horizons.</p>

    <div class="diversion-screen-layout">
      <!-- Two Pass Architecture Card -->
      <div class="two-pass-stage-card">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
          <div style="display: flex; align-items: center; gap: 12px;">
            <span class="hud-badge mono" style="background: var(--purple-bg); border-color: var(--purple); color: var(--purple);">MEMORY ENGINE</span>
            <span class="t-body" style="font-size: 19px; font-weight: 700;">Two-Pass Ingestion Pipeline</span>
          </div>
          <span class="t-caption mono" style="color: var(--text-muted);">Neo4j Graph Temporal Grounding</span>
        </div>

        <div class="two-pass-grid">
          <!-- Pass 1 -->
          <div class="pass-column-card">
            <div class="pass-col-header">
              <span>PASS 1 · GLOBAL MEMORY</span>
              <span class="hud-badge mono" style="font-size: 11px;">WHO IS WHO</span>
            </div>
            <p class="t-caption" style="color: #cbd5e1; margin-bottom: 14px;">Whole-book pass establishing canonical character entities and objective ground truth.</p>
            <div style="display: flex; flex-direction: column; gap: 10px;">
              <div style="display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: rgba(0,0,0,0.3); border-radius: 8px;">
                <img src="assets/characters/quirrell.webp" alt="Quirrell" style="width: 32px; height: 32px; border-radius: 50%;">
                <span class="mono" style="font-size: 14px; color: #fff;">Quirrell: True Host of Voldemort</span>
              </div>
              <div style="display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: rgba(0,0,0,0.3); border-radius: 8px;">
                <img src="assets/characters/snape.webp" alt="Snape" style="width: 32px; height: 32px; border-radius: 50%;">
                <span class="mono" style="font-size: 14px; color: #fff;">Snape: Misunderstood Guardian</span>
              </div>
            </div>
          </div>

          <!-- Pass 2 -->
          <div class="pass-column-card">
            <div class="pass-col-header">
              <span>PASS 2 · POV HORIZONS</span>
              <span class="hud-badge mono" style="font-size: 11px;">TIMELINE BOUNDED</span>
            </div>
            <p class="t-caption" style="color: #cbd5e1; margin-bottom: 14px;">Chronological pass attaching claims with valid_from/to and learned_at timestamps.</p>
            <div id="timeline-display-box" style="display: flex; flex-direction: column; gap: 10px;">
              <!-- Dynamic content updated by JS -->
            </div>
          </div>
        </div>

        <!-- Interactive Timeline Horizon Switcher -->
        <div class="timeline-toggle-box">
          <span class="t-body" style="font-size: 17px; font-weight: 700;">Simulate Harry's POV Horizon:</span>
          <div style="display: flex; gap: 12px;">
            <button type="button" class="btn-timeline-choice active" id="btn-ch16" onclick="setTimelineHorizon(16)">Chapter 16: Trapdoor</button>
            <button type="button" class="btn-timeline-choice" id="btn-ch17" onclick="setTimelineHorizon(17)">Chapter 17: Mirror Room</button>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ========================================================
       SLIDE 8: WHAT'S NEXT FOR ME
       ======================================================== -->
  <section class="screen" data-screen="8" data-notes="Looking forward: where are we taking this project from here? Our core takeaway is: 'Model what characters know, not just where they were.' By grounding generative models in epistemic subgraphs, we eliminate omniscience bias. Milestone 1 is 100% complete with our verified Neo4j schema and modular pipeline. Milestone 2 is currently active: scaling from single chapters to ingesting the entire 7-volume Harry Potter series. And Milestone 3 is our final horizon: autonomous POV agents that can retell entire sagas in any character's authentic voice, preserving every historical secret. Thank you! Now I'm open for questions.">
    <h1 class="t-title">What's Next for Me</h1>
    <div class="prompt-banner">
      <span class="prompt-label mono">PROMPT:</span>
      <span class="t-caption">Where are you taking this project from here? What did this experience teach you?</span>
    </div>
    <p class="answer-line">From epistemic knowledge graphs to autonomous, multi-agent POV narrators.</p>

    <div class="next-screen-layout">
      <!-- Big Core Takeaway Banner -->
      <div class="takeaway-banner">
        <div class="takeaway-quote">"Model what characters know, not just where they were."</div>
        <div class="takeaway-sub">Grounding generative LLM agents in epistemic subgraphs mathematically eliminates omniscience bias and enables authentic literary roleplay.</div>
      </div>

      <!-- 3-Milestone Roadmap Grid -->
      <div class="roadmap-grid">
        <!-- Milestone 1 -->
        <div class="roadmap-card">
          <div>
            <div class="roadmap-status-badge" style="background: var(--success-bg); color: var(--success); border: 1px solid var(--success);">
              MILESTONE 1 · COMPLETE
            </div>
            <h3 style="font-size: 22px; font-weight: 800; color: #fff; margin-bottom: 8px;">Epistemic Graph & Pipeline</h3>
            <p class="t-caption" style="color: #cbd5e1; line-height: 1.5;">
              Neo4j schema separating reality from perception; 5-stage modular LangGraph with LangSmith audit tracing.
            </p>
          </div>
          <div style="margin-top: 18px; padding-top: 12px; border-top: 1px solid rgba(255, 255, 255, 0.1);">
            <span class="mono" style="font-size: 13px; color: var(--success);">✔ 100% Verified in Competition</span>
          </div>
        </div>

        <!-- Milestone 2 -->
        <div class="roadmap-card active-lane">
          <div>
            <div class="roadmap-status-badge" style="background: rgba(250, 204, 21, 0.15); color: var(--accent); border: 1px solid var(--accent);">
              MILESTONE 2 · IN PROGRESS
            </div>
            <h3 style="font-size: 22px; font-weight: 800; color: #fff; margin-bottom: 8px;">Full-Series Ingestion</h3>
            <p class="t-caption" style="color: #cbd5e1; line-height: 1.5;">
              Scaling from single chapters to full 7-volume series ingestion with cross-book identity resolution and continuous memory.
            </p>
          </div>
          <div style="margin-top: 18px; padding-top: 12px; border-top: 1px solid rgba(255, 255, 255, 0.1);">
            <span class="mono" style="font-size: 13px; color: var(--accent);">⚡ 70% Active Testing</span>
          </div>
        </div>

        <!-- Milestone 3 -->
        <div class="roadmap-card">
          <div>
            <div class="roadmap-status-badge" style="background: var(--purple-bg); color: var(--purple); border: 1px solid var(--purple);">
              MILESTONE 3 · NEXT HORIZON
            </div>
            <h3 style="font-size: 22px; font-weight: 800; color: #fff; margin-bottom: 8px;">Autonomous POV Reteller</h3>
            <p class="t-caption" style="color: #cbd5e1; line-height: 1.5;">
              Generative agent conditioned directly on character subgraphs to write original narrative prose in any authentic persona.
            </p>
          </div>
          <div style="margin-top: 18px; padding-top: 12px; border-top: 1px solid rgba(255, 255, 255, 0.1);">
            <span class="mono" style="font-size: 13px; color: var(--purple);">🔮 Future Capstone</span>
          </div>
        </div>
      </div>

      <!-- Quick Replay Bar -->
      <div style="display: flex; align-items: center; justify-content: space-between; padding: 14px 24px; background: rgba(8, 14, 26, 0.9); border: 1px solid var(--border-muted); border-radius: 14px;">
        <span class="t-caption mono" style="color: var(--text-muted);">Replay presentation through another lens:</span>
        <div style="display: flex; gap: 10px;">
          <button type="button" class="btn-pill" onclick="selectHero('harry'); goToScreen(2)">Harry</button>
          <button type="button" class="btn-pill" onclick="selectHero('hermione'); goToScreen(2)">Hermione</button>
          <button type="button" class="btn-pill" onclick="selectHero('ron'); goToScreen(2)">Ron</button>
          <button type="button" class="btn-pill" onclick="selectHero('quirrell'); goToScreen(2)">Quirrell</button>
          
        </div>
      </div>
    </div>
  </section>

  <!-- SPEAKER NOTES DRAWER (PRESS 'N') -->
  <div class="speaker-notes-drawer" id="speaker-notes">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
      <span class="mono" style="color: var(--accent); font-weight: 700; font-size: 13px;">SPEAKER NOTES (PRESS 'N' TO TOGGLE)</span>
      <span class="mono" style="font-size: 12px; color: var(--text-muted);" id="notes-slide-indicator">Slide 1 / 8</span>
    </div>
    <div id="notes-content">Welcome everyone! I'm Nhan Vu, presenting Epistemic POV Graph...</div>
  </div>

  <!-- BOTTOM HUD BAR -->
  <div class="bottom-hud">
    <div class="progress-bar-container">
      <span class="mono t-caption" style="font-weight: 700; color: var(--accent);">PROGRESS</span>
      <div class="progress-track">
        <div class="progress-fill" id="hud-progress-fill"></div>
      </div>
    </div>

    <button type="button" class="btn-nav" id="btn-toggle-notes" onclick="toggleNotes()">
      <span>Notes [N]</span>
    </button>

    <div class="hud-nav-buttons">
      <button type="button" class="btn-nav" id="btn-prev" onclick="prevScreen()">
        <span>◀ Prev</span>
      </button>
      <span class="mono t-body" style="font-size: 16px; padding: 0 12px; font-weight: 700;" id="hud-screen-indicator">1 / 8</span>
      <button type="button" class="btn-nav" id="btn-next" onclick="nextScreen()">
        <span>Next ▶</span>
      </button>
    </div>
  </div>

  <script>
    // ==================== GLOBAL STATE & HERO DATA ====================
    const HERO_DATA = {
      harry: {
        name: "HARRY POTTER",
        role: "THE INTUITIVE SEEKER (POV LEAD)",
        color: "#facc15",
        glow: "rgba(250, 204, 21, 0.4)",
        avatar: "assets/characters/harry.webp",
        tagline: "Follows instinct · Bound by fierce loyalty · Zero tolerance for dark magic",
        perception: "Sees the world through gut feelings and strong moral absolutes. Quick to defend friends, immediate to suspect institutional authority.",
        beliefs: "100% convinced Severus Snape wants the Philosopher's Stone. Witnessed Snape's leg wound and deduced Fluffy was guarding the underground trapdoor.",
        blindspot: "Totally deceived by Quirrell's nervous stutter and timidity. Never suspects the timid Defence Against the Dark Arts teacher until Chapter 17.",
        quote: "\"Snape’s going through that trapdoor tonight. He’s going to steal the Stone for Voldemort, and I have to stop him.\""
      },
      hermione: {
        name: "HERMIONE GRANGER",
        role: "THE ANALYTICAL ARCHIVIST",
        color: "#60a5fa",
        glow: "rgba(96, 165, 250, 0.4)",
        avatar: "assets/characters/hermione.webp",
        tagline: "Cataloger of canon · Spell tactician · Logic-driven problem solver",
        perception: "Interprets reality strictly through books, rules, and verifiable documentation. Trusts published history and institutional procedures.",
        beliefs: "Deduced Flamel from Chocolate Frog cards; solved Snape's 7-potion logic puzzle; set Snape's cloak on fire because eye-contact is required for cursing.",
        blindspot: "Confused correlation with causation—assumed eye-contact equaled cursing, accidentally knocking over Quirrell without realizing he was the true caster.",
        quote: "\"Books! And cleverness! There are more important things—friendship and bravery—and Harry, just be careful!\""
      },
      ron: {
        name: "RON WEASLEY",
        role: "THE STRATEGIC TACTICIAN",
        color: "#fb923c",
        glow: "rgba(251, 146, 60, 0.4)",
        avatar: "assets/characters/ron.webp",
        tagline: "Wizarding instincts · Grandmaster tactician · Unwavering loyalty",
        perception: "Grounded in wizarding culture and ancient family folklore. Inherently suspicious of dark families and Slytherin house politics.",
        beliefs: "Sacrificed his piece on McGonagall's giant chessboard to secure Harry's checkmate. Believes Snape's bitterness towards Gryffindor proves his malice.",
        blindspot: "Underestimates quiet or nervous peers; completely overlooks Quirrell as an inconsequential background teacher.",
        quote: "\"Do you want to stop Snape getting that Stone or not? Harry, you’ve got to go on—not me, not Hermione, YOU!\""
      },
      quirrell: {
        name: "QUIRINUS QUIRRELL",
        role: "THE DECEPTIVE HOST",
        color: "#c084fc",
        glow: "rgba(192, 132, 252, 0.4)",
        avatar: "assets/characters/quirrell.webp",
        tagline: "Master of feigned weakness · Dark conduit · Voldemort's vessel",
        perception: "Cold, calculated, fully subservient to Voldemort's whisper. Uses perceived patheticness as an impenetrable cognitive camouflage.",
        beliefs: "Let the troll in on Halloween; jinxed Harry's Nimbus 2000; slaughtered unicorns in the forest; actively manipulating the Mirror of Erised.",
        blindspot: "Cannot fathom selfless love or sacrifice; baffled by how Harry pulled the Stone from the Mirror without desiring to use it.",
        quote: "\"Severus does seem the type, doesn’t he? Next to him, who would suspect p-p-poor, st-stuttering Professor Quirrell?\""
      },
      snape: {
        name: "SEVERUS SNAPE",
        role: "THE MISUNDERSTOOD GUARDIAN",
        color: "#4ade80",
        glow: "rgba(74, 222, 128, 0.4)",
        avatar: "assets/characters/snape.webp",
        tagline: "Unwavering secret oath · Occlumency master · Shadow protector",
        perception: "Bitter, hyper-vigilant, trapped between an eternal oath to Lily Potter and a ruthless exterior required to maintain cover.",
        beliefs: "Counter-jinxed Quirrell at the match; threatened Quirrell in the forest; intercepted the trapdoor on Halloween and took Fluffy's bite.",
        blindspot: "Inability to show empathy or warmth ensures Harry misinterprets every single life-saving protective action as attempted murder.",
        quote: "\"You don’t want me as your enemy, Quirrell. We’ll have another little chat soon, when you’ve had time to decide where your loyalties lie.\""
      }
    };

    const state = {
      currentScreen: 1,
      totalScreens: 8,
      selectedHero: "harry",
      isStoryLabels: false,
      notesOpen: false,
      timelineChapter: 16
    };

    // ==================== SCREEN NAVIGATION ====================
    // ==================== SLIDE 2 CINEMATIC MARVEL RIVALS SELECTION LOGIC ====================
    const HERO_CONFIG = {
      harry: {
        name: "Harry Potter",
        role: "The Intuitive Seeker",
        house: "🦁 Gryffindor",
        hud_role: "POV LEAD · YEAR 1",
        accent: "#facc15",
        glow: "rgba(250, 204, 21, 0.45)",
        avatar: "assets/characters/harry.webp",
        tags: ["⚡ The Chosen One", "🧹 Quidditch Seeker", "🦁 Fierce Loyalty", "🩸 Anti-Snape Bias"],
        stats: [
          { label: "Gut Intuition", val: 94 },
          { label: "Belief Rigidity", val: 92 },
          { label: "Truth Horizon", val: 35 }
        ],
        belief: "100% convinced Severus Snape is trying to steal the Stone through Fluffy's trapdoor.",
        quote: "“Snape’s going through that trapdoor tonight. He’s going to steal the Stone, and I have to stop him.”"
      },
      hermione: {
        name: "Hermione Granger",
        role: "The Analytical Archivist",
        house: "🦁 Gryffindor",
        hud_role: "SCHOLAR · LOGICIAN",
        accent: "#60a5fa",
        glow: "rgba(96, 165, 250, 0.45)",
        avatar: "assets/characters/hermione.webp",
        tags: ["📚 Top of the Class", "🧪 Logic Puzzles", "📜 Canon Fact-Checking", "🔥 Cloak Incinerator"],
        stats: [
          { label: "Logical Rigor", val: 98 },
          { label: "Belief Rigidity", val: 86 },
          { label: "Truth Horizon", val: 45 }
        ],
        belief: "Deduced Flamel from Chocolate Frog cards; set Snape's cloak on fire assuming eye-contact meant cursing.",
        quote: "“Books! And cleverness! There are more important things—friendship and bravery—and Harry, just be careful!”"
      },
      ron: {
        name: "Ron Weasley",
        role: "The Strategic Tactician",
        house: "🦁 Gryffindor",
        hud_role: "TACTICIAN · CHESS MASTER",
        accent: "#fb923c",
        glow: "rgba(251, 146, 60, 0.45)",
        avatar: "assets/characters/ron.webp",
        tags: ["♟️ Chess Grandmaster", "⚔️ Knight's Sacrifice", "🏰 Wizard Folklore", "🤝 Brotherly Devotion"],
        stats: [
          { label: "Tactical Insight", val: 91 },
          { label: "Belief Rigidity", val: 84 },
          { label: "Truth Horizon", val: 30 }
        ],
        belief: "Sacrificed his knight on McGonagall's chessboard. Believes Snape's anti-Gryffindor grudge confirms guilt.",
        quote: "“Do you want to stop Snape getting that Stone or not? Harry, you’ve got to go on—YOU!”"
      },
      quirrell: {
        name: "Prof. Quirrell",
        role: "The Deceptive Host",
        house: "🦅 Ravenclaw / Dark Vessel",
        hud_role: "CONSPIRATOR · DADA",
        accent: "#c084fc",
        glow: "rgba(192, 132, 252, 0.5)",
        avatar: "assets/characters/quirrell.webp",
        tags: ["🎭 Feigned Timidity", "🐍 Voldemort Host", "🧣 Turban Decoy", "🪞 Mirror Manipulator"],
        stats: [
          { label: "Deception & Camouflage", val: 99 },
          { label: "Subservience", val: 96 },
          { label: "Conspiracy Awareness", val: 95 }
        ],
        belief: "Let the troll in on Halloween; jinxed Harry's broom; drinking unicorn blood to sustain Voldemort.",
        quote: "“Severus does seem the type, doesn’t he? Next to him, who would suspect p-p-poor, st-stuttering Professor Quirrell?”"
      }
    };

    // Mathematical coordinate map for the parting lineup on 1728px width stage
    // Every character has a dedicated slot, zero overlap with the 440px HUD!
    const LINEUP_POSITIONS = {
      harry: {
        harry: 40,
        hud: 340,
        hermione: 840,
        ron: 1140,
        quirrell: 1440
      },
      hermione: {
        harry: 40,
        hermione: 320,
        hud: 620,
        ron: 1140,
        quirrell: 1440
      },
      ron: {
        harry: 40,
        hermione: 320,
        hud: 620,
        ron: 1140,
        quirrell: 1440
      },
      quirrell: {
        harry: 40,
        hermione: 320,
        ron: 600,
        hud: 900,
        quirrell: 1420
      }
    };

    let activeHoverHero = null;

    function applyPartingPositions(heroKey, immediate = false) {
      const pos = LINEUP_POSITIONS[heroKey] || LINEUP_POSITIONS.harry;
      const dur = immediate ? 0 : 0.45;
      const ease = "power2.out";

      const heroIds = ["harry", "hermione", "ron", "quirrell"];
      heroIds.forEach(id => {
        const el = document.getElementById(`hero-slot-${id}`);
        if (!el) return;
        const targetX = pos[id];

        if (window.gsap && !immediate) {
          gsap.to(el, { left: `${targetX}px`, duration: dur, ease: ease, overwrite: "auto" });
        } else {
          el.style.left = `${targetX}px`;
        }
      });

      const hud = document.getElementById("floating-hud");
      if (hud) {
        const hudX = pos.hud;
        if (window.gsap && !immediate) {
          gsap.to(hud, { left: `${hudX}px`, duration: dur, ease: ease, overwrite: "auto" });
        } else {
          hud.style.left = `${hudX}px`;
        }
      }
    }

    function updateFloatingHud(heroKey, isLocked) {
      const cfg = HERO_CONFIG[heroKey];
      if (!cfg) return;

      const hud = document.getElementById("floating-hud");
      hud.style.setProperty("--hud-border", cfg.accent);
      hud.style.setProperty("--hud-glow", cfg.glow);
      hud.style.setProperty("--hud-accent", cfg.accent);

      document.getElementById("hud-house").textContent = cfg.house;
      document.getElementById("hud-role").textContent = cfg.hud_role;
      document.getElementById("hud-name").textContent = cfg.name.toUpperCase();
      document.getElementById("hud-title-sub").textContent = cfg.role;
      document.getElementById("hud-belief").textContent = cfg.belief;
      document.getElementById("hud-quote").textContent = cfg.quote;

      const hintEl = document.getElementById("hud-action-hint");
      if (isLocked) {
        hintEl.textContent = "✓ ACTIVE POV LENS LOCKED";
        hintEl.style.color = "#34d399";
      } else {
        hintEl.textContent = "CLICK TO LOCK IN PERSPECTIVE";
        hintEl.style.color = cfg.accent;
      }

      // Populate Tags
      const tagsContainer = document.getElementById("hud-tags");
      tagsContainer.innerHTML = cfg.tags.map(t => `<span class="hud-tag-pill">${t}</span>`).join("");

      // Populate Stats
      const statsContainer = document.getElementById("hud-stats");
      statsContainer.innerHTML = cfg.stats.map(s => `
        <div class="hud-stat-item">
          <div class="hud-stat-header">
            <span class="hud-stat-label">${s.label}</span>
            <span class="hud-stat-val">${s.val}%</span>
          </div>
          <div class="hud-bar-track">
            <div class="hud-bar-fill" data-target="${s.val}%"></div>
          </div>
        </div>
      `).join("");

      // GSAP Animation Reveal
      if (window.gsap) {
        gsap.killTweensOf(hud, "opacity,scale");
        gsap.fromTo(hud,
          { opacity: 0, scale: 0.96 },
          { opacity: 1, scale: 1, duration: 0.35, ease: "power2.out", overwrite: "auto" }
        );

        // Animate stat bars
        setTimeout(() => {
          hud.querySelectorAll(".hud-bar-fill").forEach(bar => {
            bar.style.width = bar.dataset.target;
          });
        }, 50);

        // Animate tags stagger
        gsap.fromTo(tagsContainer.children,
          { opacity: 0, y: 5 },
          { opacity: 1, y: 0, stagger: 0.04, duration: 0.22, ease: "power1.out" }
        );
      } else {
        hud.style.opacity = "1";
        hud.querySelectorAll(".hud-bar-fill").forEach(bar => {
          bar.style.width = bar.dataset.target;
        });
      }
    }

    function onHeroHover(heroKey) {
      activeHoverHero = heroKey;

      document.querySelectorAll(".cinematic-hero").forEach(el => {
        el.classList.toggle("is-focused", el.dataset.hero === heroKey);
      });

      applyPartingPositions(heroKey);
      const isLocked = (state.selectedHero === heroKey);
      updateFloatingHud(heroKey, isLocked);
    }

    function onLineupLeave() {
      activeHoverHero = null;
      // Smoothly return to the selected hero state
      focusHero(state.selectedHero);
    }

    function onHeroClick(heroKey) {
      state.selectedHero = heroKey;
      const cfg = HERO_CONFIG[heroKey];
      if (cfg) {
        document.getElementById("hud-avatar").src = cfg.avatar;
        document.getElementById("hud-lens-name").textContent = cfg.name.toUpperCase();
      }

      // Update Node A in Slide 3 Draw.io Graph
      const nodeASub = document.querySelector("#node-char-a .svg-node-sub");
      if (nodeASub) {
        nodeASub.textContent = `${heroKey.toUpperCase()} · POV`;
      }

      document.querySelectorAll(".cinematic-hero").forEach(el => {
        el.classList.toggle("selected", el.dataset.hero === heroKey);
      });

      focusHero(heroKey);

      // Trigger selection shockwave via GSAP
      if (window.gsap) {
        const selectedHeroEl = document.getElementById(`hero-slot-${heroKey}`);
        if (selectedHeroEl) {
          const ring = selectedHeroEl.querySelector(".hero-magic-ring");
          gsap.fromTo(ring,
            { scale: 0.75, opacity: 1 },
            { scale: 1.3, opacity: 0.85, duration: 0.5, ease: "back.out(2)" }
          );
        }
      }
    }

    function focusHero(heroKey, immediate = false) {
      document.querySelectorAll(".cinematic-hero").forEach(el => {
        const isMatch = (el.dataset.hero === heroKey);
        el.classList.toggle("is-focused", isMatch);
        el.classList.toggle("selected", isMatch);
      });

      applyPartingPositions(heroKey, immediate);
      updateFloatingHud(heroKey, true);
    }

    function goToScreen(index) {
      if (index < 1 || index > state.totalScreens) return;
      state.currentScreen = index;
      renderScreen();
    }

    function nextScreen() {
      if (state.currentScreen < state.totalScreens) {
        state.currentScreen++;
        renderScreen();
      }
    }

    function prevScreen() {
      if (state.currentScreen > 1) {
        state.currentScreen--;
        renderScreen();
      }
    }

    function renderScreen() {
      document.querySelectorAll(".screen").forEach(el => {
        const sIndex = parseInt(el.dataset.screen);
        if (sIndex === state.currentScreen) {
          el.classList.add("active");
          // Update speaker notes
          const notesText = el.dataset.notes || "No notes for this slide.";
          document.getElementById("notes-content").textContent = notesText;
          document.getElementById("notes-slide-indicator").textContent = `Slide ${state.currentScreen} / ${state.totalScreens}`;
        } else {
          el.classList.remove("active");
        }
      });

      // Update Bottom HUD
      document.getElementById("hud-screen-indicator").textContent = `${state.currentScreen} / ${state.totalScreens}`;
      const fillPct = (state.currentScreen / state.totalScreens) * 100;
      document.getElementById("hud-progress-fill").style.width = `${fillPct}%`;

      document.getElementById("btn-prev").disabled = state.currentScreen === 1;
      document.getElementById("btn-next").disabled = state.currentScreen === state.totalScreens;
    }

    function toggleNotes() {
      state.notesOpen = !state.notesOpen;
      const drawer = document.getElementById("speaker-notes");
      drawer.classList.toggle("open", state.notesOpen);
      document.getElementById("btn-toggle-notes").classList.toggle("active", state.notesOpen);
    }

    // ==================== MARVEL RIVALS CHARACTER SELECTION ====================
    function inspectHero(heroKey) {
      const data = HERO_DATA[heroKey];
      if (!data) return;

      const panel = document.getElementById("hero-panel");
      panel.style.setProperty("--inspect-color", data.color);
      panel.style.setProperty("--inspect-glow", data.glow);

      document.getElementById("hero-inspect-avatar").src = data.avatar;
      document.getElementById("hero-inspect-name").textContent = data.name;
      document.getElementById("hero-inspect-role").textContent = data.role;
      document.getElementById("hero-inspect-tagline").textContent = data.tagline;
      document.getElementById("hero-inspect-perception").textContent = data.perception;
      document.getElementById("hero-inspect-beliefs").textContent = data.beliefs;
      document.getElementById("hero-inspect-blindspot").textContent = data.blindspot;
      document.getElementById("hero-inspect-quote").textContent = data.quote;
      document.getElementById("hero-inspect-status").textContent = data.name;

      // Update left roster highlight
      document.querySelectorAll(".character-card").forEach(card => {
        card.classList.toggle("active", card.dataset.char === heroKey);
      });
    }

    function selectHero(heroKey) {
      state.selectedHero = heroKey;
      const data = HERO_DATA[heroKey];
      if (!data) return;

      document.getElementById("hud-avatar").src = data.avatar;
      document.getElementById("hud-lens-name").textContent = data.name;

      const labelEl = document.getElementById("selected-char-label");
      if (labelEl) labelEl.textContent = data.name;

      document.querySelectorAll(".simple-char-card").forEach(card => {
        const isMatch = card.dataset.char === heroKey;
        card.classList.toggle("active", isMatch);
        const actionSpan = card.querySelector(".simple-card-action span");
        if (actionSpan) {
          actionSpan.textContent = isMatch ? "Active POV Lens" : "Click to Select";
        }
      });

      // Update Node A in Slide 3 Draw.io Graph
      const nodeASub = document.querySelector("#node-char-a .svg-node-sub");
      if (nodeASub) {
        nodeASub.textContent = `${heroKey.toUpperCase()} · POV`;
      }
    }

    // ==================== SLIDE 3 DRAW.IO GRAPH LOGIC ====================
    function toggleStoryLabels() {
      state.isStoryLabels = !state.isStoryLabels;
      const btn = document.getElementById("btn-toggle-labels");
      btn.classList.toggle("active", state.isStoryLabels);

      const nodeA = document.querySelector("#node-char-a .svg-node-sub");
      const nodeB = document.querySelector("#node-char-b .svg-node-sub");
      const nodeEvent = document.querySelector("#node-event .svg-node-prop1");
      const nodeLoc = document.querySelector("#node-location .svg-node-prop1");
      const nodeClaim = document.querySelector("#node-claim .svg-node-prop1");

      if (state.isStoryLabels) {
        if (nodeA) nodeA.textContent = "Harry (POV)";
        if (nodeB) nodeB.textContent = "Quirrell";
        if (nodeEvent) nodeEvent.textContent = "Quidditch match";
        if (nodeLoc) nodeLoc.textContent = "Quidditch pitch";
        if (nodeClaim) nodeClaim.textContent = "Snape protecting";
      } else {
        if (nodeA) nodeA.textContent = "A · POV";
        if (nodeB) nodeB.textContent = "B";
        if (nodeEvent) nodeEvent.textContent = "type · summary";
        if (nodeLoc) nodeLoc.textContent = "name · kind";
        if (nodeClaim) nodeClaim.textContent = "statement";
      }
    }

    function replayBuildSteps() {
      const allNodes = document.querySelectorAll(".graph-node");
      const allEdges = document.querySelectorAll(".graph-edge-group");

      allNodes.forEach(el => el.style.opacity = "0.15");
      allEdges.forEach(el => el.style.opacity = "0.08");

      let delay = 150;
      // Step 1: Characters
      setTimeout(() => {
        document.getElementById("node-char-a").style.opacity = "1";
        document.getElementById("node-char-b").style.opacity = "1";
        document.getElementById("edge-rel").style.opacity = "1";
      }, delay);

      // Step 2: Event & Location
      delay += 400;
      setTimeout(() => {
        document.getElementById("node-event").style.opacity = "1";
        document.getElementById("node-location").style.opacity = "1";
        document.getElementById("edge-part").style.opacity = "1";
        document.getElementById("edge-exp").style.opacity = "1";
        document.getElementById("edge-loc").style.opacity = "1";
      }, delay);

      // Step 3: Utterance & Claim
      delay += 400;
      setTimeout(() => {
        document.getElementById("node-utterance").style.opacity = "1";
        document.getElementById("node-claim").style.opacity = "1";
        document.getElementById("edge-said").style.opacity = "1";
        document.getElementById("edge-has").style.opacity = "1";
        document.getElementById("edge-assert").style.opacity = "1";
      }, delay);

      // Step 4: Knowledge Acquisition & Epistemic Rule
      delay += 400;
      setTimeout(() => {
        document.getElementById("node-knowledge").style.opacity = "1";
        document.getElementById("edge-acq").style.opacity = "1";
        document.getElementById("edge-about").style.opacity = "1";
      }, delay);
    }

    // ==================== SLIDE 5: PIPELINE SIMULATION ====================
    function simulatePipeline() {
      const steps = [
        document.getElementById("p-step-1"),
        document.getElementById("p-step-2"),
        document.getElementById("p-step-3"),
        document.getElementById("p-step-4"),
        document.getElementById("p-step-5")
      ];
      const logBox = document.getElementById("pipeline-trace-log");

      steps.forEach(s => s.classList.remove("active-pulse"));
      logBox.innerHTML = "[SIMULATION STARTED] Initializing LangGraph run trace...";

      steps.forEach((step, idx) => {
        setTimeout(() => {
          step.classList.add("active-pulse");
          if (idx === 0) logBox.innerHTML += "<br>[TRACE 0ms] 🟢 Step 1: Partitioned chapter into 8 paragraph units. Candidate delta extracted.";
          if (idx === 1) logBox.innerHTML += "<br>[TRACE 95ms] 🟢 Step 2: Pydantic validated entity types against schema. All constraints passed.";
          if (idx === 2) logBox.innerHTML += "<br>[TRACE 184ms] 🟢 Step 3: Atomic relationships mapped with source paragraph markers.";
          if (idx === 3) logBox.innerHTML += "<br>[TRACE 290ms] 🟢 Step 4: Physical scene pinned to Location node 'Underground Chambers'.";
          if (idx === 4) logBox.innerHTML += "<br>[TRACE 412ms] 🟢 Step 5: Neo4j transaction committed. 14 edges merged with zero errors.";
        }, (idx + 1) * 350);
      });
    }

    // ==================== SLIDE 7: TIMELINE HORIZON TOGGLE ====================
    function setTimelineHorizon(chapter) {
      state.timelineChapter = chapter;
      document.getElementById("btn-ch16").classList.toggle("active", chapter === 16);
      document.getElementById("btn-ch17").classList.toggle("active", chapter === 17);

      const box = document.getElementById("timeline-display-box");
      if (chapter === 16) {
        box.innerHTML = `
          <div style="padding: 10px 14px; background: rgba(244, 63, 94, 0.15); border: 1.5px solid var(--danger); border-radius: 8px;">
            <div class="mono" style="font-size: 13px; color: var(--danger); font-weight: 700;">CLAIM #102: "Snape is trying to steal the Stone"</div>
            <div style="font-size: 13px; color: #fecdd3; margin-top: 4px;">Status: ACTIVE_SUSPICION · Temporal validity: Ch 1 to Ch 16</div>
          </div>
          <div style="padding: 10px 14px; background: rgba(255, 255, 255, 0.05); border: 1px dashed rgba(255, 255, 255, 0.2); border-radius: 8px;">
            <div class="mono" style="font-size: 13px; color: var(--text-muted);">Quirrell Truth Horizon: UNKNOWN (Hidden by Turban Decoy)</div>
          </div>
        `;
      } else {
        box.innerHTML = `
          <div style="padding: 10px 14px; background: rgba(0,0,0,0.4); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; opacity: 0.7;">
            <div class="mono" style="font-size: 13px; color: #94a3b8; text-decoration: line-through;">CLAIM #102: "Snape is trying to steal the Stone"</div>
            <div style="font-size: 13px; color: #94a3b8; margin-top: 4px;">Status: SHATTERED_SUSPICION · Invalidated at Ch 17 Mirror Event</div>
          </div>
          <div style="padding: 10px 14px; background: var(--success-bg); border: 1.5px solid var(--success); border-radius: 8px;">
            <div class="mono" style="font-size: 13px; color: var(--success); font-weight: 700;">CLAIM #103: "Quirrell is host to Lord Voldemort"</div>
            <div style="font-size: 13px; color: #a7f3d0; margin-top: 4px;">Status: VERIFIED_ACQUISITION · Validated in Mirror Room</div>
          </div>
        `;
      }
    }

    // ==================== KEYBOARD NAVIGATION ====================
    window.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight" || e.key === " " || e.key === "PageDown") {
        e.preventDefault();
        nextScreen();
      } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
        e.preventDefault();
        prevScreen();
      } else if (e.key === "Home") {
        e.preventDefault();
        goToScreen(1);
      } else if (e.key === "End") {
        e.preventDefault();
        goToScreen(state.totalScreens);
      } else if (e.key === "n" || e.key === "N") {
        e.preventDefault();
        toggleNotes();
      }
    });

    // Initialize default states on load
    document.addEventListener("DOMContentLoaded", () => {
      renderScreen();
      focusHero('harry');
      setTimelineHorizon(16);
    });
  </script>
</body>
</html>
'''

target_path = "doc/presentation/pov-graph-slides.html"
with open(target_path, "w", encoding="utf-8") as f:
    f.write(HTML_CONTENT)

print(f"Successfully generated 8-slide presentation at {target_path} (File size: {len(HTML_CONTENT)} bytes).")
