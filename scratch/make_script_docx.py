import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

doc = docx.Document()

# Set page margins to 1 inch
for section in doc.sections:
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

# Color constants
PRIMARY = RGBColor(2, 132, 199)      # Sky blue
DARK = RGBColor(15, 23, 42)          # Deep slate
GRAY = RGBColor(100, 116, 139)       # Slate gray
ACCENT = RGBColor(217, 119, 6)       # Warm amber

# Title
title_p = doc.add_paragraph()
title_run = title_p.add_run("Epistemic POV Graph")
title_run.font.name = "Arial"
title_run.font.size = Pt(26)
title_run.font.bold = True
title_run.font.color.rgb = PRIMARY
title_p.paragraph_format.space_after = Pt(2)

subtitle_p = doc.add_paragraph()
sub_run = subtitle_p.add_run("Retelling Sagas from Inside Distinct Character Minds — Presentation Speaker Script")
sub_run.font.name = "Arial"
sub_run.font.size = Pt(14)
sub_run.font.color.rgb = GRAY
subtitle_p.paragraph_format.space_after = Pt(16)

# Meta info box
meta_table = doc.add_table(rows=1, cols=3)
meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
meta_table.autofit = False

col_widths = [Inches(2.2), Inches(2.3), Inches(2.0)]
for row in meta_table.rows:
    for idx, width in enumerate(col_widths):
        row.cells[idx].width = width

cell0 = meta_table.cell(0, 0)
cell0.paragraphs[0].add_run("Presenter:\n").font.bold = True
cell0.paragraphs[0].add_run("Nhan Vu")

cell1 = meta_table.cell(0, 1)
cell1.paragraphs[0].add_run("Program:\n").font.bold = True
cell1.paragraphs[0].add_run("ShiftKey Academy · Build It! ML")

cell2 = meta_table.cell(0, 2)
cell2.paragraphs[0].add_run("Term:\n").font.bold = True
cell2.paragraphs[0].add_run("Fall 2026")

for cell in meta_table.rows[0].cells:
    shading_xml = f'<w:shd {nsdecls("w")} w:fill="F1F5F9"/>'
    cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.space_before = Pt(4)
    for run in p.runs:
        run.font.name = "Arial"
        run.font.size = Pt(10)

doc.add_paragraph().paragraph_format.space_after = Pt(14)

