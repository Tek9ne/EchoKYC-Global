import os
import json
import time
import hashlib
import qrcode
from cryptography.fernet import Fernet


class SecurityVault:
    def __init__(self, key_file="master_bank.key", vault_dir="encrypted_vault"):
        self.key_file = key_file
        self.vault_dir = vault_dir
        os.makedirs(self.vault_dir, exist_ok=True)
        self.cipher = self._load_or_create_key()

    def _load_or_create_key(self):
        env_key = os.environ.get("ECHOKYC_MASTER_KEY")
        if env_key:
            return Fernet(env_key.encode("utf-8"))

        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as file:
                key = file.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as file:
                file.write(key)
        return Fernet(key)


    def encrypt_and_shred_file(self, raw_file_path, user_id, doc_type):
        if not os.path.exists(raw_file_path):
            raise FileNotFoundError(f"Cannot find file: {raw_file_path}")

        with open(raw_file_path, "rb") as raw_file:
            raw_bytes = raw_file.read()

        encrypted_bytes = self.cipher.encrypt(raw_bytes)
        safe_filename = f"{user_id}_{doc_type}_{int(time.time())}.enc"
        encrypted_path = os.path.join(self.vault_dir, safe_filename)

        with open(encrypted_path, "wb") as enc_file:
            enc_file.write(encrypted_bytes)

        os.remove(raw_file_path)

        receipt = self._create_audit_receipt(user_id, doc_type, encrypted_path)
        return encrypted_path, receipt

    def _create_audit_receipt(self, user_id, doc_type, encrypted_path):
        receipt_data = {
            "user_id": user_id,
            "document_type": doc_type,
            "vault_file": encrypted_path,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "encryption": "AES-128-CBC + HMAC-SHA256 (Fernet)"
        }
        raw_string = json.dumps(receipt_data, sort_keys=True).encode("utf-8")
        receipt_data["tamper_proof_hash"] = hashlib.sha256(raw_string).hexdigest()

        receipt_path = encrypted_path + ".receipt.json"
        with open(receipt_path, "w", encoding="utf-8") as r_file:
            json.dump(receipt_data, r_file, indent=4)

        return receipt_data

    def generate_echopass_qr(self, user_id, full_name):
        token_payload = f"ECHOKYC|{user_id}|{full_name}|{int(time.time())}"
        encrypted_token = self.cipher.encrypt(token_payload.encode("utf-8")).decode("utf-8")

        qr = qrcode.QRCode(version=2, box_size=10, border=4)
        qr.add_data(encrypted_token)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        qr_path = os.path.join(self.vault_dir, f"EchoPass_{user_id}.png")
        img.save(qr_path)
        return qr_path

    def revoke_echopass(self, user_id, reason="Lost or stolen card"):
        revoke_file = os.path.join(self.vault_dir, "revoked_users.json")
        revoked = {}
        if os.path.exists(revoke_file):
            with open(revoke_file, "r", encoding="utf-8") as f:
                revoked = json.load(f)

        revoked[user_id] = {
            "revoked_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "reason": reason
        }
        with open(revoke_file, "w", encoding="utf-8") as f:
            json.dump(revoked, f, indent=4)
        return revoked[user_id]

    def is_pass_revoked(self, user_id):
        revoke_file = os.path.join(self.vault_dir, "revoked_users.json")
        if not os.path.exists(revoke_file):
            return False
        with open(revoke_file, "r", encoding="utf-8") as f:
            revoked = json.load(f)
        return user_id in revoked


if __name__ == "__main__":
    vault = SecurityVault()
    with open("temp_test.txt", "w") as f:
        f.write("Simulated secret face image bytes")
    enc_path, receipt = vault.encrypt_and_shred_file("temp_test.txt", "NG_USER_101", "SELFIE")
    qr_path = vault.generate_echopass_qr("NG_USER_101", "Amina Yusuf")
    print("Encrypted & Shredded safely ->", enc_path)
    print("EchoPass QR generated ->", qr_path)
