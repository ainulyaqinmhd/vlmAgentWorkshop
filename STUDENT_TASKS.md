# Student Task List

Work through these tasks in pairs. Tick each box when you're done, and write what you
observed in your [test log](#test-log). There are no wrong observations: an answer that
surprises you, or a feature that fails, is exactly what we want to hear about.

**Before you start:** finish the [Quick start](README.md#quick-start) in the README, run
`python main.py`, and open **http://127.0.0.1:7860**.

**Tip:** keep the **🧠 Agent status** panel open. The **📋 Process log** shows what the agent is
doing, and **📝 Prompt sent** shows the exact text the model received.

---

## Part 1: Explore the app (about 30 min)

### 1.1 First analysis
- [ ] Click a sample image under **Sample images** (e.g. `street_perspective_sketch.jpg`), with the domain on **Auto-Detect**.
- [ ] Watch the **Process log**. Which domain was detected? How many notes were retrieved?
- [ ] Read the answer. Does it describe things that are really in the image?

**Record:** the detected domain, how long the answer took, one thing it got right and one thing it got wrong or invented.

### 1.2 Look inside the prompt
- [ ] Open the **📝 Prompt sent** tab after an analysis.
- [ ] Find the three parts: the task instructions, the theory label, and the retrieved notes.
- [ ] Open the matching file in `prompts/` (the Process log names it) and compare it with what was sent.

**Record:** which file was used, and which part of the sent prompt came from the knowledge base.

### 1.3 Critique mode
- [ ] With the same image loaded, tick **🖍️ Critique mode**. The image is analyzed again as a critique.
- [ ] Compare the analysis and the critique.

**Record:** two differences between them (structure, tone, focus, usefulness for improving the drawing).

### 1.4 Choosing the domain yourself
- [ ] Set **Analysis domain** to **Fine Art**, then re-upload the same sketch (or click the sample again).
- [ ] Do the same with **UI/UX Design**.

**Record:** how the answer changes with each theory. Does forcing the "wrong" domain still give useful feedback?

### 1.5 Your own images
- [ ] Upload a **UI screenshot** (an app or website) on **Auto-Detect**.
- [ ] Upload an **artwork or painting** on **Auto-Detect**.
- [ ] Upload one of **your own sketches** (a phone photo is fine).

**Record:** was the domain detected correctly each time? If not, what did it choose instead?

### 1.6 Follow-up questions
- [ ] After an analysis, type a follow-up such as *"What could I add to make the depth stronger?"*
- [ ] Then ask about a specific area: *"What about the left side of the image?"*
- [ ] Then just ask *"Why?"*

**Record:** does the agent remember the image and the earlier answers? Where does it lose track?

### 1.7 Questions without an image
- [ ] Click **🗑️ New conversation**, then ask a theory question: *"What is the difference between an affordance and a signifier?"*
- [ ] Check the **Process log**: which notes were retrieved?
- [ ] Ask something the notes don't cover: *"Who designed the Sydney Opera House?"*

**Record:** does the agent say when the notes don't contain the answer, or does it answer anyway?

### 1.8 Research mode *(needs internet, takes 1-3 minutes)*
- [ ] Tick **🔄 Research mode** and ask: *"How is Gibson's theory of affordances used in architecture today?"*
- [ ] Follow the **Process log**: the plan, the searches, and the sources found.

**Record:** the sub-questions it planned, how many sources it found, whether the sources are actually
relevant (look at the paper titles in the log), and whether the final answer cites them.

### 1.9 Save your work
- [ ] Click **💾 Save conversation** and download the CSV file.

---

## Part 2: The knowledge base (about 15 min)

The agent grounds its answers in the notes in the `knowledge/` folder.

### 2.1 Read the notes
- [ ] Open `knowledge/gibson_ecological_perception.md`. Each `## ` heading is one concept.

### 2.2 Add your own note
- [ ] Add a new section to one of the notes files, or create a new file such as `knowledge/my_notes.md`:
  ```markdown
  # My notes

  ## Atmospheric Perspective
  Distant objects appear lighter, bluer and less detailed because of the air between them
  and the viewer. In sketching, using lighter lines and less detail for far-away buildings
  makes them recede and strengthens the sense of depth.
  ```
  *(A section needs at least a few sentences; very short ones are skipped.)*
- [ ] **Restart the app** (Ctrl+C in the terminal, then `python main.py`). New and edited files are read at startup.
- [ ] Ask: *"How can I use atmospheric perspective in my sketch?"*

**Record:** was your note retrieved (check the Process log and Prompt sent tabs)? Did the answer use it?

---

## Part 3: Adjust the prompts (about 60 min)

Read the [Prompt Guide](prompts/README.md) first. For every task:

1. Use the **same test image and settings** before and after your change.
2. Change **one thing**, save the file, and run it again. No restart is needed.
3. Record the **before and after** in your test log.

You can always undo a change: `git checkout -- prompts/<file>.md`

### Warm-up
- [ ] **P1. Length.** In `analyze_urban_sketching.md`, ask for an answer under 120 words. Did it obey? Is the shorter answer still useful?
- [ ] **P2. Format.** In `critique_urban_sketching.md`, ask for exactly three headings: *Strengths*, *Improvements*, *Practice exercise*. Did it follow the format?
- [ ] **P3. Audience.** In `chat_system.md`, change the audience to *first-year students with no theory background*, then to *professional architects*. Ask the same question both times and compare.

### Core
- [ ] **P4. Specificity.** Answers are often generic. Change a critique prompt so that every point must refer to a specific, visible part of the image (e.g. *"the stairs in the lower left"*). Did the answers become more concrete?
- [ ] **P5. Tone.** Turn a critique prompt into a **Socratic tutor** that asks the student 3 guiding questions instead of giving the answers. Does the model keep to it?
- [ ] **P6. Grounding.** In `image_with_context.md`, ask the model to name the note each idea comes from. Then compare an answer with notes against one with the notes removed. *(Tip: temporarily delete `{{context}}` from the file.)*
- [ ] **P7. Honesty.** In `chat_message.md`, remove the instruction about questions that can't be answered from the notes. Repeat task 1.7's off-topic question. What changes?

### Challenge
- [ ] **P8. Auto-detect robustness.** Find an image that **Auto-Detect** classifies wrongly. Improve `classify_domain.md` until it's classified correctly, and check the other sample images still work.
- [ ] **P9. Faster research.** Change `research_planner.md` so it plans exactly 2 sub-questions. How much faster is research mode, and is the answer worse?
- [ ] **P10. New domain.** Add a new domain (e.g. *Photography* or *Product Design*), following *"Add your own domain"* in the [Prompt Guide](prompts/README.md#going-further-add-your-own-domain). Write its two prompt files and test it on 2 images.

---

## Part 4: Reflection

Discuss with your partner and write a few sentences for each:

1. Which prompt change made the **biggest** difference? Which made **none**, and why do you think that was?
2. When did the agent **invent** things that weren't in the image? Could a prompt change prevent that?
3. How did the retrieved notes change the answers? When did they help, and when did they get in the way?
4. Would you trust this agent's critique of your own work? What would it need to do better?
5. If you were building the next version, what would you change first?

---

## Test log

Copy this table into a document, or use one row per test in a spreadsheet.

| Task | Image | Domain & mode | What I changed | What I expected | What happened | Better / worse / same |
|---|---|---|---|---|---|---|
| 1.1 | street_perspective_sketch.jpg | Auto-Detect, analyze | n/a | Urban Sketching | Detected Urban Sketching, 4 notes, 25 s | n/a |
| P1 | street_perspective_sketch.jpg | Urban Sketching, analyze | Added "under 120 words" | Shorter answer | | |
| | | | | | | |

### If something doesn't work

Note the task number, what you did, and copy the last lines of the **Process log** and the
terminal window. Check [Troubleshooting](README.md#troubleshooting) first, then ask an instructor.
