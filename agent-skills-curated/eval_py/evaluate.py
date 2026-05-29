
import argparse
import sys
from agent_skills_curated.eval_py.models import SkillEvaluationResult
from agent_skills_curated.eval_py.prompts import HUMAN_TEMPLATE
from agent_skills_curated.eval_py.exceptions import ValidationError
from agent_skills_curated.eval_py.io import save_json, load_json


def print_human_template():
    print(HUMAN_TEMPLATE)



def validate_result(input_path, save_path=None):
    data = load_json(input_path)
    try:
        result = SkillEvaluationResult(**data)
    except Exception as e:
        raise ValidationError(f"Validation failed: {e}")
    print("Validation successful.")
    if save_path:
        save_json(result.dict(), save_path)
        print(f"Saved validated result to {save_path}")




def auto_mode(provider_name, model_name, skill_path, log_dir=None):
    from agent_skills_curated.eval_py.providers import get_provider, ProviderError
    from agent_skills_curated.eval_py.prompts import HUMAN_TEMPLATE
    import traceback
    # Load skill content
    try:
        with open(skill_path, "r", encoding="utf-8") as f:
            skill_content = f.read()
    except Exception as err:
        print(f"Failed to read skill file: {err}", file=sys.stderr)
        sys.exit(1)
    # Compose prompt
    prompt = HUMAN_TEMPLATE + "\nSkill Content:\n" + skill_content
    provider = get_provider(provider_name, model_name)
    try:
        response = provider.judge(prompt)
    except ProviderError as err:
        print(f"Provider error: {err}", file=sys.stderr)
        sys.exit(2)
    except Exception:
        print("Unexpected error during provider call:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(2)
    print("LLM response:")
    print(response)




def main():
    parser = argparse.ArgumentParser(description="Skill Evaluation CLI")
    parser.add_argument("--mode", required=True, choices=["human-template", "validate", "auto"])
    parser.add_argument("--input", help="Input JSON file for validate mode")
    parser.add_argument("--save", help="Path to save validated result")
    parser.add_argument(
        "--provider", default="anthropic",
        help="Provider for auto mode (anthropic, openai, litellm)"
    )
    parser.add_argument(
        "--model", default="claude-3-opus-20240229",
        help="Model name for provider (auto mode)"
    )
    parser.add_argument("--skill", help="Path to skill file for auto mode")
    parser.add_argument("--log-dir", help="Directory to save prompt/response logs (auto mode)")
    args = parser.parse_args()

    if args.mode == "human-template":
        print_human_template()
    elif args.mode == "validate":
        if not args.input:
            print("--input is required for validate mode", file=sys.stderr)
            sys.exit(1)
        validate_result(args.input, args.save)
    elif args.mode == "auto":
        if not args.skill:
            print("--skill is required for auto mode", file=sys.stderr)
            sys.exit(1)
        auto_mode(args.provider, args.model, args.skill, args.log_dir)
    else:
        print(f"Unknown mode: {args.mode}", file=sys.stderr)
        sys.exit(1)



if __name__ == "__main__":
    main()
