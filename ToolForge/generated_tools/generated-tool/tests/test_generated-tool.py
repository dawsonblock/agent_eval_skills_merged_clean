from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_run(tool_path: Path):
    spec = importlib.util.spec_from_file_location('generated_tool_module', tool_path)
    if spec is None or spec.loader is None:
        raise RuntimeError('Unable to load generated tool module')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run

def test_run_writes_result(tmp_path: Path, monkeypatch) -> None:
    tool_path = Path(__file__).resolve().parents[1] / 'tool.py'
    run = _load_run(tool_path)
    monkeypatch.setenv('TOOLFORGE_DEMO_OUTPUT_DIR', str(tmp_path))
    result = run({'request': 'hello'})
    output_file = Path(result['output_file'])
    assert output_file.exists()
    payload = json.loads(output_file.read_text(encoding='utf-8'))
    assert payload['status'] == 'ok'
