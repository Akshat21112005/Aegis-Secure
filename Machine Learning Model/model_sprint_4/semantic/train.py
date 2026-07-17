import os
import random
import warnings
from pathlib import Path
import pandas as pd
import numpy as np
import torch
import torch.nn as nn

from peft import (
    LoraConfig,
    TaskType,
    get_peft_model
)

from transformers import (
    AutoModel,
    AutoTokenizer,
    get_linear_schedule_with_warmup
)

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)

from dataset import create_dataloaders
from tqdm.auto import tqdm

warnings.filterwarnings("ignore")


ROOT = Path(__file__).resolve().parent

MODEL_NAME = "microsoft/deberta-v3-base"

MODEL_DIR = ROOT / "model"

TOKENIZER_DIR = MODEL_DIR / "tokenizer"

ADAPTER_DIR = MODEL_DIR / "adapter"

CHECKPOINT_DIR = ROOT / "checkpoints"

LOG_DIR = ROOT / "logs"


TOKENIZER_DIR.mkdir(
    parents=True,
    exist_ok=True
)

ADAPTER_DIR.mkdir(
    parents=True,
    exist_ok=True
)

CHECKPOINT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def clear_huggingface_cache():
    """
    Utility function to clear Hugging Face cache for microsoft/deberta-v3-base.
    Should be called manually when cache corruption occurs.
    """
    try:
        from huggingface_hub import scan_cache_dir
        print("Scanning Hugging Face cache directory...")
        cache_info = scan_cache_dir()
        target_repo = "microsoft/deberta-v3-base"
        found = False
        for repo in cache_info.repos:
            if repo.repo_id == target_repo:
                found = True
                print(f"Target found: {repo.repo_id} ({repo.size_on_disk_str})")
                revisions_to_delete = [r.commit_hash for r in repo.revisions]
                delete_strategy = cache_info.delete_revisions(*revisions_to_delete)
                print(f"Deleting {len(revisions_to_delete)} revisions...")
                delete_strategy.execute()
                print("Cache cleared successfully.")
                break
        if not found:
            print(f"No cache entries found for {target_repo}.")
    except Exception as e:
        print(f"Failed to clear cache: {e}")


SEED = 42

EPOCHS = 4

LEARNING_RATE = 2e-5

WEIGHT_DECAY = 0.01

WARMUP_RATIO = 0.1

MAX_GRAD_NORM = 1.0

DROPOUT = 0.2

LORA_RANK = 8

LORA_ALPHA = 32

LORA_DROPOUT = 0.1

EARLY_STOPPING = 2

GRADIENT_ACCUMULATION_STEPS = 8


device = torch.device(

    "cuda"

    if torch.cuda.is_available()

    else "cpu"

)


def set_seed(seed):

    random.seed(seed)

    np.random.seed(seed)

    torch.manual_seed(seed)

    torch.cuda.manual_seed_all(seed)


set_seed(SEED)

class MeanPooling(nn.Module):

    def __init__(self):

        super().__init__()

    def forward(self, last_hidden_state, attention_mask):

        attention_mask = attention_mask.unsqueeze(-1).expand(
            last_hidden_state.size()
        )

        attention_mask = attention_mask.float()

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

        print(f"\nLoading {MODEL_NAME}...")
        print("Using SafeTensors: True")

        self.encoder = AutoModel.from_pretrained(
            MODEL_NAME,
            use_safetensors=True
        )
        self.encoder.gradient_checkpointing_enable()

        self.pooling = MeanPooling()

        hidden_size = self.encoder.config.hidden_size

        self.dropout = nn.Dropout(
            DROPOUT
        )

        self.classifier = nn.Linear(
            hidden_size,
            1
        )

        print("Base Model Loaded Successfully.")

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


