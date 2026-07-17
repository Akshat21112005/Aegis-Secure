from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

try:
    from .evidence_builder import build_evidence
except ImportError:
    from evidence_builder import build_evidence  # type: ignore


BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "model" / "base"
TOKENIZER_DIR = BASE_DIR / "model" / "tokenizer"
ADAPTER_DIR = BASE_DIR / "model" / "adapter"
PROMPT_PATH = BASE_DIR / "prompt.md"
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
INFRA_MODEL_DIR = BASE_DIR.parent / "infrastructure" / "model" / "base"
INFRA_TOKENIZER_DIR = BASE_DIR.parent / "infrastructure" / "model" / "tokenizer"
INFRA_ADAPTER_DIR = BASE_DIR.parent / "infrastructure" / "model" / "adapter"


def model_exists(model_dir: Path = MODEL_DIR, tokenizer_dir: Path = TOKENIZER_DIR) -> bool:
    has_model = (model_dir / "config.json").exists() and (
        (model_dir / "model.safetensors").exists()
        or (model_dir / "pytorch_model.bin").exists()
        or bool(list(model_dir.glob("model-*.safetensors")))
    )
    has_tokenizer = (tokenizer_dir / "tokenizer_config.json").exists() or (
        model_dir / "tokenizer_config.json"
    ).exists()
    return has_model and has_tokenizer


def download_model(
    *,
    model_dir: Path = MODEL_DIR,
    tokenizer_dir: Path = TOKENIZER_DIR,
    model_name: str = MODEL_NAME,
    force: bool = False,
) -> tuple[Path, Path]:
    """Download Qwen2.5-1.5B-Instruct from Hugging Face into runtime/model/."""

    if not force and model_exists(model_dir, tokenizer_dir):
        print(f"Model already present under {model_dir.parent}")
        return model_dir, tokenizer_dir

    from transformers import AutoModelForCausalLM, AutoTokenizer

    model_dir.mkdir(parents=True, exist_ok=True)
    tokenizer_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading tokenizer: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    tokenizer.save_pretrained(tokenizer_dir)

    print(f"Downloading model weights: {model_name}")
    model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)
    model.save_pretrained(model_dir)

    if not model_exists(model_dir, tokenizer_dir):
        raise RuntimeError(f"Download completed but model files were not saved under {model_dir.parent}")

    print(f"Saved tokenizer to {tokenizer_dir}")
    print(f"Saved model to {model_dir}")
    return model_dir, tokenizer_dir


def ensure_local_model(
    *,
    model_dir: Path = MODEL_DIR,
    tokenizer_dir: Path = TOKENIZER_DIR,
    model_name: str = MODEL_NAME,
    download_if_missing: bool = False,
    force_download: bool = False,
) -> tuple[Path, Path]:
    """Return local runtime model paths, optionally downloading them first."""

    if force_download or (download_if_missing and not model_exists(model_dir, tokenizer_dir)):
        return download_model(
            model_dir=model_dir,
            tokenizer_dir=tokenizer_dir,
            model_name=model_name,
            force=force_download,
        )
    if model_exists(model_dir, tokenizer_dir):
        return model_dir, tokenizer_dir
    return model_dir, tokenizer_dir


def resolve_model_paths() -> tuple[Path, Path, Path]:
    if model_exists(MODEL_DIR, TOKENIZER_DIR):
        return MODEL_DIR, TOKENIZER_DIR, ADAPTER_DIR
    if model_exists(INFRA_MODEL_DIR, INFRA_TOKENIZER_DIR):
        return INFRA_MODEL_DIR, INFRA_TOKENIZER_DIR, INFRA_ADAPTER_DIR
    return MODEL_DIR, TOKENIZER_DIR, ADAPTER_DIR


def extract_json(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.S)
    if fenced:
        cleaned = fenced.group(1)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output.")
    return json.loads(cleaned[start : end + 1])


def _coerce_score(value: Any, default: int = 0) -> int:
    try:
        number = float(value)
    except Exception:
        return default
    if number <= 1:
        number *= 100
    return int(max(0, min(100, round(number))))


def normalize_result(result: dict[str, Any], raw_output: str = "") -> dict[str, Any]:
    prediction = str(result.get("prediction") or "Suspicious").strip().title()
    if prediction not in {"Safe", "Suspicious", "Phishing"}:
        prediction = "Suspicious"

    return {
        "module": "Runtime Analysis",
        "prediction": prediction,
        "confidence": _coerce_score(result.get("confidence"), 0),
        "risk_score": _coerce_score(result.get("risk_score"), 0),
        "summary": str(result.get("summary") or "").strip(),
        "positive_indicators": list(result.get("positive_indicators") or []),
        "negative_indicators": list(result.get("negative_indicators") or []),
        "missing_evidence": list(result.get("missing_evidence") or []),
        "raw_output": raw_output,
    }


