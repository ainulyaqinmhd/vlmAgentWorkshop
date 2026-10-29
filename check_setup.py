"""
Setup check. Run this BEFORE the workshop day, from the project folder:

    python check_setup.py

Every line should say [OK]. If something says [FAIL], follow the hint below it.
"""

import os
import sys
import tempfile

results = []


def check(name, fn, hint):
    try:
        detail = fn()
        print(f"[OK]   {name}" + (f"  ({detail})" if detail else ""))
        results.append(True)
        return True
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        print(f"       Fix: {hint}")
        results.append(False)
        return False


def python_version():
    found = sys.version.split()[0]
    if sys.version_info < (3, 12):
        raise RuntimeError(f"found {found}, need 3.12, 3.13 or 3.14")
    if sys.version_info >= (3, 15):
        raise RuntimeError(f"found {found}, which is too new: some packages don't support it yet")
    return found


def packages():
    import gradio, numpy, pypdf, ddgs, arxiv, bs4, PIL, requests  # noqa: F401
    return f"gradio {gradio.__version__}"


print("Checking your setup...\n")

if not check("Python 3.12 - 3.14", python_version,
             "Install Python 3.14 from python.org, then delete the venv folder and recreate it (see README step 3)"):
    sys.exit(1)
if not check("Python packages", packages,
             "Activate the virtual environment, then run: pip install -r requirements.txt"):
    sys.exit(1)

import requests  # noqa: E402
from PIL import Image  # noqa: E402

from modules import config  # noqa: E402


def ollama_running():
    data = requests.get(f"{config.OLLAMA_HOST}/api/version", timeout=5).json()
    return f"version {data.get('version')}"


if not check("Ollama is running", ollama_running,
             "Install Ollama from https://ollama.com and make sure it is running"):
    sys.exit(1)

installed = {m["name"] for m in requests.get(f"{config.OLLAMA_HOST}/api/tags", timeout=10).json()["models"]}


def has_model(name):
    def fn():
        if (name if ":" in name else f"{name}:latest") not in installed:
            raise RuntimeError("not downloaded")
    return fn


models_ok = True
for model in sorted({config.OLLAMA_VLM_MODEL, config.OLLAMA_MODEL, config.EMBED_MODEL}):
    models_ok &= check(f"Model {model}", has_model(model), f"Run: ollama pull {model}")


def vision_works():
    # A plain red square: any working vision model should say "red"
    from modules.ollama_client import generate

    path = os.path.join(tempfile.gettempdir(), "vpa_check_red.png")
    Image.new("RGB", (64, 64), (220, 20, 20)).save(path)
    answer = generate("What single colour fills this image? Answer with one word.", image_path=path)
    if "red" not in answer.lower():
        raise RuntimeError(f"model answered {answer!r}; it may not support images")
    return f"answered {answer.strip()!r}"


def embeddings_work():
    response = requests.post(f"{config.OLLAMA_HOST}/api/embed",
                             json={"model": config.EMBED_MODEL, "input": ["texture gradient"]}, timeout=120)
    response.raise_for_status()
    return f"{len(response.json()['embeddings'][0])}-dimensional vectors"


def project_files():
    prompts = [f for f in os.listdir(config.PROMPTS_DIR) if f.endswith(".md") and f != "README.md"]
    notes = [f for f in os.listdir(config.KNOWLEDGE_DIR) if f.lower().endswith((".md", ".txt", ".pdf"))]
    if not prompts or not notes:
        raise RuntimeError("prompts/ or knowledge/ is empty")
    return f"{len(prompts)} prompts, {len(notes)} knowledge files"


if models_ok:
    check("Vision model can see images (the first run loads the model, may take a minute)", vision_works,
          f"Try a smaller model: set OLLAMA_VLM_MODEL in modules/config.py and run ollama pull for it")
    check("Embeddings work", embeddings_work, f"Run: ollama pull {config.EMBED_MODEL}")
check("Project files", project_files, "Download the project again with git clone")

print()
if all(results):
    print("All good! Start the app with: python main.py")
else:
    print(f"{results.count(False)} check(s) failed. Fix them before the workshop, or ask an instructor.")
    sys.exit(1)