def apply_lora(model):

    print("\nApplying LoRA...")

    config = LoraConfig(

        task_type=TaskType.FEATURE_EXTRACTION,

        inference_mode=False,

        r=LORA_RANK,

        lora_alpha=LORA_ALPHA,

        lora_dropout=LORA_DROPOUT,

        target_modules=[
            "query_proj",
            "key_proj",
            "value_proj"
        ]

    )

    model.encoder = get_peft_model(

        model.encoder,

        config

    )

    model.encoder.print_trainable_parameters()

    print("LoRA Applied.")

    return model


def load_model():

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        use_fast=True
    )

    tokenizer.save_pretrained(
        TOKENIZER_DIR
    )

    model = SemanticClassifier()

    model = apply_lora(
        model
    )

    for param in model.encoder.embeddings.parameters():
        param.requires_grad = False

    model = model.to(
        device
    )

    return model, tokenizer

def create_optimizer(model):

    optimizer = torch.optim.AdamW(

        model.parameters(),

        lr=LEARNING_RATE,

        weight_decay=WEIGHT_DECAY

    )

    return optimizer


def create_scheduler(

    optimizer,

    train_loader

):

    total_steps = EPOCHS * len(train_loader)

    warmup_steps = int(

        WARMUP_RATIO * total_steps

    )

    scheduler = get_linear_schedule_with_warmup(

        optimizer,

        num_warmup_steps=warmup_steps,

        num_training_steps=total_steps

    )

    return scheduler


def create_loss(train_loader):

    labels = []

    for batch in train_loader:

        labels.extend(

            batch["labels"].tolist()

        )

    labels = np.array(labels)

    positive = np.sum(labels == 1)

    negative = np.sum(labels == 0)

    pos_weight = torch.tensor(
        [negative / max(positive, 1)],
        dtype=torch.float32,
        device=device,
    )

    print("\nLoss Configuration")

    print(f"Positive : {positive}")

    print(f"Negative : {negative}")

    print(f"Positive Weight : {pos_weight.item():.4f}")

    criterion = nn.BCEWithLogitsLoss(

        pos_weight=pos_weight

    )

    return criterion


def create_training_components():

    train_loader, val_loader, test_loader, tokenizer = (

        create_dataloaders()

    )

    model, tokenizer = load_model()

    optimizer = create_optimizer(

        model

    )

    scheduler = create_scheduler(

        optimizer,

        train_loader

    )

    criterion = create_loss(

        train_loader

    )

    scaler = torch.cuda.amp.GradScaler(

        enabled=torch.cuda.is_available()

    )

    return (
        model,
        tokenizer,
        train_loader,
        val_loader,
        test_loader,
        optimizer,
        scheduler,
        criterion,
        scaler,
    )


def train_epoch(
    model,
    train_loader,
    optimizer,
    scheduler,
    criterion,
    scaler,
    epoch,
):

    model.train()

    running_loss = 0.0

    predictions = []

    labels_list = []

    optimizer.zero_grad()

    progress_bar = tqdm(
        train_loader,
        desc=None,
        leave=True
    )

    for i, batch in enumerate(progress_bar):

        input_ids = batch["input_ids"].to(device)

        attention_mask = batch["attention_mask"].to(device)

        labels = batch["labels"].to(device)

        with torch.amp.autocast(

            device_type=device.type,

            enabled=(device.type == "cuda")

        ):

            logits = model(

                input_ids,

                attention_mask

            )

            loss = criterion(

                logits,

                labels

            )

            loss = loss / GRADIENT_ACCUMULATION_STEPS

        scaler.scale(loss).backward()

        if (i + 1) % GRADIENT_ACCUMULATION_STEPS == 0 or (i + 1) == len(train_loader):

            scaler.unscale_(optimizer)

            torch.nn.utils.clip_grad_norm_(

                model.parameters(),

                MAX_GRAD_NORM

            )

            scaler.step(optimizer)

            scaler.update()

            scheduler.step()

            optimizer.zero_grad()

        running_loss += loss.item() * GRADIENT_ACCUMULATION_STEPS

        probs = torch.sigmoid(logits)

        preds = (probs >= 0.5).float()

        predictions.extend(

            preds.detach().cpu().numpy()

        )

        labels_list.extend(

            labels.detach().cpu().numpy()

        )

        if hasattr(scheduler, "get_last_lr"):
            current_lr = scheduler.get_last_lr()[0]
        else:
            current_lr = optimizer.param_groups[0]["lr"]

        progress_bar.set_postfix({
            "Loss": f"{loss.item() * GRADIENT_ACCUMULATION_STEPS:.4f}",
            "LR": f"{current_lr:.2e}"
        })

    epoch_loss = running_loss / len(train_loader)

    accuracy = accuracy_score(

        labels_list,

        predictions

    )

    precision = precision_score(

        labels_list,

        predictions,

        zero_division=0

    )

    recall = recall_score(

        labels_list,

        predictions,

        zero_division=0

    )

    f1 = f1_score(

        labels_list,

        predictions,

        zero_division=0

    )

    return {

        "loss": epoch_loss,

        "accuracy": accuracy,

        "precision": precision,

        "recall": recall,

        "f1": f1

    }