class RuntimePredictor:
    """Lazy local Qwen predictor for browser runtime evidence."""

    def __init__(
        self,
        *,
        model_dir: str | Path | None = None,
        tokenizer_dir: str | Path | None = None,
        adapter_dir: str | Path | None = None,
        prompt_path: str | Path = PROMPT_PATH,
        local_files_only: bool = True,
        auto_download: bool = True
    ):
        self.model_dir = Path(model_dir or MODEL_DIR)
        self.tokenizer_dir = Path(tokenizer_dir or TOKENIZER_DIR)
        self.adapter_dir = Path(adapter_dir or ADAPTER_DIR)
        self.prompt_path = Path(prompt_path)
        self.local_files_only = local_files_only
        self.auto_download = auto_download
        self.tokenizer = None
        self.model = None
        self.torch = None
        self.system_prompt = self.prompt_path.read_text(encoding="utf-8")

    def load(self) -> None:
        if self.model is not None and self.tokenizer is not None:
            return

        using_runtime_paths = self.model_dir == MODEL_DIR and self.tokenizer_dir == TOKENIZER_DIR
        if using_runtime_paths:
            ensure_local_model(download_if_missing=self.auto_download)
            if model_exists(MODEL_DIR, TOKENIZER_DIR):
                self.model_dir = MODEL_DIR
                self.tokenizer_dir = TOKENIZER_DIR
            elif model_exists(INFRA_MODEL_DIR, INFRA_TOKENIZER_DIR):
                self.model_dir = INFRA_MODEL_DIR
                self.tokenizer_dir = INFRA_TOKENIZER_DIR
                self.adapter_dir = INFRA_ADAPTER_DIR
        elif not model_exists(self.model_dir, self.tokenizer_dir):
            resolved_model, resolved_tokenizer, resolved_adapter = resolve_model_paths()
            if model_exists(resolved_model, resolved_tokenizer):
                self.model_dir = resolved_model
                self.tokenizer_dir = resolved_tokenizer
                self.adapter_dir = resolved_adapter

        if not model_exists(self.model_dir, self.tokenizer_dir):
            raise FileNotFoundError(
                "Local runtime model/tokenizer not found. "
                f"Run `python predictor.py --download-model` to save {MODEL_NAME} under {MODEL_DIR.parent}."
            )

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        tokenizer_path = self.tokenizer_dir if self.tokenizer_dir.exists() else self.model_dir
        self.tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_path,
            trust_remote_code=True,
            local_files_only=self.local_files_only,
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        kwargs: dict[str, Any] = {
            "trust_remote_code": True,
            "local_files_only": self.local_files_only,
        }
        if torch.cuda.is_available():
            kwargs["dtype"] = torch.float16
            kwargs["device_map"] = "auto"
        else:
            kwargs["dtype"] = torch.float32

        try:
            model = AutoModelForCausalLM.from_pretrained(self.model_dir, **kwargs)
        except TypeError as exc:
            if "dtype" not in str(exc):
                raise
            kwargs["torch_dtype"] = kwargs.pop("dtype")
            model = AutoModelForCausalLM.from_pretrained(self.model_dir, **kwargs)

        if self.adapter_dir.exists() and (self.adapter_dir / "adapter_config.json").exists():
            try:
                from peft import PeftModel

                model = PeftModel.from_pretrained(
                    model,
                    self.adapter_dir,
                    local_files_only=self.local_files_only,
                )
            except Exception:
                pass

        if not torch.cuda.is_available():
            model.to("cpu")
        model.eval()
        self.model = model

    def build_messages(self, evidence: dict[str, Any]) -> list[dict[str, str]]:
        evidence_json = json.dumps(evidence, indent=2, ensure_ascii=False)
        return [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": (
                    "Runtime Evidence\n\n"
                    f"{evidence_json}\n\n"
                    "Analyze the evidence and return the required JSON only."
                ),
            },
        ]

    def generate(self, evidence: dict[str, Any], *, max_new_tokens: int = 1024) -> str:
        self.load()
        assert self.model is not None
        assert self.tokenizer is not None
        assert self.torch is not None

        messages = self.build_messages(evidence)
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(text, return_tensors="pt")
        inputs = {key: value.to(self.model.device) for key, value in inputs.items()}

        with self.torch.inference_mode():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                repetition_penalty=1.05,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        generated = outputs[0][inputs["input_ids"].shape[1] :]
        return self.tokenizer.decode(generated, skip_special_tokens=True)

    def predict_evidence(self, evidence: dict[str, Any]) -> dict[str, Any]:
        start = time.time()
        raw_output = ""
        try:
            raw_output = self.generate(evidence)
            parsed = extract_json(raw_output)
            result = normalize_result(parsed, raw_output)
        except Exception as exc:
            result = {
                "module": "Runtime Analysis",
                "prediction": "Suspicious",
                "confidence": 0,
                "risk_score": 0,
                "summary": f"Runtime model failed to generate valid JSON: {type(exc).__name__}.",
                "positive_indicators": [],
                "negative_indicators": [],
                "missing_evidence": [],
                "raw_output": raw_output,
                "error": str(exc),
            }
        result["latency_seconds"] = round(time.time() - start, 3)
        return result

    def predict_url(self, url: str, *, timeout_ms: int = 30_000, headless: bool = True) -> dict[str, Any]:
        evidence = build_evidence(url, timeout_ms=timeout_ms, headless=headless)
        result = self.predict_evidence(evidence)
        result["evidence"] = evidence
        return result


def predict(url: str, *, timeout_ms: int = 30_000, headless: bool = True) -> dict[str, Any]:
    return RuntimePredictor().predict_url(url, timeout_ms=timeout_ms, headless=headless)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AEGIS Runtime Specialist predictor.")
    parser.add_argument("url", nargs="?", help="URL to analyze in a live browser.")
    parser.add_argument(
        "--download-model",
        action="store_true",
        help=f"Download and save {MODEL_NAME} into runtime/model/.",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download the model even if local files already exist.",
    )
    parser.add_argument("--timeout-ms", type=int, default=30_000)
    parser.add_argument("--headed", action="store_true", help="Run the browser with a visible window.")
    args = parser.parse_args()

    if args.download_model or args.force_download:
        download_model(force=args.force_download)
        if not args.url:
            raise SystemExit(0)

    target = args.url or input("URL: ")
    print(
        json.dumps(
            predict(target, timeout_ms=args.timeout_ms, headless=not args.headed),
            indent=2,
            ensure_ascii=False,
        )
    )