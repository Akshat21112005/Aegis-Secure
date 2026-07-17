from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

try:
    from .config import FusionConfig, load_config
    from .preprocessing import preprocess_communication
    from .specialist_runner import run_specialists
except ImportError:
    from config import FusionConfig, load_config  # type: ignore
    from preprocessing import preprocess_communication  # type: ignore
    from specialist_runner import run_specialists  # type: ignore


BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "model" / "base"
TOKENIZER_DIR = BASE_DIR / "model" / "tokenizer"
ADAPTER_DIR = BASE_DIR / "model" / "adapter"
PROMPT_PATH = BASE_DIR / "prompt.md"
DEFAULT_MODEL_NAME = "Qwen/Qwen2.5-3B-Instruct"
RUNTIME_MODEL_DIR = BASE_DIR.parent / "runtime" / "model" / "base"
RUNTIME_TOKENIZER_DIR = BASE_DIR.parent / "runtime" / "model" / "tokenizer"
RUNTIME_ADAPTER_DIR = BASE_DIR.parent / "runtime" / "model" / "adapter"
INFRA_MODEL_DIR = BASE_DIR.parent / "infrastructure" / "model" / "base"
INFRA_TOKENIZER_DIR = BASE_DIR.parent / "infrastructure" / "model" / "tokenizer"
INFRA_ADAPTER_DIR = BASE_DIR.parent / "infrastructure" / "model" / "adapter"


MOCK_GMAIL_COMMUNICATION: dict[str, Any] = {
    "source": "gmail",
    "message_id": "18f3a2b4c5d6e7f8091122aabbccddee",
    "thread_id": "18f3a2b4c5d6e7f8091122aabbccddee",
    "history_id": "823451",
    "sender": "security-alerts@microsoft-support-verify.com",
    "receiver": "user@gmail.com",
    "subject": "Urgent: Verify your Microsoft account within 24 hours",
    "headers": {
        "From": "security-alerts@microsoft-support-verify.com",
        "To": "user@gmail.com",
        "Reply-To": "support@m365-login-verify.net",
        "Return-Path": "security-alerts@microsoft-support-verify.com",
        "Authentication-Results": "spf=fail; dmarc=fail",
        "List-Unsubscribe": "<https://m365-login-verify.net/unsubscribe>",
    },
    "metadata": {
        "label_ids": ["INBOX", "UNREAD", "IMPORTANT"],
        "size_estimate": 8240,
        "snippet": "Your Microsoft account will be locked unless you verify immediately.",
    },
    "timestamps": {
        "internal_date": "2026-07-15T10:42:11Z",
        "received_at": "2026-07-15T10:42:12Z",
    },
    "plain_text_body": (
        "Dear user,\n\n"
        "Your Microsoft account will be locked within 24 hours due to unusual sign-in activity.\n"
        "Verify immediately at https://m365-login-verify.net/account/update\n\n"
        "Microsoft Security Team"
    ),
    "html_body": (
        "<html><body>"
        "<p>Dear user,</p>"
        "<p>Your Microsoft account will be locked within 24 hours due to unusual sign-in activity.</p>"
        "<p><a href='https://m365-login-verify.net/account/update'>Verify Account Now</a></p>"
        "<img src='https://cdn.fake-ms-logo.com/logo.png' alt='Microsoft Logo' />"
        "</body></html>"
    ),
    "attachments": [
        {
            "filename": "Account_Notice.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 48213,
            "content_id": "att-001",
            "metadata_urls": ["https://m365-login-verify.net/account/update"],
        }
    ],
    "embedded_images": [
        {
            "filename": "logo.png",
            "mime_type": "image/png",
            "content_id": "img-001",
            "metadata_urls": ["https://cdn.fake-ms-logo.com/logo.png"],
        }
    ],
}


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
    model_name: str = DEFAULT_MODEL_NAME,
    force: bool = False,
) -> tuple[Path, Path]:
    """Download the Fusion reasoning model into fusion/model/."""

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


def resolve_model_paths(config: FusionConfig | None = None) -> tuple[Path, Path, Path]:
    cfg = config or load_config()
    if model_exists(cfg.model_dir, cfg.tokenizer_dir):
        return cfg.model_dir, cfg.tokenizer_dir, cfg.adapter_dir
    if model_exists(RUNTIME_MODEL_DIR, RUNTIME_TOKENIZER_DIR):
        return RUNTIME_MODEL_DIR, RUNTIME_TOKENIZER_DIR, RUNTIME_ADAPTER_DIR
    if model_exists(INFRA_MODEL_DIR, INFRA_TOKENIZER_DIR):
        return INFRA_MODEL_DIR, INFRA_TOKENIZER_DIR, INFRA_ADAPTER_DIR
    return cfg.model_dir, cfg.tokenizer_dir, cfg.adapter_dir


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


