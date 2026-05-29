from agent_skills_curated.eval_py.models import SkillEvaluationResult
from agent_skills_curated.eval_py.prompts import HUMAN_TEMPLATE
from agent_skills_curated.eval_py.exceptions import ValidationError
from agent_skills_curated.eval_py.io import save_json, load_json


def print_human_template():
	print(HUMAN_TEMPLATE)


def validate_result(input_path, save_path=None):
	data = load_json(input_path)
	try:
		SkillEvaluationResult(**data)
	except Exception as e:
		raise ValidationError(f"Validation failed: {e}")
	print("Validation successful.")
	if save_path:
		save_json(data, save_path)
		print(f"Saved validated result to {save_path}")
from agent_skills_curated.eval_py.models import SkillEvaluationResult
from agent_skills_curated.eval_py.prompts import HUMAN_TEMPLATE
from agent_skills_curated.eval_py.exceptions import ValidationError
from agent_skills_curated.eval_py.io import save_json, load_json


def print_human_template():
	print(HUMAN_TEMPLATE)


def validate_result(input_path, save_path=None):
	data = load_json(input_path)
	try:
		SkillEvaluationResult(**data)
	except Exception as e:
		raise ValidationError(f"Validation failed: {e}")
	print("Validation successful.")
	if save_path:
		save_json(data, save_path)
		print(f"Saved validated result to {save_path}")
from agent_skills_curated.eval_py.models import SkillEvaluationResult
from agent_skills_curated.eval_py.prompts import HUMAN_TEMPLATE
from agent_skills_curated.eval_py.exceptions import ValidationError
from agent_skills_curated.eval_py.io import save_json, load_json



def print_human_template():
	print(HUMAN_TEMPLATE)



def validate_result(input_path, save_path=None):
	data = load_json(input_path)
	try:
		SkillEvaluationResult(**data)
	except Exception as e:
		raise ValidationError(f"Validation failed: {e}")
	print("Validation successful.")
	if save_path:
		save_json(data, save_path)
		print(f"Saved validated result to {save_path}")


