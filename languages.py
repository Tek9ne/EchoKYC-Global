import os
import json
import queue
import threading
import time
import pyttsx3

try:
    import winsound
except ImportError:
    winsound = None

DEFAULT_LOCALES = {
    "en": {
        "language_name": "English",
        "welcome": "Welcome to Echo K Y C Global. Your voice-guided bank assistant is ready.",
        "noise_high": "The environment is very noisy. Switching to visual lip-tracking mode.",
        "noise_ok": "Background noise is low. Voice and camera checks are active.",
        "move_left": "Move your face slightly to the left.",
        "move_right": "Move your face slightly to the right.",
        "move_closer": "Move closer to the camera.",
        "move_back": "Move a little further back from the camera.",
        "face_centered": "Perfect! Hold steady right there.",
        "liveness_prompt": "Please say the four-digit code out loud now: {otp}",
        "liveness_passed": "Liveness verified! Thank you.",
        "id_scan_start": "Please hold your I D card flat in front of the camera.",
        "id_blurry": "The image is blurry. Please hold the card steady.",
        "id_captured": "I D card captured and encrypted safely.",
        "atm_code": "Your cardless A T M paycode is {code}. It expires in ten minutes."
    },
    "pcm": {
        "language_name": "Nigerian Pidgin",
        "welcome": "Welcome to Echo K Y C Global. Your talking bank helper don ready.",
        "noise_high": "Dis place noisy well well. I don switch to lip-tracking mode so noise no go disturb us.",
        "noise_ok": "Dis place quiet well. Make we start your face check.",
        "move_left": "Shift your face small go left.",
        "move_right": "Shift your face small go right.",
        "move_closer": "Come close to di camera small.",
        "move_back": "Step back small from di camera.",
        "face_centered": "Correct! Stay still like dat.",
        "liveness_prompt": "Abeg call dis four numbers loud now: {otp}",
        "liveness_passed": "We don confirm say na real human being! Well done.",
        "id_scan_start": "Abeg hold your I D card straight for front of di camera.",
        "id_blurry": "Di picture dey shake. Hold your hand steady small.",
        "id_captured": "We don snap your I D card and lock am inside bank safe.",
        "atm_code": "Your cardless A T M code na {code}. E go expire after ten minutes."
    },
    "ha": {
        "language_name": "Hausa",
        "welcome": "Barka da zuwa Echo K Y C Global. Mataimakin banki mai magana ya shirya.",
        "noise_high": "Wannan wuri yana da hayaniya sosai. Mun koma yanayin duba motsin baki.",
        "noise_ok": "Wurin yana da shiru. Za mu fara duba fuskar ka yanzu.",
        "move_left": "Matsar da fuskar ka kadan zuwa hagu.",
        "move_right": "Matsar da fuskar ka kadan zuwa dama.",
        "move_closer": "Matsa kusa da kyamara kadan.",
        "move_back": "Ja baya kadan daga kyamara.",
        "face_centered": "Ya yi kyau! Tsaya cak a haka.",
        "liveness_prompt": "Don Allah fadi wadannan lambobi hudu da karfi yanzu: {otp}",
        "liveness_passed": "Mun tabbatar da kai! Mun gode.",
        "id_scan_start": "Don Allah rike katin shaidar ka a gaban kyamara.",
        "id_blurry": "Hoton yana rawa. Rike hannun ka da kyau.",
        "id_captured": "An dauki hoton katin ka kuma an rufe shi cikin aminci.",
        "atm_code": "Lambar cirar kudi ta A T M ita ce {code}. Za ta kare nan da minti goma."
    },
    "yo": {
        "language_name": "Yoruba",
        "welcome": "Kaabo si Echo K Y C Global. Oluranlowo banki olohun re ti setan.",
        "noise_high": "Ariwo po ni ibi yii. A ti yipada si eto ti o n wo bi ete re se n sise.",
        "noise_ok": "Ibi yii dake jeje. E je ki a bere ayewo oju re.",
        "move_left": "Sun oju re die si apa osi.",
        "move_right": "Sun oju re die si apa otun.",
        "move_closer": "Sun mo kamera die si i.",
        "move_back": "Feyin seyin die kuro lara kamera.",
        "face_centered": "O dara gan! Duro je be yen.",
        "liveness_prompt": "Jowo pe awon nomba merin wonyi soke bayii: {otp}",
        "liveness_passed": "A ti rii daju pe eniyan gidi ni o! O seun.",
        "id_scan_start": "Jowo mu kaadi idanimo re duro dede niwaju kamera.",
        "id_blurry": "Aworan naa ko mo kedere. Jowo mu owo re duro je.",
        "id_captured": "A ti ya aworan kaadi re a si ti fi pamo sinu apo aabo banki.",
        "atm_code": "Nomba igbowo A T M re ni {code}. Yio pari laarin iseju mewa."
    },
    "ig": {
        "language_name": "Igbo",
        "welcome": "Nnoo na Echo K Y C Global. Onye enyemaka ulo aku gi adila njikere.",
        "noise_high": "Ebe a na-eme mkpotu nke ukwuu. Anyi agbanweela gaa na nlele egbugbere onu.",
        "noise_ok": "Ebe a di juu. Ka anyi malite nyocha ihu gi.",
        "move_left": "Bugharia ihu gi ntakiri gaa n'aka ekpe.",
        "move_right": "Bugharia ihu gi ntakiri gaa n'aka nri.",
        "move_closer": "Biaruo nso na kamera ntakiri.",
        "move_back": "Laghachi azu ntakiri na kamera.",
        "face_centered": "O di mma! Kwusi otu ahu.",
        "liveness_prompt": "Biko kpoo onu ogugu ano ndi a n'olu dara uda ugbu a: {otp}",
        "liveness_passed": "Anyi ekwenyela na o bu gi! Daalu.",
        "id_scan_start": "Biko jide kaadi njirimara gi kwuro oto n'ihu kamera.",
        "id_blurry": "Foto a adighi cha mma. Biko jide aka gi otu ebe.",
        "id_captured": "Anyi eseela kaadi gi ma kpachie ya n'ime igbe nchekwa ulo aku.",
        "atm_code": "Koodu A T M gi bu {code}. O ga-agwu n'ime nkeji iri."
    },
    "fr": {
        "language_name": "French",
        "welcome": "Bienvenue sur Echo K Y C Global. Votre assistant bancaire vocal est prêt.",
        "noise_high": "L'environnement est très bruyant. Passage au mode visuel de suivi des lèvres.",
        "noise_ok": "Le bruit ambiant est faible. Vérification vocale et caméra activée.",
        "move_left": "Déplacez légèrement votre visage vers la gauche.",
        "move_right": "Déplacez légèrement votre visage vers la droite.",
        "move_closer": "Rapprochez-vous de la caméra.",
        "move_back": "Éloignez-vous un peu de la caméra.",
        "face_centered": "Parfait ! Restez immobile.",
        "liveness_prompt": "Veuillez prononcer à voix haute le code à quatre chiffres : {otp}",
        "liveness_passed": "Présence confirmée ! Merci.",
        "id_scan_start": "Veuillez tenir votre carte d'identité à plat devant la caméra.",
        "id_blurry": "L'image est floue. Veuillez garder la carte immobile.",
        "id_captured": "Carte d'identité capturée et chiffrée en toute sécurité.",
        "atm_code": "Votre code de retrait sans carte est {code}. Il expire dans dix minutes."
    }
}


