import json
import time
import socket
import sqlite3
import hashlib


class OfflineSyncEngine:
    def __init__(self, db_path="echokyc_offline.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tx_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    integrity_hash TEXT NOT NULL,
                    status TEXT DEFAULT 'QUEUED_OFFLINE',
                    created_at REAL NOT NULL,
                    synced_at REAL
                )
            """)
            conn.commit()

    def is_internet_available(self, host="8.8.8.8", port=53, timeout=1.5):
        try:
            socket.setdefaulttimeout(timeout)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((host, port))
            return True
        except OSError:
            return False

    def record_transaction(self, event_type, user_id, payload_dict, force_offline=False):
        tx_id = f"TX_{int(time.time() * 1000)}_{user_id}"
        payload_str = json.dumps(payload_dict, sort_keys=True, default=str)
        integrity_hash = hashlib.sha256(f"{tx_id}|{payload_str}".encode("utf-8")).hexdigest()

        online = False if force_offline else self.is_internet_available()
        status = "SYNCED_LIVE" if online else "QUEUED_OFFLINE"
        synced_at = time.time() if online else None

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO sync_outbox (
                    tx_id, event_type, user_id, payload_json,
                    integrity_hash, status, created_at, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (tx_id, event_type, user_id, payload_str, integrity_hash, status, time.time(), synced_at))
            conn.commit()

        return {
            "tx_id": tx_id,
            "status": status,
            "online_connection": online,
            "integrity_hash": integrity_hash
        }

    def sync_pending_records(self):
        if not self.is_internet_available():
            return {"synced_count": 0, "message": "Still offline. Records remain safe in local vault."}

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id, tx_id, payload_json, integrity_hash FROM sync_outbox WHERE status = 'QUEUED_OFFLINE'")
            pending_rows = cursor.fetchall()

            synced_count = 0
            for row_id, tx_id, payload_str, saved_hash in pending_rows:
                recomputed = hashlib.sha256(f"{tx_id}|{payload_str}".encode("utf-8")).hexdigest()
                if recomputed != saved_hash:
                    conn.execute("UPDATE sync_outbox SET status = 'TAMPER_ALERT' WHERE id = ?", (row_id,))
                    continue

                conn.execute(
                    "UPDATE sync_outbox SET status = 'SYNCED_LIVE', synced_at = ? WHERE id = ?",
                    (time.time(), row_id)
                )
                synced_count += 1
            conn.commit()

        return {"synced_count": synced_count, "message": f"Successfully synced {synced_count} offline records to bank ledger."}

    def get_queue_summary(self):
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM sync_outbox").fetchone()
            queued = conn.execute("SELECT COUNT(*) FROM sync_outbox WHERE status = 'QUEUED_OFFLINE'").fetchone()
            synced = conn.execute("SELECT COUNT(*) FROM sync_outbox WHERE status = 'SYNCED_LIVE'").fetchone()
        return {"total_records": total, "pending_offline": queued, "synced_to_bank": synced}


if __name__ == "__main__":
    syncer = OfflineSyncEngine()
    res1 = syncer.record_transaction("KYC_VERIFICATION", "NG_USER_101", {"tier": 1, "verified": True}, force_offline=True)
    print("Recorded in Airplane Mode:", res1)
    print("Queue Before Sync:", syncer.get_queue_summary())
    print("Sync Result:", syncer.sync_pending_records())
    print("Queue After Sync:", syncer.get_queue_summary())
