from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any

try:
    from .config import FusionConfig, load_config
except ImportError:
    from config import FusionConfig, load_config  # type: ignore


SPRINT_ROOT = Path(__file__).resolve().parent.parent
if str(SPRINT_ROOT) not in sys.path:
    sys.path.insert(0, str(SPRINT_ROOT))


def _unavailable_report(module: str, reason: str) -> dict[str, Any]:
    return {
        "module": module,
        "prediction": "Suspicious",
        "confidence": 0,
        "risk_score": 0,
        "summary": reason,
        "positive_indicators": [],
        "negative_indicators": [],
        "missing_evidence": [reason],
        "error": reason,
        "latency_seconds": 0.0,
    }


def _normalize_report(report: dict[str, Any], *, module: str) -> dict[str, Any]:
    normalized = dict(report)
    normalized["module"] = module
    normalized.setdefault("prediction", "Suspicious")
    normalized.setdefault("confidence", 0)
    normalized.setdefault("risk_score", 0)
    normalized.setdefault("summary", "")
    normalized.setdefault("positive_indicators", [])
    normalized.setdefault("negative_indicators", [])
    normalized.setdefault("missing_evidence", [])
    normalized.setdefault("latency_seconds", 0.0)
    return normalized


def _aggregate_url_reports(
    reports: list[dict[str, Any]],
    *,
    module: str,
    jo2: dict[str, Any],
) -> dict[str, Any]:
    if not reports:
        return _unavailable_report(module, "No URLs were available for analysis.")

    available = [report for report in reports if not report.get("error")]
    if not available:
        return _normalize_report(reports[0], module=module)

    prediction_rank = {"Phishing": 3, "Suspicious": 2, "Safe": 1}
    primary = max(
        available,
        key=lambda report: (
            prediction_rank.get(str(report.get("prediction", "Suspicious")).title(), 2),
            float(report.get("risk_score") or 0),
            float(report.get("confidence") or 0),
        ),
    )

    aggregated = _normalize_report(primary, module=module)
    aggregated["urls_analyzed"] = jo2.get("urls", [])
    aggregated["url_reports"] = reports
    aggregated["url_count"] = len(reports)
    return aggregated


def _run_semantic_local(jo1: dict[str, Any]) -> dict[str, Any]:
    start = time.time()
    subject = str(jo1.get("subject") or "")
    body = str(jo1.get("plain_text_body") or jo1.get("cleaned_html_text") or "")

    if not subject and not body:
        return _unavailable_report(
            "Semantic Analysis",
            "Semantic specialist requires subject or body text in JO1.",
        )

    try:
        from semantic.evaluate import load_model, predict_email

        model, tokenizer = load_model()
        result = predict_email(model, tokenizer, subject, body)
        result["risk_score"] = result.get("phishing_probability", result.get("confidence", 0))
        result["summary"] = result.pop("analysis", result.get("summary", ""))
        result["positive_indicators"] = []
        result["negative_indicators"] = []
        result["missing_evidence"] = []
        result["latency_seconds"] = round(time.time() - start, 3)
        return _normalize_report(result, module="Semantic Analysis")
    except Exception as exc:
        report = _unavailable_report("Semantic Analysis", f"Semantic specialist failed: {exc}")
        report["latency_seconds"] = round(time.time() - start, 3)
        return report


def _run_infrastructure_local(jo2: dict[str, Any], *, timeout: float = 8.0) -> dict[str, Any]:
    start = time.time()
    urls = list(jo2.get("urls") or [])
    if not urls:
        report = _unavailable_report(
            "Infrastructure Analysis",
            "Infrastructure specialist received JO2 with no URLs.",
        )
        report["latency_seconds"] = round(time.time() - start, 3)
        return report

    try:
        from infrastructure.predictor import predict

        reports = []
        for url in urls:
            result = predict(url, timeout=timeout, enable_network=True)
            result.pop("evidence", None)
            reports.append(_normalize_report(result, module="Infrastructure Analysis"))

        aggregated = _aggregate_url_reports(reports, module="Infrastructure Analysis", jo2=jo2)
        aggregated["latency_seconds"] = round(time.time() - start, 3)
        return aggregated
    except Exception as exc:
        report = _unavailable_report(
            "Infrastructure Analysis",
            f"Infrastructure specialist failed: {exc}",
        )
        report["latency_seconds"] = round(time.time() - start, 3)
        return report


