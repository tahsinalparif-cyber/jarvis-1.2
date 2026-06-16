import os
import sys
# .exe olduğunda klasör yolunu sabitleme kodu
if getattr(sys, 'frozen', False):
    DOKUMAN_YOLU = os.path.dirname(sys.executable)
else:
    DOKUMAN_YOLU = os.path.dirname(os.path.abspath(__file__))

HAFIZA_FILE = os.path.join(DOKUMAN_YOLU, "hafiza.txt")
KEY_FILE_PATH = os.path.join(DOKUMAN_YOLU, "jarvis_api_key.txt")
import time
import asyncio
import threading
import tempfile
import glob
import platform
import psutil
import requests
from bs4 import BeautifulSoup
import datetime
import wikipedia
wikipedia.set_lang("tr")

# Arayüz kütüphaneleri
import tkinter as tk
from tkinter import ttk, messagebox

# Gerekli arka plan kütüphaneleri
import speech_recognition as sr
import keyboard
import pyaudio
import edge_tts
import pygame

# Groq kütüphanesi
from groq import Groq

# Global değişkenler
secilen_mikrofon_id = None
mikrofon_aktif = True
son_basim = 0
client = None

# Yeni eklenen hafıza değişkenleri
sohbet_gecmisi = [] 
HAFIZA_FILE = "hafiza.txt"

def hafizayi_oku():
    dosya_yolu = os.path.join(DOKUMAN_YOLU, "hafiza.txt")
    if os.path.exists(dosya_yolu):
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            return f.read()
    return "Henüz bir bilgi kaydedilmemiş."

KEY_FILE_PATH = os.path.join(os.path.expanduser("~"), "jarvis_api_key.txt")

# Pygame ses mikserini başlatıyoruz kanka
pygame.mixer.init()

# 🔊 KİLİTLENMEYEN BENZERSİZ SES MOTORU
def ses_calici_thread(yazi, log_callback):
    """Her istek için benzersiz dosya oluşturarak Windows erişim hatasını çözen motor kanka"""
    # Dosya isminin sonuna anlık milisaniyeyi ekliyoruz ki asla çakışmasın kanka
    zaman_damgasi = int(time.time() * 1000)
    ses_dosyasi = os.path.join(tempfile.gettempdir(), f"jarvis_voice_{zaman_damgasi}.mp3")
    
    # Eğer o an bir şey çalıyorsa hemen durdur ve müziği boşa çıkar kanka
    try:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
    except:
        pass

    async def speak_async():
        communicate = edge_tts.Communicate(yazi, "tr-TR-EmelNeural")
        await communicate.save(ses_dosyasi)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(speak_async())
        loop.close()

        if os.path.exists(ses_dosyasi):
            if log_callback:
                log_callback(f"🤖 J.A.R.V.İ.S: {yazi}")
            
            pygame.mixer.music.load(ses_dosyasi)
            pygame.mixer.music.play()
            
            # 🧹 Arka planda biriken eski jarvis mp3 dosyalarını temizleme operasyonu
            threading.Thread(target=eski_sesleri_temizle, args=(ses_dosyasi,), daemon=True).start()

    except Exception as e:
        if log_callback: log_callback(f"⚠️ Ses Hatası: {e}")

def eski_sesleri_temizle(su_anki_dosya):
    """Kullanılmayan eski ses dosyalarını bilgisayarı yormasın diye arkadan siler kanka"""
    time.sleep(2) # Çalmaya başlaması için kısa bir süre tanıyalım
    klasor = tempfile.gettempdir()
    for dosya in glob.glob(os.path.join(klasor, "jarvis_voice_*.mp3")):
        # Şu an çalan dosya haricindeki kilitlenmesi bitmiş eski dosyaları sil kanka
        if dosya != su_anki_dosya:
            try:
                os.remove(dosya)
            except:
                pass # Hala kilitliyse zorlama, bir sonraki turda silinir

def sesli_konus(yazi, log_callback=None):
    threading.Thread(target=ses_calici_thread, args=(yazi, log_callback), daemon=True).start()

# 🧠 SYSTEM INSTRUCTION
SYSTEM_INSTRUCTION = """
Sen kullanıcının bilgisayarında çalışan, J.A.R.V.İ.S adında sesli bir AI asistansın.
Kurallar:
1. Sadece samimi bir arkadaş gibi, sıcak ve doğal konuş (efendim hitabını kullan başka şekilde hitap et derse dediği şekilde hitap et).
2. Cevapları asla çok uzun tutma, sesli okunduğu için maksimum 1-2-3 kısa cümle olsun.
3. sana sorulan her soruya cevap ver 
4. Bilmediğin bir soruda bilmediğini dile getir
5. seni yapan kişi icomnes53 asıl adı Tahsin Çavuşoğlu 
6. hatalı bir durumda hata vemeden önce konuyu değiştir"""

