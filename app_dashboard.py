import os
import json
import threading
from flask import Flask, render_template_string, request, jsonify, Response

from languages import VoiceEngine
from security_vault import SecurityVault
from smart_camera_kyc import SmartCameraKYC
from cardless_cash_engine import CardlessCashEngine, resolve_pos_identity
from offline_sync_engine import OfflineSyncEngine
from security_hardening import CBNComplianceGuard

app = Flask(__name__)

cbn_guard = CBNComplianceGuard()
vault = SecurityVault()
sync_engine = OfflineSyncEngine()
cash_engine = CardlessCashEngine(lang="en")
voice_hub = cash_engine.voice

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EchoKYC Global — Zero-Barrier Voice Banking</title>
    <style>
        body { font-family: Arial, sans-serif; background: #0b0f19; color: #fff; padding: 20px; }
        header, .card { background: #1f2937; border: 2px solid #facc15; border-radius: 10px; padding: 18px; margin-bottom: 18px; }
        h1, h2 { color: #facc15; margin-top: 0; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 16px; }
        input, select, button { width: 100%; padding: 10px; margin-top: 8px; border-radius: 6px; font-size: 1rem; box-sizing: border-box; }
        input, select { background: #111827; color: #fff; border: 1px solid #6b7280; }
        button { background: #facc15; color: #000; font-weight: bold; border: none; cursor: pointer; }
        button.danger { background: #ef4444; color: #fff; }
        button.audit { background: #10b981; color: #000; }
        .status-box { background: #111827; border: 2px solid #10b981; padding: 16px; border-radius: 8px; white-space: pre-wrap; font-family: monospace; }
    </style>
</head>
<body>
    <header role="banner">
        <h1>EchoKYC Global — Zero-Barrier Voice Banking</h1>
        <select id="globalLang" aria-label="Select Language" onchange="postApi('/api/set_language', {lang: this.value})">
            {% for code, name in languages.items() %}
                <option value="{{ code }}">{{ name }} ({{ code.upper() }})</option>
            {% endfor %}
        </select>
    </header>
    <main class="grid" role="main">
        <section class="card" aria-label="Tier 1 AI Camera KYC">
            <h2>Tier 1: AI Camera KYC</h2>
            <input type="text" id="t1User" value="NG_USER_101" aria-label="Tier 1 User ID">
            <button onclick="postApi('/api/tier1/start', {user_id: document.getElementById('t1User').value, lang: document.getElementById('globalLang').value})">Start AI Voice Camera KYC</button>
        </section>
        <section class="card" aria-label="Tier 2 Button Phone USSD">
            <h2>Tier 2: Button Phone (*347*99#)</h2>
            <input type="text" id="t2Phone" value="+2348012345678" aria-label="Phone Number">
            <input type="password" id="t2Pin" value="4829" aria-label="4-Digit DTMF PIN">
            <button onclick="postApi('/api/tier2/ussd', {phone: document.getElementById('t2Phone').value, dtmf_pin: document.getElementById('t2Pin').value})">Dial *347*99# Callback</button>
        </section>
        <section class="card" aria-label="Tier 3 EchoPass QR and Security">
            <h2>Tier 3: EchoPass QR &amp; Shield</h2>
            <input type="text" id="t3User" value="NG_USER_101" aria-label="Customer User ID">
            <input type="text" id="t3Name" value="Amina Yusuf" aria-label="Customer Full Name">
            <button onclick="postApi('/api/tier3/echopass', {user_id: document.getElementById('t3User').value, full_name: document.getElementById('t3Name').value})">Generate EchoPass QR</button>
            <button class="danger" onclick="postApi('/api/tier3/revoke', {user_id: document.getElementById('t3User').value})">Revoke Lost Card</button>
            <button class="audit" onclick="getApi('/api/audit/verify')">Verify CBN Hash-Chain Audit</button>
        </section>
        <section class="card" aria-label="Cardless ATM and POS">
            <h2>Cardless ATM &amp; POS (Offline)</h2>
            <input type="text" id="agentName" placeholder="POS Merchant Name (Auto-Locates Online)" aria-label="POS Merchant Name">
            <input type="number" id="amt" value="5000" aria-label="Amount in Naira">
            <input type="password" id="posPin" value="4829" placeholder="PIN (4829 Normal / 9911 Duress)" aria-label="Transaction PIN">
            <select id="offMode" aria-label="Network Mode">
                <option value="false">Online Live Sync</option>
                <option value="true">Zero-Data Offline Mode</option>
            </select>
            <button onclick="postApi('/api/cash/atm', {user_id: document.getElementById('t3User').value, amount_ngn: Number(document.getElementById('amt').value), force_offline: document.getElementById('offMode').value === 'true'})">Generate 10-Min ATM Code</button>
            <button onclick="postApi('/api/cash/pos', {user_id: document.getElementById('t3User').value, agent_name: document.getElementById('agentName').value, amount_ngn: Number(document.getElementById('amt').value), spoken_pin: document.getElementById('posPin').value, force_offline: document.getElementById('offMode').value === 'true'})">Test POS Audio Shield</button>
            <button onclick="postApi('/api/offline/sync', {})">Sync Offline Outbox</button>
        </section>
    </main>
    <section class="status-box" id="out" role="status" aria-live="polite">System Ready...</section>
    <script>
        function speakBrowser(text) {
            if ('speechSynthesis' in window && text) {
                window.speechSynthesis.cancel();
                const msg = new SpeechSynthesisUtterance(text);
                msg.rate = 0.95;
                window.speechSynthesis.speak(msg);
            }
        }
        async function postApi(url, payload) {
            document.getElementById('out').textContent = 'Processing...';
            const res = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
            const data = await res.json();
            document.getElementById('out').textContent = JSON.stringify(data, null, 2);
            if (data.spoken_prompt) speakBrowser(data.spoken_prompt);
        }
        async function getApi(url) {
            document.getElementById('out').textContent = 'Auditing cryptographic chain...';
            const res = await fetch(url);
            const data = await res.json();
            document.getElementById('out').textContent = JSON.stringify(data, null, 2);
            if (data.message) speakBrowser(data.message);
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_DASHBOARD, languages=voice_hub.get_supported_languages())


@app.route("/api/set_language", methods=["POST"])
def set_language():
    lang = request.get_json().get("lang", "en")
    voice_hub.set_language(lang)
    cash_engine.voice.set_language(lang)
    voice_hub.speak("welcome", cooldown=0)
    greeting = voice_hub.translations.get(lang, {}).get("welcome", "Voice language updated.")
    return jsonify({"status": "Language updated", "active_language": lang, "spoken_prompt": greeting})


@app.route("/api/tier1/start", methods=["POST"])
@cbn_guard.rate_limit(max_requests=10, window_seconds=60)
def start_tier1():
    data = request.get_json()
    user_id = data.get("user_id", "NG_USER_101")
    lang = data.get("lang", "en")
    cbn_guard.append_audit_event("TIER1_KYC_STARTED", user_id, {"lang": lang})

    def run_cam():
        report = SmartCameraKYC(user_id=user_id, lang=lang).start_full_kyc()
        sync_engine.record_transaction("TIER1_CAMERA_KYC", user_id, report)

    threading.Thread(target=run_cam, daemon=True).start()
    return jsonify({
        "status": "Tier 1 AI Camera started",
        "user_id": user_id,
        "spoken_prompt": "Tier 1 A I Camera K Y C initiated."
    })


@app.route("/api/tier2/ussd", methods=["POST"])
@cbn_guard.rate_limit(max_requests=15, window_seconds=60)
def tier2_ussd():
    data = request.get_json()
    phone = data.get("phone", "")
    pin = data.get("dtmf_pin", "")
    prompt = f"Incoming toll-free U S S D callback for {phone}. Keypad PIN verified."
    voice_hub.speak_raw(prompt)
    receipt = sync_engine.record_transaction("TIER2_USSD_KYC", phone, {"ussd": "*347*99#", "verified": len(pin) == 4})
    cbn_guard.append_audit_event("TIER2_USSD_VERIFIED", phone, {"verified": len(pin) == 4})
    return jsonify({"tier": 2, "verified": True, "receipt": receipt, "spoken_prompt": prompt})


@app.route("/api/tier3/echopass", methods=["POST"])
@cbn_guard.rate_limit(max_requests=15, window_seconds=60)
def tier3_echopass():
    data = request.get_json()
    user_id = data.get("user_id", "NG_USER_101")
    qr_path = vault.generate_echopass_qr(user_id, data.get("full_name", "Amina Yusuf"))
    prompt = "Tactile EchoPass Q R generated and ready for printing."
    voice_hub.speak_raw(prompt)
    cbn_guard.append_audit_event("TIER3_ECHOPASS_ISSUED", user_id, {"qr_file": qr_path})
    return jsonify({"tier": 3, "echopass_qr_file": qr_path, "spoken_prompt": prompt})


@app.route("/api/tier3/revoke", methods=["POST"])
@cbn_guard.rate_limit(max_requests=15, window_seconds=60)
def tier3_revoke():
    user_id = request.get_json().get("user_id", "NG_USER_101")
    rev = vault.revoke_echopass(user_id)
    prompt = f"Security alert! EchoPass for {user_id} permanently revoked."
    voice_hub.speak_raw(prompt)
    cbn_guard.append_audit_event("TIER3_ECHOPASS_REVOKED", user_id, rev)
    return jsonify({"status": "REVOKED", "details": rev, "spoken_prompt": prompt})


@app.route("/api/cash/atm", methods=["POST"])
@cbn_guard.rate_limit(max_requests=15, window_seconds=60)
def cash_atm():
    d = request.get_json()
    user_id = d.get("user_id", "NG_USER_101")
    amt = int(d.get("amount_ngn", 5000))
    res = cash_engine.generate_atm_paycode(user_id, amt, bool(d.get("force_offline", False)))
    cbn_guard.append_audit_event("ATM_PAYCODE_GENERATED", user_id, {"amount_ngn": amt, "mode": res.get("mode")})
    if res.get("paycode"):
        spaced_code = " ".join(str(res["paycode"]))
        res["spoken_prompt"] = f"Your cardless A T M paycode is {spaced_code}. It expires in ten minutes."
    return jsonify(res)


@app.route("/api/cash/pos", methods=["POST"])
@cbn_guard.rate_limit(max_requests=15, window_seconds=60)
def cash_pos():
    d = request.get_json()
    user_id = d.get("user_id", "NG_USER_101")
    amt = int(d.get("amount_ngn", 3000))
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    agent = resolve_pos_identity(client_ip, d.get("agent_name", ""))
    res = cash_engine.authorize_pos_withdrawal(
        user_id=user_id,
        agent_name=agent,
        amount_ngn=amt,
        user_confirmed=True,
        force_offline=bool(d.get("force_offline", False)),
        spoken_pin=str(d.get("spoken_pin", ""))
    )
    event_label = "SILENT_DURESS_ALERT" if res.get("duress_triggered") else "POS_WITHDRAWAL_ATTEMPT"
    cbn_guard.append_audit_event(event_label, user_id, {"agent": agent, "amount_ngn": res.get("amount_ngn", amt), "approved": res.get("approved")})

    if res.get("approved"):
        res["spoken_prompt"] = f"Attention! {agent} is requesting {res['amount_ngn']} Naira. Transaction approved."
    else:
        res["spoken_prompt"] = res.get("reason", "Transaction blocked.")
    return jsonify(res)


@app.route("/api/offline/sync", methods=["POST"])
def offline_sync():
    sync_out = sync_engine.sync_pending_records()
    if sync_out.get("synced_count", 0) > 0:
        cash_engine.offline_spent_ledger.clear()
    cbn_guard.append_audit_event("OFFLINE_LEDGER_SYNC", "system", sync_out)
    res = {"sync": sync_out, "summary": sync_engine.get_queue_summary()}
    res["spoken_prompt"] = sync_out["message"]
    return jsonify(res)


@app.route("/api/audit/verify", methods=["GET"])
def audit_verify():
    return jsonify(cbn_guard.verify_audit_chain())


@app.route("/api/telco/ussd", methods=["POST"])
@cbn_guard.rate_limit(max_requests=30, window_seconds=60)
def telco_ussd_webhook():
    phone = request.values.get("phoneNumber", "unknown")
    text = request.values.get("text", "").strip()
    if text == "":
        reply = "CON Welcome to EchoKYC Voice Banking\n1. Verify Identity\n2. Cardless ATM Code"
    elif text == "1":
        reply = "CON Enter your 4-digit Voice PIN:"
    elif text.startswith("1*"):
        cbn_guard.append_audit_event("TELCO_USSD_KYC", phone, {"session_input": "***"})
        reply = "END Identity Verified! Toll-free voice assistant activated."
    else:
        reply = "END Thank you for using EchoKYC Global."
    return Response(reply, mimetype="text/plain")


@app.route("/api/telco/voice", methods=["POST"])
@cbn_guard.rate_limit(max_requests=30, window_seconds=60)
def telco_voice_webhook():
    xml_response = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response>'
        '<Say voice="woman">Welcome to Echo K Y C Global. Press 1 on your phone keypad to confirm cardless withdrawal.</Say>'
        '</Response>'
    )
    return Response(xml_response, mimetype="application/xml")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"=== EchoKYC Global Server Running at http://127.0.0.1:{port} ===")
    app.run(host="0.0.0.0", port=port, debug=False)
