import time
import random
import cv2
import numpy as np
import sounddevice as sd
import easyocr

from languages import VoiceEngine
from security_vault import SecurityVault


class SmartCameraKYC:
    def __init__(self, user_id, lang="en"):
        self.user_id = user_id
        self.voice = VoiceEngine(lang=lang)
        self.vault = SecurityVault()

        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.mouth_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_smile.xml"
        )
        self.ocr_reader = None
        print("[CAMERA ENGINE]: 100% Offline OpenCV Face & Lip Engine Ready.")

    def check_ambient_noise(self, duration=1.5, sample_rate=16000, threshold_db=68.0):
        try:
            audio = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="float32"
            )
            sd.wait()
            rms = np.sqrt(np.mean(np.square(audio)))
            decibels = 20 * np.log10(max(rms, 1e-7)) + 90
        except Exception:
            decibels = 50.0

        is_noisy = decibels > threshold_db
        if is_noisy:
            self.voice.speak("noise_high", cooldown=0)
        else:
            self.voice.speak("noise_ok", cooldown=0)

        time.sleep(3.5)
        return round(float(decibels), 1), is_noisy

    def _detect_face_and_mouth(self, frame):
        h, w, _ = frame.shape
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.2, minNeighbors=5, minSize=(100, 100)
        )
        if len(faces) == 0:
            return None

        fx, fy, fw, fh = faces[0]
        nose_x = (fx + fw / 2.0) / w
        face_width = fw / float(w)

        lower_face = gray[fy + int(fh * 0.55):fy + fh, fx:fx + fw]
        mouths = self.mouth_cascade.detectMultiScale(
            lower_face, scaleFactor=1.5, minNeighbors=15
        )
        is_mouth_open = len(mouths) > 0
        cv2.rectangle(frame, (fx, fy), (fx + fw, fy + fh), (0, 255, 255), 2)
        return nose_x, face_width, is_mouth_open

    def run_face_and_liveness(self, cap):
        centered_start = None
        selfie_captured = False
        selfie_audit = None

        otp_digits = [str(random.randint(1, 9)) for _ in range(4)]
        otp_spoken = " ".join(otp_digits)
        otp_announced = False

        mouth_open = False
        syllable_count = 0
        liveness_passed = False

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            detection = self._detect_face_and_mouth(frame)

            if detection is not None:
                nose_x, face_width, currently_open = detection

                if not selfie_captured:
                    if nose_x < 0.38:
                        self.voice.speak("move_right")
                        centered_start = None
                    elif nose_x > 0.62:
                        self.voice.speak("move_left")
                        centered_start = None
                    elif face_width < 0.22:
                        self.voice.speak("move_closer")
                        centered_start = None
                    elif face_width > 0.52:
                        self.voice.speak("move_back")
                        centered_start = None
                    else:
                        self.voice.speak("face_centered", cooldown=4.0)
                        if centered_start is None:
                            centered_start = time.time()
                        elif time.time() - centered_start >= 2.0:
                            raw_selfie = f"temp_selfie_{self.user_id}.jpg"
                            cv2.imwrite(raw_selfie, frame)
                            _, selfie_audit = self.vault.encrypt_and_shred_file(
                                raw_selfie, self.user_id, "SELFIE"
                            )
                            selfie_captured = True

                elif not liveness_passed:
                    if not otp_announced:
                        self.voice.speak("liveness_prompt", cooldown=0, otp=otp_spoken)
                        otp_announced = True
                        time.sleep(2.5)

                    if currently_open and not mouth_open:
                        mouth_open = True
                    elif not currently_open and mouth_open:
                        mouth_open = False
                        syllable_count += 1

                    cv2.putText(
                        frame,
                        f"OTP: {otp_spoken} | Syllables: {syllable_count}/4",
                        (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 255, 0),
                        2
                    )

                    if syllable_count >= 4:
                        self.voice.speak("liveness_passed", cooldown=0)
                        liveness_passed = True
                        time.sleep(3.0)
                        break

            cv2.imshow("EchoKYC Global - Tier 1 AI Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        return selfie_audit, liveness_passed

    def run_id_card_scan(self, cap):
        self.voice.speak("id_scan_start", cooldown=0)
        time.sleep(3.5)

        if self.ocr_reader is None:
            self.ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)

        id_audit = None
        extracted_lines = []

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

            cv2.rectangle(frame, (100, 100), (540, 380), (255, 200, 0), 2)
            cv2.putText(
                frame,
                f"Sharpness: {int(sharpness)} (Need > 110)",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 200, 0),
                2
            )
            cv2.imshow("EchoKYC Global - Tier 1 AI Camera", frame)

            if sharpness < 110:
                self.voice.speak("id_blurry", cooldown=4.0)
            else:
                roi = frame[100:380, 100:540]
                ocr_results = self.ocr_reader.readtext(roi, detail=0)

                if len(ocr_results) >= 2:
                    raw_id = f"temp_id_{self.user_id}.jpg"
                    cv2.imwrite(raw_id, roi)
                    _, id_audit = self.vault.encrypt_and_shred_file(
                        raw_id, self.user_id, "ID_CARD"
                    )
                    extracted_lines = ocr_results
                    self.voice.speak("id_captured", cooldown=0)
                    time.sleep(3.0)
                    summary = "Detected text on your I D card: " + ", ".join(extracted_lines[:4])
                    self.voice.speak_raw(summary)
                    time.sleep(5.0)
                    break

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        return id_audit, extracted_lines

    def start_full_kyc(self):
        self.voice.speak("welcome", cooldown=0)
        time.sleep(4.0)

        db_level, noisy_mode = self.check_ambient_noise()
        cap = cv2.VideoCapture(0)

        try:
            selfie_audit, liveness_ok = self.run_face_and_liveness(cap)
            if not liveness_ok:
                return {"status": "INCOMPLETE", "noise_db": db_level}

            id_audit, id_text = self.run_id_card_scan(cap)
            qr_card = self.vault.generate_echopass_qr(self.user_id, "Verified Customer")

            return {
                "status": "VERIFIED",
                "user_id": self.user_id,
                "noise_db": db_level,
                "noisy_environment_mode": noisy_mode,
                "selfie_receipt": selfie_audit,
                "id_receipt": id_audit,
                "extracted_id_text": id_text,
                "echopass_qr": qr_card
            }
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.voice.stop()


if __name__ == "__main__":
    kyc = SmartCameraKYC(user_id="NG_USER_101", lang="en")
    report = kyc.start_full_kyc()
    print("\n=== ECHOKYC TIER 1 REPORT ===")
    print(report)
