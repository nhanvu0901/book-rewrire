import re

with open('scratch/build_8_slides.py') as f:
    c = f.read()

# 1. Update Slide 2 CSS to original character-slot design
css_old_start = c.find('/* ==================== SLIDE 2: SIMPLE CHARACTER ROSTER ==================== */')
css_old_end = c.find('/* ==================== SLIDE 3: SPRINT 1 (DRAW.IO GRAPH) ==================== */')

new_slide2_css = r'''/* ==================== SLIDE 2: CLASSIC CHARACTER ROSTER (NO ATTRIBUTES) ==================== */
    .roster-grid {
      display: grid;
      grid-template-columns: repeat(4, 370px);
      gap: 32px;
      justify-content: center;
      align-items: end;
      height: 600px;
      margin-top: 20px;
    }

    .character-slot {
      position: relative;
      height: 580px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: flex-end;
      cursor: pointer;
      outline: none;
      transition: all 0.3s ease;
    }

    .feet-glow {
      position: absolute;
      bottom: 110px;
      left: 50%;
      transform: translateX(-50%) scale(0.85);
      width: 240px;
      height: 65px;
      border-radius: 50%;
      background: radial-gradient(ellipse at center, rgba(251, 191, 36, 0.7) 0%, rgba(251, 191, 36, 0.2) 50%, transparent 75%);
      opacity: 0;
      pointer-events: none;
      z-index: 2;
      transition: opacity 0.3s ease, transform 0.3s ease;
    }

    .character-figure {
      position: relative;
      z-index: 4;
      height: 420px;
      margin-bottom: -20px;
      display: flex;
      align-items: flex-end;
      justify-content: center;
      transform-origin: 50% 95%;
      pointer-events: none;
      filter: drop-shadow(0 16px 26px rgba(0, 0, 0, 0.75));
      transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), filter 0.3s ease;
    }

    .character-figure img {
      height: 100%;
      width: auto;
      display: block;
      pointer-events: none;
    }

    .character-slot:hover .character-figure,
    .character-slot.selected .character-figure {
      transform: translateY(-16px) scale(1.05);
      filter: drop-shadow(0 22px 34px rgba(0, 0, 0, 0.85)) drop-shadow(0 0 16px var(--accent-glow));
    }

    .character-slot:hover .feet-glow,
    .character-slot.selected .feet-glow {
      opacity: 0.85;
      transform: translateX(-50%) scale(1.05);
    }

    .name-plate {
      position: relative;
      z-index: 3;
      width: 100%;
      min-height: 120px;
      padding: 18px 20px 14px;
      background: rgba(15, 25, 52, 0.88);
      border: 3px solid #64748b;
      border-radius: 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 4px;
      box-shadow: 0 14px 32px rgba(0, 0, 0, 0.65);
      transition: all 0.3s ease;
    }

    .character-slot.house-gryffindor .name-plate {
      border-color: #ef4444;
      box-shadow: inset 0 0 0 2px rgba(250, 204, 21, 0.6), 0 14px 32px rgba(0, 0, 0, 0.65);
    }

    .character-slot.house-neutral .name-plate {
      border-color: #c084fc;
      box-shadow: inset 0 0 0 2px rgba(192, 132, 252, 0.6), 0 14px 32px rgba(0, 0, 0, 0.65);
    }

    .character-slot:hover .name-plate,
    .character-slot.selected .name-plate {
      border-color: var(--accent);
      background: rgba(22, 36, 70, 0.96);
      box-shadow: 0 0 28px var(--accent-glow), inset 0 0 0 2.5px var(--accent);
      transform: translateY(-4px);
    }

    .ready-badge {
      position: absolute;
      top: -14px;
      right: 18px;
      padding: 2px 12px;
      border-radius: 8px;
      background: #451a03;
      border: 1.5px solid var(--accent);
      color: var(--accent);
      font-size: 11px;
      font-weight: 800;
      opacity: 0;
      transition: opacity 0.25s ease;
      z-index: 6;
    }

    .character-slot.selected .ready-badge {
      opacity: 1;
    }

    .plate-name {
      color: #f8fafc;
      text-align: center;
      font-size: 24px;
      font-weight: 800;
      line-height: 1.2;
    }

    .plate-tag {
      color: var(--accent);
      text-align: center;
      font-size: 13px;
      font-weight: 700;
      opacity: 0;
      transition: opacity 0.25s ease;
      font-family: var(--font-mono);
    }

    .character-slot:hover .plate-tag,
    .character-slot.selected .plate-tag {
      opacity: 1;
    }
'''