class VoiceEngine:
    def __init__(self, lang="en", rate=160, locales_dir="locales", audio_dir="audio_locales"):
        self.locales_dir = locales_dir
        self.audio_dir = audio_dir
        self.translations = {}
        self._initialize_locales()

        self.lang = lang if lang in self.translations else "en"
        self.rate = rate
        self.speech_queue = queue.Queue()
        self.last_spoken_key = None
        self.last_spoken_time = 0
        self.is_running = True

        self.worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.worker_thread.start()

    def _initialize_locales(self):
        os.makedirs(self.locales_dir, exist_ok=True)
        os.makedirs(self.audio_dir, exist_ok=True)
        for code, phrases in DEFAULT_LOCALES.items():
            os.makedirs(os.path.join(self.audio_dir, code), exist_ok=True)
            file_path = os.path.join(self.locales_dir, f"{code}.json")
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(phrases, f, ensure_ascii=False, indent=4)

        for filename in os.listdir(self.locales_dir):
            if filename.endswith(".json"):
                lang_code = filename[:-5]
                full_path = os.path.join(self.locales_dir, filename)
                with open(full_path, "r", encoding="utf-8") as f:
                    self.translations[lang_code] = json.load(f)

    def get_supported_languages(self):
        return {
            code: data.get("language_name", code.upper())
            for code, data in self.translations.items()
        }

    def set_language(self, lang_code):
        if lang_code in self.translations:
            self.lang = lang_code
            self.last_spoken_key = None

    def _speech_worker(self):
        try:
            import ctypes
            ctypes.windll.ole32.CoInitialize(None)
        except Exception:
            pass

        engine = pyttsx3.init()
        engine.setProperty("rate", self.rate)

        while self.is_running:
            try:
                item = self.speech_queue.get(timeout=0.5)
                if item is None:
                    break

                wav_path, text_to_speak = item
                if wav_path and os.path.exists(wav_path) and winsound is not None:
                    print(f"[NATIVE AUDIO - {self.lang.upper()}]: Playing {wav_path}")
                    winsound.PlaySound(wav_path, winsound.SND_FILENAME)
                else:
                    print(f"[TTS VOICE - {self.lang.upper()}]: {text_to_speak}")
                    engine.say(text_to_speak)
                    engine.runAndWait()

                self.speech_queue.task_done()
            except queue.Empty:
                continue
            except Exception as err:
                print(f"[VOICE ERROR]: {err}")

    def speak(self, key, cooldown=2.5, **kwargs):
        now = time.time()
        if key == self.last_spoken_key and (now - self.last_spoken_time) < cooldown:
            return

        current_dict = self.translations.get(self.lang, self.translations["en"])
