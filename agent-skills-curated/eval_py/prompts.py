"""
Prompt templates for LLM-based skill judging.
"""


HUMAN_TEMPLATE = (
	"""
You are an expert evaluator. Given a skill description and content, judge according to the rubric below and return a structured JSON object.

Rubric:
- Description: clarity, specificity, usefulness
- Content: completeness, actionability, technical quality, documentation quality
- Provide concise rationale for each section, strengths, weaknesses, and suggestions.
- Do not include step-by-step reasoning; only a summary rationale.
- Return only the JSON object, no extra commentary.
"""
)

# You may add more prompt templates for different providers/models as needed.
