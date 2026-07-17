from __future__ import annotations

from typing import Any

try:
    from .predictor import MOCK_GMAIL_COMMUNICATION, build_fusion_input
    from .preprocessing import build_jo1, build_jo2, preprocess_communication
    from .specialist_runner import run_specialists
except ImportError:
    from predictor import MOCK_GMAIL_COMMUNICATION, build_fusion_input  # type: ignore
    from preprocessing import build_jo1, build_jo2, preprocess_communication  # type: ignore
    from specialist_runner import run_specialists  # type: ignore


REQUIRED_JF_FIELDS = {
    "prediction",
    "confidence",
    "risk_score",
    "summary",
    "reasoning",
    "recommended_action",
    "positive_indicators",
    "negative_indicators",
    "missing_evidence",
}

FORBIDDEN_JF_FIELDS = {
    "JO1",
    "JO2",
    "SO1",
    "IO1",
    "RO1",
    "PF",
    "fusion_evidence",
    "specialist_outputs",
    "url_reports",
}


def _check(name: str, condition: bool, detail: str, checks: list[dict[str, Any]]) -> None:
    checks.append({"name": name, "passed": condition, "detail": detail})


def validate_architecture(
    communication: dict[str, Any] | None = None,
    *,
    run_model: bool = False,
    headless: bool = True,
) -> dict[str, Any]:
    """Validate the mandatory Fusion communication-object architecture."""

    communication = communication or MOCK_GMAIL_COMMUNICATION
    checks: list[dict[str, Any]] = []

    _check(
        "communication_source_supported",
        communication.get("source") in {"gmail", "sms"},
        f"source={communication.get('source')}",
        checks,
    )

    jo1, jo2 = preprocess_communication(communication)

    _check("jo1_created", jo1.get("object_type") == "JO1", "JO1 object_type present", checks)
    _check("jo2_created", jo2.get("object_type") == "JO2", "JO2 object_type present", checks)
    _check(
        "jo1_has_semantic_fields",
        all(key in jo1 for key in ("subject", "sender", "receiver", "plain_text_body", "cleaned_html_text")),
        "semantic fields present in JO1",
        checks,
    )
    _check(
        "jo1_excludes_url_intelligence",
        "urls" not in jo1 and "url_sources" not in jo1,
        "JO1 does not contain URL intelligence fields",
        checks,
    )
    _check(
        "jo2_has_urls",
        isinstance(jo2.get("urls"), list) and len(jo2["urls"]) > 0,
        f"urls={jo2.get('urls')}",
        checks,
    )
    _check(
        "jo2_has_ocr_extension_point",
        "ocr_urls" in jo2 and isinstance(jo2["ocr_urls"], list),
        "ocr_urls list reserved for future OCR integration",
        checks,
    )

    ocr_jo2 = build_jo2(communication, ocr_urls=["https://ocr-example.test/future"])
    _check(
        "ocr_urls_append_without_fusion_changes",
        "https://ocr-example.test/future" in ocr_jo2["urls"],
        "OCR URLs append into JO2 only",
        checks,
    )

    specialist_outputs = run_specialists(jo1, jo2, headless=headless)
    so1 = specialist_outputs.get("SO1", {})
    io1 = specialist_outputs.get("IO1", {})
    ro1 = specialist_outputs.get("RO1", {})

    _check("so1_created", bool(so1), "SO1 returned", checks)
    _check("io1_created", bool(io1), "IO1 returned", checks)
    _check("ro1_created", bool(ro1), "RO1 returned", checks)

    fusion_input = build_fusion_input(
        pf="PF",
        jo1=jo1,
        so1=so1,
        jo2=jo2,
        io1=io1,
        ro1=ro1,
    )
    _check(
        "fusion_input_exact_keys",
        set(fusion_input.keys()) == {"PF", "JO1", "SO1", "JO2", "IO1", "RO1"},
        f"keys={sorted(fusion_input.keys())}",
        checks,
    )

    if run_model:
        from predictor import FusionPredictor

        jf = FusionPredictor().predict_communication(communication, headless=headless)
    else:
        jf = {
            "prediction": "Suspicious",
            "confidence": 50,
            "risk_score": 55,
            "summary": "Validation mode without model inference.",
            "reasoning": "Structural checks only.",
            "recommended_action": "Review manually.",
            "positive_indicators": [],
            "negative_indicators": [],
            "missing_evidence": [],
        }

    _check(
        "jf_required_fields",
        REQUIRED_JF_FIELDS.issubset(jf.keys()),
        f"missing={sorted(REQUIRED_JF_FIELDS - set(jf.keys()))}",
        checks,
    )
    _check(
        "jf_excludes_internal_objects",
        not (FORBIDDEN_JF_FIELDS & set(jf.keys())),
        f"forbidden={sorted(FORBIDDEN_JF_FIELDS & set(jf.keys()))}",
        checks,
    )

    passed = all(item["passed"] for item in checks)
    return {
        "passed": passed,
        "checks": checks,
        "JO1": jo1,
        "JO2": jo2,
        "SO1": so1,
        "IO1": io1,
        "RO1": ro1,
        "JF": jf if run_model else None,
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Validate Fusion communication-object architecture.")
    parser.add_argument("--with-model", action="store_true")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    report = validate_architecture(run_model=args.with_model, headless=not args.headed)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report["passed"] else 1)
