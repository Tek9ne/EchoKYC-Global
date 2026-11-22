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
voice_hub = cash_engine.voice

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>EchoKYC Global</title>
    <style>
        body { font-family: Arial, sans-serif; background: #0b0f19; color: #fff; padding: 20px; }
        header, .card { background: #1f2937; border: 2px solid #facc15; border-radius: 10px; padding: 18px; margin-bottom: 18px; }
        h1, h2 { color: #facc15; margin-top: 0; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 16px; }
        input, select, button { width: 100%; padding: 10px; margin-top: 8px; border-radius: 6px; font-size: 1rem; box-sizing: border-box; }
        input, select { background: #111827; color: #fff; border: 1px solid #6b7280; }
        button { background: #facc15; color: #000; font-weight: bold; border: none; cursor: pointer; }
        button.danger { background: #ef4444; color: #fff; }
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
        <section class="card">
            <h2>Tier 1: AI Camera KYC</h2>
            <input type="text" id="t1User" value="NG_USER_101">
            <button onclick="postApi('/api/tier1/start', {user_id: document.getElementById('t1User').value, lang: document.getElementById('globalLang').value})">Start AI Voice Camera KYC</button>
        </section>
        <section class="card">
            <h2>Tier 2: Button Phone (*347*99#)</h2>
            <input type="text" id="t2Phone" value="+2348012345678">
            <input type="password" id="t2Pin" value="4829">
            <button onclick="postApi('/api/tier2/ussd', {phone: document.getElementById('t2Phone').value, dtmf_pin: document.getElementById('t2Pin').value})">Dial *347*99# Callback</button>
        </section>
        <section class="card">
            <h2>Tier 3: EchoPass QR & Shield</h2>
            <input type="text" id="t3User" value="NG_USER_101">
            <input type="text" id="t3Name" value="Amina Yusuf">
            <button onclick="postApi('/api/tier3/echopass', {user_id: document.getElementById('t3User').value, full_name: document.getElementById('t3Name').value})">Generate EchoPass QR</button>
            <button class="danger" onclick="postApi('/api/tier3/revoke', {user_id: document.getElementById('t3User').value})">Revoke Lost Card</button>
        </section>
        <section class="card">
            <h2>Cardless ATM & POS (Offline)</h2>
            <input type="number" id="amt" value="5000">
            <select id="offMode"><option value="false">Online Live Sync</option><option value="true">Zero-Data Offline Mode</option></select>
            <button onclick="postApi('/api/cash/atm', {user_id: document.getElementById('t3User').value, amount_ngn: Number(document.getElementById('amt').value), force_offline: document.getElementById('offMode').value === 'true'})">Generate 10-Min ATM Code</button>
            <button onclick="postApi('/api/cash/pos', {user_id: document.getElementById('t3User').value, agent_name: 'Bukuru POS', amount_ngn: Number(document.getElementById('amt').value), force_offline: document.getElementById('offMode').value === 'true'})">Test POS Audio Shield</button>
            <button onclick="postApi('/api/offline/sync', {})">Sync Offline Outbox</button>
        </section>
    </main>
    <section class="status-box" id="out" role="status" aria-live="polite">System Ready...</section>
    <script>
        async function postApi(url, payload) {
            document.getElementById('out').textContent = 'Processing...';
            const res = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
            document.getElementById('out').textContent = JSON.stringify(await res.json(), null, 2);
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
    return jsonify({"status": "Language updated", "active_language": lang})


@app.route("/api/tier1/start", methods=["POST"])
def start_tier1():
    data = request.get_json()
    user_id = data.get("user_id", "NG_USER_101")
    lang = data.get("lang", "en")

    def run_cam():
        report = SmartCameraKYC(user_id=user_id, lang=lang).start_full_kyc()
        sync_engine.record_transaction("TIER1_CAMERA_KYC", user_id, report)

    threading.Thread(target=run_cam, daemon=True).start()
    return jsonify({"status": "Tier 1 AI Camera started", "user_id": user_id})


@app.route("/api/tier2/ussd", methods=["POST"])
def tier2_ussd():
    data = request.get_json()
    phone = data.get("phone", "")
    pin = data.get("dtmf_pin", "")
    voice_hub.speak_raw(f"Incoming toll-free U S S D callback for {phone}. Keypad PIN verified.")
    receipt = sync_engine.record_transaction("TIER2_USSD_KYC", phone, {"ussd": "*347*99#", "verified": len(pin) == 4})
    return jsonify({"tier": 2, "verified": True, "receipt": receipt})


@app.route("/api/tier3/echopass", methods=["POST"])
def tier3_echopass():
    data = request.get_json()
    qr_path = vault.generate_echopass_qr(data.get("user_id", "NG_USER_101"), data.get("full_name", "Amina Yusuf"))
    voice_hub.speak_raw("Tactile EchoPass Q R generated and ready for printing.")
    return jsonify({"tier": 3, "echopass_qr_file": qr_path})


@app.route("/api/tier3/revoke", methods=["POST"])
def tier3_revoke():
    user_id = request.get_json().get("user_id", "NG_USER_101")
    rev = vault.revoke_echopass(user_id)
    voice_hub.speak_raw(f"Security alert! EchoPass for {user_id} permanently revoked.")
    return jsonify({"status": "REVOKED", "details": rev})


@app.route("/api/cash/atm", methods=["POST"])
def cash_atm():
    d = request.get_json()
    return jsonify(cash_engine.generate_atm_paycode(d.get("user_id", "NG_USER_101"), int(d.get("amount_ngn", 5000)), bool(d.get("force_offline", False))))


@app.route("/api/cash/pos", methods=["POST"])
def cash_pos():
    d = request.get_json()
    return jsonify(cash_engine.authorize_pos_withdrawal(d.get("user_id", "NG_USER_101"), d.get("agent_name", "POS Agent"), int(d.get("amount_ngn", 3000)), True, bool(d.get("force_offline", False))))


@app.route("/api/offline/sync", methods=["POST"])
def offline_sync():
    return jsonify({"sync": sync_engine.sync_pending_records(), "summary": sync_engine.get_queue_summary()})


if __name__ == "__main__":
    print("=== EchoKYC Global Server Running at http://127.0.0.1:5000 ===")
    app.run(host="127.0.0.1", port=5000, debug=False)
