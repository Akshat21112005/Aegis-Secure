from __future__ import annotations

import socket
import ssl
from datetime import datetime, timezone
from typing import Any

from ._utils import extract_hostname, limit_string, safe_error


def _parse_cert_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _name_from_tuple(items: tuple[Any, ...]) -> str:
    parts: list[str] = []
    for group in items or ():
        for key, value in group:
            if key in {"commonName", "organizationName", "countryName"} and value:
                parts.append(str(value))
    return ", ".join(parts)


def _hostname_matches(cert: dict[str, Any], hostname: str) -> bool:
    matcher = getattr(ssl, "match_hostname", None)
    if matcher is not None:
        try:
            matcher(cert, hostname)
            return True
        except Exception:
            return False

    host = hostname.lower().strip(".")
    candidates = {
        value.lower()
        for key, value in cert.get("subjectAltName", ())
        if str(key).lower() == "dns"
    }
    for group in cert.get("subject", ()):
        for key, value in group:
            if key == "commonName" and value:
                candidates.add(str(value).lower())

    for candidate in candidates:
        if candidate == host:
            return True
        if candidate.startswith("*.") and host.endswith(candidate[1:]):
            return True
    return False


def collect_tls(url: str, *, timeout: float = 5.0, enable_network: bool = True) -> dict[str, Any]:
    hostname = extract_hostname(url)
    evidence: dict[str, Any] = {
        "collector": "tls",
        "status": "unknown",
        "hostname": hostname,
        "certificate_present": False,
        "issuer": "",
        "subject": "",
        "common_name": "",
        "alternative_names": [],
        "valid_from": "",
        "valid_until": "",
        "validity_days": None,
        "expires_in_days": None,
        "expired": None,
        "self_signed": None,
        "hostname_match": None,
        "tls_version": "",
        "cipher_suite": "",
        "public_key_bits": None,
        "signature_algorithm": "",
        "error": "",
    }
    if not hostname:
        evidence["status"] = "no_hostname"
        return evidence
    if not enable_network:
        evidence["status"] = "skipped"
        return evidence

    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as tls_sock:
                cert = tls_sock.getpeercert()
                binary_cert = tls_sock.getpeercert(binary_form=True)
                not_before = str(cert.get("notBefore") or "")
                not_after = str(cert.get("notAfter") or "")
                before_dt = _parse_cert_time(not_before)
                after_dt = _parse_cert_time(not_after)
                now = datetime.now(timezone.utc)
                issuer = _name_from_tuple(cert.get("issuer", ()))
                subject = _name_from_tuple(cert.get("subject", ()))
                sans = [
                    str(value)
                    for key, value in cert.get("subjectAltName", ())
                    if str(key).lower() in {"dns", "ip address"}
                ]
                common_name = ""
                for group in cert.get("subject", ()):
                    for key, value in group:
                        if key == "commonName":
                            common_name = str(value)
                            break
                    if common_name:
                        break
                hostname_match = _hostname_matches(cert, hostname)

                evidence.update(
                    {
                        "status": "ok",
                        "certificate_present": True,
                        "issuer": issuer,
                        "subject": subject,
                        "common_name": common_name,
                        "alternative_names": sans[:40],
                        "valid_from": not_before,
                        "valid_until": not_after,
                        "validity_days": (after_dt - before_dt).days if before_dt and after_dt else None,
                        "expires_in_days": (after_dt - now).days if after_dt else None,
                        "expired": after_dt < now if after_dt else None,
                        "self_signed": bool(issuer and subject and issuer == subject),
                        "hostname_match": hostname_match,
                        "tls_version": tls_sock.version() or "",
                        "cipher_suite": tls_sock.cipher()[0] if tls_sock.cipher() else "",
                    }
                )
                if binary_cert:
                    try:
                        from cryptography import x509
                        from cryptography.hazmat.primitives.asymmetric import dsa, ec, rsa

                        parsed_cert = x509.load_der_x509_certificate(binary_cert)
                        public_key = parsed_cert.public_key()
                        if isinstance(public_key, (rsa.RSAPublicKey, dsa.DSAPublicKey)):
                            evidence["public_key_bits"] = public_key.key_size
                        elif isinstance(public_key, ec.EllipticCurvePublicKey):
                            evidence["public_key_bits"] = public_key.curve.key_size
                        evidence["signature_algorithm"] = limit_string(
                            parsed_cert.signature_hash_algorithm.name
                            if parsed_cert.signature_hash_algorithm
                            else "",
                            80,
                        )
                    except Exception:
                        pass
    except ssl.SSLError as exc:
        evidence["status"] = "ssl_error"
        evidence["error"] = safe_error(exc)
    except socket.timeout:
        evidence["status"] = "timeout"
        evidence["error"] = "tls_timeout"
    except OSError as exc:
        evidence["status"] = "connection_failed"
        evidence["error"] = safe_error(exc)
    except Exception as exc:
        evidence["status"] = "failed"
        evidence["error"] = safe_error(exc)
    return evidence

