<!--
WHAT: Research mode, step 2: answers one sub-question from the web and academic search results.
USED BY: modules/research_agent.py -> answer_node() (runs once per sub-question)
PLACEHOLDERS:
  {{question}} = the current sub-question
  {{sources}}  = search results (web pages, paper abstracts, one full-text extract)
TRY: Ask for a one-paragraph answer, or require at least two different sources per answer.
-->
Answer the following question using ONLY the provided context.
Question: {{question}}
Context: {{sources}}

If the context doesn't contain the answer, say "Information not found."
Include citations [Source: URL].
