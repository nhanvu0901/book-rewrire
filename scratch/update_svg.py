import re

new_svg = r'''          <!-- Exact Draw.io Graph in SVG (Clean, Spacious, Balanced 2-Tier Architecture, No Colons) -->
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
                <rect x="-75" y="-15" width="150" height="30" rx="15" fill="#102034" stroke="#73BFFF" stroke-width="1.8"/>
                <text x="0" y="5" text-anchor="middle" fill="#73BFFF" class="t-caption mono" font-weight="bold" font-size="14">RELATES TO</text>
              </g>
            </g>

            <!-- e_exp: Character A -> Event (EXPERIENCED) -->
            <g id="edge-exp" class="graph-edge-group">
              <line x1="270" y1="205" x2="600" y2="385" stroke="#74DEBF" stroke-width="3" marker-end="url(#arr-teal)" class="flowing-edge"/>
              <g transform="translate(435, 295)">
                <rect x="-75" y="-15" width="150" height="30" rx="15" fill="#102034" stroke="#74DEBF" stroke-width="1.8"/>
                <text x="0" y="5" text-anchor="middle" fill="#74DEBF" class="t-caption mono" font-weight="bold" font-size="14">EXPERIENCED</text>
              </g>
            </g>

            <!-- e_acq: Character A -> KnowledgeAcquisition (ACQUIRED) -->
            <g id="edge-acq" class="graph-edge-group">
              <line x1="225" y1="230" x2="225" y2="355" stroke="#D0A7FF" stroke-width="3.5" marker-end="url(#arr-magenta)" class="flowing-edge"/>
              <g transform="translate(225, 295)">
                <rect x="-55" y="-15" width="110" height="30" rx="15" fill="#102034" stroke="#D0A7FF" stroke-width="1.8"/>
                <text x="0" y="5" text-anchor="middle" fill="#D0A7FF" class="t-caption mono" font-weight="bold" font-size="14">ACQUIRED</text>
              </g>
            </g>

            <!-- e_part: Character B -> Event (PARTICIPATED IN) -->
            <g id="edge-part" class="graph-edge-group">
              <line x1="745" y1="225" x2="685" y2="360" stroke="#74DEBF" stroke-width="3" marker-end="url(#arr-teal)" class="flowing-edge"/>
              <g transform="translate(775, 285)">
                <rect x="-80" y="-15" width="160" height="30" rx="15" fill="#102034" stroke="#74DEBF" stroke-width="1.8"/>
                <text x="0" y="5" text-anchor="middle" fill="#74DEBF" class="t-caption mono" font-weight="bold" font-size="13">PARTICIPATED IN</text>
              </g>
            </g>

            <!-- e_said: Character B -> Utterance (SAID) -->
            <g id="edge-said" class="graph-edge-group">
              <path d="M 840 150 C 1020 110, 1220 110, 1370 145" fill="none" stroke="#B8ABFF" stroke-width="3" marker-end="url(#arr-purple)" class="flowing-edge"/>
              <g transform="translate(1105, 105)">
                <rect x="-50" y="-15" width="100" height="30" rx="15" fill="#102034" stroke="#B8ABFF" stroke-width="1.8"/>
                <text x="0" y="5" text-anchor="middle" fill="#B8ABFF" class="t-caption mono" font-weight="bold" font-size="14">SAID</text>
              </g>
            </g>

            <!-- e_loc: Event -> Location (OCCURRED AT) -->
            <g id="edge-loc" class="graph-edge-group">
              <line x1="720" y1="425" x2="1010" y2="425" stroke="#F1BD8B" stroke-width="3" marker-end="url(#arr-amber)" class="flowing-edge"/>
              <g transform="translate(865, 425)">
                <rect x="-70" y="-15" width="140" height="30" rx="15" fill="#102034" stroke="#F1BD8B" stroke-width="1.8"/>
                <text x="0" y="5" text-anchor="middle" fill="#F1BD8B" class="t-caption mono" font-weight="bold" font-size="14">OCCURRED AT</text>
              </g>
            </g>

            <!-- e_has: Event -> Claim (HAS CLAIM) -->
            <g id="edge-has" class="graph-edge-group">
              <path d="M 700 380 C 850 310, 1220 310, 1380 385" fill="none" stroke="#F8CF85" stroke-width="3" marker-end="url(#arr-gold)" class="flowing-edge"/>
              <g transform="translate(1040, 310)">
                <rect x="-60" y="-15" width="120" height="30" rx="15" fill="#102034" stroke="#F8CF85" stroke-width="1.8"/>
                <text x="0" y="5" text-anchor="middle" fill="#F8CF85" class="t-caption mono" font-weight="bold" font-size="14">HAS CLAIM</text>
              </g>
            </g>

            <!-- e_assert: Utterance -> Claim (ASSERTS) -->
            <g id="edge-assert" class="graph-edge-group">
              <line x1="1440" y1="230" x2="1440" y2="355" stroke="#D0A7FF" stroke-width="3" marker-end="url(#arr-purple)" class="flowing-edge"/>
              <g transform="translate(1440, 295)">
                <rect x="-50" y="-15" width="100" height="30" rx="15" fill="#102034" stroke="#D0A7FF" stroke-width="1.8"/>
                <text x="0" y="5" text-anchor="middle" fill="#D0A7FF" class="t-caption mono" font-weight="bold" font-size="14">ASSERTS</text>
              </g>
            </g>

            <!-- e_about: KnowledgeAcquisition -> Claim (ABOUT) -->
            <g id="edge-about" class="graph-edge-group">
              <path d="M 290 445 C 560 515, 1100 515, 1375 445" fill="none" stroke="#FFE18B" stroke-width="3.5" marker-end="url(#arr-yellow)" class="flowing-edge"/>
              <g transform="translate(830, 505)">
                <rect x="-85" y="-16" width="170" height="32" rx="16" fill="#102034" stroke="#FFE18B" stroke-width="1.8"/>
                <text x="0" y="5" text-anchor="middle" fill="#FFE18B" class="t-caption mono" font-weight="bold" font-size="15">ABOUT (Truth)</text>
              </g>
            </g>

            <!-- ==================== 7 NODES (SPACIOUS, HIGH LEGIBILITY, NO COLONS) ==================== -->
            <!-- Node 1: Character A · POV -->
            <g class="graph-node" id="node-char-a" transform="translate(225, 160)">
              <circle cx="0" cy="0" r="68" fill="#152E4D" stroke="#65B9FF" stroke-width="3"/>
              <text x="0" y="-23" text-anchor="middle" fill="#FFFFFF" class="t-body" font-size="19">Character</text>
              <text x="0" y="-2" text-anchor="middle" fill="#65B9FF" class="t-caption mono" font-weight="bold">A · POV</text>
              <line x1="-40" y1="7" x2="40" y2="7" stroke="#65B9FF" stroke-opacity="0.5" stroke-width="1.5"/>
              <text x="0" y="24" text-anchor="middle" fill="#CBD5E1" font-size="13" class="mono">name · role</text>
              <text x="0" y="42" text-anchor="middle" fill="#94A3B8" font-size="12" class="mono">perspective</text>
            </g>

            <!-- Node 2: Character B -->
            <g class="graph-node" id="node-char-b" transform="translate(770, 160)">
              <circle cx="0" cy="0" r="68" fill="#152E4D" stroke="#65B9FF" stroke-width="3"/>
              <text x="0" y="-23" text-anchor="middle" fill="#FFFFFF" class="t-body" font-size="19">Character</text>
              <text x="0" y="-2" text-anchor="middle" fill="#65B9FF" class="t-caption mono" font-weight="bold">B</text>
              <line x1="-40" y1="7" x2="40" y2="7" stroke="#65B9FF" stroke-opacity="0.5" stroke-width="1.5"/>
              <text x="0" y="24" text-anchor="middle" fill="#CBD5E1" font-size="13" class="mono">name · role</text>
              <text x="0" y="42" text-anchor="middle" fill="#94A3B8" font-size="12" class="mono">aliases</text>
            </g>

            <!-- Node 3: Event -->
            <g class="graph-node" id="node-event" transform="translate(650, 425)">
              <circle cx="0" cy="0" r="68" fill="#0E3D30" stroke="#60E1AC" stroke-width="3"/>
              <text x="0" y="-21" text-anchor="middle" fill="#FFFFFF" class="t-body" font-size="19">Event</text>
              <line x1="-40" y1="-5" x2="40" y2="-5" stroke="#60E1AC" stroke-opacity="0.5" stroke-width="1.5"/>
              <text x="0" y="16" text-anchor="middle" fill="#CBD5E1" font-size="13" class="mono">type · summary</text>
              <text x="0" y="36" text-anchor="middle" fill="#94A3B8" font-size="12" class="mono">story_order</text>
            </g>

            <!-- Node 4: Location -->
            <g class="graph-node" id="node-location" transform="translate(1080, 425)">
              <circle cx="0" cy="0" r="68" fill="#3D2B14" stroke="#EEC594" stroke-width="3"/>
              <text x="0" y="-21" text-anchor="middle" fill="#FFFFFF" class="t-body" font-size="19">Location</text>
              <line x1="-40" y1="-5" x2="40" y2="-5" stroke="#EEC594" stroke-opacity="0.5" stroke-width="1.5"/>
              <text x="0" y="16" text-anchor="middle" fill="#CBD5E1" font-size="13" class="mono">name · kind</text>
              <text x="0" y="36" text-anchor="middle" fill="#94A3B8" font-size="12" class="mono">scene place</text>
            </g>

            <!-- Node 5: Utterance -->
            <g class="graph-node" id="node-utterance" transform="translate(1440, 160)">
              <circle cx="0" cy="0" r="68" fill="#2E1F4D" stroke="#B8ABFF" stroke-width="3"/>
              <text x="0" y="-21" text-anchor="middle" fill="#FFFFFF" class="t-body" font-size="19">Utterance</text>
              <line x1="-40" y1="-5" x2="40" y2="-5" stroke="#B8ABFF" stroke-opacity="0.5" stroke-width="1.5"/>
              <text x="0" y="16" text-anchor="middle" fill="#CBD5E1" font-size="13" class="mono">text · speaker</text>
              <text x="0" y="36" text-anchor="middle" fill="#94A3B8" font-size="12" class="mono">spoken words</text>
            </g>

            <!-- Node 6: Knowledge Acquisition -->
            <g class="graph-node" id="node-knowledge" transform="translate(225, 425)">
              <circle cx="0" cy="0" r="68" fill="#3D1A4D" stroke="#D0A7FF" stroke-width="3"/>
              <text x="0" y="-23" text-anchor="middle" fill="#FFFFFF" class="t-body" font-size="18">Knowledge</text>
              <text x="0" y="-2" text-anchor="middle" fill="#D0A7FF" class="t-caption mono" font-weight="bold">Acquisition</text>
              <line x1="-40" y1="7" x2="40" y2="7" stroke="#D0A7FF" stroke-opacity="0.5" stroke-width="1.5"/>
              <text x="0" y="24" text-anchor="middle" fill="#CBD5E1" font-size="13" class="mono">channel · time</text>
              <text x="0" y="42" text-anchor="middle" fill="#94A3B8" font-size="12" class="mono">stance · belief</text>
            </g>

            <!-- Node 7: Claim -->
            <g class="graph-node" id="node-claim" transform="translate(1440, 425)">
              <circle cx="0" cy="0" r="68" fill="#3D3011" stroke="#FFE18B" stroke-width="3"/>
              <text x="0" y="-21" text-anchor="middle" fill="#FFFFFF" class="t-body" font-size="19">Claim</text>
              <line x1="-40" y1="-5" x2="40" y2="-5" stroke="#FFE18B" stroke-opacity="0.5" stroke-width="1.5"/>
              <text x="0" y="16" text-anchor="middle" fill="#CBD5E1" font-size="13" class="mono">statement</text>
              <text x="0" y="36" text-anchor="middle" fill="#94A3B8" font-size="12" class="mono">truth status</text>
            </g>
          </svg>'''

with open('scratch/rebuild_slides.py') as f:
    content = f.read()

pattern = re.compile(r'<!-- Exact Draw\.io Graph in SVG.*?<\/svg>', re.DOTALL)
new_content, count = pattern.subn(new_svg, content)

if count > 0:
    with open('scratch/rebuild_slides.py', 'w') as f:
        f.write(new_content)
    print(f"Successfully replaced SVG in scratch/rebuild_slides.py (matched {count} times).")
else:
    print("Pattern match failed!")