@torch.no_grad()
def validate_epoch(

    model,

    val_loader,

    criterion

):

    model.eval()

    running_loss = 0.0

    predictions = []

    labels_list = []

    progress_bar = tqdm(
        val_loader,
        desc="Validation Loss",
        leave=True
    )

    for batch in progress_bar:

        input_ids = batch["input_ids"].to(device)

        attention_mask = batch["attention_mask"].to(device)

        labels = batch["labels"].to(device)

        logits = model(

            input_ids,

            attention_mask

        )

        loss = criterion(

            logits,

            labels

        )

        running_loss += loss.item()

        probs = torch.sigmoid(logits)

        preds = (probs >= 0.5).float()

        predictions.extend(

            preds.cpu().numpy()

        )

        labels_list.extend(

            labels.cpu().numpy()

        )

        progress_bar.set_postfix({
            "Loss": f"{loss.item():.4f}"
        })

    epoch_loss = running_loss / len(val_loader)

    accuracy = accuracy_score(

        labels_list,

        predictions

    )

    precision = precision_score(

        labels_list,

        predictions,

        zero_division=0

    )

    recall = recall_score(

        labels_list,

        predictions,

        zero_division=0

    )

    f1 = f1_score(

        labels_list,

        predictions,

        zero_division=0

    )

    return {

        "loss": epoch_loss,

        "accuracy": accuracy,

        "precision": precision,

        "recall": recall,

        "f1": f1

    }

def save_checkpoint(
    epoch,
    model,
    optimizer,
    scheduler,
    scaler,
    best_f1
):

    checkpoint = {

        "epoch": epoch,

        "best_f1": best_f1,

        "model_state_dict": model.state_dict(),

        "optimizer_state_dict": optimizer.state_dict(),

        "scheduler_state_dict": scheduler.state_dict(),

        "scaler_state_dict": scaler.state_dict()

    }

    checkpoint_path = CHECKPOINT_DIR / "latest_checkpoint.pt"

    torch.save(
        checkpoint,
        checkpoint_path
    )

    print(f"Checkpoint Saved : {checkpoint_path}")


def load_checkpoint(
    model,
    optimizer,
    scheduler,
    scaler
):

    checkpoint_path = CHECKPOINT_DIR / "latest_checkpoint.pt"

    if not checkpoint_path.exists():

        print("\nNo checkpoint found. Starting fresh.\n")

        return 0, 0.0

    print(f"\nLoading Checkpoint : {checkpoint_path}")

    checkpoint = torch.load(

        checkpoint_path,

        map_location=device

    )

    model.load_state_dict(

        checkpoint["model_state_dict"]

    )

    optimizer.load_state_dict(

        checkpoint["optimizer_state_dict"]

    )

    scheduler.load_state_dict(

        checkpoint["scheduler_state_dict"]

    )

    scaler.load_state_dict(

        checkpoint["scaler_state_dict"]

    )

    start_epoch = checkpoint["epoch"] + 1

    best_f1 = checkpoint["best_f1"]

    print(f"Resuming From Epoch {start_epoch}")

    print(f"Best Validation F1 : {best_f1:.4f}")

    return start_epoch, best_f1


