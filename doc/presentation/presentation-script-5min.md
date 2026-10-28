# POV Graph — Five-Minute Presentation Script

Spoken text: 504 words. Aim for 115–120 words per minute with short pauses for reveals. Finish by 5:00; rehearse aloud to confirm your pace.

Read the quoted paragraphs aloud. Bracketed cues are stage directions and are not spoken. NEXT means one press of Next, Space, or ArrowRight. The first build is already visible when a slide opens. After the last build, one more NEXT opens the next slide. Prev or ArrowLeft reverses a build.

Use Harry for the demo. The script does not read out the percentage badges or the roadmap completion percentages. The trace and knowledge timeline are illustrations; present the knowledge timeline as a design.

| Slide | Time | Duration |
| --- | --- | --- |
| 1 · POV Graph | 0:00–0:20 | 20s |
| 2 · Choose a Point of View | 0:20–0:40 | 20s |
| 3 · Sprint 1 | 0:40–1:30 | 50s |
| 4 · Sprint 2 · Too Much at Once | 1:30–2:15 | 45s |
| 5 · Sprint 2 · One Job at a Time | 2:15–3:10 | 55s |
| 6 · Sprint 3 · Harry Does Not Know Yet | 3:10–3:55 | 45s |
| 7 · Sprint 3 · Keep Both Views | 3:55–4:40 | 45s |
| 8 · What's Next for Me | 4:40–5:00 | 20s |

## Spoken Script

### Slide 1 — POV Graph · 0:00–0:20

**[Opening slide]**

> Hi, I'm Nhan Vu. My project is POV Graph. The goal is to retell a story from a character's point of view, using only what that character knows at that moment.

**[NEXT · Open slide 2]**

### Slide 2 — Choose a Point of View · 0:20–0:40

**[Select Harry and briefly hover his card]**

> These characters share a story, but they do not share the same knowledge. I'll use Harry today. He can see an event and still misunderstand it. That difference is what the project needs to preserve.

**[NEXT · Open slide 3]**

### Slide 3 — Sprint 1 · 0:40–1:30

**[Step 1/4 · People and relationships]**

> Sprint one was the graph design. We start with people and the relationships between them.

**[NEXT · Step 2/4 · Events and locations]**

> Next, we record events and locations: what happened, who was there, and where.

**[NEXT · Step 3/4 · Utterance and claim]**

> Then we separate what someone says from whether it is true. A claim is something a character might believe.

**[NEXT · Step 4/4 · Knowledge acquisition]**

> Finally, we record how a character learns that claim. Hearing something, seeing something, and knowing it are different. This structure lets us track both the story and a person's limited understanding of it.

**[NEXT · Open slide 4]**

### Slide 4 — Sprint 2 · Too Much at Once · 1:30–2:15

**[Step 1/7 · First approach]**

> In sprint two, our first approach was one prompt for everything.

**[NEXT · Step 2/7 · Chapter input and diagram]**

> We gave it a whole chapter, around six thousand words.

**[NEXT · Step 3/7 · Everything asked of the AI]**

> We asked for people, feelings, relationships, and scenes in one large answer.

**[NEXT · Step 4/7 · Invented connections]**

> It sometimes invented connections between people who had not spoken.

**[NEXT · Step 5/7 · Missing people]**

> It also missed less prominent characters.

**[NEXT · Step 6/7 · Failed output]**

> A cut-off answer or broken format could stop the whole job.

**[NEXT · Step 7/7 · Takeaway]**

> Because everything came back together, we struggled to locate the failure.

**[NEXT · Open slide 5]**

### Slide 5 — Sprint 2 · One Job at a Time · 2:15–3:10

**[Step 1/7 · Find people]**

> We changed the workflow so each step has one clear job. First, find new people and update existing ones.

**[NEXT · Step 2/7 · Check the answer]**

> Second, check that the answer has the required fields and data types.

**[NEXT · Step 3/7 · Find connections]**

> Third, find relationships and connect them to evidence in the text.

**[NEXT · Step 4/7 · Place the scenes]**

> Fourth, record who was in each scene, where, and in what order.

**[NEXT · Step 5/7 · Save the result]**

> Fifth, save the checked result to Neo4j.

**[NEXT · Step 6/7 · Trace]**

> LangGraph controls the sequence. LangSmith records the prompts, answers, and errors so we can investigate a specific step.

**[NEXT · Step 7/7 · Results]**

> These checks help, but correct formatting alone does not prove a story fact is correct.

**[NEXT · Open slide 6]**

### Slide 6 — Sprint 3 · Harry Does Not Know Yet · 3:10–3:55

**[Step 1/4 · Harry's suspicion]**

> Sprint three exposed a different problem. Before the reveal, Harry suspects Snape of trying to steal the Stone.

**[NEXT · Step 2/4 · The clues]**

> He sees an injured leg, hears about Snape muttering during Quidditch, and overhears him confronting Quirrell. Harry connects those clues in the wrong way.

**[NEXT · Step 3/4 · Quirrell appears]**

> In the final chamber, he finds Quirrell instead.

**[NEXT · Step 4/4 · What Harry learns]**

> He then learns that Voldemort was hiding in Quirrell, while Snape had been protecting him. An AI that already knows this ending could accidentally spoil an earlier Harry scene.

**[NEXT · Open slide 7]**

### Slide 7 — Sprint 3 · Keep Both Views · 3:55–4:40

**[Step 1/3 · Story facts]**

> Our design uses two readings. First, read the whole book to resolve names and identities, including late revelations.

**[NEXT · Step 2/3 · Harry's Chapter 16 view]**

> Then follow the chapters in order and record what the character knows. In chapter sixteen, Harry still suspects Snape. That belief matters to his narration, even though it is wrong.

**[NEXT · Step 3/3 · Chapter 17 changes his knowledge]**

> Chapter seventeen adds what he learns about Quirrell and Voldemort. We keep the earlier belief for earlier scenes. The narrator should receive the knowledge available at the chosen point in the story.

**[NEXT · Open slide 8]**

### Slide 8 — What's Next for Me · 4:40–5:00

**[Closing slide · No further advance]**

> Next, I will test complete books and the full series, improve extraction, and build the POV narrator. The main lesson: a character's knowledge changes over time, and the graph must preserve that. Thank you.

## Rehearsal Check

- At 1:30, start the First Approach slide.
- At 3:10, move to the Harry/Snape example.
- At 4:40, start the closing slide.
- Keep the character-card demonstration brief. Do not read every card, diagram label, or percentage aloud.
- If you are behind, shorten the three-clue sentence on slide 6 to: "Harry misreads several clues and suspects Snape."
- End on "Thank you" by 5:00.