# Slide script data
slides_data = [
    {
        "num": 1,
        "title": "Title Slide",
        "time": "35 seconds",
        "visual": "Title screen with 'Epistemic POV Graph', Nhan Vu, and ShiftKey Academy Fall 2026 badge.",
        "script": (
            "Hello everyone! My name is Nhan Vu, and today I am excited to present the Epistemic POV Graph for the ShiftKey Academy UP Build It! Machine Learning program.\n\n"
            "Standard generative LLMs suffer from 'Omniscience Bias'—they know how the entire book ends, and when you ask them to roleplay or retell a chapter, they accidentally leak future secrets into character voices.\n\n"
            "To solve this, we built an epistemic knowledge graph in Neo4j that mathematically restricts an AI agent's memory to only what a character actually witnessed, heard, or believed at that exact timeline horizon. Let's see how this works."
        ),
        "cue": "Click 'Start Presentation →' or press the Right Arrow key to advance to Slide 2."
    },
    {
        "num": 2,
        "title": "Character Perspectives & Project Overview",
        "time": "45 seconds",
        "visual": "Clean 5-character roster. Hovering over each character card highlights their personal attributes.",
        "script": (
            "Instead of treating a story as one single global timeline, our project models it as multiple subjective realities.\n\n"
            "Take a look at our characters:\n"
            "• Harry Potter is the Chosen One and a natural Seeker, but his perspective is driven by gut feeling—he saw Snape's leg bleeding from Fluffy's bite and is 100% convinced Snape is the thief.\n"
            "• Hermione Granger is the top of her class who solved the logic potion puzzle, but she mistakenly assumed eye-contact meant cursing Harry's broom, so she set Snape's cloak on fire.\n"
            "• Ron Weasley is our chess tactician who bravely sacrificed his knight piece.\n"
            "• Professor Quirrell pretends to be a timid, stuttering teacher, but in reality, he is the deceptive host to Lord Voldemort.\n"
            "• And Severus Snape is strict and feared, but secretly protecting Harry under a sacred oath.\n\n"
            "Every character lives in a completely different subgraph of truth, bias, and suspicion."
        ),
        "cue": "Hover your mouse over Harry, Hermione, Quirrell, and Snape to demonstrate the interactive attribute cards."
    },
    {
        "num": 3,
        "title": "Sprint 1: Epistemic POV Graph (Accomplishment)",
        "time": "50 seconds",
        "visual": "Exact Draw.io Neo4j knowledge graph without colons, with flowing edge animations.",
        "script": (
            "In Sprint 1, our primary accomplishment was designing the epistemic Neo4j knowledge graph schema you see here.\n\n"
            "We couldn't just throw unstructured text into a database. We had to design an explicit schema separating objective reality from character perception. Notice our 7 node types: Characters, Events, Locations, Utterances, Claims, and crucially, Knowledge Acquisition.\n\n"
            "The foundational model rule is shown at the bottom: 'A character witnessing an event does not automatically know every claim in it.' When I click 'Toggle Story Labels', you can see Harry Potter canon mapped directly: Harry experienced the Quidditch match event at the pitch, but Snape's true intention is recorded as a separate Claim. ACQUIRED and ABOUT relationships precisely track what each character learns, when they learn it, and what stance they hold."
        ),
        "cue": "Click 'Toggle Story Labels' to switch between schema names and Harry Potter story names, then click 'Replay Build Steps'."
    },
    {
        "num": 4,
        "title": "Sprint 2 (Part 1): The Barrier / Challenge",
        "time": "40 seconds",
        "visual": "Monolithic prompt failure breakdown with red warning cards.",
        "script": (
            "In Sprint 2, our biggest barrier was tool integration and LLM hallucination.\n\n"
            "Initially, we attempted a naive monolithic approach: passing an entire 6,000-word chapter into a single LLM prompt asking it to extract all characters, locations, dialogue, and typed graph relationships all in one shot.\n\n"
            "The result was disastrous. We measured a 42% hallucination rate on relationships—the model invented interactions between characters who were in different rooms! Furthermore, context saturation caused secondary characters like Neville and Fluffy to be silently dropped. And whenever the JSON schema encountered a parsing error, the entire chapter extraction crashed with zero error visibility. Monolithic prompts were completely unviable."
        ),
        "cue": "Point out the 3 fault cards on the right: 42% Hallucinations, Silent Drops, and Zero Traceability."
    },
    {
        "num": 5,
        "title": "Sprint 2 (Part 2): How We Overcame It (LangGraph & LangSmith)",
        "time": "50 seconds",
        "visual": "5-step modular pipeline glowing green, interactive simulation, and real-time LangSmith audit log.",
        "script": (
            "To overcome this barrier, we completely abandoned monolithic prompts and engineered a 5-stage modular LangGraph pipeline backed by LangSmith audit tracing.\n\n"
            "Watch what happens when I click 'Simulate Traced Execution':\n"
            "• Step 1 extracts candidate entity rosters per paragraph chunk.\n"
            "• Step 2 passes entities through a Pydantic schema validator with automated self-correction.\n"
            "• Step 3 maps atomic relationships with direct paragraph evidence.\n"
            "• Step 4 pins scenes to validated Location nodes.\n"
            "• Step 5 commits an idempotent Cypher transaction to Neo4j.\n\n"
            "In the LangSmith trace inspector below, every single run records latency, token count, and exact input/output logs. We achieved 100% schema compliance and reduced hallucination leaks to under 0.5%."
        ),
        "cue": "Click '▶ Simulate Traced Execution' and let the green pulses travel through all 5 steps while the audit log updates."
    },
    {
        "num": 6,
        "title": "Sprint 3 (Part 1): The Surprise (The Twist Paradox)",
        "time": "45 seconds",
        "visual": "Side-by-side comparison of Chapters 1-16 (Red Herring) vs Chapter 17 (Mirror Revelation).",
        "script": (
            "In Sprint 3, our biggest surprise was the profound technical challenge posed by mystery narratives and plot twists.\n\n"
            "In Harry Potter, throughout Chapters 1 to 16, every single piece of evidence points to Severus Snape being the villain. Harry saw Snape's leg mauled by Fluffy, saw his cloak catch fire, and heard him cornering Quirrell in the forest. A naive knowledge graph would permanently mark Snape as the antagonist.\n\n"
            "Then in Chapter 17, the entire premise flips: Quirrell unwraps his turban, revealing Lord Voldemort living in the back of his head, while Snape was secretly counter-cursing to save Harry's life!\n\n"
            "The technical crisis was: if you update the graph naively, Chapter 17 retroactively overwrites Chapter 16! Characters would lose their historical authenticity and suffer from future omniscience leakage."
        ),
        "cue": "Contrast the yellow red-herring card on the left with the purple revelation card on the right."
    },
    {
        "num": 7,
        "title": "Sprint 3 (Part 2): The Diversion (Two-Pass Memory Architecture)",
        "time": "50 seconds",
        "visual": "Two-Pass Ingestion pipeline with interactive Chapter 16 vs Chapter 17 timeline toggle.",
        "script": (
            "To solve this twist paradox, we took a major architectural diversion: we engineered a Two-Pass Epistemic Ingestion pipeline.\n\n"
            "In Pass 1, we read the entire book from a global omniscient perspective to resolve true entity identities—knowing that Quirrell is the true host and Snape is the protector.\n\n"
            "Then in Pass 2, we re-read the saga chronologically, bounding each character's beliefs with explicit temporal horizons.\n\n"
            "Watch our interactive timeline toggle:\n"
            "When set to Chapter 16, Harry's active claim is that Snape is trying to steal the Stone.\n"
            "When we toggle to Chapter 17, that suspicion is crossed out and marked as 'Shattered', while the verified knowledge that Quirrell is Voldemort's vessel is acquired.\n"
            "Both facts coexist permanently in Neo4j with timestamps, allowing Harry to retell early chapters with authentic innocence without leaking the finale."
        ),
        "cue": "Click 'Chapter 16: Trapdoor', then click 'Chapter 17: Mirror Room' to demonstrate the shattered suspicion effect."
    },
    {
        "num": 8,
        "title": "What's Next for Me: Autonomous POV Narrators",
        "time": "40 seconds",
        "visual": "Key takeaway banner, 3 roadmap lanes, and quick lens replay buttons.",
        "script": (
            "Looking forward: where are we taking this project from here?\n\n"
            "Our core takeaway from this entire experience is: 'Model what characters know, not just where they were.' Grounding generative agents in epistemic subgraphs mathematically eliminates omniscience bias.\n\n"
            "• Milestone 1 is complete: verified Neo4j epistemic schema and modular LangGraph pipeline.\n"
            "• Milestone 2 is currently in active testing: scaling from single chapters to ingesting the entire 7-volume Harry Potter series with cross-book identity resolution.\n"
            "• And Milestone 3 is our next horizon: autonomous multi-agent POV narrators that can retell the entire saga from any character's authentic voice and perspective.\n\n"
            "Thank you so much for your time and attention! I am now happy to take any questions."
        ),
        "cue": "Thank the judges and invite questions. You can click any character pill at the bottom to replay the presentation through another lens."
    }
]

