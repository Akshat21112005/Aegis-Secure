from email.utils import parsedate_to_datetime


def parse_headers(headers: list[dict]) -> dict:

    parsed = {}

    for header in headers:

        name = header.get("name", "").strip().lower()

        value = header.get("value", "").strip()

        parsed[name] = value

    if "date" in parsed:

        try:

            parsed["parsed_date"] = parsedate_to_datetime(
                parsed["date"]
            )

        except Exception:

            parsed["parsed_date"] = None

    else:

        parsed["parsed_date"] = None

    return parsed