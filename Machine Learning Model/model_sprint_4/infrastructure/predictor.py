from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

try:
    from .evidence_builder import build_evidence
    from .preprocessing import missing_evidence
except ImportError:  # Allows `python predictor.py` from this directory.
    from evidence_builder import build_evidence  # type: ignore
    from preprocessing import missing_evidence  # type: ignore


BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "model" / "base"
TOKENIZER_DIR = BASE_DIR / "model" / "tokenizer"
ADAPTER_DIR = BASE_DIR / "model" / "adapter"
PROMPT_PATH = BASE_DIR / "prompt.md"
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"


def model_exists(model_dir: Path = MODEL_DIR, tokenizer_dir: Path = TOKENIZER_DIR) -> bool:
    has_model = (model_dir / "config.json").exists() and (
        (model_dir / "model.safetensors").exists()
        or (model_dir / "pytorch_model.bin").exists()
        or bool(list(model_dir.glob("model-*.safetensors")))
    )
    has_tokenizer = (tokenizer_dir / "tokenizer_config.json").exists() or (model_dir / "tokenizer_config.json").exists()
    return has_model and has_tokenizer


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


def normalize_result(result: dict[str, Any], evidence: dict[str, Any], raw_output: str = "") -> dict[str, Any]:
    prediction = str(result.get("prediction") or "Suspicious").strip().title()
    if prediction not in {"Safe", "Suspicious", "Phishing"}:
        prediction = "Suspicious"

    missing = list(result.get("missing_evidence") or missing_evidence(evidence))
    confidence = _coerce_score(result.get("confidence"), 0)
    risk_score = _coerce_score(result.get("risk_score"), 0)
    statuses = {
        key: value.get("status")
        for key, value in evidence.items()
        if isinstance(value, dict) and value.get("collector")
    }
    unavailable_count = sum(
        1
        for status in statuses.values()
        if status not in {"ok", "partial_socket_resolution", "non_html"}
    )
    if prediction == "Safe" and unavailable_count >= 4:
        prediction = "Suspicious"
        risk_score = max(risk_score, 35)
        confidence = min(confidence, 40)
        if not result.get("summary"):
            result["summary"] = "Infrastructure evidence is too incomplete for a safe assessment."
        if not missing:
            missing = [f"{name}: {status}" for name, status in statuses.items() if status != "ok"]

    return {
        "module": "Infrastructure Analysis",
        "prediction": prediction,
        "confidence": confidence,
        "risk_score": risk_score,
        "summary": str(result.get("summary") or "").strip(),
        "positive_indicators": list(result.get("positive_indicators") or []),
        "negative_indicators": list(result.get("negative_indicators") or []),
        "missing_evidence": missing,
        "raw_output": raw_output,
    }


class InfrastructurePredictor:
    """Lazy local Qwen predictor for infrastructure evidence."""

    def __init__(
        self,
        *,
        model_dir: str | Path = MODEL_DIR,
        tokenizer_dir: str | Path = TOKENIZER_DIR,
        adapter_dir: str | Path = ADAPTER_DIR,
        prompt_path: str | Path = PROMPT_PATH,
        local_files_only: bool = True,
    ):
        self.model_dir = Path(model_dir)
        self.tokenizer_dir = Path(tokenizer_dir)
        self.adapter_dir = Path(adapter_dir)
        self.prompt_path = Path(prompt_path)
        self.local_files_only = local_files_only
        self.tokenizer = None
        self.model = None
        self.torch = None
        self.system_prompt = self.prompt_path.read_text(encoding="utf-8")

    def load(self) -> None:
        if self.model is not None and self.tokenizer is not None:
            return

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch

        if not model_exists(self.model_dir, self.tokenizer_dir):
            print("=" * 100)
            print("Model not found. Downloading...")
            print("=" * 100)

            self.model_dir.mkdir(parents=True, exist_ok=True)
            self.tokenizer_dir.mkdir(parents=True, exist_ok=True)

            tokenizer = AutoTokenizer.from_pretrained(
                MODEL_NAME,
                trust_remote_code=True,
                local_files_only=False,
            )

            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            tokenizer.save_pretrained(self.tokenizer_dir)

            kwargs = {
                "trust_remote_code": True,
                "local_files_only": False,
            }

            if torch.cuda.is_available():
                kwargs["dtype"] = torch.float16
                kwargs["device_map"] = "auto"
            else:
                kwargs["dtype"] = torch.float32

            try:
                model = AutoModelForCausalLM.from_pretrained(
                    MODEL_NAME,
                    **kwargs,
                )
            except TypeError:
                kwargs["torch_dtype"] = kwargs.pop("dtype")
                model = AutoModelForCausalLM.from_pretrained(
                    MODEL_NAME,
                    **kwargs,
                )

            model.save_pretrained(self.model_dir)

            print("Download complete.")

        tokenizer_path = (
            self.tokenizer_dir
            if self.tokenizer_dir.exists()
            else self.model_dir
        )

        self.tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_path,
            trust_remote_code=True,
            local_files_only=True,
        )

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        kwargs = {
            "trust_remote_code": True,
            "local_files_only": True,
        }

        if torch.cuda.is_available():
            kwargs["dtype"] = torch.float16
            kwargs["device_map"] = "auto"
        else:
            kwargs["dtype"] = torch.float32

        try:
            model = AutoModelForCausalLM.from_pretrained(
                self.model_dir,
                **kwargs,
            )
        except TypeError:
            kwargs["torch_dtype"] = kwargs.pop("dtype")
            model = AutoModelForCausalLM.from_pretrained(
                self.model_dir,
                **kwargs,
            )

        if self.adapter_dir.exists() and (
            self.adapter_dir / "adapter_config.json"
        ).exists():
            try:
                from peft import PeftModel

                model = PeftModel.from_pretrained(
                    model,
                    self.adapter_dir,
                    local_files_only=True,
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
                    "Infrastructure Evidence\n\n"
                    f"{evidence_json}\n\n"
                    "Analyze the evidence and return the required JSON only."
                ),
            },
        ]

    def generate(self, evidence: dict[str, Any], *, max_new_tokens: int = 256) -> str:
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
            result = normalize_result(parsed, evidence, raw_output)
        except Exception as exc:
            result = {
                "module": "Infrastructure Analysis",
                "prediction": "Suspicious",
                "confidence": 0,
                "risk_score": 0,
                "summary": f"Infrastructure model failed to generate valid JSON: {type(exc).__name__}.",
                "positive_indicators": [],
                "negative_indicators": [],
                "missing_evidence": missing_evidence(evidence),
                "raw_output": raw_output,
                "error": str(exc),
            }
        result["latency_seconds"] = round(time.time() - start, 3)
        return result

    def predict_url(self, url: str, *, timeout: float = 8.0, enable_network: bool = True) -> dict[str, Any]:
        evidence = build_evidence(url, timeout=timeout, enable_network=enable_network)
        result = self.predict_evidence(evidence)
        result["evidence"] = evidence
        return result


def predict(url: str, *, timeout: float = 8.0, enable_network: bool = True) -> dict[str, Any]:
    return InfrastructurePredictor().predict_url(url, timeout=timeout, enable_network=enable_network)


if __name__ == "__main__":
    target = input("URL: ")
    print(json.dumps(predict(target), indent=2, ensure_ascii=False))