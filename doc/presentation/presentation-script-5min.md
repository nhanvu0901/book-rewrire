# POV Graph — Five-Minute Presentation Script

Spoken text: 480 words. Aim for 110–115 words per minute, allowing short pauses for reveals. The schedule includes those pauses. Finish by 5:00; rehearse aloud to confirm your pace.

Read only the quoted paragraphs aloud. Bracketed cues are stage directions. NEXT means one press of Next, Space, or ArrowRight. Each slide opens at step 1; after its last step, NEXT opens the next slide. Prev or ArrowLeft reverses a step. On the final slide, Next disables after the closing lesson.

Use Harry for the demo. Keep the card hover brief. The trace and chapter-input panels are illustrations. Slide 6 raises the plot-twist problem; slide 7 shows how the current pipeline keeps a memory version for every chapter. Do not read the percentage badges aloud.

| Slide | Time | Duration |
| --- | --- | --- |
| 1 · POV Graph | 0:00–0:20 | 20s |
| 2 · Choose a Point of View | 0:20–0:40 | 20s |
| 3 · Sprint 1 | 0:40–1:25 | 45s |
| 4 · Sprint 2 · Too Much at Once | 1:25–2:10 | 45s |
| 5 · Sprint 2 · One Job at a Time | 2:10–3:00 | 50s |
| 6 · Sprint 3 · A Future POV Challenge | 3:00–3:45 | 45s |
| 7 · Sprint 3 · Read in Order, Keep Every Version | 3:45–4:25 | 40s |
| 8 · What's Next for Me | 4:25–5:00 | 35s |

## Spoken Script

### Slide 1 — POV Graph · 0:00–0:20

**[Opening slide]**

> Hi, I'm Nhan Vu. My project is POV Graph. The goal is to retell a story from a character's point of view, using only what that character knows at that moment.

**[NEXT · Open slide 2]**

### Slide 2 — Choose a Point of View · 0:20–0:40

**[Select Harry and briefly hover his card]**

> I'll use Harry. Choosing a narrator sets which facts the AI is allowed to use. His view may differ from Hermione's, even in the same scene.

**[NEXT · Open slide 3]**

### Slide 3 — Sprint 1 · 0:40–1:25

**[Step 1/4 · People and relationships]**

> Sprint one was the graph design. Start with people and the relationships between them.

**[NEXT · Step 2/4 · Events and locations]**

> Add events and locations: what happened, who was there, and where.

**[NEXT · Step 3/4 · Utterance and claim]**

> Then store what was said as a claim. A character can believe that claim before it is confirmed.

**[NEXT · Step 4/4 · Knowledge acquisition]**

> Finally, record the source of a belief: an event the character witnessed or a report they heard.

**[NEXT · Open slide 4]**

### Slide 4 — Sprint 2 · Too Much at Once · 1:25–2:10

**[Step 1/7 · First approach]**

> In sprint two, we tried one prompt for everything.

**[NEXT · Step 2/7 · Chapter input and diagram]**

> We sent a whole chapter, around six thousand words.

**[NEXT · Step 3/7 · Everything asked of the AI]**

> It had to find people, feelings, relationships, and scenes.

**[NEXT · Step 4/7 · Invented connections]**

> It invented interactions between people who had never spoken.

**[NEXT · Step 5/7 · Missing people]**

> Less prominent characters were left out.

**[NEXT · Step 6/7 · Failed output]**

> Broken JSON or a cut-off answer could stop the whole job.

**[NEXT · Step 7/7 · Takeaway]**

> We needed a way to find the failing step.

**[NEXT · Open slide 5]**

### Slide 5 — Sprint 2 · One Job at a Time · 2:10–3:00

**[Step 1/7 · Find people]**

> The new workflow separates those jobs. First, identify characters and update their records.

**[NEXT · Step 2/7 · Check the answer]**

> Pydantic checks that the answer has the expected fields and types.

**[NEXT · Step 3/7 · Find connections]**

> Extract relationships with evidence from the chapter.

**[NEXT · Step 4/7 · Place the scenes]**

> Record who was in each scene, where, and in what order.

**[NEXT · Step 5/7 · Save the result]**

> Save the checked result to Neo4j.

**[NEXT · Step 6/7 · Trace]**

> LangGraph controls the order. LangSmith lets us inspect the prompt, response, and error for each call.

**[NEXT · Step 7/7 · Results]**

> A valid format is only the first check; the story facts still need review.

**[NEXT · Open slide 6]**

### Slide 6 — Sprint 3 · A Future POV Challenge · 3:00–3:45

**[Step 1/4 · Harry's suspicion]**

> This story illustrates a requirement for our future narrator. In chapter sixteen, Harry still suspects Snape.

**[NEXT · Step 2/4 · The clues]**

> His clues include Snape's injured leg, the Quidditch match, and his confrontation with Quirrell.

**[NEXT · Step 3/4 · Quirrell appears]**

> In chapter seventeen, he finds Quirrell in the final chamber.

**[NEXT · Step 4/4 · The future requirement]**

> Harry learns that Voldemort was hiding in Quirrell and Snape was protecting him. If the AI read the whole book at once, it could leak chapter seventeen into a chapter sixteen retelling. A future narrator must use only what Harry knows at the chosen point in the story.

**[NEXT · Open slide 7]**

### Slide 7 — Sprint 3 · Read in Order, Keep Every Version · 3:45–4:25

**[Step 1/3 · Chapter 16 version]**

> To handle the twist, we read the book in order and save memory for every chapter. In the chapter sixteen version, Quirrell is just a nervous teacher, and Snape is the one Harry suspects.

**[NEXT · Step 2/3 · Chapter 17 version]**

> In chapter seventeen, the reveal updates the records: Voldemort was sharing Quirrell's body, and Snape had been protecting Harry.

**[NEXT · Step 3/3 · Why both versions matter]**

> We keep both versions, so a chapter sixteen retelling only uses the chapter sixteen version. The next step is to track what each character knows, not just what the story has shown so far.

**[NEXT · Open slide 8]**

### Slide 8 — What's Next for Me · 4:25–5:00

**[Step 1/4 · Test whole books]**

> Next, test the pipeline across complete books and the full series.

**[NEXT · Step 2/4 · Improve accuracy]**

> Review identity matches, relationships, and the source evidence.

**[NEXT · Step 3/4 · Build POV narrators]**

> Then build a narrator that receives only the chosen character's knowledge.

**[NEXT · Step 4/4 · Closing lesson]**

> That's the lesson I want to carry forward: the graph must preserve a character's changing understanding. Thank you.

## Rehearsal Check

- At 1:25, start First Approach.
- At 3:00, start the Harry/Snape example.
- At 4:25, start the closing slide and reveal its three goals, then its final lesson.
- Pause for a reveal, then speak. Let the short card text support the explanation.
- If behind, shorten slide 6 step 2 to: "Harry misreads several clues and suspects Snape."
- End on "Thank you" by 5:00.
