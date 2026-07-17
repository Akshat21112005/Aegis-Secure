import hashlib


def _hash(value: str) -> str:
    value = value.strip().lower()
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_url(url: str) -> str:
    return f"canonical:{_hash(url)}"


def playwright(url: str) -> str:
    return f"playwright:{_hash(url)}"


def whois(domain: str) -> str:
    return f"whois:{_hash(domain)}"


def dns(domain: str) -> str:
    return f"dns:{_hash(domain)}"


def tls(domain: str) -> str:
    return f"tls:{_hash(domain)}"


def reputation(domain: str) -> str:
    return f"reputation:{_hash(domain)}"


def semantic(text: str) -> str:
    return f"semantic:{_hash(text)}"


def runtime(data: str) -> str:
    return f"runtime:{_hash(data)}"


def infrastructure(data: str) -> str:
    return f"infrastructure:{_hash(data)}"


def visual(image_hash: str) -> str:
    return f"visual:{image_hash}"


def ocr(image_hash: str) -> str:
    return f"ocr:{image_hash}"


def siglip(image_hash: str) -> str:
    return f"siglip:{image_hash}"


def qr(image_hash: str) -> str:
    return f"qr:{image_hash}"


def pdf(pdf_hash: str) -> str:
    return f"pdf:{pdf_hash}"


def screenshot(image_hash: str) -> str:
    return f"screenshot:{image_hash}"


def fusion(event_id: str) -> str:
    return f"fusion:{event_id}"