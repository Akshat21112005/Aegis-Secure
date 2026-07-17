from __future__ import annotations

import argparse
import json

try:
    from .predictor import predict
    from .evidence_builder import build_evidence
except ImportError:
    from predictor import predict  # type: ignore
    from evidence_builder import build_evidence  # type: ignore


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a URL with the AEGIS runtime specialist.")
    parser.add_argument("url", nargs="?", help="URL to analyze in a live browser.")
    parser.add_argument("--timeout-ms", type=int, default=30_000)
    parser.add_argument("--headed", action="store_true", help="Run the browser with a visible window.")
    parser.add_argument("--evidence-only", action="store_true", help="Collect evidence without loading the model.")
    args = parser.parse_args()

    target = args.url or input("URL: ")
    if args.evidence_only:
        result = build_evidence(target, timeout_ms=args.timeout_ms, headless=not args.headed)
    else:
        result = predict(target, timeout_ms=args.timeout_ms, headless=not args.headed)
    print(json.dumps(result, indent=2, ensure_ascii=False))
