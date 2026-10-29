<!--
WHAT: Wraps an analysis or critique prompt together with the notes retrieved from the knowledge base.
USED BY: modules/image_analysis.py -> build_image_prompt() (only when notes were found)
PLACEHOLDERS:
  {{task}}    = the domain prompt, e.g. analyze_urban_sketching.md or critique_fine_art.md
  {{theory}}  = the domain's theory label from DOMAINS in config.py
  {{context}} = the retrieved notes (capped at IMAGE_CONTEXT_CHARS characters)
TRY: Move the notes above the task. Ask the model to name which note each idea came from.
-->
Carefully inspect and analyze the attached image directly.

{{task}}

---
### Reference Background Knowledge ({{theory}})
Use the following domain knowledge to ground your analysis and critique:
{{context}}