# 🖥️ ULTRA MİNİMAL HUD ARAYÜZÜ
class JarvisMinimalHUD:
    def __init__(self, root):
        self.root = root
        self.root.title("JARVIS")
        
        self.root.geometry("280x280")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#0b0f19")
        self.root.resizable(False, False)
        
        self.check_api_key()
        
    def check_api_key(self):
        if os.path.exists(KEY_FILE_PATH):
            with open(KEY_FILE_PATH, "r", encoding="utf-8") as f:
                saved_key = f.read().strip()
            if saved_key:
                self.start_jarvis_engine(saved_key)
                return
        self.create_login_widgets()

    def create_login_widgets(self):
        self.clear_window()
        tk.Label(self.root, text="⚡ JARVIS GROQ LOGIN ⚡", font=("Segoe UI", 10, "bold"), bg="#0b0f19", fg="#00f0ff").pack(pady=20)
        tk.Label(self.root, text="Groq API Key Yapıştır Kanka (gsk_...):", font=("Segoe UI", 9), bg="#0b0f19", fg="#8a95a5").pack(pady=5)
        
        self.entry_key = tk.Entry(self.root, width=26, bg="#141a29", fg="#e1e7ed", insertbackground="#00f0ff", font=("Segoe UI", 10), bd=0, highlightthickness=1, highlightbackground="#1f2d3d")
        self.entry_key.pack(pady=10, ipady=4)
        
        tk.Button(self.root, text="BAŞLAT 🚀", bg="#00ff66", fg="#0f141c", font=("Segoe UI", 10, "bold"), width=12, bd=0, cursor="hand2", command=self.save_and_activate_key).pack(pady=15)

    def save_and_activate_key(self):
        input_key = self.entry_key.get().strip()
        if not input_key:
            messagebox.showwarning("Uyarı", "Anahtar boş olamaz kanka.")
            return
        try:
            with open(KEY_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(input_key)
            self.start_jarvis_engine(input_key)
        except Exception as e:
            messagebox.showerror("Hata", f"Yazma hatası: {e}")

    def start_jarvis_engine(self, api_key):
        global client
        try:
            client = Groq(api_key=api_key)
        except Exception as e:
            messagebox.showerror("Hata", f"Groq API Hatası: {e}")
            if os.path.exists(KEY_FILE_PATH): os.remove(KEY_FILE_PATH)
            self.create_login_widgets()
            return
            
        self.clear_window()
        self.create_hud_widgets()
        
        self.running = True
        self.loop_thread = threading.Thread(target=self.jarvis_ana_dongu, daemon=True)
        
        self.p = pyaudio.PyAudio()
        self.taraci_mikrofonlar()
        keyboard.add_hotkey('m', self.tetikle_mute_klavye)

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def create_hud_widgets(self):
        self.mic_box = ttk.Combobox(self.root, width=28, state="readonly", font=("Segoe UI", 9))
        self.mic_box.pack(pady=6)
        self.mic_box.bind("<<ComboboxSelected>>", self.mikrofon_degistir)
        
        self.txt_logs = tk.Text(self.root, height=5, width=32, bg="#111625", fg="#d1d9e6", insertbackground="white", font=("Consolas", 9), bd=0, highlightthickness=1, highlightbackground="#1c2336")
        self.txt_logs.pack(pady=4)
        self.txt_logs.config(state="disabled")
        
        self.btn_mute = tk.Button(self.root, text="🎙️ MİKROFON: AKTİF", bg="#00ff66", fg="#0b0f19", font=("Segoe UI", 9, "bold"), width=24, bd=0, cursor="hand2", command=self.tetikle_mute_click)
        self.btn_mute.pack(pady=6)
        
        self.entry_text = tk.Entry(self.root, width=26, bg="#111625", fg="#e1e7ed", insertbackground="#00f0ff", font=("Segoe UI", 10), bd=0, highlightthickness=1, highlightbackground="#1c2336")
        self.entry_text.pack(pady=4, ipady=4)
        self.entry_text.bind("<Return>", self.elle_yazi_gonder)
        
        self.lbl_info = tk.Label(self.root, text="Kısayol: 'M' | Yaz ve Enter'a bas", font=("Segoe UI", 8), bg="#0b0f19", fg="#525f78")
        self.lbl_info.pack(pady=4)

    def log_yaz(self, mesaj):
        self.txt_logs.config(state="normal")
        self.txt_logs.insert(tk.END, mesaj + "\n")
        self.txt_logs.see(tk.END)
        self.txt_logs.config(state="disabled")

    def taraci_mikrofonlar(self):
        device_count = self.p.get_device_count()
        self.gecerli_mics = {}
        liste = []
        sayac = 0
        for i in range(device_count):
            info = self.p.get_device_info_by_index(i)
            if info.get('maxInputChannels') > 0:
                name = info.get('name')
                try: name = name.encode('utf-8', errors='ignore').decode('utf-8')
                except: pass
                self.gecerli_mics[sayac] = i
                liste.append(f"[{sayac}] {name[:18]}")
                sayac += 1
        self.mic_box['values'] = liste
        if liste:
            self.mic_box.current(0)
            self.mikrofon_degistir(None)
            
    def mikrofon_degistir(self, event):
        global secilen_mikrofon_id
        index = self.mic_box.current()
        if index != -1:
            secilen_mikrofon_id = self.gecerli_mics[index]
            self.log_yaz(f"⚙️ Mic ID {secilen_mikrofon_id} seçildi.")
            if not self.loop_thread.is_alive():
                self.loop_thread.start()

    def tetikle_mute_click(self):
        global mikrofon_aktif, son_basim
        son_basim = time.time()
        mikrofon_aktif = not mikrofon_aktif
        self.arayuz_mute_guncelle()

    def tetikle_mute_klavye(self):
        global mikrofon_aktif, son_basim
        su_an = time.time()
        if su_an - son_basim < 0.5: return  
        son_basim = su_an
        mikrofon_aktif = not mikrofon_aktif
        self.arayuz_mute_guncelle()

    def arayuz_mute_guncelle(self):
        if mikrofon_aktif:
            self.btn_mute.config(text="🎙️ MİKROFON: AKTİF", bg="#00ff66", fg="#0b0f19")
            self.log_yaz("🔊 Dinleme aktif.")
        else:
            self.btn_mute.config(text="🔇 MİKROFON: KAPALI", bg="#ff3366", fg="#ffffff")
            self.log_yaz("🔇 Dinleme durduruldu.")

    def elle_yazi_gonder(self, event):
        yazi = self.entry_text.get().strip()
        if not yazi: return
        self.entry_text.delete(0, tk.END)
        self.log_yaz(f"🗣️ Sen: {yazi}")
        threading.Thread(target=self.jarvis_cevap_uret, args=(yazi,), daemon=True).start()

    def modern_onay_kutusu(self, baslik, mesaj):
        onay_penceresi = tk.Toplevel(self.root)
        onay_penceresi.title(baslik)
        onay_penceresi.geometry("200x100")
        onay_penceresi.configure(bg="#111625")
        onay_penceresi.attributes("-topmost", True)
        onay_penceresi.resizable(False, False)
        
        x = self.root.winfo_x() + 40
        y = self.root.winfo_y() + 80
        onay_penceresi.geometry(f"+{x}+{y}")
        
        lbl = tk.Label(onay_penceresi, text=mesaj, bg="#111625", fg="#d1d9e6", font=("Segoe UI", 9), wraplength=160)
        lbl.pack(pady=10)
        
        self.onay_sonuc = False
        def secim_yap(deger):
            self.onay_sonuc = deger
            onay_penceresi.destroy()
            
        btn_frame = tk.Frame(onay_penceresi, bg="#111625")
        btn_frame.pack()
        tk.Button(btn_frame, text="Evet", bg="#00ff66", fg="#0b0f19", font=("Segoe UI", 9, "bold"), width=6, bd=0, command=lambda: secim_yap(True)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Hayır", bg="#ff3366", fg="#ffffff", font=("Segoe UI", 9, "bold"), width=6, bd=0, command=lambda: secim_yap(False)).pack(side=tk.RIGHT, padx=5)
        
        self.root.wait_window(onay_penceresi)
        return self.onay_sonuc

    def jarvis_cevap_uret(self, istek):
        global client, sohbet_gecmisi

        # 1. Kaydetme Kontrolü (Garantili Yazma)
        if "kaydet" in istek.lower():
            # KEY dosyasıyla aynı yolu kullanıyoruz
            dosya_yolu = os.path.join(DOKUMAN_YOLU, "hafiza.txt")
            
            with open(dosya_yolu, "a", encoding="utf-8") as f:
                # "kaydet" kelimesini temizleyip kalan kısmı kaydediyoruz
                temiz_metin = istek.lower().replace("kaydet", "").strip()
                f.write(temiz_metin + "\n")
                f.flush()
            
            sesli_konus("Not aldım efendim.", self.log_yaz)
            return

        # Kapatma bloğu
        if "iptal" in istek.lower() or "exit" in istek.lower() or "kapat" in istek.lower():
            if self.modern_onay_kutusu("Onay", "Kapatılsın mı?"):
                sesli_konus("Görüşürüz efendim.", self.log_yaz)
                time.sleep(1.5) # Vedayı tamamlaması için süre veriyoruz
                os._exit(0) # Programı zorla ve anında kapatır
            else:
                self.log_yaz("⚙️ İptal edildi.")
                return

        # Yerel sorgular (AI'ya gerek yok)
        if "saat kaç" in istek.lower() or "saat nedir" in istek.lower():
            zaman = saati_ogren()
            sesli_konus(f"Şu an saat {zaman}, efendim.", self.log_yaz)
            return

        if "durumun nasıl" in istek.lower() or "sistem durumu" in istek.lower():
            bilgi = sistem_durumu_ogren()
            sesli_konus(bilgi, self.log_yaz)
            return

        if "bugün günlerden ne" in istek.lower() or "bugün ne günü" in istek.lower():
            gun = gunu_ogren()
            sesli_konus(f"Bugün günlerden {gun}, efendim.", self.log_yaz)
            return

        if "nedir" in istek.lower() or "kimdir" in istek.lower():
            konu = istek.lower().replace("nedir", "").replace("kimdir", "").strip()
            sesli_konus(f"{konu} hakkında araştırma yapıyorum, lütfen bekleyin.", self.log_yaz)
            bilgi = wikipedia_arastir(konu)
            sesli_konus(bilgi, self.log_yaz)
            return

        # 2. Sohbeti geçmişe ekle
        sohbet_gecmisi.append({"role": "user", "content": istek})
        if len(sohbet_gecmisi) > 80: sohbet_gecmisi.pop(0)
        
        # 3. BURASI KRİTİK: Bilgiyi ve sistemi birleştir
        bilgi = hafizayi_oku()
        sistem_talimati = f"{SYSTEM_INSTRUCTION}\nKullanıcı hakkında bilgiler: {bilgi}"
        
        # Geçmişi her zaman sistem talimatının altına ekliyoruz
        messages = [{"role": "system", "content": sistem_talimati}] + sohbet_gecmisi[-40:]

        try:
            chat_completion = client.chat.completions.create(
                messages=messages,
                model="llama-3.3-70b-versatile",
                temperature=0.3, # Sıcaklığı düşürdük ki daha kararlı cevap versin
                max_tokens=150
            )
            cevap = chat_completion.choices[0].message.content
            sohbet_gecmisi.append({"role": "assistant", "content": cevap})
            sesli_konus(cevap, self.log_yaz)
        except Exception as e:
            self.log_yaz(f"❌ Hata: {e}")

    def jarvis_ana_dongu(self):
        global mikrofon_aktif, secilen_mikrofon_id
        r = sr.Recognizer()
        r.dynamic_energy_threshold = True
        r.energy_threshold = 1750   
        r.pause_threshold = 1.2     
        r.non_speaking_duration = 0.5
        
        self.root.after(800, lambda: sesli_konus("jarvis hazır efendim.", self.log_yaz))

        while self.running:
            if not mikrofon_aktif or secilen_mikrofon_id is None:
                time.sleep(0.3)
                continue

            with sr.Microphone(device_index=secilen_mikrofon_id) as source:
                r.adjust_for_ambient_noise(source, duration=0.4)
                try:
                    audio = r.listen(source, timeout=4, phrase_time_limit=10)
                except sr.WaitTimeoutError:
                    continue
                
            if not mikrofon_aktif: continue
            
            try:
                istek = r.recognize_google(audio, language="tr-TR")
                if istek.strip() and len(istek.strip()) >= 4:
                    self.log_yaz(f"🗣️ Sen: {istek}")
                    self.jarvis_cevap_uret(istek)
            except sr.UnknownValueError:
                pass
            except Exception as e:
                self.log_yaz(f"⚠️ Hata: {e}")
def saati_ogren():
    return datetime.datetime.now().strftime("%H:%M")

def sistem_durumu_ogren():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    os_bilgi = platform.system()
    return f"Sistemim {os_bilgi} üzerinde çalışıyor. İşlemci kullanımı yüzde {cpu}, bellek kullanımı ise yüzde {ram} seviyesinde efendim."

def gunu_ogren():
    return datetime.datetime.now().strftime("%A")

def wikipedia_arastir(sorgu):
    try:
        ozet = wikipedia.summary(sorgu, sentences=2)
        return ozet
    except:
        return "Üzgünüm, bu konuda yeterli bilgi bulamadım efendim."
 
if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = JarvisMinimalHUD(root)
        root.mainloop()
    except Exception as e:
        print(f"Hata çıktı kanka: {e}")
        input()