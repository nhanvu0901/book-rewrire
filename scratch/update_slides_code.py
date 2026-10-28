import re

with open('scratch/build_8_slides.py') as f:
    content = f.read()

# Replace Slide 1 section
slide1_old = content[content.find('<!-- ========================================================\n       SLIDE 1: TITLE SLIDE'):content.find('<!-- ========================================================\n       SLIDE 2: MARVEL RIVALS')]

slide1_new = r'''<!-- ========================================================
       SLIDE 1: TITLE SLIDE (Clean, Minimalist, Elegant)
       ======================================================== -->
  <section class="screen active" data-screen="1" data-notes="Hello everyone! My name is Nhan Vu, presenting the Epistemic POV Graph for the ShiftKey Academy UP Build It! Machine Learning program. Standard generative LLMs suffer from Omniscience Bias—they know how the entire book ends and leak future twists into character voices. We built an epistemic knowledge graph in Neo4j that mathematically restricts AI memory to only what a character actually witnessed, heard, or believed at that exact timeline horizon.">
    <div class="title-screen-layout">
      <div class="title-program-badge">
        <span>⚡</span> ShiftKey Academy · UP Build It! Machine Learning · Fall 2026
      </div>
      <h1 class="title-h1">Epistemic POV Graph</h1>
      <div class="title-subheading">Retelling Sagas from Inside Distinct Character Minds</div>

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

  '''

# Replace Slide 2 section
slide2_old = content[content.find('<!-- ========================================================\n       SLIDE 2: MARVEL RIVALS'):content.find('<!-- ========================================================\n       SLIDE 3: SPRINT 1')]