c = c[:css_old_start] + new_slide2_css + c[css_old_end:]

# 2. Update Slide 2 HTML
html_old_start = c.find('<!-- ========================================================\n       SLIDE 2: CHARACTER PERSPECTIVES')
html_old_end = c.find('<!-- ========================================================\n       SLIDE 3: SPRINT 1')

new_slide2_html = r'''<!-- ========================================================
       SLIDE 2: CHOOSE YOUR CHARACTER (Classic 4-Hero Slot Grid, No Attributes)
       ======================================================== -->
  <section class="screen" data-screen="2" data-notes="Instead of treating a story as one single global timeline, our project models it as multiple subjective realities. Choose any character below to explore their point of view. Harry Potter, Hermione Granger, Ron Weasley, or Professor Quirrell. Each character experiences Hogwarts through a completely different subgraph of truth, bias, and suspicion. Click to lock in their perspective.">
    <h1 class="t-title">Choose Your Character</h1>
    <div class="prompt-banner">
      <span class="prompt-label mono">PROJECT OVERVIEW:</span>
      <span class="t-caption">Modeling stories not as a global timeline, but as distinct subjective viewpoints.</span>
    </div>
    <p class="answer-line" style="font-size: 22px;">Select a character to explore the story through their distinct point of view.</p>

    <div class="roster-grid">
      <!-- 1. Harry -->
      <div class="character-slot house-gryffindor selected" tabindex="0" data-character="harry" onclick="selectSlot('harry')">
        <div class="feet-glow"></div>
        <div class="character-figure">
          <img src="assets/characters/harry.webp" alt="Harry Potter">
        </div>
        <div class="name-plate">
          <span class="ready-badge mono">SELECTED</span>
          <span class="plate-name">Harry Potter</span>
          <span class="plate-tag mono">The Seeker</span>
        </div>
      </div>

      <!-- 2. Hermione -->
      <div class="character-slot house-gryffindor" tabindex="0" data-character="hermione" onclick="selectSlot('hermione')">
        <div class="feet-glow"></div>
        <div class="character-figure">
          <img src="assets/characters/hermione.webp" alt="Hermione Granger">
        </div>
        <div class="name-plate">
          <span class="ready-badge mono">SELECTED</span>
          <span class="plate-name">Hermione Granger</span>
          <span class="plate-tag mono">The Scholar</span>
        </div>
      </div>

      <!-- 3. Ron -->
      <div class="character-slot house-gryffindor" tabindex="0" data-character="ron" onclick="selectSlot('ron')">
        <div class="feet-glow"></div>
        <div class="character-figure">
          <img src="assets/characters/ron.webp" alt="Ron Weasley">
        </div>
        <div class="name-plate">
          <span class="ready-badge mono">SELECTED</span>
          <span class="plate-name">Ron Weasley</span>
          <span class="plate-tag mono">The Strategist</span>
        </div>
      </div>

      <!-- 4. Quirrell -->
      <div class="character-slot house-neutral" tabindex="0" data-character="quirrell" onclick="selectSlot('quirrell')">
        <div class="feet-glow"></div>
        <div class="character-figure">
          <img src="assets/characters/quirrell.webp" alt="Professor Quirrell">
        </div>
        <div class="name-plate">
          <span class="ready-badge mono">SELECTED</span>
          <span class="plate-name">Professor Quirrell</span>
          <span class="plate-tag mono">Carries a secret</span>
        </div>
      </div>
    </div>
  </section>

  '''

c = c[:html_old_start] + new_slide2_html + c[html_old_end:]

# 3. Add JS function selectSlot
js_insert_point = c.find('function goToScreen(index)')
new_js = r'''function selectSlot(charKey) {
      state.selectedHero = charKey;
      const data = HERO_DATA[charKey];
      if (data) {
        document.getElementById("hud-avatar").src = data.avatar;
        document.getElementById("hud-lens-name").textContent = data.name;
      }

      document.querySelectorAll(".character-slot").forEach(slot => {
        const isMatch = slot.dataset.character === charKey;
        slot.classList.toggle("selected", isMatch);
      });

      // Update Node A in Slide 3 Draw.io Graph
      const nodeASub = document.querySelector("#node-char-a .svg-node-sub");
      if (nodeASub) {
        nodeASub.textContent = `${charKey.toUpperCase()} · POV`;
      }
    }

    '''

c = c[:js_insert_point] + new_js + c[js_insert_point:]

with open('scratch/build_8_slides.py', 'w') as f:
    f.write(c)

print("Reverted Slide 2 to classic 4-character slot design (no attributes, just character figures and name plates).")
