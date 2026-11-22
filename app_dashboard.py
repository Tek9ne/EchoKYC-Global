import threading
from flask import Flask, render_template_string, request, jsonify

from languages import VoiceEngine
from security_vault import SecurityVault
from smart_camera_kyc import SmartCameraKYC
from cardless_cash_engine import CardlessCashEngine
from offline_sync_engine import OfflineSyncEngine

app = Flask(__name__)

vault = SecurityVault()
sync_engine = OfflineSyncEngine()
cash_engine = CardlessCashEngine(lang="en")
voice_hub = VoiceEngine(lang="en")

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EchoKYC Global — Zero-Barrier Voice Banking & Identity</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #0b0f19;
            color: #ffffff;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }
        header {
            background: #111827;
            border: 2px solid #facc15;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 24px;
        }
        h1 { color: #facc15; margin: 0 0 8px 0; font-size: 1.8rem; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
        }
        .card {
            background: #1f2937;
            border: 2px solid #374151;
            border-radius: 12px;
            padding: 20px;
        }
        .card h2 { color: #facc15; margin-top: 0; font-size: 1.3rem; }
        label { display: block; margin-top: 10px; font-weight: bold; }
        input, select, button {
            width: 100%;
            padding: 12px;
            margin-top: 6px;
            border-radius: 8px;
            font-size: 1rem;
            box-sizing: border-box;
        }
        input, select {
            background: #111827;
            color: #ffffff;
            border: 1px solid #6b7280;
        }
        button {
            background: #facc15;
            color: #000000;
            font-weight: bold;
            border: none;
            cursor: pointer;
            margin-top: 14px;
        }
        button:hover { background: #eab308; }
        button.danger { background: #ef4444; color: #ffffff; }
        .status-box {
            margin-top: 24px;
            background: #111827;
            border: 2px solid #10b981;
            padding: 18px;
            border-radius: 10px;
            white-space: pre-wrap;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <header role="banner">
        <h1>EchoKYC Global — Zero-Barrier AI Identity & Cardless Banking</h1>
        <p>Built for Blind & Visually Impaired Users | 100% Offline-Capable | Multilingual Voice Guidance</p>
        <label for="globalLang">Select Spoken Language (Nigerian & Global Locales):</label>
        <select id="globalLang" aria-label="Select Spoken Language" onchange="changeLanguage()">
            {% for code, name in languages.items() %}
                <option value="{{ code }}">{{ name }} ({{ code.upper() }})</option>
            {% endfor %}
        </select>
    </header>

    <main class="grid" role="main">
        <section class="card" aria-labelledby="tier1-title">
            <h2 id="tier1-title">Tier 1: Smartphone / Kiosk AI KYC</h2>
            <p>Hands-free camera coach, decibel noise gatekeeper, lip-movement OTP liveness, and ID OCR scanner.</p>
            <label for="t1User">User ID:</label>
            <input type="text" id="t1User" value="NG_USER_101">
            <button onclick="launchTier1Camera()">Start AI Voice Camera KYC</button>
        </section>

        <section class="card" aria-labelledby="tier2-title">
            <h2 id="tier2-title">Tier 2: Button Phone USSD (*347*99#)</h2>
            <p>Zero data & zero smartphone needed. Triggers toll-free voice callback + keypad DTMF verification.</p>
            <label for="t2Phone">Customer Phone Number:</label>
            <input type="text" id="t2Phone" value="+2348012345678">
            <label for="t2Dtmf">Simulated Keypad PIN (DTMF):</label>
            <input type="password" id="t2Dtmf" value="4829">
            <button onclick="triggerUssdCallback()">Dial *347*99# Voice Callback</button>
        </section>

        <section class="card" aria-labelledby="tier3-title">
            <h2 id="tier3-title">Tier 3: EchoPass QR & POS Shield</h2>
            <p>Works with 0% phone battery. Tactile QR + POS Audio Consent Shield + Lost Card Revocation.</p>
            <label for="t3User">User ID:</label>
            <input type="text" id="t3User" value="NG_USER_101">
            <label for="t3Name">Customer Full Name:</label>
            <input type="text" id="t3Name" value="Amina Yusuf">
            <button onclick="issueEchoPass()">Generate Tactile EchoPass QR</button>
            <button class="danger" onclick="revokeEchoPass()">Report Lost Card (Revoke QR)</button>
        </section>

        <section class="card" aria-labelledby="cash-title">
            <h2 id="cash-title">Cardless ATM & POS (Offline Ready)</h2>
            <p>10-minute amount-locked ATM paycodes & POS Audio Consent Shield with Airplane-Mode SQLite queue.</p>
            <label for="cashAmount">Amount (NGN):</label>
            <input type="number" id="cashAmount" value="5000">
            <label for="offlineMode">Network Mode:</label>
            <select id="offlineMode">
                <option value="false">Online (Live Bank Sync)</option>
                <option value="true">Zero-Data / Airplane Mode (Offline Outbox)</option>
            </select>
            <button onclick="createAtmPaycode()">Generate 10-Min ATM Paycode</button>
            <button onclick="runPosConsent()">Test POS Audio Consent Shield</button>
            <button onclick="syncOfflineQueue()">Sync Offline Outbox to Bank</button>
        </section>
    </main>

    <section class="status-box" id="outputLog" role="status" aria-live="polite">
System Ready. Select any tier above to test EchoKYC Global...
    </section>

    <script>
        function logOutput(data) {
            document.getElementById("outputLog").textContent = JSON.stringify(data, null, 2);
        }

        async function changeLanguage() {
            const lang = document.getElementById("globalLang").value;
            const res = await fetch("/api/set_language", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({lang})
            });
            logOutput(await res.json());
        }

        async function launchTier1Camera() {
            const user_id = document.getElementById("t1User").value;
            const lang = document.getElementById("globalLang").value;
            logOutput({status: "Starting local AI camera window... Check your taskbar if it opens behind the browser."});
            const res = await fetch("/api/tier1/start", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({user_id, lang})
            });
            logOutput(await res.json());
        }

        async function triggerUssdCallback() {
            const phone = document.getElementById("t2Phone").value;
            const dtmf_pin = document.getElementById("t2Dtmf").value;
            const res = await fetch("/api/tier2/ussd", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({phone, dtmf_pin})
            });
            logOutput(await res.json());
        }

        async function issueEchoPass() {
            const user_id = document.getElementById("t3User").value;
            const full_name = document.getElementById("t3Name").value;
            const res = await fetch("/api/tier3/echopass", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({user_id, full_name})
            });
            logOutput(await res.json());
        }

        async function revokeEchoPass() {
            const user_id = document.getElementById("t3User").value;
            const res = await fetch("/api/tier3/revoke", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({user_id})
            });
            logOutput(await res.json());
        }

        async function createAtmPaycode() {
            const user_id = document.getElementById("t3User").value;
            const amount_ngn = Number(document.getElementById("cashAmount").value);
            const force_offline = document.getElementById("offlineMode").value === "true";
            const res = await fetch("/api/cash/atm", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({user_id, amount_ngn, force_offline})
            });
            logOutput(await res.json());
        }

        async function runPosConsent() {
            const user_id = document.getElementById("t3User").value;
            const amount_ngn = Number(document.getElementById("cashAmount").value);
            const force_offline = document.getElementById("offlineMode").value === "true";
            const res = await fetch("/api/cash/pos", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({user_id, agent_name: "Bukuru Verified POS", amount_ngn, force_offline})
            });
            logOutput(await res.json());
        }

        async function syncOfflineQueue() {
            const res = await fetch("/api/offline/sync", {method: "POST"});
            logOutput(await res.json());
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
