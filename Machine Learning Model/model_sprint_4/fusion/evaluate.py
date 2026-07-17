from __future__ import annotations

import argparse
import json
import time

from pathlib import Path

try:
    from .predictor import MOCK_GMAIL_COMMUNICATION, predict
    from .preprocessing import preprocess_communication
    from .specialist_runner import run_specialists
    from .validate_pipeline import validate_architecture
except ImportError:
    from predictor import MOCK_GMAIL_COMMUNICATION, predict  # type: ignore
    from preprocessing import preprocess_communication  # type: ignore
    from specialist_runner import run_specialists  # type: ignore
    from validate_pipeline import validate_architecture  # type: ignore


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the AEGIS Fusion communication pipeline.")
    parser.add_argument(
        "--communication-json",
        help="Path to a communication JSON file. Defaults to the built-in mock Gmail object.",
    )
    parser.add_argument("--validate", action="store_true", help="Run mandatory architectural validation.")
    parser.add_argument("--with-model", action="store_true", help="Include Fusion model inference in validation.")
    parser.add_argument("--specialists-only", action="store_true", help="Run preprocessing and specialists only.")
    parser.add_argument("--headed", action="store_true", help="Run Runtime browser visibly.")
    args = parser.parse_args()

    communication = (
        json.loads(Path(args.communication_json).read_text(encoding="utf-8"))
        if args.communication_json
        else MOCK_GMAIL_COMMUNICATION
    )

    if args.validate:
        report = validate_architecture(
            communication,
            run_model=args.with_model,
            headless=not args.headed,
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))
        raise SystemExit(0 if report["passed"] else 1)

    started = time.time()
    if args.specialists_only:
        jo1, jo2 = preprocess_communication(communication)
        outputs = run_specialists(jo1, jo2, headless=not args.headed)
        payload = {
            "JO1": jo1,
            "JO2": jo2,
            "SO1": outputs.get("SO1"),
            "IO1": outputs.get("IO1"),
            "RO1": outputs.get("RO1"),
            "total_latency_seconds": round(time.time() - started, 3),
        }
    else:
        payload = predict(communication, headless=not args.headed)

    print(json.dumps(payload, indent=2, ensure_ascii=False))
