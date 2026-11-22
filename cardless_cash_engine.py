import time
import random
import hashlib
from languages import VoiceEngine
from security_vault import SecurityVault
from offline_sync_engine import OfflineSyncEngine


class CardlessCashEngine:
    def __init__(self, lang="en"):
        self.voice = VoiceEngine(lang=lang)
        self.vault = SecurityVault()
        self.sync_engine = OfflineSyncEngine()
        self.active_paycodes = {}

    def generate_atm_paycode(self, user_id, amount_ngn, force_offline=False):
        if amount_ngn <= 0 or amount_ngn > 100000:
            raise ValueError("Amount must be between 1 and 100,000 NGN.")

        raw_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
        spoken_code = " ".join(raw_code)
        expires_at = time.time() + 600

        self.active_paycodes[raw_code] = {
            "user_id": user_id,
            "locked_amount_ngn": amount_ngn,
            "expires_at": expires_at,
            "used": False
        }

        self.voice.speak("atm_code", cooldown=0, code=spoken_code)

        sync_receipt = self.sync_engine.record_transaction(
            event_type="ATM_CARDLESS_PAYCODE",
            user_id=user_id,
            payload_dict={"amount_ngn": amount_ngn, "code_hash": hashlib.sha256(raw_code.encode()).hexdigest()},
            force_offline=force_offline
        )

        return {
            "paycode": raw_code,
            "locked_amount_ngn": amount_ngn,
            "expires_in_seconds": 600,
            "sync_status": sync_receipt["status"],
            "tx_id": sync_receipt["tx_id"]
        }

    def redeem_atm_paycode(self, paycode, requested_amount_ngn):
        record = self.active_paycodes.get(paycode)
        if not record:
            return {"approved": False, "reason": "Invalid ATM paycode."}
        if record["used"]:
            return {"approved": False, "reason": "Paycode already used."}
        if time.time() > record["expires_at"]:
            return {"approved": False, "reason": "Paycode expired after 10 minutes."}
        if requested_amount_ngn != record["locked_amount_ngn"]:
            return {
                "approved": False,
                "reason": f"Security Block: Code is strictly locked to {record['locked_amount_ngn']} NGN."
            }

        record["used"] = True
        return {
            "approved": True,
            "dispensed_ngn": requested_amount_ngn,
            "user_id": record["user_id"]
        }

    def authorize_pos_withdrawal(self, user_id, agent_name, amount_ngn, user_confirmed=True, force_offline=False):
        consent_prompt = (
            f"Attention! Agent {agent_name} is requesting a cardless withdrawal of "
            f"{amount_ngn} Naira from your account. Confirming transaction now."
        )
        self.voice.speak_raw(consent_prompt)
        time.sleep(5.5)

        if not user_confirmed:
            self.voice.speak_raw("Transaction cancelled. Zero Naira deducted.")
            return {"approved": False, "reason": "User declined POS consent."}

        sync_receipt = self.sync_engine.record_transaction(
            event_type="POS_CARDLESS_CASHOUT",
            user_id=user_id,
            payload_dict={
                "agent_name": agent_name,
                "amount_ngn": amount_ngn,
                "audio_consent_verified": True
            },
            force_offline=force_offline
        )

        self.voice.speak_raw(f"Approved! {amount_ngn} Naira paid to {agent_name}.")
        time.sleep(3.5)

        return {
            "approved": True,
            "amount_ngn": amount_ngn,
            "agent_name": agent_name,
            "sync_status": sync_receipt["status"],
            "tx_id": sync_receipt["tx_id"]
        }

    def authorize_tier3_echopass_pos(
        self,
        encrypted_qr_token,
        agent_name,
        amount_ngn,
        biometric_face_verified=True,
        liveness_lip_verified=True,
        force_offline=False
    ):
        if amount_ngn > 10000:
            self.voice.speak_raw("Security limit exceeded. Zero-phone EchoPass withdrawals are capped at ten thousand Naira.")
            return {"approved": False, "reason": "Exceeds 10,000 NGN Tier 3 dead-phone daily cap."}

        try:
            decrypted_payload = self.vault.cipher.decrypt(encrypted_qr_token.encode("utf-8")).decode("utf-8")
            parts = decrypted_payload.split("|")
            if len(parts) < 3 or parts != "ECHOKYC":
                return {"approved": False, "reason": "Invalid or forged EchoPass QR card."}
            user_id = parts
            full_name = parts
        except Exception:
            return {"approved": False, "reason": "Corrupted or unauthorized EchoPass QR token."}

        if self.vault.is_pass_revoked(user_id):
            self.voice.speak_raw("Security alert! This EchoPass card has been reported lost and is permanently blocked.")
            return {"approved": False, "reason": "EchoPass card has been revoked."}

        if not (biometric_face_verified and liveness_lip_verified):
            self.voice.speak_raw("Security alert! Face and lip liveness check failed. Withdrawal blocked.")
            return {"approved": False, "reason": "Biometric or liveness check failed on POS camera."}

        return self.authorize_pos_withdrawal(
            user_id=user_id,
            agent_name=f"{agent_name} (Tier-3 EchoPass: {full_name})",
            amount_ngn=amount_ngn,
            user_confirmed=True,
            force_offline=force_offline
        )

    def shutdown(self):
        self.voice.stop()


if __name__ == "__main__":
    cash = CardlessCashEngine(lang="pcm")
    atm_ticket = cash.generate_atm_paycode("NG_USER_101", 5000, force_offline=True)
    print("ATM Ticket:", atm_ticket)
    time.sleep(5.0)

    print("Fraud Block Test:", cash.redeem_atm_paycode(atm_ticket["paycode"], 10000))
    print("Valid ATM Test:", cash.redeem_atm_paycode(atm_ticket["paycode"], 5000))

    pos_tx = cash.authorize_pos_withdrawal("NG_USER_101", "Bukuru Verified POS", 3000, user_confirmed=True, force_offline=True)
    print("POS Result:", pos_tx)
    cash.shutdown()
