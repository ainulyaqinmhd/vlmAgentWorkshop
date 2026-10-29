"""
Web interface (Gradio)
Image analysis, chat with the knowledge base, research mode, and a live view of
what the agent is doing: the process log, the model's thinking, and the exact prompt sent.
"""

import csv
import os
import time

import gradio as gr
from PIL import ImageOps

from . import conversation
from .config import logger, DOMAINS, UPLOAD_FOLDER, PROJECT_ROOT, CHAT_HISTORY_MESSAGES, OLLAMA_MODEL, OLLAMA_VLM_MODEL, OLLAMA_THINKING
from .image_analysis import classify_domain, retrieval_query, build_image_prompt
from .ollama_client import stream
from .prompts import load_prompt
from .rag_engine import RAGEngine
from .research_agent import run_research

AUTO_DETECT = "Auto-Detect"
STREAM_UPDATE_SECONDS = 0.05  # How often the chat refreshes while an answer streams in
SAMPLE_IMAGES_DIR = os.path.join(PROJECT_ROOT, "sample_images")
THINKING_PLACEHOLDER = (
    "Thinking is turned off, so answers come faster.\n"
    "To watch the model reason here, set OLLAMA_THINKING = True in modules/config.py and restart the app."
    if not OLLAMA_THINKING else "The model's reasoning will appear here while it works..."
)
ERROR_HINT = "Is Ollama running, and is the model downloaded? See Troubleshooting in the README."

rag_engine = RAGEngine()


def stream_into_history(history, prompt, image_path, system, log):
    """
    Stream the model's answer into the last chat message.
    Yields (history, log, thinking); the last yield holds the complete answer.
    """
    thinking, answer = "", ""
    last_update = 0.0
    for thinking, answer in stream(prompt, image_path=image_path, system=system):
        if time.time() - last_update > STREAM_UPDATE_SECONDS:
            last_update = time.time()
            history[-1]["content"] = answer
            status = "💭 The model is thinking...\n" if not answer else "✍️ Writing the answer...\n"
            yield history, log + status, thinking
    history[-1]["content"] = answer
    yield history, log, thinking


# -----------------------------------------------------------------------------
# Event handlers
# Image handlers yield: chatbot, history, process log, thinking, prompt sent
# The chat handler also yields the (cleared) text box
# -----------------------------------------------------------------------------
def analyze_image(image, domain_choice, critique, history):
    """Analyze or critique an uploaded image"""
    if image is None:  # Image was cleared
        yield history, history, gr.update(), gr.update(), gr.update()
        return

    log = "🔄 Processing uploaded image...\n"
    thinking, prompt = "", ""
    yield history, history, log, thinking, prompt
    placeholder_added = False
    try:
        path = os.path.join(UPLOAD_FOLDER, "uploaded.png")
        # Apply the phone's rotation tag (EXIF) so the model sees the photo upright,
        # and convert to RGB so CMYK/palette images can be saved as PNG
        ImageOps.exif_transpose(image).convert("RGB").save(path)

        domain = domain_choice
        if domain == AUTO_DETECT:
            log += "🔍 Detecting the image's domain (prompt file: prompts/classify_domain.md)...\n"
            yield history, history, log, thinking, prompt
            domain = classify_domain(path)
            log += f"✅ Detected domain: {domain}\n"
        else:
            log += f"🎯 Domain: {domain}\n"

        query = retrieval_query(domain, critique)
        log += f"📚 Searching the knowledge base for: '{query}'\n"
        yield history, history, log, thinking, prompt
        context = rag_engine.query(query, knowledge_files=DOMAINS[domain]["knowledge_files"])
        log += f"✅ Retrieved {context.count('[Source:')} notes\n" if context else "⚪ No notes found\n"

        mode = "critique" if critique else "analyze"
        prompt = build_image_prompt(domain, critique, context)
        log += f"📝 Prompt file: prompts/{mode}_{DOMAINS[domain]['prompt_key']}.md\n"
        log += f"🧠 Sending the image and prompt to {OLLAMA_VLM_MODEL}...\n"

        conversation.state.update(image_path=path, domain=domain)
        label = "🖍️ Critique this image" if critique else "🖼️ Analyze this image"
        history = history + [
            {"role": "user", "content": f"{label} ({domain})"},
            {"role": "assistant", "content": ""},
        ]
        placeholder_added = True

        for history, status, thinking in stream_into_history(history, prompt, path, None, log):
            yield history, history, status, thinking, prompt
        log += "✅ Analysis complete.\n"
        yield history, history, log, thinking, prompt

    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
        error_msg = f"I ran into a problem analyzing that image. {ERROR_HINT}"
        if placeholder_added:
            history[-1]["content"] = error_msg
        else:
            history = history + [{"role": "assistant", "content": error_msg}]
        yield history, history, log + f"❌ Error: {e}\n", thinking, prompt


