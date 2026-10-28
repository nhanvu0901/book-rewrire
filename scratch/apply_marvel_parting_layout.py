import re

with open('scratch/build_8_slides.py') as f:
    c = f.read()

# 1. Update Slide 2 CSS
css_old_start = c.find('/* ==================== SLIDE 2:')
css_old_end = c.find('/* ==================== SLIDE 3: SPRINT 1')

new_slide2_css = r'''/* ==================== SLIDE 2: MARVEL RIVALS CINEMATIC SELECTION (PARTING LINEUP) ==================== */
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
'''

c = c[:css_old_start] + new_slide2_css + c[css_old_end:]

# 2. Update Slide 2 HTML
html_old_start = c.find('<!-- ========================================================\n       SLIDE 2:')
html_old_end = c.find('<!-- ========================================================\n       SLIDE 3: SPRINT 1')

new_slide2_html = r'''<!-- ========================================================
       SLIDE 2: MARVEL RIVALS CINEMATIC CHARACTER SELECTION (PARTING LINEUP)
       ======================================================== -->
  <section class="screen" data-screen="2" data-notes="Instead of treating a story as one single global timeline, our project models it as multiple subjective realities. Notice our four characters standing freely on stage. When you hover over each hero, the lineup gracefully parts and an elegant floating game HUD reveals their perspective, epistemic bias, and cognitive attributes. Harry's view is driven by intense gut suspicion, Hermione by causal logic, Ron by strategic loyalty, and Quirrell by calculated deception. Click any character to lock in their point of view.">
    <div class="cinematic-select-stage">
      <div class="cinematic-header">
        <h1 class="cinematic-title">Choose Your Character</h1>
        <p class="cinematic-sub">Hover over any character to reveal their perspective and abilities. Click to lock in their point of view.</p>
      </div>

      <div class="cinematic-lineup-area" id="cinematic-lineup">
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
             onmouseenter="onHeroHover('harry')" onmouseleave="onHeroLeave()" onclick="onHeroClick('harry')">
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
             onmouseenter="onHeroHover('hermione')" onmouseleave="onHeroLeave()" onclick="onHeroClick('hermione')">
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
             onmouseenter="onHeroHover('ron')" onmouseleave="onHeroLeave()" onclick="onHeroClick('ron')">
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
             onmouseenter="onHeroHover('quirrell')" onmouseleave="onHeroLeave()" onclick="onHeroClick('quirrell')">
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

  '''

c = c[:html_old_start] + new_slide2_html + c[html_old_end:]

# 3. Update JavaScript with GSAP Parting Layout
js_search = '// ==================== SLIDE 2 CINEMATIC MARVEL RIVALS SELECTION LOGIC ===================='
js_end = c.find('function goToScreen(index)')

new_js = r'''// ==================== SLIDE 2 CINEMATIC MARVEL RIVALS SELECTION LOGIC ====================
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

    function onHeroLeave() {
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

    '''

c = c.replace(c[c.find(js_search):js_end], new_js)

with open('scratch/build_8_slides.py', 'w') as f:
    f.write(c)

# Generate target HTML
import subprocess
subprocess.check_call(['python3', 'scratch/build_8_slides.py'])
print("Successfully applied parting lineup layout to pov-graph-slides.html!")
