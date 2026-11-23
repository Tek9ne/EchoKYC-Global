import os
import json
import time
import hmac
import base64
import hashlib
from functools import wraps
from flask import request, jsonify


class CBNComplianceGuard:
    """
    CBN & NDPA Cybersecurity Layer for EchoKYC Global:
    1. Sliding-window API Rate Limiter (stops paycode brute-force & DDoS)
    2. Stateless HMAC-SHA256 JWT Authentication (zero external dependencies)
    3. Blockchain-style Hash-Chained Audit Ledger (tamper-evident logs)
    """

    def __init__(self, audit_log_path="cbn_audit_chain.jsonl"):
        # Load secret signing key from environment or fallback for local dev
        secret = os.environ.get("ECHOKYC_JWT_SECRET", "dev-local-cbn-shield-key-change-in-prod")
        self.secret_key = secret.encode("utf-8")
        self.audit_log_path = audit_log_path

        # Dictionary storing request timestamps per IP: { "127.0.0.1": [t1, t2, ...] }
        self.rate_buckets = {}

    # ---------------------------------------------------------
    # 1. API RATE LIMITER (Anti-Brute-Force Shield)
    # ---------------------------------------------------------
    def rate_limit(self, max_requests=20, window_seconds=60):
        """Decorator that blocks any IP exceeding max_requests within window_seconds."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Support Render/Cloud reverse proxy headers (X-Forwarded-For)
                forwarded_for = request.headers.get("X-Forwarded-For", "")
                client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else (request.remote_addr or "unknown")

                now = time.time()
                window_start = now - window_seconds

                # Keep only timestamps inside the active time window
                timestamps = self.rate_buckets.get(client_ip, [])
                timestamps = [t for t in timestamps if t > window_start]

                if len(timestamps) >= max_requests:
                    self.append_audit_event(
                        event_type="RATE_LIMIT_BLOCKED",
                        actor=client_ip,
                        details={"endpoint": request.path, "limit": max_requests}
                    )
                    return jsonify({
                        "status": "error",
                        "code": "CBN_RATE_LIMIT_429",
                        "message": "Too many requests. Security cooldown active."
                    }), 429

                timestamps.append(now)
                self.rate_buckets[client_ip] = timestamps
                return func(*args, **kwargs)
            return wrapper
        return decorator

    # ---------------------------------------------------------
    # 2. STATELESS JWT TOKEN ENGINE (HS256)
    # ---------------------------------------------------------
    def _b64url_encode(self, data_bytes):
        return base64.urlsafe_b64encode(data_bytes).rstrip(b"=").decode("utf-8")

    def _b64url_decode(self, data_str):
        padding = "=" * (-len(data_str) % 4)
        return base64.urlsafe_b64decode((data_str + padding).encode("utf-8"))

    def issue_jwt(self, subject_id, role="teller", ttl_seconds=3600):
        """Creates a signed JWT valid for ttl_seconds (default 1 hour)."""
        header = {"alg": "HS256", "typ": "JWT"}
        now = int(time.time())
        payload = {
            "sub": str(subject_id),
            "role": role,
            "iat": now,
            "exp": now + ttl_seconds
        }

        header_b64 = self._b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_b64 = self._b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

        signature = hmac.new(self.secret_key, signing_input, hashlib.sha256).digest()
        sig_b64 = self._b64url_encode(signature)
        return f"{header_b64}.{payload_b64}.{sig_b64}"

    def verify_jwt(self, token):
        """Verifies JWT signature and expiration. Returns payload dict or None."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_b64, payload_b64, sig_b64 = parts

            signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
            expected_sig = hmac.new(self.secret_key, signing_input, hashlib.sha256).digest()
            actual_sig = self._b64url_decode(sig_b64)

            # Constant-time comparison prevents timing side-channel attacks
            if not hmac.compare_digest(expected_sig, actual_sig):
                return None

            payload = json.loads(self._b64url_decode(payload_b64).decode("utf-8"))
            if int(time.time()) > payload.get("exp", 0):
                return None

            return payload
        except Exception:
            return None

    def require_jwt(self, required_role=None):
        """Decorator protecting sensitive bank/admin endpoints with Bearer JWT."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                auth_header = request.headers.get("Authorization", "")
                if not auth_header.startswith("Bearer "):
                    return jsonify({"status": "error", "message": "Missing Bearer JWT token"}), 401

                token = auth_header.split(" ", 1)[1].strip()
                payload = self.verify_jwt(token)
                if not payload:
                    return jsonify({"status": "error", "message": "Invalid or expired JWT token"}), 401

                if required_role and payload.get("role") != required_role:
                    return jsonify({"status": "error", "message": "Insufficient role clearance"}), 403

                request.jwt_user = payload
                return func(*args, **kwargs)
            return wrapper
        return decorator

    # ---------------------------------------------------------
    # 3. HASH-CHAINED AUDIT LOG (CBN / NDPA Tamper-Proof Trail)
    # ---------------------------------------------------------
    def _get_last_hash(self):
        """Reads the final entry's hash from disk, or returns 64 zeros for genesis."""
        if not os.path.exists(self.audit_log_path):
            return "0" * 64
        try:
            with open(self.audit_log_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                if not lines:
                    return "0" * 64
                last_record = json.loads(lines[-1])
                return last_record.get("entry_hash", "0" * 64)
        except Exception:
            return "0" * 64

    def append_audit_event(self, event_type, actor, details=None):
        """Appends a cryptographically chained log record to disk."""
        prev_hash = self._get_last_hash()
        record = {
            "timestamp": int(time.time()),
            "event_type": event_type,
            "actor": str(actor),
            "details": details or {},
            "prev_hash": prev_hash
        }
        canonical = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
        record["entry_hash"] = hashlib.sha256(canonical).hexdigest()

        with open(self.audit_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return record["entry_hash"]

    def verify_audit_chain(self):
        """Audits the entire log file from line 1 to verify zero tampering."""
        if not os.path.exists(self.audit_log_path):
            return {"valid": True, "records_checked": 0, "message": "Empty chain (clean)"}

        expected_prev = "0" * 64
        count = 0
        with open(self.audit_log_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                stored_hash = record.pop("entry_hash", None)

                if record.get("prev_hash") != expected_prev:
                    return {
                        "valid": False,
                        "broken_at_line": line_num,
                        "message": "TAMPER ALERT: Broken previous-hash link!"
                    }

                canonical = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
                recomputed_hash = hashlib.sha256(canonical).hexdigest()
                if stored_hash != recomputed_hash:
                    return {
                        "valid": False,
                        "broken_at_line": line_num,
                        "message": "TAMPER ALERT: Record content modified!"
                    }

                expected_prev = stored_hash
                count += 1

        return {"valid": True, "records_checked": count, "message": "CBN Audit Chain Verified 100% Intact"}
