from __future__ import annotations

import json
import os
from pathlib import Path

def run(inputs: dict) -> dict:
    output_dir = Path(
        os.environ.get(
            'TOOLFORGE_DEMO_OUTPUT_DIR',
            str(Path(__file__).resolve().parents[1] / '_outputs' / 'generated-tool'),
        )
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {'echo': inputs, 'status': 'ok'}
    out_file = output_dir / 'result.json'
    out_file.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    return {'message': 'Tool executed', 'output_file': str(out_file)}

def main() -> int:
    raw = os.environ.get('TOOLFORGE_INPUTS', '{}')
    try:
        inputs = json.loads(raw)
    except json.JSONDecodeError:
        inputs = {}
    result = run(inputs)
    print(json.dumps(result))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