def _run_runtime_local(
    jo2: dict[str, Any],
    *,
    timeout_ms: int = 30_000,
    headless: bool = True,
) -> dict[str, Any]:
    start = time.time()
    urls = list(jo2.get("urls") or [])
    if not urls:
        report = _unavailable_report("Runtime Analysis", "Runtime specialist received JO2 with no URLs.")
        report["latency_seconds"] = round(time.time() - start, 3)
        return report

    try:
        from runtime.predictor import predict

        reports = []
        for url in urls:
            result = predict(url, timeout_ms=timeout_ms, headless=headless)
            result.pop("evidence", None)
            reports.append(_normalize_report(result, module="Runtime Analysis"))

        aggregated = _aggregate_url_reports(reports, module="Runtime Analysis", jo2=jo2)
        aggregated["latency_seconds"] = round(time.time() - start, 3)
        return aggregated
    except Exception as exc:
        report = _unavailable_report("Runtime Analysis", f"Runtime specialist failed: {exc}")
        report["latency_seconds"] = round(time.time() - start, 3)
        return report


async def _call_remote_specialist(
    *,
    name: str,
    endpoint: str,
    payload: dict[str, Any],
    timeout: int,
    retries: int,
) -> dict[str, Any]:
    import requests

    start = time.time()
    last_error = "Unknown error"
    attempts = max(1, retries + 1)

    for attempt in range(attempts):
        try:
            response = await asyncio.to_thread(
                requests.post,
                endpoint.rstrip("/") + "/predict",
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            result = response.json()
            result["latency_seconds"] = round(time.time() - start, 3)
            return _normalize_report(result, module=name)
        except Exception as exc:
            last_error = str(exc)
            if attempt < attempts - 1:
                await asyncio.sleep(min(2**attempt, 4))

    report = _unavailable_report(name, f"Remote specialist call failed: {last_error}")
    report["latency_seconds"] = round(time.time() - start, 3)
    return report


async def run_specialists_async(
    jo1: dict[str, Any],
    jo2: dict[str, Any],
    *,
    config: FusionConfig | None = None,
    headless: bool = True,
) -> dict[str, dict[str, Any]]:
    """Launch enabled specialists concurrently. Semantic consumes JO1; Infra/Runtime consume JO2."""

    cfg = config or load_config()
    tasks: dict[str, asyncio.Task] = {}

    if cfg.semantic_enabled:
        if cfg.mode == "api" and cfg.semantic_url:
            tasks["SO1"] = asyncio.create_task(
                _call_remote_specialist(
                    name="Semantic Analysis",
                    endpoint=cfg.semantic_url,
                    payload={"JO1": jo1},
                    timeout=cfg.http_timeout,
                    retries=cfg.specialist_retries,
                )
            )
        else:
            tasks["SO1"] = asyncio.create_task(asyncio.to_thread(_run_semantic_local, jo1))

    if cfg.infrastructure_enabled:
        if cfg.mode == "api" and cfg.infrastructure_url:
            tasks["IO1"] = asyncio.create_task(
                _call_remote_specialist(
                    name="Infrastructure Analysis",
                    endpoint=cfg.infrastructure_url,
                    payload={"JO2": jo2},
                    timeout=cfg.http_timeout,
                    retries=cfg.specialist_retries,
                )
            )
        else:
            tasks["IO1"] = asyncio.create_task(asyncio.to_thread(_run_infrastructure_local, jo2))

    if cfg.runtime_enabled:
        if cfg.mode == "api" and cfg.runtime_url:
            tasks["RO1"] = asyncio.create_task(
                _call_remote_specialist(
                    name="Runtime Analysis",
                    endpoint=cfg.runtime_url,
                    payload={"JO2": jo2, "headless": headless},
                    timeout=cfg.http_timeout,
                    retries=cfg.specialist_retries,
                )
            )
        else:
            tasks["RO1"] = asyncio.create_task(
                asyncio.to_thread(_run_runtime_local, jo2, headless=headless)
            )

    outputs: dict[str, dict[str, Any]] = {}
    if tasks:
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for key, result in zip(tasks.keys(), results):
            module_name = {
                "SO1": "Semantic Analysis",
                "IO1": "Infrastructure Analysis",
                "RO1": "Runtime Analysis",
            }[key]
            if isinstance(result, Exception):
                outputs[key] = _unavailable_report(module_name, str(result))
            else:
                outputs[key] = result

    return outputs


def run_specialists(
    jo1: dict[str, Any],
    jo2: dict[str, Any],
    *,
    config: FusionConfig | None = None,
    headless: bool = True,
) -> dict[str, dict[str, Any]]:
    """Synchronous wrapper for specialist orchestration."""

    return asyncio.run(
        run_specialists_async(
            jo1,
            jo2,
            config=config,
            headless=headless,
        )
    )
