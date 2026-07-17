import re
import unicodedata


ZERO_WIDTH_CHARACTERS = (
    "\u200b",
    "\u200c",
    "\u200d",
    "\ufeff",
)


def normalize_sms(text: str) -> str:

    if not text:
        return ""

    text = unicodedata.normalize(
        "NFKC",
        text,
    )

    for character in ZERO_WIDTH_CHARACTERS:

        text = text.replace(
            character,
            "",
        )

    text = text.replace(
        "\r\n",
        "\n",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    text = text.replace(
        "\t",
        " ",
    )

    text = re.sub(
        r"[ ]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n+",
        "\n",
        text,
    )

    return text.strip()