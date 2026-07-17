import warnings
from pathlib import Path

import pandas as pd
import torch

from sklearn.model_selection import train_test_split

from torch.utils.data import Dataset
from torch.utils.data import DataLoader

from transformers import AutoTokenizer

try:
    from .text_format import format_email_text
except ImportError:
    from text_format import format_email_text  # type: ignore

warnings.filterwarnings("ignore")


ROOT = Path(__file__).resolve().parent.parent

DATASET_PATH = (
    ROOT
    / "datasets"
    / "semantic"
    / "processed"
    / "semantic_clean.csv"
)

MODEL_NAME = "microsoft/deberta-v3-base"


MAX_LENGTH = 512

BATCH_SIZE = 16

NUM_WORKERS = 2

SEED = 42


class SemanticDataset(Dataset):

    def __init__(
        self,
        dataframe,
        tokenizer,
        max_length=MAX_LENGTH
    ):

        self.df = dataframe.reset_index(
            drop=True
        )

        self.tokenizer = tokenizer

        self.max_length = max_length

        self.texts = self.build_inputs()

        self.labels = (
            self.df["label"]
            .astype(int)
            .tolist()
        )

    def build_inputs(self):

        inputs = []

        for _, row in self.df.iterrows():

            subject = str(row["subject_clean"]) if pd.notna(row["subject_clean"]) else ""

            body = str(row["body_clean"]) if pd.notna(row["body_clean"]) else ""

            text = format_email_text(subject, body)

            inputs.append(text)

        return inputs

    def __len__(self):

        return len(self.df)
    def tokenize(self, text):

        encoding = self.tokenizer(

            text,

            truncation=True,

            max_length=self.max_length,

            padding="max_length",

            return_attention_mask=True,

            return_tensors="pt"

        )

        return encoding


    def __getitem__(self, index):

        text = self.texts[index]

        label = self.labels[index]

        encoding = self.tokenize(text)

        return {

            "input_ids": encoding["input_ids"].squeeze(0),

            "attention_mask": encoding["attention_mask"].squeeze(0),

            "labels": torch.tensor(
                label,
                dtype=torch.float32
            )

        }


def load_dataset():

    print("=" * 100)

    print("Loading Semantic Dataset")

    print("=" * 100)

    df = pd.read_csv(DATASET_PATH)

    print(f"Loaded {len(df):,} emails")

    print("\nLabel Distribution")

    print(df["label"].value_counts())

    print("\nSource Distribution")

    print(df["source"].value_counts())

    return df


def load_tokenizer():

    print("\nLoading Tokenizer...")

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        use_fast=True
    )

    print("Tokenizer Loaded")

    return tokenizer
def create_dataloaders():

    print("\nSplitting Dataset...")

    df = load_dataset()

    tokenizer = load_tokenizer()

    train_df, temp_df = train_test_split(

        df,

        test_size=0.2,

        random_state=SEED,

        stratify=df["label"]

    )

    val_df, test_df = train_test_split(

        temp_df,

        test_size=0.5,

        random_state=SEED,

        stratify=temp_df["label"]

    )

    print(f"\nTrain : {len(train_df):,}")
    print(f"Validation : {len(val_df):,}")
    print(f"Test : {len(test_df):,}")

    train_dataset = SemanticDataset(

        dataframe=train_df,

        tokenizer=tokenizer

    )

    val_dataset = SemanticDataset(

        dataframe=val_df,

        tokenizer=tokenizer

    )

    test_dataset = SemanticDataset(

        dataframe=test_df,

        tokenizer=tokenizer

    )

    pin_memory = torch.cuda.is_available()

    train_loader = DataLoader(

        train_dataset,

        batch_size=BATCH_SIZE,

        shuffle=True,

        num_workers=NUM_WORKERS,

        pin_memory=pin_memory

    )

    val_loader = DataLoader(

        val_dataset,

        batch_size=BATCH_SIZE,

        shuffle=False,

        num_workers=NUM_WORKERS,

        pin_memory=pin_memory

    )

    test_loader = DataLoader(

        test_dataset,

        batch_size=BATCH_SIZE,

        shuffle=False,

        num_workers=NUM_WORKERS,

        pin_memory=pin_memory

    )

    print("\nDataLoaders Created Successfully.")

    return (

        train_loader,

        val_loader,

        test_loader,

        tokenizer

    )


if __name__ == "__main__":

    train_loader, val_loader, test_loader, tokenizer = create_dataloaders()

    print("\nChecking One Batch...")

    batch = next(iter(train_loader))

    print("\nInput IDs Shape")

    print(batch["input_ids"].shape)

    print("\nAttention Mask Shape")

    print(batch["attention_mask"].shape)

    print("\nLabels Shape")

    print(batch["labels"].shape)

    print("\nTokenizer Vocabulary")

    print(tokenizer.vocab_size)

    print("\nDataset Pipeline Ready.")