slide2_new = r'''<!-- ========================================================
       SLIDE 2: CHARACTER PERSPECTIVES (Simple 5-Card Grid, Hover for Attributes)
       ======================================================== -->
  <section class="screen" data-screen="2" data-notes="Instead of treating a story as one single global timeline, our project models it as multiple subjective realities. Notice our 5 characters here: when you hover over Harry, he is the Chosen One and gifted at Quidditch, but convinced Snape is the thief. Hermione is the top of her class who solved the logic riddle, but set Snape's cloak on fire assuming eye-contact meant cursing. Ron is our chess grandmaster who sacrificed his knight. Quirrell disguises himself as a stuttering coward while hosting Voldemort. And Snape is strict and feared, but secretly protecting Harry. Every character lives in a completely different subgraph of truth.">
    <h1 class="t-title">Character Perspectives</h1>
    <div class="prompt-banner">
      <span class="prompt-label mono">PROJECT OVERVIEW:</span>
      <span class="t-caption">Modeling stories not as a global timeline, but as distinct subjective viewpoints.</span>
    </div>
    <p class="answer-line" style="font-size: 22px;">Hover over any character to inspect their distinct perception, role, and epistemic beliefs.</p>

    <div class="simple-roster-container">
      <!-- 5 Character Cards in a Balanced Horizontal Row -->
      <div class="simple-roster-row">
        <!-- 1. Harry -->
        <div class="simple-char-card active" data-char="harry" style="--c-accent: #facc15; --c-glow: rgba(250, 204, 21, 0.4);" onclick="selectHero('harry')">
          <div class="simple-card-top">
            <div class="simple-avatar-wrapper">
              <img src="assets/characters/harry.webp" alt="Harry" class="simple-avatar">
            </div>
            <div class="simple-char-name">Harry Potter</div>
            <div class="simple-char-house mono">Gryffindor · Seeker</div>
          </div>
          <div class="simple-card-divider"></div>
          <div class="simple-attributes-list">
            <div class="simple-attr-item">
              <span class="attr-bullet">⚡</span>
              <span>The Chosen One</span>
            </div>
            <div class="simple-attr-item">
              <span class="attr-bullet">🧹</span>
              <span>Good at Quidditch</span>
            </div>
            <div class="simple-attr-item">
              <span class="attr-bullet">🦁</span>
              <span>Instinctive & Loyal</span>
            </div>
            <div class="simple-attr-item highlight">
              <span class="attr-bullet">🩸</span>
              <span>Convinced Snape is the thief</span>
            </div>
          </div>
          <div class="simple-card-action">
            <span class="mono" style="font-size: 12px; color: var(--accent);">Active POV Lens</span>
          </div>
        </div>

        <!-- 2. Hermione -->
        <div class="simple-char-card" data-char="hermione" style="--c-accent: #60a5fa; --c-glow: rgba(96, 165, 250, 0.4);" onclick="selectHero('hermione')">
          <div class="simple-card-top">
            <div class="simple-avatar-wrapper">
              <img src="assets/characters/hermione.webp" alt="Hermione" class="simple-avatar">
            </div>
            <div class="simple-char-name">Hermione Granger</div>
            <div class="simple-char-house mono">Gryffindor · Top of Class</div>
          </div>
          <div class="simple-card-divider"></div>
          <div class="simple-attributes-list">
            <div class="simple-attr-item">
              <span class="attr-bullet">📚</span>
              <span>Top of the class</span>
            </div>
            <div class="simple-attr-item">
              <span class="attr-bullet">🧪</span>
              <span>Master of spells & logic</span>
            </div>
            <div class="simple-attr-item">
              <span class="attr-bullet">📜</span>
              <span>Solved 7-potion riddle</span>
            </div>
            <div class="simple-attr-item highlight">
              <span class="attr-bullet">🔥</span>
              <span>Set Snape's cloak on fire</span>
            </div>
          </div>
          <div class="simple-card-action">
            <span class="mono" style="font-size: 12px; color: #60a5fa;">Click to Select</span>
          </div>
        </div>

        <!-- 3. Ron -->
        <div class="simple-char-card" data-char="ron" style="--c-accent: #fb923c; --c-glow: rgba(251, 146, 60, 0.4);" onclick="selectHero('ron')">
          <div class="simple-card-top">
            <div class="simple-avatar-wrapper">
              <img src="assets/characters/ron.webp" alt="Ron" class="simple-avatar">
            </div>
            <div class="simple-char-name">Ron Weasley</div>
            <div class="simple-char-house mono">Gryffindor · Chess Master</div>
          </div>
          <div class="simple-card-divider"></div>
          <div class="simple-attributes-list">
            <div class="simple-attr-item">
              <span class="attr-bullet">♟️</span>
              <span>Chess Grandmaster</span>
            </div>
            <div class="simple-attr-item">
              <span class="attr-bullet">🤝</span>
              <span>Fiercely loyal friend</span>
            </div>
            <div class="simple-attr-item">
              <span class="attr-bullet">🏰</span>
              <span>Wizarding folklore</span>
            </div>
            <div class="simple-attr-item highlight">
              <span class="attr-bullet">🛡️</span>
              <span>Sacrificed knight piece</span>
            </div>
          </div>
          <div class="simple-card-action">
            <span class="mono" style="font-size: 12px; color: #fb923c;">Click to Select</span>
          </div>
        </div>

        <!-- 4. Quirrell -->
        <div class="simple-char-card" data-char="quirrell" style="--c-accent: #c084fc; --c-glow: rgba(192, 132, 252, 0.4);" onclick="selectHero('quirrell')">
          <div class="simple-card-top">
            <div class="simple-avatar-wrapper">
              <img src="assets/characters/quirrell.webp" alt="Quirrell" class="simple-avatar">
            </div>
            <div class="simple-char-name">Quirinus Quirrell</div>
            <div class="simple-char-house mono">Ravenclaw · DADA Professor</div>
          </div>
          <div class="simple-card-divider"></div>
          <div class="simple-attributes-list">
            <div class="simple-attr-item">
              <span class="attr-bullet">🧣</span>
              <span>Stuttering professor</span>
            </div>
            <div class="simple-attr-item">
              <span class="attr-bullet">🎭</span>
              <span>Feigned timidity</span>
            </div>
            <div class="simple-attr-item">
              <span class="attr-bullet">🐍</span>
              <span>Host to Lord Voldemort</span>
            </div>
            <div class="simple-attr-item highlight">
              <span class="attr-bullet">🪞</span>
              <span>Seeking the Stone in Mirror</span>
            </div>
          </div>
          <div class="simple-card-action">
            <span class="mono" style="font-size: 12px; color: #c084fc;">Click to Select</span>
          </div>
        </div>

        <!-- 5. Snape -->
        <div class="simple-char-card" data-char="snape" style="--c-accent: #4ade80; --c-glow: rgba(74, 222, 128, 0.4);" onclick="selectHero('snape')">
          <div class="simple-card-top">
            <div class="simple-avatar-wrapper">
              <img src="assets/characters/snape.webp" alt="Snape" class="simple-avatar">
            </div>
            <div class="simple-char-name">Severus Snape</div>
            <div class="simple-char-house mono">Slytherin · Potions Master</div>
          </div>
          <div class="simple-card-divider"></div>
          <div class="simple-attributes-list">
            <div class="simple-attr-item">
              <span class="attr-bullet">🧪</span>
              <span>Potions Master</span>
            </div>
            <div class="simple-attr-item">
              <span class="attr-bullet">🖤</span>
              <span>Strict, cold & feared</span>
            </div>
            <div class="simple-attr-item">
              <span class="attr-bullet">🛡️</span>
              <span>Secret guardian by oath</span>
            </div>
            <div class="simple-attr-item highlight">
              <span class="attr-bullet">🐺</span>
              <span>Bitten guarding the Stone</span>
            </div>
          </div>
          <div class="simple-card-action">
            <span class="mono" style="font-size: 12px; color: #4ade80;">Click to Select</span>
          </div>
        </div>
      </div>

      <!-- Bottom bar on Slide 2 -->
      <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 24px; padding: 14px 28px; background: rgba(13, 24, 43, 0.85); border: 1.5px solid var(--border-muted); border-radius: 16px;">
        <span class="t-caption mono" style="color: var(--text-muted);">
          Selected POV Lens: <strong id="selected-char-label" style="color: var(--accent); font-size: 16px;">Harry Potter</strong>
        </span>
        <button type="button" class="btn-pill active" onclick="goToScreen(3)">
          Continue to Sprint 1 Graph →
        </button>
      </div>
    </div>
  </section>

  '''

