"""
Research agent (IterDRAG)
For deep questions: plan sub-questions, search the web and academic databases for
each one, answer them one by one, then combine everything into a cited report.

    plan -> for each sub-question: [ search -> answer ] -> synthesize

Each step is a plain function, and run_research() calls them in order.
"""

import json

from .config import logger, CHAT_HISTORY_MESSAGES
from .ollama_client import generate
from .prompts import load_prompt
from .web_search import web_search_tool
from .academic_search import search_arxiv, search_openalex, download_and_extract_pdf

MAX_SUB_QUESTIONS = 4


def plan(question: str, history: str, knowledge: str) -> list:
    """Step 1: break the question into sub-questions"""
    response = generate(load_prompt("research_planner", question=question,
                                    history=history or "None", knowledge=knowledge or "None"))
    try:
        cleaned = response.replace("```json", "").replace("```", "").strip()
        sub_questions = [str(q) for q in json.loads(cleaned)][:MAX_SUB_QUESTIONS]
        if sub_questions:
            return sub_questions
    except (ValueError, TypeError):
        pass
    logger.warning(f"Could not parse the plan, researching the original question. Planner said: {response[:200]}")
    return [question]


def search(question: str):
    """Step 2: search the web, ArXiv and OpenAlex. Returns (sources_text, log_lines)"""
    logs = [f"🔍 Searching: {question}"]
    content = ""
    pdf_urls = []

    web = web_search_tool(question, max_results=3)
    if web.get("results"):
        logs.append(f"   • {len(web['results'])} web results")
        content += "--- WEB SOURCES ---\n"
        for res in web["results"]:
            content += f"URL: {res.get('url', '')}\nContent: {res.get('content', '')[:1000]}\n\n"

    for name, result in (("ArXiv", search_arxiv(question, max_results=3)),
                         ("OpenAlex", search_openalex(question, max_results=3))):
        papers = result.get("results") if result else None
        if not papers:
            continue
        logs.append(f"   • {len(papers)} {name} papers")
        content += f"--- ACADEMIC SOURCES ({name}) ---\n"
        for p in papers:
            content += (f"Title: {p['title']}\nAuthors: {p['authors']}\nPublished: {p['published']}\n"
                        f"Link: {p['pdf_url']}\nAbstract: {p['summary']}\n\n")
            if p["pdf_url"] and (p["pdf_url"].lower().endswith(".pdf") or "arxiv.org/pdf" in p["pdf_url"]):
                pdf_urls.append((p["title"], p["pdf_url"]))

    # Deep read: add the full text of the first paper we can download
    for title, url in pdf_urls:
        text = download_and_extract_pdf(url, max_chars=4000)
        if text:
            logs.append(f"   • 📖 Read full text of: {title}")
            content += f"\n--- FULL TEXT EXTRACT ({title}) ---\n{text}\n"
            break

    return content or "No matching information found in web or academic sources.", logs


def answer(question: str, sources: str) -> str:
    """Step 3: answer one sub-question from its search results"""
    return generate(load_prompt("research_answer", question=question, sources=sources))


def synthesize(question: str, findings: list) -> str:
    """Step 4: combine the sub-answers into one report"""
    return generate(load_prompt("research_synthesizer", question=question, findings="\n\n".join(findings)))


def run_research(question: str, history: list, rag_engine=None):
    """
    Run the whole research process.
    Yields {"type": "log", "content": ...} while working, then {"type": "result", "content": ...}.
    """
    try:
        history_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in history[-CHAT_HISTORY_MESSAGES:] if m.get("content")
        )

        knowledge = ""
        if rag_engine:
            yield {"type": "log", "content": "📚 Checking the local knowledge base..."}
            knowledge = rag_engine.query(question)
            yield {"type": "log", "content": "✅ Found relevant notes." if knowledge else "⚪ No relevant notes found."}

        sub_questions = plan(question, history_text, knowledge)
        yield {"type": "log", "content": "📅 Plan:"}
        for i, q in enumerate(sub_questions, 1):
            yield {"type": "log", "content": f"   {i}. {q}"}

        findings = []
        for q in sub_questions:
            sources, logs = search(q)
            for line in logs:
                yield {"type": "log", "content": line}
            findings.append(f"**{q}**\n{answer(q, sources)}")
            yield {"type": "log", "content": f"📝 Answered: {q}"}

        yield {"type": "log", "content": "🧩 Combining the findings (prompt file: prompts/research_synthesizer.md)..."}
        report = synthesize(question, findings)
        yield {"type": "log", "content": "✅ Synthesis complete."}
        yield {"type": "result", "content": report}

    except Exception as e:
        logger.error(f"Research failed: {e}")
        yield {"type": "log", "content": f"❌ Error: {e}"}
        yield {"type": "result", "content": "Sorry, the research process failed. Check your internet connection and try again."}