def on_critique_toggle(critique, image, domain_choice, history):
    """Turning critique mode on re-runs the analysis as a critique"""
    if critique and image is not None:
        yield from analyze_image(image, domain_choice, True, history)
    else:
        yield gr.update(), gr.update(), gr.update(), gr.update(), gr.update()


def chat(message, research_mode, history):
    """Answer a typed question, using the knowledge base (or research mode) and the current image"""
    if not message or not message.strip():
        yield history, history, gr.update(), gr.update(), gr.update(), message
        return

    history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": ""}]
    log, thinking, prompt = "", "", ""
    try:
        if research_mode:
            log = "🔄 Research mode: planning sub-questions (prompt file: prompts/research_planner.md)...\n"
            yield history, history, log, thinking, prompt, ""
            for update in run_research(message, history[:-2], rag_engine):
                if update["type"] == "log":
                    log += f"{update['content']}\n"
                    yield history, history, log, thinking, prompt, ""
                else:
                    history[-1]["content"] = update["content"]
            yield history, history, log, thinking, "(Research mode uses prompts/research_*.md)", ""
            return

        log = f"📚 Searching the knowledge base for: '{message}'\n"
        yield history, history, log, thinking, prompt, ""
        context = rag_engine.query(message)
        log += f"✅ Retrieved {context.count('[Source:')} notes\n" if context else "⚪ No relevant notes found\n"

        earlier = history[:-2][-CHAT_HISTORY_MESSAGES:]
        prompt = load_prompt(
            "chat_message",
            history="\n".join(f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}" for m in earlier) or "(This is the first message.)",
            knowledge=context or "(No relevant notes were found in the knowledge base.)",
            question=message,
        )
        system = load_prompt("chat_system")

        image_path = conversation.state["image_path"]
        if image_path and not os.path.exists(image_path):
            image_path = None
        model = OLLAMA_VLM_MODEL if image_path else OLLAMA_MODEL
        log += "📝 Prompt files: prompts/chat_system.md + prompts/chat_message.md\n"
        log += f"🧠 Asking {model}" + (" (with the current image)...\n" if image_path else "...\n")

        prompt_view = f"=== SYSTEM PROMPT ===\n{system}\n\n=== MESSAGE ===\n{prompt}"
        for history, status, thinking in stream_into_history(history, prompt, image_path, system, log):
            yield history, history, status, thinking, prompt_view, ""
        log += f"✅ Answer complete ({len(history[-1]['content'])} characters).\n"
        yield history, history, log, thinking, prompt_view, ""

    except Exception as e:
        logger.error(f"Error answering message: {e}")
        history[-1]["content"] = f"Sorry, I had trouble answering that. {ERROR_HINT}"
        yield history, history, log + f"❌ Error: {e}\n", thinking, prompt, ""


def new_conversation():
    conversation.reset()
    welcome = [{"role": "assistant", "content": conversation.welcome_message()}]
    return welcome, welcome, "Waiting for a task...", THINKING_PLACEHOLDER, "", None, False


