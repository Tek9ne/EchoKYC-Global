# EchoKYC Global — Zero-Barrier, Offline-First Voice Banking & AI KYC

**EchoKYC Global** is an offline-first, 100% cardless voice banking and AI identity verification (KYC) platform built in Python for blind, visually impaired, and underserved users.

Engineered to meet **Central Bank of Nigeria (CBN)** cybersecurity standards and **Nigeria Data Protection Act (NDPA)** biometric privacy mandates, EchoKYC works across smartphones, feature/button phones, and zero-phone scenarios—even in **Airplane Mode**.

---

## Why EchoKYC Global?

Traditional digital banking and POS terminals rely entirely on visual screens, leaving over **1.1 million blind and visually impaired citizens** vulnerable to financial exclusion, POS amount inflation fraud, and physical coercion. EchoKYC replaces visual barriers with **multilingual voice guidance, noise-adaptive computer vision, cryptographic biometric shredding, and real-time audio consent shields**.

---

## 3-Tier Universal Inclusion Architecture

| Tier | Target User / Device | Connectivity | How Verification & Cash Access Work |
| :--- | :--- | :--- | :--- |
| **Tier 1** | Smartphone Users | **100% Offline** | OpenCV AI camera voice-guides face centering, checks ambient noise (`> 68 dB`), runs 4-syllable lip-tracking liveness, and scans ID cards via blur-guarded `easyocr`. |
| **Tier 2** | Button / Feature Phones | **Zero Data (GSM)** | Toll-free USSD (`*347*99#`) & DTMF keypad PIN verification with live **Africa's Talking** USSD (`CON`/`END`) and Voice XML webhooks. |
| **Tier 3** | No Phone / Dead Battery | **Offline POS** | Printable, encrypted tactile **EchoPass QR** cards for POS withdrawals (capped at **₦10,000/day**) with instant lost/stolen card revocation. |

---

## Core Security, Fraud Prevention & CBN/NDPA Compliance

- **NDPA Biometric Encryption & Zero-Trace Shredding (`security_vault.py`):** Captured face and ID frames are encrypted immediately with AES-128 (`cryptography.fernet`) and permanently deleted from disk (`os.remove`), issuing tamper-proof `SHA-256` JSON receipts.
- **POS Audio Consent Shield (`cardless_cash_engine.py`):** Dynamically identifies the POS terminal via IP geolocation when online and speaks the exact merchant identity and Naira amount aloud before authorizing debit.
- **Silent Duress Coercion PIN (`9911`):** Under physical threat, entering `9911` approves a **₦1,000 decoy withdrawal** without an immediate reversal (preventing attacker retaliation on the spot) while silently logging `SILENT_DURESS_FRAUD_ALERT` with terminal telemetry for law enforcement and delayed Post-No-Debit (PND) hold.
- **10-Minute Amount-Locked ATM Paycodes:** Generates single-use, 6-digit cardless ATM withdrawal codes bound strictly to one user and exact Naira amount.
- **Zero-Data Store-and-Forward Ledger (`offline_sync_engine.py`):** Queues offline transactions in SQLite (`QUEUED_OFFLINE`) with a **₦15,000 cumulative offline double-spend cap**, verifying `SHA-256` integrity hashes before syncing (`SYNCED_LIVE` / `TAMPER_ALERT`).
- **CBN Compliance Guard (`security_hardening.py`):** Sliding-window IP rate limiting (`HTTP 429`), stateless `HS256` JWT session authentication (`hmac.compare_digest`), and blockchain-style **SHA-256 hash-chained audit logs** (`/api/audit/verify`).

---

## Multilingual Voice Support (6 Languages)

Plug-and-play `locales/*.json` + native `.wav` audio playback (`languages.py`) with browser `Web Speech API` (`speechSynthesis`) fallback:
- **English (`en`)**
- **Nigerian Pidgin (`pcm`)**
- **Hausa (`ha`)**
- **Yoruba (`yo`)**
- **Igbo (`ig`)**
- **French (`fr`)**

---

## Project Architecture

```text
EchoKYC_Global/
├── app_dashboard.py         # High-contrast ARIA web dashboard, REST APIs & Telco webhooks
├── languages.py             # Thread-safe multilingual voice engine & audio queue
├── smart_camera_kyc.py      # Offline OpenCV face centering, lip liveness & Laplacian OCR
├── security_vault.py        # Fernet AES-128 biometric encryption, shredding & EchoPass QR
├── cardless_cash_engine.py  # 10-min ATM paycodes, POS Audio Shield, offline cap & Duress PIN
├── offline_sync_engine.py   # SQLite store-and-forward ledger with SHA-256 tamper checks
├── security_hardening.py    # CBN rate limiting, HS256 JWT & hash-chained audit ledger
├── requirements.txt         # Cloud & local Python dependencies
└── Procfile                 # Gunicorn production entry point
```

---

## Local Quick Start

```bash
# 1. Clone the repository
git clone https://github.com
cd EchoKYC-Global

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the accessible dashboard
python app_dashboard.py
```

Open **`http://127.0.0.1:5000`** in your browser.

---

## Cloud Deployment (Render.com)

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app_dashboard:app --bind 0.0.0.0:$PORT --workers 1 --threads 4`
- **Environment Variables:**
  - `ECHOKYC_MASTER_KEY` — Base64 Fernet master key for persistent vault encryption
  - `ECHOKYC_JWT_SECRET` — Cryptographic secret key for signing JWT tokens

---

## License & Security Disclosure

Built for open financial inclusion and accessibility innovation. Sensitive runtime artifacts (`master_bank.key`, `*.db`, `*.jsonl`, `encrypted_vault/`, `.env`) are strictly excluded from version control.

