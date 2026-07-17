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
    parser = argparse.ArgumentParser(description="Evaluate a URL with the AEGIS infrastructure specialist.")
    parser.add_argument("url", nargs="?", help="URL or domain to analyze.")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--no-network", action="store_true", help="Build structure without live network collection.")
    parser.add_argument("--evidence-only", action="store_true", help="Collect evidence without loading the model.")
    args = parser.parse_args()

    target = args.url or input("URL: ")
    if args.evidence_only:
        result = build_evidence(target, timeout=args.timeout, enable_network=not args.no_network)
    else:
        result = predict(target, timeout=args.timeout, enable_network=not args.no_network)
    print(json.dumps(result, indent=2, ensure_ascii=False))