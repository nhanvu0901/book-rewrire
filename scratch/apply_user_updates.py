with open('scratch/build_8_slides.py') as f:
    c = f.read()

# 1. Update Slide 1 Title & Subtitle
c = c.replace('<h1 class="title-h1">Epistemic POV Graph</h1>', '<h1 class="title-h1">POV Graph</h1>')
c = c.replace('<div class="title-subheading">Retelling Sagas from Inside Distinct Character Minds</div>',
              '<div class="title-subheading">AI Storytelling from Every Perspective</div>')

# 2. Update CSS for 4-column roster
c = c.replace('grid-template-columns: repeat(5, 1fr);', 'grid-template-columns: repeat(4, 1fr); gap: 24px;')

# 3. Update Slide 2 HTML to 4 characters (Harry, Hermione, Ron, Quirrell)
slide2_start = c.find('<!-- ========================================================\n       SLIDE 2: CHARACTER PERSPECTIVES')
slide2_end = c.find('<!-- ========================================================\n       SLIDE 3: SPRINT 1')

new_slide2 = r'''<!-- ========================================================
       SLIDE 2: CHARACTER PERSPECTIVES (Simple 4-Character Grid, Hover for Attributes)
       ======================================================== -->
  <section class="screen" data-screen="2" data-notes="Instead of treating a story as one single global timeline, our project models it as multiple subjective realities. Notice our 4 characters here: when you hover over Harry, he is the Chosen One and gifted at Quidditch, but convinced Snape is the thief. Hermione is the top of her class who solved the logic riddle, but set Snape's cloak on fire assuming eye-contact meant cursing. Ron is our chess grandmaster who sacrificed his knight. Quirrell disguises himself as a stuttering coward while secretly hosting Voldemort. Every character lives in a completely different subgraph of truth.">
    <h1 class="t-title">Character Perspectives</h1>
    <div class="prompt-banner">
      <span class="prompt-label mono">PROJECT OVERVIEW:</span>
      <span class="t-caption">Modeling stories not as a global timeline, but as distinct subjective viewpoints.</span>
    </div>
    <p class="answer-line" style="font-size: 22px;">Hover over any character to inspect their distinct perception, role, and epistemic beliefs.</p>

    <div class="simple-roster-container">
      <!-- 4 Character Cards in a Balanced Horizontal Row -->
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

c = c[:slide2_start] + new_slide2 + c[slide2_end:]

# 4. In Slide 8 quick replay buttons, remove Snape button to match 4-hero roster
c = c.replace('<button type="button" class="btn-pill" onclick="selectHero(\'snape\'); goToScreen(2)">Snape</button>', '')

with open('scratch/build_8_slides.py', 'w') as f:
    f.write(c)

print("Applied user updates: Title 'POV Graph', Subtitle 'AI Storytelling from Every Perspective', and 4-hero roster on Slide 2.")
