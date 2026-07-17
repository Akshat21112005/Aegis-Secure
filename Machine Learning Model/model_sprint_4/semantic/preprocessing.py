import re
import html
import unicodedata
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = ROOT / "datasets" / "semantic" / "processed" / "semantic.csv"
OUTPUT_FILE = ROOT / "datasets" / "semantic" / "processed" / "semantic_clean.csv"

EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)

URL_PATTERN = re.compile(
    r"(https?://\S+|www\.\S+)",
    flags=re.IGNORECASE
)

PHONE_PATTERN = re.compile(
    r"\+?\d[\d\-\(\)\s]{7,}\d"
)

MULTI_SPACE = re.compile(
    r"\s+"
)

HTML_PATTERN = re.compile(
    r"<[^>]+>"
)

HEADER_SEPARATOR = re.compile(
    r"[-_=]{5,}"
)

CONTROL_PATTERN = re.compile(
    r"[\x00-\x08\x0B\x0C\x0E-\x1F]"
)

ZERO_WIDTH_PATTERN = re.compile(
    r"[\u200B-\u200D\uFEFF]"
)

MAX_BODY_CHARS = 50000
MAX_SUBJECT_CHARS = 300


class SemanticPreprocessor:

    def __init__(self):

        self.df = None

    def load(self):

        print("=" * 100)
        print("Loading Dataset")
        print("=" * 100)

        self.df = pd.read_csv(INPUT_FILE)

        print(f"Loaded {len(self.df):,} emails")

    def prepare_columns(self):

        self.df["subject"] = (
            self.df["subject"]
            .fillna("")
            .astype(str)
        )

        self.df["body"] = (
            self.df["body"]
            .fillna("")
            .astype(str)
        )

        self.df["subject_clean"] = self.df["subject"]

        self.df["body_clean"] = self.df["body"]

    def report(self):

        print("\nDataset Statistics")

        print(f"Rows : {len(self.df):,}")

        print(f"Columns : {len(self.df.columns)}")

        print("\nMissing Values")

        print(self.df.isnull().sum())

        print("\nLabel Distribution")

        print(self.df["label"].value_counts())

        print("\nSource Distribution")

        print(self.df["source"].value_counts())

    def normalize_unicode(self, text):

        return unicodedata.normalize(
            "NFKC",
            text
        )


    def decode_html(self, text):

        return html.unescape(text)


    def remove_html_tags(self, text):

        return HTML_PATTERN.sub(
            " ",
            text
        )


    def replace_urls(self, text):

        return URL_PATTERN.sub(
            " <URL> ",
            text
        )


    def replace_emails(self, text):

        return EMAIL_PATTERN.sub(
            " <EMAIL> ",
            text
        )


    def replace_phone_numbers(self, text):

        return PHONE_PATTERN.sub(
            " <PHONE> ",
            text
        )


    def remove_control_characters(self, text):

        return CONTROL_PATTERN.sub(
            " ",
            text
        )


    def remove_zero_width_characters(self, text):

        return ZERO_WIDTH_PATTERN.sub(
            "",
            text
        )


    def normalize_separators(self, text):

        return HEADER_SEPARATOR.sub(
            " ",
            text
        )


    def normalize_whitespace(self, text):

        text = MULTI_SPACE.sub(
            " ",
            text
        )

        return text.strip()


    def clip_subject(self, text):

        return text[:MAX_SUBJECT_CHARS]


    def clip_body(self, text):

        return text[:MAX_BODY_CHARS]


    def clean_text(self, text):

        text = self.normalize_unicode(text)

        text = self.decode_html(text)

        text = self.remove_html_tags(text)

        text = self.replace_urls(text)

        text = self.replace_emails(text)

        text = self.replace_phone_numbers(text)

        text = self.remove_control_characters(text)

        text = self.remove_zero_width_characters(text)

        text = self.normalize_separators(text)

        text = self.normalize_whitespace(text)

        return text


    def preprocess(self):

        print("\nCleaning Subject...")

        self.df["subject_clean"] = (
            self.df["subject_clean"]
            .apply(self.clean_text)
            .apply(self.clip_subject)
        )

        print("Cleaning Body...")

        self.df["body_clean"] = (
            self.df["body_clean"]
            .apply(self.clean_text)
            .apply(self.clip_body)
        )

        self.df["subject_length"] = (
            self.df["subject_clean"]
            .str.len()
        )

        self.df["body_length"] = (
            self.df["body_clean"]
            .str.len()
        )

        self.df["subject_words"] = (
            self.df["subject_clean"]
            .str.split()
            .apply(len)
        )

        self.df["body_words"] = (
            self.df["body_clean"]
            .str.split()
            .apply(len)
        )

        print("Cleaning Completed.")


    def remove_invalid_samples(self):

        before = len(self.df)

        self.df = self.df[
            self.df["body_clean"].str.len() > 20
        ]

        self.df = self.df[
            self.df["subject_clean"].str.len() < MAX_SUBJECT_CHARS + 1
        ]

        self.df = self.df[
            self.df["body_clean"].str.len() < MAX_BODY_CHARS + 1
        ]

        self.df = self.df.reset_index(drop=True)

        print(f"\nRemoved {before-len(self.df):,} invalid samples")


    def save(self):

        print("\nSaving Dataset...")

        self.df.to_csv(
            OUTPUT_FILE,
            index=False,
            encoding="utf-8"
        )

        print(f"Saved to {OUTPUT_FILE}")


    def run(self):

        self.load()

        self.prepare_columns()

        self.report()

        self.preprocess()

        self.remove_invalid_samples()

        self.save()

        print("\nDone.")


if __name__ == "__main__":

    SemanticPreprocessor().run()