def save_conversation(history):
    """Save the chat as a CSV of question/answer pairs"""
    path = os.path.join(UPLOAD_FOLDER, "conversation.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Question", "Answer"])
        question = ""
        for msg in history:
            if msg["role"] == "user":
                question = msg["content"]
            elif msg["role"] == "assistant":
                writer.writerow([question, msg["content"]])
                question = ""
    return gr.update(value=path, visible=True)


# -----------------------------------------------------------------------------
# Layout
# -----------------------------------------------------------------------------
CSS = """
#process_log textarea, #thinking_log textarea, #prompt_view textarea {
    font-family: Consolas, Monaco, 'Courier New', monospace;
    font-size: 13px;
}
"""


def create_interface():
    with gr.Blocks(title="Visual Perception Agent") as demo:
        gr.Markdown("# 👁️ Visual Perception Agent\nUpload a sketch, artwork or interface design, or ask a question.")
        history = gr.State([])

        with gr.Row():
            with gr.Column(scale=1):
                image_input = gr.Image(type="pil", label="🖼️ Upload an image (JPG/PNG)", height=380)
                domain = gr.Dropdown(
                    label="🔍 Analysis domain",
                    choices=[AUTO_DETECT] + list(DOMAINS),
                    value=AUTO_DETECT,
                    info="The theory used to analyze the image",
                )
                critique = gr.Checkbox(label="🖍️ Critique mode", info="Feedback on how to improve the image")
                research = gr.Checkbox(label="🔄 Research mode (IterDRAG)", info="Deep research on the web for typed questions (slower, needs internet)")
                samples = sorted(f for f in os.listdir(SAMPLE_IMAGES_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png")))
                gr.Examples(
                    examples=[[os.path.join(SAMPLE_IMAGES_DIR, f)] for f in samples],
                    inputs=[image_input],
                    label="Sample images (click to load)",
                    examples_per_page=6,
                )

            with gr.Column(scale=2):
                chatbot = gr.Chatbot(label="💬 Conversation", height=480, show_label=False)
                with gr.Row():
                    text_input = gr.Textbox(placeholder="Ask a question and press Enter...", show_label=False, scale=6)
                    send_btn = gr.Button("Send", variant="primary", scale=1)
                with gr.Row():
                    clear_btn = gr.Button("🗑️ New conversation")
                    save_btn = gr.Button("💾 Save conversation")
                saved_file = gr.File(label="Saved conversation", visible=False)

                with gr.Accordion("🧠 Agent status", open=True):
                    with gr.Tabs():
                        with gr.Tab("📋 Process log"):
                            process_log = gr.Textbox(value="Waiting for a task...", show_label=False, lines=8,
                                                     max_lines=12, interactive=False, autoscroll=True, elem_id="process_log")
                        with gr.Tab("💭 Model thinking"):
                            thinking_log = gr.Textbox(value=THINKING_PLACEHOLDER, show_label=False, lines=8,
                                                      max_lines=20, interactive=False, autoscroll=True, elem_id="thinking_log")
                        with gr.Tab("📝 Prompt sent"):
                            prompt_view = gr.Textbox(value="The exact prompt sent to the model will appear here.",
                                                     show_label=False, lines=8, max_lines=25, interactive=False,
                                                     elem_id="prompt_view")

        image_outputs = [chatbot, history, process_log, thinking_log, prompt_view]
        chat_outputs = image_outputs + [text_input]

        demo.load(new_conversation, None, [chatbot, history, process_log, thinking_log, prompt_view, image_input, critique])
        image_input.change(analyze_image, [image_input, domain, critique, history], image_outputs)
        critique.change(on_critique_toggle, [critique, image_input, domain, history], image_outputs)
        text_input.submit(chat, [text_input, research, history], chat_outputs)
        send_btn.click(chat, [text_input, research, history], chat_outputs)
        clear_btn.click(new_conversation, None, [chatbot, history, process_log, thinking_log, prompt_view, image_input, critique])
        save_btn.click(save_conversation, [history], [saved_file])

    return demo
