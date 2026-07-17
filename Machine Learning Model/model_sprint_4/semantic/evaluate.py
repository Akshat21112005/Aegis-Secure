import os
import json
import warnings
from pathlib import Path

import torch
import torch.nn as nn

from peft import PeftModel
from transformers import AutoModel, AutoTokenizer

try:
    from .text_format import format_email_text
except ImportError:
    from text_format import format_email_text  # type: ignore

warnings.filterwarnings("ignore")


ROOT = Path(__file__).resolve().parent

MODEL_NAME = "microsoft/deberta-v3-base"

MODEL_DIR = ROOT / "model"

TOKENIZER_DIR = MODEL_DIR / "tokenizer"

ADAPTER_DIR = MODEL_DIR / "adapter"

CHECKPOINT_DIR = ROOT / "checkpoints"

DEVICE = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

MAX_LENGTH = 512


class MeanPooling(nn.Module):

    def __init__(self):
        super().__init__()

    def forward(self, last_hidden_state, attention_mask):

        attention_mask = attention_mask.unsqueeze(-1).expand(
            last_hidden_state.size()
        ).float()

        embeddings = last_hidden_state * attention_mask

        summed = torch.sum(
            embeddings,
            dim=1
        )

        counts = torch.clamp(
            attention_mask.sum(dim=1),
            min=1e-9
        )

        return summed / counts


class SemanticClassifier(nn.Module):

    def __init__(self):

        super().__init__()

        self.encoder = AutoModel.from_pretrained(
            MODEL_NAME,
            use_safetensors=True
        )

        self.pooling = MeanPooling()

        hidden_size = self.encoder.config.hidden_size

        self.dropout = nn.Dropout(0.2)

        self.classifier = nn.Linear(
            hidden_size,
            1
        )

    def forward(
        self,
        input_ids,
        attention_mask
    ):

        outputs = self.encoder(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        pooled = self.pooling(
            outputs.last_hidden_state,
            attention_mask
        )

        pooled = self.dropout(
            pooled
        )

        logits = self.classifier(
            pooled
        )

        return logits.squeeze(-1)


def load_model():

    print("=" * 100)
    print("Loading Semantic Model")
    print("=" * 100)

    tokenizer = AutoTokenizer.from_pretrained(
        TOKENIZER_DIR
    )

    model = SemanticClassifier()

    model.encoder = PeftModel.from_pretrained(
        model.encoder,
        ADAPTER_DIR
    )

    checkpoint = torch.load(
        CHECKPOINT_DIR / "latest_checkpoint.pt",
        map_location=DEVICE
    )

    model.load_state_dict(
        checkpoint["model_state_dict"],
        strict=False
    )

    model.to(DEVICE)

    model.eval()

    print("Semantic Model Loaded Successfully.\n")

    return model, tokenizer
def predict_email(
    model,
    tokenizer,
    subject,
    body
):

    text = format_email_text(subject, body)

    inputs = tokenizer(

        text,

        max_length=MAX_LENGTH,

        truncation=True,

        padding="max_length",

        return_tensors="pt"

    )

    inputs = {

        key: value.to(DEVICE)

        for key, value in inputs.items()

    }

    with torch.no_grad():

        logits = model(

            input_ids=inputs["input_ids"],

            attention_mask=inputs["attention_mask"]

        )

        probability = torch.sigmoid(logits).item()

    prediction = "Phishing" if probability >= 0.5 else "Safe"

    confidence = probability if prediction == "Phishing" else (1 - probability)

    result = {

        "module": "Semantic Analysis",

        "prediction": prediction,

        "confidence": round(confidence * 100, 2),

        "phishing_probability": round(probability * 100, 2),

        "safe_probability": round((1 - probability) * 100, 2),

        "analysis": (
            f"As a semantic analysis specialist, I have analyzed the provided email "
            f"using a fine-tuned DeBERTa-v3 semantic classification model. "
            f"My prediction for this message is '{prediction.upper()}' with "
            f"{confidence * 100:.2f}% confidence. "
            f"This assessment is produced solely from the semantic understanding "
            f"learned during training on the phishing email dataset and is not "
            f"based on handcrafted rules, keyword matching, or manually engineered heuristics."
        )

    }

    return result

if __name__ == "__main__":

    model, tokenizer = load_model()

    subject = input("Subject : ")

    print()

    body = input("Body : ")

    result = predict_email(
        model,
        tokenizer,
        subject,
        body
    )

    print("\n")

    print(json.dumps(
        result,
        indent=4
    ))