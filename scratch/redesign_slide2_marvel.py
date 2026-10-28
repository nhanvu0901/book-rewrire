import re

with open('scratch/build_8_slides.py') as f:
    c = f.read()

# 1. Add GSAP vendor script in <head> if not present
if 'assets/vendor/gsap.min.js' not in c:
    head_tag = '<meta name="viewport" content="width=device-width, initial-scale=1">'
    c = c.replace(head_tag, head_tag + '\n  <script src="assets/vendor/gsap.min.js"></script>')

# 2. Update Slide 2 CSS
css_old_start = c.find('/* ==================== SLIDE 2:')
css_old_end = c.find('/* ==================== SLIDE 3: SPRINT 1')

new_slide2_css = r'''/* ==================== SLIDE 2: MARVEL RIVALS CINEMATIC CHARACTER SELECTION ==================== */
    .cinematic-select-stage {
      position: absolute;
      top: 130px;
      left: 96px;
      right: 96px;
      bottom: 80px;
      display: flex;
      flex-direction: column;
      justify-content: flex-start;
      z-index: 10;
    }

    .cinematic-header {
      margin-bottom: 8px;
    }

    .cinematic-title {
      font-size: 64px;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #ffffff;
      line-height: 1.1;
      text-shadow: 0 4px 20px rgba(0, 0, 0, 0.7);
    }

    .cinematic-sub {
      font-size: 22px;
      color: #94a3b8;
      margin-top: 8px;
      font-weight: 500;
    }

    .cinematic-lineup-area {
      position: relative;
      flex: 1;
      width: 100%;
      height: 700px;
      margin-top: 20px;
      display: flex;
      align-items: flex-end;
      justify-content: center;
      gap: 56px;
    }

    /* Ambient atmospheric floor light */
    .stage-floor-light {
      position: absolute;
      bottom: 60px;
      left: 5%;
      right: 5%;
      height: 140px;
      background: radial-gradient(ellipse at 50% 100%, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.3) 50%, transparent 80%);
      pointer-events: none;
      z-index: 1;
    }

    /* Standee hero container */
    .cinematic-hero {
      position: relative;
      width: 320px;
      height: 640px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: flex-end;
      cursor: pointer;
      outline: none;
      z-index: 5;
      transition: opacity 0.35s ease, filter 0.35s ease, transform 0.35s ease;
      transform-origin: 50% 90%;
    }

    /* Ground shadow */
    .hero-ground-shadow {
      position: absolute;
      bottom: 110px;
      left: 50%;
      transform: translateX(-50%);
      width: 220px;
      height: 42px;
      border-radius: 50%;
      background: radial-gradient(ellipse at center, rgba(0, 0, 0, 0.88) 0%, rgba(0, 0, 0, 0.45) 45%, transparent 75%);
      pointer-events: none;
      z-index: 2;
      transition: transform 0.35s ease, opacity 0.35s ease;
    }

    /* Magical summoning floor ring */
    .hero-magic-ring {
      position: absolute;
      bottom: 95px;
      left: 50%;
      transform: translateX(-50%) rotateX(68deg);
      width: 260px;
      height: 260px;
      border-radius: 50%;
      border: 2px dashed var(--char-accent, #fbbf24);
      box-shadow: 0 0 30px var(--char-glow, rgba(251, 191, 36, 0.3)), inset 0 0 20px var(--char-glow, rgba(251, 191, 36, 0.2));
      opacity: 0;
      pointer-events: none;
      z-index: 3;
      transition: opacity 0.4s ease, border-color 0.4s ease;
    }

    .cinematic-hero.is-focused .hero-magic-ring {
      opacity: 0.9;
      animation: spinMagicRing 14s linear infinite;
    }

    @keyframes spinMagicRing {
      0% { transform: translateX(-50%) rotateX(68deg) rotate(0deg); }
      100% { transform: translateX(-50%) rotateX(68deg) rotate(360deg); }
    }

    /* Hero aura behind the character */
    .hero-ambient-aura {
      position: absolute;
      bottom: 120px;
      left: 50%;
      transform: translateX(-50%);
      width: 320px;
      height: 460px;
      border-radius: 50%;
      background: radial-gradient(ellipse at center, var(--char-glow, rgba(251, 191, 36, 0.25)) 0%, transparent 70%);
      opacity: 0;
      pointer-events: none;
      z-index: 3;
      transition: opacity 0.4s ease;
      filter: blur(12px);
    }

    .cinematic-hero.is-focused .hero-ambient-aura {
      opacity: 1;
    }

    /* Character figure */
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
    .cinematic-lineup-area.has-focus .cinematic-hero:not(.is-focused) {
      opacity: 0.35;
      filter: brightness(0.6) saturate(0.5) blur(0.5px);
      transform: scale(0.96);
    }

    .cinematic-hero.is-focused .hero-figure-wrap {
      transform: translateY(-16px) scale(1.1);
      filter: drop-shadow(0 22px 36px rgba(0, 0, 0, 0.88)) drop-shadow(0 0 24px var(--char-glow, rgba(251, 191, 36, 0.45)));
    }

    .cinematic-hero.is-focused .hero-ground-shadow {
      transform: translateX(-50%) scale(1.18);
      opacity: 0.95;
    }

    /* Minimal Floating Name Label beneath feet (No Card / No Box) */
    .hero-label-wrap {
      position: relative;
      z-index: 8;
      margin-top: 16px;
      margin-bottom: 24px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 3px;
      pointer-events: none;
      text-align: center;
    }

    .hero-name-text {
      font-size: 26px;
      font-weight: 800;
      letter-spacing: 0.03em;
      color: #f1f5f9;
      text-transform: uppercase;
      text-shadow: 0 3px 12px rgba(0, 0, 0, 0.9);
      transition: color 0.3s ease, text-shadow 0.3s ease;
    }

    .cinematic-hero.is-focused .hero-name-text {
      color: #ffffff;
      text-shadow: 0 0 18px var(--char-glow, rgba(251, 191, 36, 0.6)), 0 4px 14px rgba(0, 0, 0, 0.9);
    }

    .hero-role-text {
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.14em;
      color: var(--char-accent, #fbbf24);
      text-shadow: 0 0 10px var(--char-glow, rgba(251, 191, 36, 0.3));
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
      padding: 3px 12px;
      border-radius: 999px;
      margin-top: 4px;
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
      top: 18px;
      width: 440px;
      background: linear-gradient(145deg, rgba(12, 19, 38, 0.96) 0%, rgba(6, 10, 22, 0.98) 100%);
      border: 1.5px solid var(--hud-border, rgba(251, 191, 36, 0.45));
      border-radius: 20px;
      padding: 24px 26px;
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.9), 0 0 40px var(--hud-glow, rgba(251, 191, 36, 0.28));
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
      margin-bottom: 6px;
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
      margin-bottom: 14px;
    }

    /* Tag badges row */
    .hud-tags-row {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      margin-bottom: 16px;
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
      margin: 14px 0;
    }

    .hud-section-label {
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.14em;
      color: #94a3b8;
      margin-bottom: 10px;
    }

    /* Animated Stat Bars */
    .hud-stats-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .hud-stat-item {
      display: flex;
      flex-direction: column;
      gap: 4px;
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
      margin-bottom: 10px;
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
      margin-top: 8px;
    }

    .hud-footer {
      margin-top: 14px;
      padding-top: 10px;
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

# 3. Update Slide 2 HTML
html_old_start = c.find('<!-- ========================================================\n       SLIDE 2: CHOOSE YOUR CHARACTER')
html_old_end = c.find('<!-- ========================================================\n       SLIDE 3: SPRINT 1')

new_slide2_html = r'''<!-- ========================================================
       SLIDE 2: MARVEL RIVALS CINEMATIC CHARACTER SELECTION (NO CARDS, FREESTANDING)
       ======================================================== -->
  <section class="screen" data-screen="2" data-notes="Instead of treating a story as one single global timeline, our project models it as multiple subjective realities. Notice our four characters standing freely on stage. When you hover over each hero, an elegant floating game HUD reveals their perspective, epistemic bias, and cognitive attributes. Harry's view is driven by intense gut suspicion, Hermione by causal logic, Ron by strategic loyalty, and Quirrell by calculated deception. Click any character to lock in their point of view.">
    <div class="cinematic-select-stage">
      <div class="cinematic-header">
        <h1 class="cinematic-title">Choose Your Character</h1>
        <p class="cinematic-sub">Hover over any character to reveal their perspective and abilities. Click to lock in their point of view.</p>
      </div>

      <div class="cinematic-lineup-area" id="cinematic-lineup">
        <div class="stage-floor-light"></div>

        <!-- 1. Harry -->
        <div class="cinematic-hero is-focused selected" data-hero="harry" tabindex="0"
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
        <div class="cinematic-hero" data-hero="hermione" tabindex="0"
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
        <div class="cinematic-hero" data-hero="ron" tabindex="0"
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
        <div class="cinematic-hero" data-hero="quirrell" tabindex="0"
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

