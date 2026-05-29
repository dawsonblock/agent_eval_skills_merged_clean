import argparse
import sys
from agent_skills_curated.eval_py.models import SkillEvaluationResult
from agent_skills_curated.eval_py.prompts import HUMAN_TEMPLATE
from agent_skills_curated.eval_py.exceptions import ValidationError
from agent_skills_curated.eval_py.io import save_json, load_json


        print("Auto mode not yet implemented.")
    print(HUMAN_TEMPLATE)


    else:
    data = load_json(input_path)
    try:
        result = SkillEvaluationResult(**data)
    except Exception as e:
        raise ValidationError(f"Validation failed: {e}")
    print("Validation successful.")
    if save_path:
        save_json(result.dict(), save_path)
        print(f"Saved validated result to {save_path}")


        print(f"Unknown mode: {args.mode}", file=sys.stderr)
    parser = argparse.ArgumentParser(description="Skill Evaluation CLI")
    parser.add_argument("--mode", required=True, choices=["human-template", "validate", "auto"])
    parser.add_argument("--input", help="Input JSON file for validate mode")
    parser.add_argument("--save", help="Path to save validated result")
    args = parser.parse_args()

    if args.mode == "human-template":
        print_human_template()
    elif args.mode == "validate":
        if not args.input:
            print("--input is required for validate mode", file=sys.stderr)
            sys.exit(1)
        validate_result(args.input, args.save)
    elif args.mode == "auto":
        print("Auto mode not yet implemented.")
    else:
        print(f"Unknown mode: {args.mode}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
        sys.exit(1)

if __name__ == "__main__":
    main()
