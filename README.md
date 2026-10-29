# Visual Perception Agent

An AI assistant that looks at your **sketches, artworks and interface designs** and critiques
them through classic visual perception theory: **James J. Gibson** (ecological perception),
**Rudolf Arnheim** (composition) and **Donald Norman** (interaction design).

It runs **entirely on your own computer** with [Ollama](https://ollama.com). No API keys, no cloud account.

| Start here | What it is |
|---|---|
| [Quick start](#quick-start) | Install everything and run the app |
| [STUDENT_TASKS.md](STUDENT_TASKS.md) | **Workshop tasks:** test the app, extend its knowledge, adjust its prompts |
| [prompts/README.md](prompts/README.md) | **Prompt Guide:** how to change what the agent says, without coding |

---

## Quick start

You need about **6 GB of free disk space** and **8 GB of RAM** or more.

### 1. Install the tools

- **Python 3.10 or newer** (3.12 recommended): [python.org/downloads](https://www.python.org/downloads/).
  On Windows, tick **"Add Python to PATH"** in the installer.
- **Git**: [git-scm.com](https://git-scm.com/downloads)
- **Ollama**: [ollama.com/download](https://ollama.com/download). After installing, make sure it's running
  (on Windows and macOS it starts automatically and shows an icon in the system tray / menu bar).

### 2. Download the AI models

Open a terminal (Windows: **PowerShell**; macOS: **Terminal**) and run:

```bash
ollama pull qwen3.5:4b
ollama pull nomic-embed-text
```

This downloads about 4.3 GB. On an older laptop, use `qwen3.5:2b` instead (see [Configuration](#configuration)).

### 3. Get the code and install it

```bash
git clone https://github.com/ainulyaqinmhd/vlmAgentWorkshop.git
cd vlmAgentWorkshop

python -m venv venv
```

Activate the virtual environment. You need to do this **every time** you open a new terminal:

```bash
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# macOS / Linux
source venv/bin/activate
```

You should now see `(venv)` at the start of your terminal line. Then install the packages:

```bash
pip install -r requirements.txt
```

> **Windows: "running scripts is disabled on this system"?** Run this once, then activate again:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 4. Check your setup

```bash
python check_setup.py
```

Every line should say `[OK]`. If something says `[FAIL]`, follow the fix it prints.

### 5. Run the app

```bash
python main.py
```

Open **http://127.0.0.1:7860** in your browser. To stop the app, press **Ctrl+C** in the terminal.

---

## Using the app

1. **Upload an image** (or click a sample image). The agent detects the domain, looks up the
   matching theory in its knowledge base, and analyzes the image.
2. **Ask follow-up questions** in the chat. It remembers the image and the conversation.
3. Tick **🖍️ Critique mode** for concrete feedback on how to improve the image.
4. Pick an **Analysis domain** to choose the theory yourself: Urban Sketching (Gibson),
   UI/UX Design (Norman) or Fine Art (Arnheim).
5. Tick **🔄 Research mode** for deep questions: the agent plans sub-questions and searches the
   web, ArXiv and OpenAlex (needs internet, takes 1-3 minutes).
6. Watch the **🧠 Agent status** panel:
   - **📋 Process log**: each step, including which prompt file and notes were used
   - **💭 Model thinking**: the model's reasoning (when thinking is turned on, see [Configuration](#configuration))
   - **📝 Prompt sent**: the exact text the model received

---

## Workshop plan

| Session | Duration | Activity |
|---|---|---|
| Before the workshop | 30 min + downloads | [Quick start](#quick-start) steps 1-4 at home |
| 1. Explore | ~45 min | Demo, then [STUDENT_TASKS.md](STUDENT_TASKS.md) Parts 1-2: test the app, add knowledge |
| 2. Adjust the prompts | ~60-90 min | Read the [Prompt Guide](prompts/README.md), then STUDENT_TASKS.md Part 3 |
| 3. Reflect | ~20 min | STUDENT_TASKS.md Part 4: discuss results |

---

## How it works

```
Upload image ──► Detect domain ──► Search knowledge base ──► Build prompt ──► Vision model ──► Answer
                 (classify_domain)  (knowledge/ notes)         (prompts/*.md)   (Ollama)          (streamed)
```

- **Prompts** live in [`prompts/`](prompts/) as text files, re-read on every request.
- **Knowledge** lives in [`knowledge/`](knowledge/): short notes on each theory, split into chunks,
  embedded with `nomic-embed-text` and stored in a local ChromaDB database (`chroma_db/`).
  This is retrieval-augmented generation (RAG).
- **Research mode** is an agent built with LangGraph: plan → search → answer each sub-question → combine.

## Adding your own knowledge

1. Put a `.md`, `.txt` or `.pdf` file in `knowledge/`. In notes, use `## ` headings: each section is one concept.
2. Optionally, add the file name to a domain's `knowledge_files` in [`modules/config.py`](modules/config.py)
   so it's searched when analyzing images of that domain. (Chat questions always search everything.)
3. Restart the app. New files are added automatically. If you **edited** a file that was already added,
   delete the `chroma_db` folder first so it's read again.

Only add material you have the right to share.

---

## Configuration

All settings are in [`modules/config.py`](modules/config.py). Restart the app after changing them.

| Setting | Default | Change it to… |
|---|---|---|
| `OLLAMA_MODEL`, `OLLAMA_VLM_MODEL` | `"qwen3.5:4b"` | `"qwen3.5:2b"` on a slow laptop, `"qwen3.5:9b"` with a strong GPU (run `ollama pull` for it first) |
| `OLLAMA_THINKING` | `False` | `True` to see the model's reasoning in the **Model thinking** tab (slower; also raise `OLLAMA_NUM_PREDICT` to `8192`) |
| `TEMPERATURE` | `0.7` | Lower (e.g. `0.2`) for more repeatable answers when comparing prompts |
| `DOMAINS` | 3 domains | Add your own domain, see the [Prompt Guide](prompts/README.md#going-further-add-your-own-domain) |
| `RAG_TOP_K` | `4` | How many notes are retrieved per question |

---

## Project structure

```
vlmAgentWorkshop/
├── README.md                  # You are here
├── LICENSE                    # MIT License
├── STUDENT_TASKS.md           # Workshop task list and test log
├── main.py                    # Start the app
├── check_setup.py             # Checks your installation
├── requirements.txt           # Python packages
├── prompts/                   # Every prompt the agent uses (edit these!)
│   └── README.md              # Prompt Guide
├── knowledge/                 # Notes the agent retrieves from (add your own)
├── sample_images/             # Example sketches to try
├── modules/
│   ├── config.py              # All settings
│   ├── ui.py                  # Web interface (Gradio) and event handlers
│   ├── image_analysis.py      # Domain detection and image prompt building
│   ├── prompts.py             # Loads prompt files and fills in {{placeholders}}
│   ├── ollama_client.py       # Talks to Ollama (with images, streaming)
│   ├── rag_engine.py          # Knowledge base: ingestion and retrieval
│   ├── research_agent.py      # Research mode (LangGraph agent)
│   ├── web_search.py, academic_search.py   # Research mode's search tools
│   └── conversation.py        # Remembers the current image between messages
```

Created when you run the app (not in git): `venv/`, `chroma_db/`, `uploads/`, `agent.log`.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` is not recognized | Reinstall Python and tick "Add Python to PATH", or use `py` instead of `python` (Windows). |
| `ModuleNotFoundError` | The virtual environment isn't active. Activate it (step 3) and try again. |
| `Connection refused` / the chat says "Is Ollama running?" | Start the Ollama app, or run `ollama serve` in another terminal. |
| `model "qwen3.5:4b" not found` | Run `ollama pull qwen3.5:4b` (or whichever model is set in the config). |
| Answers are very slow | Use `qwen3.5:2b` and keep `OLLAMA_THINKING = False`. The first answer is always slower while the model loads. |
| Research mode finds nothing | It needs internet access. Some school networks block search engines. |
| The knowledge base seems out of date | Delete the `chroma_db/` folder and restart the app to rebuild it. |
| Port 7860 is already in use | Another copy of the app is running. Close it, or stop it with Ctrl+C in its terminal. |
| Something else | Check the terminal window and `agent.log` for the error message. |

---

## Background reading

- Gibson, J. J. (1979). *The Ecological Approach to Visual Perception.*
- Arnheim, R. (1974). *Art and Visual Perception: A Psychology of the Creative Eye.*
- Norman, D. A. (1988/2013). *The Design of Everyday Things.*
- Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.*

The notes in `knowledge/` are short summaries written for teaching, not substitutes for these books.

## License

The code is released under the [MIT License](LICENSE).
