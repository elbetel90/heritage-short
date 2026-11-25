import json
import time
import urllib.error
import urllib.request


class HTTPError(Exception):
    def __init__(self, status, body):
        snippet = " ".join(body.split())[:240]
        super(HTTPError, self).__init__("HTTP %s: %s" % (status, snippet))
        self.status = status
        self.body = body


def post_json(url, payload, headers, timeout=60, attempts=3):
    """POST JSON. Retries 429 and 5xx with backoff. Returns (status, parsed, latency_ms)."""
    data = json.dumps(payload).encode("utf-8")
    last_error = None
    for attempt in range(attempts):
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                latency_ms = int((time.time() - started) * 1000)
                parsed = json.loads(raw.decode("utf-8")) if raw else {}
                return response.status, parsed, latency_ms
        except urllib.error.HTTPError as error:
            latency_ms = int((time.time() - started) * 1000)
            body = error.read().decode("utf-8", errors="replace")
            last_error = HTTPError(error.code, body)
            last_error.latency_ms = latency_ms
            if error.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise last_error
        time.sleep(0.4 * (2 ** attempt))
    raise last_error