for s in slides_data:
    # Heading
    h = doc.add_heading(level=1)
    h_run = h.add_run(f"SLIDE {s['num']}: {s['title']}")
    h_run.font.name = "Arial"
    h_run.font.size = Pt(16)
    h_run.font.bold = True
    h_run.font.color.rgb = DARK
    h.paragraph_format.space_before = Pt(16)
    h.paragraph_format.space_after = Pt(4)

    # Sub-info
    p_info = doc.add_paragraph()
    r_time = p_info.add_run(f"Suggested Time: {s['time']}  |  Visual: ")
    r_time.font.name = "Arial"
    r_time.font.size = Pt(10)
    r_time.font.bold = True
    r_time.font.color.rgb = ACCENT

    r_vis = p_info.add_run(s['visual'])
    r_vis.font.name = "Arial"
    r_vis.font.size = Pt(10)
    r_vis.font.color.rgb = GRAY
    p_info.paragraph_format.space_after = Pt(8)

    # Script Box (Table with left border)
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.rows[0].cells[0].width = Inches(6.5)
    c = t.rows[0].cells[0]
    shd = f'<w:shd {nsdecls("w")} w:fill="F8FAFC"/>'
    c._tc.get_or_add_tcPr().append(parse_xml(shd))

    p_script = c.paragraphs[0]
    p_script.paragraph_format.space_before = Pt(6)
    p_script.paragraph_format.space_after = Pt(6)
    r_lbl = p_script.add_run("SPEAKER SCRIPT:\n")
    r_lbl.font.name = "Arial"
    r_lbl.font.size = Pt(10)
    r_lbl.font.bold = True
    r_lbl.font.color.rgb = PRIMARY

    r_body = p_script.add_run(s['script'])
    r_body.font.name = "Arial"
    r_body.font.size = Pt(11)
    r_body.font.color.rgb = DARK

    # Cue
    p_cue = doc.add_paragraph()
    p_cue.paragraph_format.space_before = Pt(6)
    p_cue.paragraph_format.space_after = Pt(16)
    r_cue_lbl = p_cue.add_run("Action / Visual Cue: ")
    r_cue_lbl.font.name = "Arial"
    r_cue_lbl.font.size = Pt(10)
    r_cue_lbl.font.bold = True
    r_cue_lbl.font.color.rgb = PRIMARY

    r_cue_txt = p_cue.add_run(s['cue'])
    r_cue_txt.font.name = "Arial"
    r_cue_txt.font.size = Pt(10)
    r_cue_txt.font.italic = True
    r_cue_txt.font.color.rgb = GRAY

out_path = "doc/presentation/script.docx"
doc.save(out_path)
print(f"Successfully generated presentation script document at {out_path}!")
