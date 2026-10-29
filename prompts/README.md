# Prompt Guide

Every instruction the agent gives the AI model is a plain text file in this folder.
**You can change how the agent behaves without touching any Python code.**

## How it works

1. Open a prompt file in any text editor (VS Code, Notepad, TextEdit).
2. Change the text and **save**.
3. Back in the app, upload an image or send a message. **Your change is used immediately.**
   There's no need to restart the app.
4. Open **🧠 Agent status → 📝 Prompt sent** in the app to see the exact text the model received.

Two special things you'll see in the files:

| You see | What it means |
|---|---|
| `<!-- ... -->` | A note for you. It's removed before the prompt is sent, so the model never sees it. |
| `{{question}}`, `{{context}}`, … | A placeholder the code fills in (the student's question, the retrieved notes, …). Keep these, spelled exactly the same. Each file lists the placeholders it supports at the top. |

## Which file does what

| When you… | The agent uses | Notes |
|---|---|---|
| Upload an image with **Auto-Detect** | `classify_domain.md` | Must make the model answer with one exact domain name |
| Upload an image (critique mode **off**) | `analyze_<domain>.md` | One per domain: `urban_sketching`, `ui_ux_design`, `fine_art` |
| Upload an image (critique mode **on**) | `critique_<domain>.md` | One per domain |
| Either of the above, when notes are found | `image_with_context.md` | Wraps the domain prompt together with the retrieved notes |
| Type a question | `chat_system.md` + `chat_message.md` | The system prompt sets personality and rules; the message adds history, notes and the question |
| Type a question in **Research mode** | `research_planner.md` → `research_answer.md` → `research_synthesizer.md` | Plan sub-questions → answer each one → combine into a report |

The **📋 Process log** tab in the app also names the prompt file used for each step.

## How to write a good prompt

A clear prompt usually has these parts. The existing files follow this pattern, so look at one while you read:

1. **Role**: who the model should be. *"You are an expert UI/UX Design Tutor specializing in…"*
2. **Task**: what to do with the input. *"Analyze the attached sketch to evaluate how it represents…"*
3. **Focus points**: what to look at, as a short numbered or bulleted list.
4. **Output format**: the structure you want back. *"Use three headings: Strengths, Improvements, Exercises."*
5. **Constraints**: length, tone, audience, what *not* to do. *"Under 200 words. No jargon without a definition."*

Tips:
- **Be specific.** "Keep it short" is vague; "under 150 words" is clear.
- **Show the format you want.** A tiny example of the output often works better than a description.
- **One change at a time.** Change one thing, test it on the same image, compare. Otherwise you won't know which change helped.
- **Ask for evidence.** "Refer to specific, visible parts of the image" makes answers less generic.
- **Small models follow short, direct instructions best.** If the model ignores a rule, move it to the end of the prompt, or say it twice.

## A simple testing routine

Prompts are easy to change and hard to judge, so test them the same way every time:

1. Pick **one test image** (e.g. `sample_images/street_perspective_sketch.jpg`) and keep the same domain and mode.
2. Run it with the **original** prompt. Save the answer (💾 Save conversation, or copy it into a document).
3. Make **one** change to the prompt and save the file.
4. Run the **same image** again. Note what changed: length, structure, specificity, use of theory, tone.
5. Run it a **second time**. Answers vary a little each run; if a change only shows up once, it may be luck.
   (Lower `TEMPERATURE` in `modules/config.py` for more repeatable answers.)
6. Keep the change if it's better. Otherwise undo it.

## Undoing your changes

- **With Git:** `git checkout -- prompts/critique_fine_art.md` restores one file; `git checkout -- prompts/` restores all of them.
- **Without Git:** copy the file before you edit it (e.g. `critique_fine_art.original.md`). Files with other names are ignored by the app.

## Going further: add your own domain

Want the agent to critique **photography**, **product design** or **landscape architecture**?

1. In `modules/config.py`, copy one entry in `DOMAINS` and change it, e.g. `"Photography"` with `"prompt_key": "photography"`,
   its own theory label, search queries, and knowledge files.
2. Create `prompts/analyze_photography.md` and `prompts/critique_photography.md` (copy an existing pair as a start).
3. In `classify_domain.md`, add a numbered description of the new domain so auto-detection can choose it.
4. Optionally, add a notes file for it to `knowledge/` (see the main README).
5. Restart the app. The new domain appears in the **Analysis domain** dropdown.

## When something goes wrong

| Problem | Likely cause |
|---|---|
| A `{{placeholder}}` appears literally in the **Prompt sent** tab | It's misspelled, or that file doesn't support it. Check the list at the top of the file. A warning also appears in the terminal. |
| Auto-detect always picks Urban Sketching | The model's answer didn't contain an exact domain name. Tighten `classify_domain.md`. |
| Research mode only researches the original question | The planner didn't reply with a JSON list. Keep the "Return ONLY a JSON list" instruction. |
| The answer stops mid-sentence | It hit the token limit. Ask for shorter answers, or raise `OLLAMA_NUM_PREDICT` in `modules/config.py`. |
| `FileNotFoundError: prompts/...` | A prompt file was renamed or deleted. Restore it with `git checkout -- prompts/`. |