content = content.replace(slide1_old, slide1_new)
content = content.replace(slide2_old, slide2_new)

# Add CSS for simple roster and remove obsolete CSS
simple_roster_css = r'''
    /* ==================== SLIDE 2: SIMPLE CHARACTER ROSTER ==================== */
    .simple-roster-container {
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: center;
      min-height: 0;
    }

    .simple-roster-row {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 20px;
      align-items: stretch;
    }

    .simple-char-card {
      background: rgba(13, 24, 43, 0.85);
      border: 2px solid var(--border-muted);
      border-radius: 20px;
      padding: 24px 18px;
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      cursor: pointer;
      position: relative;
      overflow: hidden;
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .simple-char-card:hover, .simple-char-card.active {
      transform: translateY(-8px);
      border-color: var(--c-accent, var(--border-bright));
      background: rgba(18, 32, 58, 0.95);
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.5), 0 0 24px var(--c-glow, rgba(56, 189, 248, 0.3));
    }

    .simple-card-top {
      display: flex;
      flex-direction: column;
      align-items: center;
      width: 100%;
    }

    .simple-avatar-wrapper {
      width: 90px;
      height: 90px;
      border-radius: 50%;
      overflow: hidden;
      border: 3px solid var(--c-accent, var(--border-bright));
      box-shadow: 0 0 16px var(--c-glow, rgba(56, 189, 248, 0.3));
      margin-bottom: 14px;
      transition: transform 0.3s;
    }

    .simple-char-card:hover .simple-avatar-wrapper, .simple-char-card.active .simple-avatar-wrapper {
      transform: scale(1.08);
    }

    .simple-avatar {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .simple-char-name {
      font-size: 20px;
      font-weight: 800;
      color: #fff;
      margin-bottom: 4px;
      white-space: nowrap;
    }

    .simple-char-house {
      font-size: 13px;
      color: var(--text-muted);
      margin-bottom: 12px;
    }

    .simple-card-divider {
      width: 40px;
      height: 2px;
      background: var(--c-accent, var(--border-muted));
      opacity: 0.5;
      margin-bottom: 16px;
      transition: width 0.3s;
    }

    .simple-char-card:hover .simple-card-divider, .simple-char-card.active .simple-card-divider {
      width: 70px;
      opacity: 1;
    }

    .simple-attributes-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
      width: 100%;
      opacity: 0.35;
      transform: translateY(4px);
      transition: all 0.3s ease;
      flex: 1;
      justify-content: center;
    }

    .simple-char-card:hover .simple-attributes-list, .simple-char-card.active .simple-attributes-list {
      opacity: 1;
      transform: translateY(0);
    }

    .simple-attr-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      background: rgba(8, 14, 24, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 8px;
      font-size: 13px;
      color: #e2e8f0;
      text-align: left;
    }

    .simple-attr-item.highlight {
      border-color: var(--c-accent, var(--accent));
      background: rgba(250, 204, 21, 0.08);
      color: #fff;
      font-weight: 600;
    }

    .attr-bullet {
      font-size: 14px;
      flex-shrink: 0;
    }

    .simple-card-action {
      margin-top: 16px;
      padding-top: 10px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      width: 100%;
    }
'''

content = content.replace('/* ==================== SLIDE 2: MARVEL RIVALS CHARACTER SELECTION ==================== */', simple_roster_css)

# Update JS function selectHero
js_select_old = r'''    function selectHero(heroKey) {
      state.selectedHero = heroKey;
      inspectHero(heroKey);

      const data = HERO_DATA[heroKey];
      document.getElementById("hud-avatar").src = data.avatar;
      document.getElementById("hud-lens-name").textContent = data.name;

      // Update Node A in Slide 3 Draw.io Graph if Harry or selected
      const nodeASub = document.querySelector("#node-char-a .svg-node-sub");
      if (nodeASub) {
        nodeASub.textContent = `${heroKey.toUpperCase()} · POV`;
      }
    }'''

js_select_new = r'''    function selectHero(heroKey) {
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
    }'''

content = content.replace(js_select_old, js_select_new)

with open('scratch/build_8_slides.py', 'w') as f:
    f.write(content)

print("Updated scratch/build_8_slides.py with clean Slide 1 and simple hover-card Slide 2.")