# 4. Update JavaScript for Slide 2
js_search = 'function selectSlot(charKey) {'
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
        hud_x: 480, // Right of Harry
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
        hud_x: 820, // Right of Hermione
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
        hud_x: 520, // Left of Ron
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
        hud_x: 880, // Left of Quirrell
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

    let activeHoverHero = null;

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

      // Position HUD horizontally beside hero
      hud.style.left = `${cfg.hud_x}px`;

      // GSAP Animation Reveal
      if (window.gsap) {
        gsap.killTweensOf(hud);
        gsap.fromTo(hud,
          { opacity: 0, y: 15, scale: 0.96 },
          { opacity: 1, y: 0, scale: 1, duration: 0.35, ease: "power2.out" }
        );

        // Animate stat bars
        setTimeout(() => {
          hud.querySelectorAll(".hud-bar-fill").forEach(bar => {
            bar.style.width = bar.dataset.target;
          });
        }, 50);

        // Animate tags stagger
        gsap.fromTo(tagsContainer.children,
          { opacity: 0, y: 6 },
          { opacity: 1, y: 0, stagger: 0.05, duration: 0.25, ease: "power1.out" }
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
      const lineup = document.getElementById("cinematic-lineup");
      lineup.classList.add("has-focus");

      document.querySelectorAll(".cinematic-hero").forEach(el => {
        el.classList.toggle("is-focused", el.dataset.hero === heroKey);
      });

      const isLocked = (state.selectedHero === heroKey);
      updateFloatingHud(heroKey, isLocked);
    }

    function onHeroLeave() {
      activeHoverHero = null;
      // Return to selected hero
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

      // Trigger selection shockwave via GSAP if available
      if (window.gsap) {
        const selectedHeroEl = document.querySelector(`.cinematic-hero[data-hero="${heroKey}"]`);
        if (selectedHeroEl) {
          const ring = selectedHeroEl.querySelector(".hero-magic-ring");
          gsap.fromTo(ring,
            { scale: 0.8, opacity: 1 },
            { scale: 1.25, opacity: 0.85, duration: 0.45, ease: "back.out(1.8)" }
          );
        }
      }
    }

    function focusHero(heroKey) {
      const lineup = document.getElementById("cinematic-lineup");
      lineup.classList.add("has-focus");

      document.querySelectorAll(".cinematic-hero").forEach(el => {
        const isMatch = (el.dataset.hero === heroKey);
        el.classList.toggle("is-focused", isMatch);
        el.classList.toggle("selected", isMatch);
      });

      updateFloatingHud(heroKey, true);
    }

    '''

c = c.replace(c[c.find(js_search):js_end], new_js)

# Also ensure DOMContentLoaded calls focusHero('harry')
c = c.replace("selectSlot('harry');", "focusHero('harry');")
c = c.replace("inspectHero(\"harry\");", "focusHero('harry');")

with open('scratch/build_8_slides.py', 'w') as f:
    f.write(c)

# Run build_8_slides.py to generate target HTML
import subprocess
subprocess.check_call(['python3', 'scratch/build_8_slides.py'])
print("Successfully generated pov-graph-slides.html with Marvel Rivals cinematic selection!")
