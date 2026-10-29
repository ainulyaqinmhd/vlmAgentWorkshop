<!--
WHAT: Research mode, step 1: breaks the question into sub-questions to research one by one.
USED BY: modules/research_agent.py -> planner_node()
PLACEHOLDERS:
  {{question}}  = the student's question
  {{history}}   = recent conversation
  {{knowledge}} = notes found in the local knowledge base
NOTE: The reply MUST be a JSON list of strings, or the agent falls back to researching the original question.
TRY: Change "2-4" to exactly 2 to make research faster, or ask for one sub-question about real-world examples.
-->
You are a Research Planner.
User Query: {{question}}

Context from previous conversation:
{{history}}

Context from local documents (RAG):
{{knowledge}}

Break this query down into 2-4 specific, step-by-step research questions.
Focus on filling gaps in the local knowledge.
Return ONLY a JSON list of strings.
Example: ["Define X", "Find examples of X", "Compare X and Y"]
