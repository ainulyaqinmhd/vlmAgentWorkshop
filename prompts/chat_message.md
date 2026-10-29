<!--
WHAT: The message built for every typed question (outside research mode).
USED BY: modules/ui.py -> chat()
PLACEHOLDERS:
  {{history}}   = the last few messages of the conversation (CHAT_HISTORY_MESSAGES in config.py)
  {{knowledge}} = notes retrieved from the knowledge base for this question
  {{question}}  = what the student just typed
TRY: Remove the "don't make up an answer" rule and ask something the notes don't cover. What changes?
-->
Conversation so far:
{{history}}

Relevant notes from the knowledge base:
{{knowledge}}

Instructions:
- Give an educational, context-rich answer that is easy to understand. Don't oversimplify the concepts, but avoid dense academic jargon. Use bullet points or short paragraphs.
- When you use information from the notes, refer to the source by the name shown in its [Source: ...] tag, e.g. "according to the Gibson notes".
- If the question is about the uploaded image, look at the image and refer to specific parts of it.
- If the question can't be answered from the notes or the image, say so clearly instead of making up an answer.

Student's question: {{question}}
