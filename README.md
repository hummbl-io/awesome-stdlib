<div align="center">

# Awesome Stdlib [![Awesome](https://awesome.re/badge.svg)](https://awesome.re) [![Zero Dependencies](https://img.shields.io/badge/Dependencies-0%20Runtime%20Deps-brightgreen)](scripts/verify_zero_deps.py) [![CI](https://github.com/hummbl-io/awesome-stdlib/actions/workflows/ci.yml/badge.svg)](https://github.com/hummbl-io/awesome-stdlib/actions)

> Python standard library examples to inspect and adapt, alongside a directory of related Python packages. Examples are not drop-in equivalents or a certification of production readiness.

*Batteries included. Fewer dependencies do not eliminate security or maintenance risks.*

</div>

---

## Contents

- [Why Stdlib-Only?](#why-stdlib-only)
- [Stdlib Examples](#stdlib-examples)
  - [HTTP & Networking](#http--networking)
  - [Schemas & Validation](#schemas--validation)
  - [Graphs & DAG Scheduling](#graphs--dag-scheduling)
  - [Cryptography & Hashing](#cryptography--hashing)
  - [Rate Limiting & Concurrency](#rate-limiting--concurrency)
  - [Inter-Process Communication & Memory](#inter-process-communication--memory)
  - [Configuration & File Parsing](#configuration--file-parsing)
  - [Terminal & CLI Formatting](#terminal--cli-formatting)
- [Modern Python Hidden Gems (3.11+)](#modern-python-hidden-gems-311)
- [Verified Zero-Dependency PyPI Packages](#verified-zero-dependency-pypi-packages)
- [AST checks and focused tests](#ast-checks-and-focused-tests)
- [Contributing](#contributing)

---

## Why Stdlib-Only?

In modern software engineering, AI agent swarms, defense systems, and fintech infrastructure, third-party dependencies introduce major risks:
1. **Supply-Chain Vulnerabilities**: Runtime external payload fetches, malicious wheel injections, and typosquatting.
2. **Dependency Churn**: Breaking trans-dependency updates across subagent microservices.
3. **Audit Bloat**: Pulling 50,000 lines of untrusted third-party code for a 5-line utility.

The Python standard library can support some use cases without third-party imports. Choose between a focused example and a maintained package by checking the behavior, limits and maintenance work your application requires. The related-package labels in this catalog are context, not claims of equivalent APIs or guarantees.

---

## Stdlib Examples

### HTTP & Networking

#### Replace `requests` / `httpx` with Pure Stdlib JSON Client
```python
import urllib.request
import urllib.error
import json
from typing import Any, Optional, Dict

def http_json_request(
    url: str,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 10.0
) -> Dict[str, Any]:
    """Pure stdlib JSON HTTP client with custom headers, timeouts, and error handling."""
    req_headers = {"User-Agent": "Awesome-Stdlib/1.0", "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    
    data_bytes = None
    if payload is not None:
        req_headers["Content-Type"] = "application/json"
        data_bytes = json.dumps(payload).encode("utf-8")
        
    req = urllib.request.Request(url, data=data_bytes, headers=req_headers, method=method.upper())
    
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"HTTP {e.code} Error from {url}: {err_body}") from e
    except urllib.error.URLError as e:
        raise ConnectionError(f"Failed to reach {url}: {e.reason}") from e
```

---

### Schemas & Validation

#### Replace `pydantic.BaseModel` with Frozen Data Classes & Contracts
```python
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Optional
import json

@dataclass(frozen=True)
class DataContract:
    contract_id: str
    max_budget_usd: float
    allowed_ops: list[str] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.max_budget_usd <= 0:
            raise ValueError("max_budget_usd must be positive")
        if not self.contract_id.strip():
            raise ValueError("contract_id cannot be empty")

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"), sort_keys=True)
```

---

### Graphs & DAG Scheduling

#### Replace `networkx` with Built-in `graphlib` Topological Sorter
```python
import graphlib  # Python 3.9+ built-in

def compute_execution_order(dependency_graph: dict[str, set[str]]) -> list[str]:
    """
    Computes deterministic execution order for task DAGs.
    Raises graphlib.CycleError if circular dependencies exist.
    """
    ts = graphlib.TopologicalSorter(dependency_graph)
    return list(ts.static_order())
```

---

### Cryptography & Hashing

#### Python JSON HMAC example (not RFC 8785 or JWT)
```python
import hmac
import hashlib
import json
from typing import Dict, Any

def sign_json_receipt(secret_key: bytes, payload: Dict[str, Any]) -> str:
    """HMAC over this Python JSON encoding; not RFC 8785 JCS or JWT."""
    encoded_bytes = json.dumps(
        payload,
        separators=(',', ':'),
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False
    ).encode('utf-8')
    return hmac.new(secret_key, encoded_bytes, hashlib.sha256).hexdigest()

def verify_json_receipt(secret_key: bytes, payload: Dict[str, Any], expected_sig: str) -> bool:
    candidate_sig = sign_json_receipt(secret_key, payload)
    return hmac.compare_digest(expected_sig.encode(), candidate_sig.encode())
```

#### Replace `bcrypt` with `hashlib.scrypt` (Memory-Hard Hashing)
```python
import hashlib
import secrets

def hash_password_scrypt(password: str, salt: bytes = None) -> tuple[bytes, bytes]:
    """Memory-hard password hashing using Python stdlib hashlib.scrypt."""
    if salt is None:
        salt = secrets.token_bytes(16)
    hashed = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, maxmem=32 * 1024 * 1024)
    return hashed, salt
```

---

### Rate Limiting & Concurrency

#### Replace `ratelimit` with Thread-Safe Monotonic Token Bucket
```python
import time
from threading import Lock

class TokenBucketLimiter:
    def __init__(self, refill_rate_per_sec: float, max_tokens: int):
        self.rate = refill_rate_per_sec
        self.capacity = max_tokens
        self.tokens = float(max_tokens)
        self.last_refill = time.monotonic()
        self.lock = Lock()

    def acquire(self, tokens: int = 1) -> bool:
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.last_refill = now
            self.tokens = min(float(self.capacity), self.tokens + elapsed * self.rate)
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
```

---

### Inter-Process Communication & Memory

#### Replace `redis` (local flags) with Zero-Copy Shared Memory (`mmap`)
```python
import mmap
import os

def create_shared_kill_switch(path: str = "/tmp/hummbl_kill.flag") -> mmap.mmap:
    """Atomic sub-microsecond IPC kill switch across processes without sockets."""
    with open(path, "a+b") as f:
        if os.path.getsize(path) < 1:
            f.write(b"\x00")
            f.flush()
        return mmap.mmap(f.fileno(), 1, access=mmap.ACCESS_WRITE)

def trip_kill_switch(shm: mmap.mmap):
    shm[0] = 1

def is_tripped(shm: mmap.mmap) -> bool:
    return shm[0] == 1
```

---

### Configuration & File Parsing

#### Replace `tomli` / `pyyaml` with Built-in `tomllib` (Python 3.11+)
```python
import tomllib
from pathlib import Path
from typing import Dict, Any

def read_config(file_path: Path) -> Dict[str, Any]:
    """Reads TOML config in pure stdlib."""
    with open(file_path, "rb") as f:
        return tomllib.load(f)
```

---

### Terminal & CLI Formatting

#### Replace `tabulate` with Zero-Dependency Dynamic Table Formatter
```python
from typing import List, Dict, Any

def render_table(rows: List[Dict[str, Any]], headers: List[str]) -> str:
    """Renders formatted ASCII table with auto-aligned column widths."""
    if not rows:
        return ""
    widths = {h: max(len(h), max(len(str(r.get(h, ""))) for r in rows)) for h in headers}
    header_line = "| " + " | ".join(f"{h:<{widths[h]}}" for h in headers) + " |"
    divider_line = "+-" + "-+-".join("-" * widths[h] for h in headers) + "-+"
    data_lines = [
        "| " + " | ".join(f"{str(r.get(h, '')):<{widths[h]}}" for h in headers) + " |"
        for r in rows
    ]
    return f"{divider_line}\n{header_line}\n{divider_line}\n" + "\n".join(data_lines) + f"\n{divider_line}"
```

---

## Modern Python Hidden Gems (3.11+)

| Module / Feature | Standard Library Since | Replaces Third-Party Tool |
|---|---|---|
| `graphlib.TopologicalSorter` | Python 3.9 | `networkx` for dependency resolution |
| `tomllib` | Python 3.11 | `tomli`, `toml` |
| `asyncio.TaskGroup` | Python 3.11 | `trio` nursery pattern / safe concurrent cancellation |
| `secrets` | Python 3.6 | Insecure random generators for tokens/nonces |
| `functools.cache` | Python 3.9 | Unbounded memoization without `lru_cache(maxsize=None)` |
| `pathlib.Path.walk` | Python 3.12 | `os.walk` with object-oriented Path instances |

---

## Verified Zero-Dependency PyPI Packages

Production libraries on PyPI with **0 runtime dependencies**:

* [`hummbl-governance`](https://pypi.org/project/hummbl-governance/) — AI agent runtime governance primitives (kill switch, circuit breaker, delegation tokens, receipts).
* [`base120`](https://pypi.org/project/base120/) — 120 callable cognitive reasoning operators for AI agents.
* [`hummbl-bus`](https://pypi.org/project/hummbl-bus/) — Append-only TSV coordination bus client for multi-agent systems.
* [`hummbl-tuples`](https://pypi.org/project/hummbl-tuples/) — Universal governance tuples schema.
* [`bottle`](https://pypi.org/project/bottle/) — Fast and simple WSGI micro web-framework in a single file.

---

## AST checks and focused tests

CI runs import checks and focused behavior tests. These have different scopes:
```bash
# 1. AST Zero-Dependency Linter across README and registry.json (30 recipes)
python scripts/verify_zero_deps.py

# 2. Focused recipe behavior and regression tests
python -m unittest discover -s tests -v
```
The AST check inspects explicit imports against `sys.stdlib_module_names`; it does not establish runtime safety, dependency behavior reached through dynamic loading, or functional equivalence with another package. The registry contains 30 examples, but focused tests cover selected behavior rather than every recipe or supported platform. Read each example's notes and run the checks relevant to your application before reuse.

The numeric cron example follows Sunday=0/7 and restricted day-of-month/day-of-week OR matching, as described in [crontab(5)](https://man7.org/linux/man-pages/man5/crontab.5.html); it excludes names and extended syntax. The HMAC example intentionally does not implement [RFC 8785 JCS](https://www.rfc-editor.org/rfc/rfc8785.html): Python JSON number serialization and key ordering are a different contract. Peers must agree on the same encoding and input types. A matching HMAC does not itself grant authority.

---

## Contributing

Pull requests are welcome! All submissions must satisfy one rule:
**Zero third-party runtime dependencies.** Every recipe must pass `verify_zero_deps.py`.

---

## License

Apache-2.0 © 2026 HUMMBL, LLC