def build_fusion_input(
    *,
    pf: str,
    jo1: dict[str, Any],
    so1: dict[str, Any],
    jo2: dict[str, Any],
    io1: dict[str, Any],
    ro1: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the exact Fusion reasoning payload: PF + JO1 + SO1 + JO2 + IO1 + RO1."""

    return {
        "PF": pf,
        "JO1": jo1,
        "SO1": so1,
        "JO2": jo2,
        "IO1": io1,
        "RO1": ro1,
    }


def normalize_jf(result: dict[str, Any]) -> dict[str, Any]:
    prediction = str(result.get("prediction") or "Suspicious").strip().title()
    if prediction not in {"Safe", "Suspicious", "Phishing"}:
        prediction = "Suspicious"

    return {
        "prediction": prediction,
        "confidence": _coerce_score(result.get("confidence"), 0),
        "risk_score": _coerce_score(result.get("risk_score"), 0),
        "summary": str(result.get("summary") or "").strip(),
        "reasoning": str(result.get("reasoning") or result.get("summary") or "").strip(),
        "recommended_action": str(result.get("recommended_action") or "").strip(),
        "positive_indicators": list(result.get("positive_indicators") or []),
        "negative_indicators": list(result.get("negative_indicators") or []),
        "missing_evidence": list(result.get("missing_evidence") or []),
    }


class FusionPredictor:
    """Chief decision engine: reasons over JO1/SO1/JO2/IO1/RO1 only."""

    def __init__(
        self,
        *,
        config: FusionConfig | None = None,
        model_dir: str | Path | None = None,
        tokenizer_dir: str | Path | None = None,
        adapter_dir: str | Path | None = None,
        prompt_path: str | Path | None = None,
        local_files_only: bool = True,
    ):
        self.config = config or load_config()
        resolved_model, resolved_tokenizer, resolved_adapter = resolve_model_paths(self.config)
        self.model_dir = Path(model_dir or resolved_model)
        self.tokenizer_dir = Path(tokenizer_dir or resolved_tokenizer)
        self.adapter_dir = Path(adapter_dir or resolved_adapter)
        self.prompt_path = Path(prompt_path or self.config.prompt_path)
        self.local_files_only = local_files_only
        self.tokenizer = None
        self.model = None
        self.torch = None
        self.system_prompt = self.prompt_path.read_text(encoding="utf-8")

    def load(self) -> None:
        if self.model is not None and self.tokenizer is not None:
            return
        if not model_exists(self.model_dir, self.tokenizer_dir):
            raise FileNotFoundError(
                "Local Fusion model/tokenizer not found. "
                f"Run `python predictor.py --download-model` to save {self.config.model_name} under {BASE_DIR / 'model'}."
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

    def build_messages(self, fusion_input: dict[str, Any]) -> list[dict[str, str]]:
        payload = {
            "JO1": fusion_input["JO1"],
            "SO1": fusion_input["SO1"],
            "JO2": fusion_input["JO2"],
            "IO1": fusion_input["IO1"],
            "RO1": fusion_input["RO1"],
        }
        payload_json = json.dumps(payload, indent=2, ensure_ascii=False)
        return [
            {"role": "system", "content": fusion_input["PF"]},
            {
                "role": "user",
                "content": (
                    "Fusion Input Objects\n\n"
                    f"{payload_json}\n\n"
                    "Reason over the specialist outputs and return JF JSON only."
                ),
            },
        ]

    def generate(self, fusion_input: dict[str, Any], *, max_new_tokens: int = 1024) -> str:
        self.load()
        assert self.model is not None
        assert self.tokenizer is not None
        assert self.torch is not None

        messages = self.build_messages(fusion_input)
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

    def predict_fusion_input(self, fusion_input: dict[str, Any]) -> dict[str, Any]:
        raw_output = self.generate(fusion_input)
        parsed = extract_json(raw_output)
        return normalize_jf(parsed)

    def predict_communication(
        self,
        communication: dict[str, Any],
        *,
        headless: bool = True,
        ocr_urls: list[str] | None = None,
    ) -> dict[str, Any]:
        jo1, jo2 = preprocess_communication(communication, ocr_urls=ocr_urls)
        specialist_outputs = run_specialists(jo1, jo2, config=self.config, headless=headless)

        fusion_input = build_fusion_input(
            pf=self.system_prompt,
            jo1=jo1,
            so1=specialist_outputs.get("SO1", {}),
            jo2=jo2,
            io1=specialist_outputs.get("IO1", {}),
            ro1=specialist_outputs.get("RO1", {}),
        )
        return self.predict_fusion_input(fusion_input)


def predict(
    communication: dict[str, Any],
    *,
    headless: bool = True,
    ocr_urls: list[str] | None = None,
) -> dict[str, Any]:
    return FusionPredictor().predict_communication(
        communication,
        headless=headless,
        ocr_urls=ocr_urls,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AEGIS Fusion pipeline (communication object entry point).")
    parser.add_argument(
        "--communication-json",
        help="Path to a communication JSON file. Defaults to the built-in mock Gmail object.",
    )
    parser.add_argument(
        "--download-model",
        action="store_true",
        help="Download and save the Fusion reasoning model into fusion/model/.",
    )
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--headed", action="store_true", help="Run Runtime browser visibly.")
    parser.add_argument("--validate", action="store_true", help="Run architectural validation checks.")
    args = parser.parse_args()

    cfg = load_config()
    if args.download_model or args.force_download:
        download_model(
            model_dir=cfg.model_dir,
            tokenizer_dir=cfg.tokenizer_dir,
            model_name=cfg.model_name,
            force=args.force_download,
        )
        if not args.communication_json and not args.validate:
            raise SystemExit(0)

    if args.communication_json:
        communication = json.loads(Path(args.communication_json).read_text(encoding="utf-8"))
    else:
        communication = MOCK_GMAIL_COMMUNICATION

    if args.validate:
        from validate_pipeline import validate_architecture

        report = validate_architecture(communication, run_model=False, headless=not args.headed)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        raise SystemExit(0 if report["passed"] else 1)

    print(
        json.dumps(
            predict(communication, headless=not args.headed),
            indent=2,
            ensure_ascii=False,
        )
    )
