"""
Research agent (IterDRAG)
For deep questions: plan sub-questions, search the web and academic databases for
each one, answer them one by one, then combine everything into a cited report.
Built as a LangGraph state machine:

    planner -> search -> answer -> (more sub-questions? back to search) -> synthesize
"""

import json
import operator
from typing import Annotated, List, TypedDict

from langgraph.graph import StateGraph, END

from .config import logger, CHAT_HISTORY_MESSAGES
from .ollama_client import generate
from .prompts import load_prompt
from .web_search import web_search_tool
from .academic_search import search_arxiv, search_openalex, download_and_extract_pdf

MAX_SUB_QUESTIONS = 4


class ResearchState(TypedDict):
    query: str
    sub_questions: List[str]
    current_question_index: int
    answers: Annotated[List[str], operator.add]
    final_answer: str
    conversation_history: str
    rag_context: str
    current_context: str  # Search results passed from the search node to the answer node
    logs: Annotated[List[str], operator.add]


# --- Nodes ---

def planner_node(state: ResearchState):
    """Break the question into sub-questions"""
    prompt = load_prompt(
        "research_planner",
        question=state["query"],
        history=state["conversation_history"] or "None",
        knowledge=state["rag_context"] or "None",
    )
    response = generate(prompt)
    try:
        cleaned = response.replace("```json", "").replace("```", "").strip()
        sub_questions = [str(q) for q in json.loads(cleaned)][:MAX_SUB_QUESTIONS]
        if not sub_questions:
            raise ValueError("empty plan")
    except (ValueError, TypeError):
        logger.warning(f"Could not parse the plan, researching the original question. Planner said: {response[:200]}")
        sub_questions = [state["query"]]

    return {
        "sub_questions": sub_questions,
        "current_question_index": 0,
        "logs": ["📅 Plan:"] + [f"   {i}. {q}" for i, q in enumerate(sub_questions, 1)],
    }


def search_node(state: ResearchState):
    """Search the web, ArXiv and OpenAlex for the current sub-question"""
    question = state["sub_questions"][state["current_question_index"]]
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

    return {
        "current_context": content or "No matching information found in web or academic sources.",
        "logs": logs,
    }


def answer_node(state: ResearchState):
    """Answer the current sub-question from the search results"""
    idx = state["current_question_index"]
    question = state["sub_questions"][idx]
    answer = generate(load_prompt("research_answer", question=question, sources=state["current_context"]))
    return {
        "answers": [f"**{question}**\n{answer}"],
        "current_question_index": idx + 1,
        "logs": [f"📝 Answered: {question}"],
    }


def synthesizer_node(state: ResearchState):
    """Combine the sub-answers into one report"""
    prompt = load_prompt("research_synthesizer", question=state["query"], findings="\n\n".join(state["answers"]))
    return {"final_answer": generate(prompt), "logs": ["✅ Synthesis complete."]}


def should_continue(state: ResearchState):
    return "search" if state["current_question_index"] < len(state["sub_questions"]) else "synthesize"


workflow = StateGraph(ResearchState)
workflow.add_node("planner", planner_node)
workflow.add_node("search", search_node)
workflow.add_node("answer", answer_node)
workflow.add_node("synthesize", synthesizer_node)
workflow.set_entry_point("planner")
workflow.add_edge("planner", "search")
workflow.add_edge("search", "answer")
workflow.add_conditional_edges("answer", should_continue, {"search": "search", "synthesize": "synthesize"})
workflow.add_edge("synthesize", END)
research_graph = workflow.compile()


def run_research(question: str, history: list, rag_engine=None):
    """
    Run the research graph.
    Yields {"type": "log", "content": ...} while working, then {"type": "result", "content": ...}.
    """
    history_text = "\n".join(
        f"{m['role']}: {m['content']}" for m in history[-CHAT_HISTORY_MESSAGES:] if m.get("content")
    )

    rag_context = ""
    if rag_engine:
        yield {"type": "log", "content": "📚 Checking the local knowledge base..."}
        rag_context = rag_engine.query(question)
        yield {"type": "log", "content": "✅ Found relevant notes." if rag_context else "⚪ No relevant notes found."}

    inputs = {
        "query": question,
        "sub_questions": [],
        "current_question_index": 0,
        "answers": [],
        "final_answer": "",
        "conversation_history": history_text,
        "rag_context": rag_context,
        "current_context": "",
        "logs": [],
    }

    try:
        for output in research_graph.stream(inputs):
            for node_name, update in output.items():
                for log in update.get("logs", []):
                    yield {"type": "log", "content": log}
                if node_name == "synthesize":
                    yield {"type": "result", "content": update.get("final_answer", "")}
                    return
    except Exception as e:
        logger.error(f"Research failed: {e}")
        yield {"type": "log", "content": f"❌ Error: {e}"}
        yield {"type": "result", "content": "Sorry, the research process failed. Check your internet connection and try again."}
