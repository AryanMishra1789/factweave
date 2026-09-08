from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from .models import VerificationResult


class VerificationError(ValueError):
    pass


def verify_url(url: str, allowed_domains: set[str], timeout: float = 5.0, max_bytes: int = 1_000_000) -> VerificationResult:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host or not any(host == domain or host.endswith("." + domain) for domain in allowed_domains):
        raise VerificationError("Only HTTPS URLs on explicitly allowed domains may be verified")
    response = None
    try:
        request = Request(url, headers={"User-Agent": "Factweave-verifier/1.0"})
        response = urlopen(request, timeout=timeout)
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise VerificationError("Response exceeds the configured size limit")
        content_type = response.headers.get("Content-Type")
        excerpt = raw.decode("utf-8", errors="replace")[:4000]
        return VerificationResult(url=url, status_code=response.status, content_type=content_type, excerpt=excerpt, retrieved_at=datetime.now(timezone.utc), trusted_domain=True)
    finally:
        if response:
            response.close()