def save_best_model(model):

    print("\nSaving Best LoRA Adapter...")

    model.encoder.save_pretrained(

        ADAPTER_DIR

    )

    print(f"Adapter Saved : {ADAPTER_DIR}")

    print(f"Tokenizer Saved : {TOKENIZER_DIR}")


def save_history(history):

    history_df = pd.DataFrame(history)

    history_path = LOG_DIR / "history.csv"

    history_df.to_csv(

        history_path,

        index=False

    )

    print(f"History Saved : {history_path}")


def train():

    (
        model,
        tokenizer,
        train_loader,
        val_loader,
        test_loader,
        optimizer,
        scheduler,
        criterion,
        scaler
    ) = create_training_components()

    start_epoch, best_f1 = load_checkpoint(

        model,

        optimizer,

        scheduler,

        scaler

    )

    history = []

    early_stop_counter = 0

    print("\n")
    print("=" * 120)
    print("STARTING TRAINING")
    print("=" * 120)
    print(f"Device : {device}")

    for epoch in range(

        start_epoch,

        EPOCHS

    ):

        print(f"\nEpoch {epoch+1}/{EPOCHS}")

        train_metrics = train_epoch(

            model,

            train_loader,

            optimizer,

            scheduler,

            criterion,

            scaler,

            epoch=epoch + 1

        )

        val_metrics = validate_epoch(

            model,

            val_loader,

            criterion

        )

        print("\nTrain")

        print(
            f"Loss : {train_metrics['loss']:.4f} | "
            f"Acc : {train_metrics['accuracy']:.4f} | "
            f"Precision : {train_metrics['precision']:.4f} | "
            f"Recall : {train_metrics['recall']:.4f} | "
            f"F1 : {train_metrics['f1']:.4f}"
        )

        print("\nValidation")

        print(
            f"Loss : {val_metrics['loss']:.4f} | "
            f"Acc : {val_metrics['accuracy']:.4f} | "
            f"Precision : {val_metrics['precision']:.4f} | "
            f"Recall : {val_metrics['recall']:.4f} | "
            f"F1 : {val_metrics['f1']:.4f}"
        )

        history.append({

            "epoch": epoch + 1,

            "train_loss": train_metrics["loss"],

            "train_accuracy": train_metrics["accuracy"],

            "train_precision": train_metrics["precision"],

            "train_recall": train_metrics["recall"],

            "train_f1": train_metrics["f1"],

            "val_loss": val_metrics["loss"],

            "val_accuracy": val_metrics["accuracy"],

            "val_precision": val_metrics["precision"],

            "val_recall": val_metrics["recall"],

            "val_f1": val_metrics["f1"]

        })

        save_checkpoint(

            epoch,

            model,

            optimizer,

            scheduler,

            scaler,

            best_f1

        )

        if val_metrics["f1"] > best_f1:

            best_f1 = val_metrics["f1"]

            early_stop_counter = 0

            save_best_model(

                model

            )

            print("\nNew Best Model Saved.")

        else:

            early_stop_counter += 1

            print(
                f"\nEarly Stopping : "
                f"{early_stop_counter}/{EARLY_STOPPING}"
            )

        if early_stop_counter >= EARLY_STOPPING:

            print("\nEarly Stopping Triggered.")

            break

    save_history(

        history

    )

    print("\n")
    print("=" * 120)
    print("TRAINING FINISHED")
    print("=" * 120)

    return model, test_loader


if __name__ == "__main__":

    train()