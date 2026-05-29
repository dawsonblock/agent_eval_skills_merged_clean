import sys
import argparse
from agent_skills_curated.eval_py.evaluate import print_human_template, validate_result, auto_mode


def main():
    parser = argparse.ArgumentParser(description="Skill Evaluation CLI")
    parser.add_argument("--mode", required=True, choices=["human-template", "validate", "auto"])
    parser.add_argument("--input", help="Path to input file (validate mode)")
    parser.add_argument("--save", help="Path to save validated result (validate mode)")
    parser.add_argument("--provider", help="Provider name for auto mode")
    parser.add_argument(
        "--model",
        default="claude-3-opus-20240229",
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
