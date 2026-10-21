import cv2
import sys
import time
import threading
import queue
import csv
import os
import pykinect_azure as pykinect


from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer

# --- OSC ---
OSC_IP = "127.0.0.1"       
OSC_PORT = 5005            
OSC_ADDRESS_TAG = "/timer"  


class VideoWriterThread:
    """Thread x scrittura asincrona dei frame su disco"""
    def __init__(self, filename, fourcc, fps, size):
        self.filename = filename
        self.fourcc = fourcc
        self.fps = fps
        self.size = size
        self.frame_queue = queue.Queue(maxsize=120)
        self.writer = cv2.VideoWriter(self.filename, self.fourcc, self.fps, self.size)
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._write_loop, daemon=True)
        self.thread.start()

    def write(self, frame):
        if self.running:
            try:
                self.frame_queue.put_nowait(frame)
            except queue.Full:
                pass

    def _write_loop(self):
        while self.running or not self.frame_queue.empty():
            try:
                frame = self.frame_queue.get(timeout=0.1)
                self.writer.write(frame)
                self.frame_queue.task_done()
            except queue.Empty:
                continue
        self.writer.release()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()


class OSCReceiver:
    def __init__(self, ip, port, address_tag):
        self.ip = ip
        self.port = port
        self.address_tag = address_tag
        
        # Valore double condiviso protetto da Lock per garantire sincronia thread-safe
        self.latest_double_value = 0.0
        self.lock = threading.Lock()
        
        self.server = None
        self.server_thread = None

    def _osc_handler(self, address, *args):
        # Callback attivata alla ricezione del messaggio OSC con il tag 
        if args:
            try:
                val = float(args[0])
                with self.lock:
                    self.latest_double_value = val
            except (ValueError, TypeError):
                pass  

    def get_latest_value(self):
        with self.lock:
            return self.latest_double_value

    def start(self):
        dispatcher = Dispatcher()
        dispatcher.map(self.address_tag, self._osc_handler)
        
        self.server = ThreadingOSCUDPServer((self.ip, self.port), dispatcher)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        print(f"[OSC] Server in ascolto su {self.ip}:{self.port} per il tag '{self.address_tag}'")

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print("[OSC] Server arrestato.")


def main():
    pykinect.initialize_libraries()

    resolutions = {
        "1": {"name": "720p (1280x720)", "val": pykinect.K4A_COLOR_RESOLUTION_720P, "w": 1280, "h": 720},
        "2": {"name": "1080p (1920x1080)", "val": pykinect.K4A_COLOR_RESOLUTION_1080P, "w": 1920, "h": 1080},
        "3": {"name": "1440p (2560x1440)", "val": pykinect.K4A_COLOR_RESOLUTION_1440P, "w": 2560, "h": 1440},
        "4": {"name": "4K (3840x2160)", "val": pykinect.K4A_COLOR_RESOLUTION_2160P, "w": 3840, "h": 2160}
    }

    print("--- Seleziona la Risoluzione ---")
    for key, res in resolutions.items():
        print(f"[{key}] {res['name']}")
    
    scelta = input("Scelta (default: 1080p): ").strip()
    if scelta not in resolutions:
        scelta = "2"
        
    selected_res = resolutions[scelta]

    # Inizializzazione Server OSC
    osc_receiver = OSCReceiver(OSC_IP, OSC_PORT, OSC_ADDRESS_TAG)
    osc_receiver.start()

    # Configurazione Kinect
    device_config = pykinect.default_configuration
    device_config.color_resolution = selected_res["val"]
    device_config.camera_fps = pykinect.K4A_FRAMES_PER_SECOND_30
    device_config.depth_mode = pykinect.K4A_DEPTH_MODE_OFF

    device = pykinect.start_device(config=device_config)
    print("Azure Kinect avviata.")

    # Output file di registrazione
    output_video_filename = "registrazione_kinect.mp4"
    output_csv_filename = "registrazione_kinect_data.csv"
    
    fps = 30.0
    frame_size = (selected_res["w"], selected_res["h"])
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    # Apertura del file CSV per scrivere i dati associati ai frame
    csv_file = open(output_csv_filename, mode='w', newline='')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["Frame_ID", "OSC_Value"])  # Header del log

    # Avvio thread di scrittura video asincrono
    video_thread = VideoWriterThread(output_video_filename, fourcc, fps, frame_size)
    video_thread.start()

    print(f"\nRegistrazione avviata.")
    print(f"-> Video: {output_video_filename}")
    print(f"-> Log Dati: {output_csv_filename}")
    print("Premere 'q' sulla finestra della preview per terminare.")
    
    cv2.namedWindow('Azure Kinect (Preview)', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Azure Kinect (Preview)', 1280, 720)

    frame_counter = 0

    try:
        while True:
            capture = device.update()
            ret, color_image = capture.get_color_image()

            if not ret or color_image is None:
                continue

            # Conversione formato per OpenCV VideoWriter
            if color_image.shape[2] == 4:
                color_image_rgb = cv2.cvtColor(color_image, cv2.COLOR_BGRA2BGR)
            else:
                color_image_rgb = color_image

            # 1. Recupera l'ultimo dato double arrivato via OSC
            current_osc_value = osc_receiver.get_latest_value()

            # 2. Spedisci il frame video al thread asincrono di scrittura
            video_thread.write(color_image_rgb)
            
            # 3. Registra nel file CSV il numero di frame corrente e il rispettivo valore OSC
            csv_writer.writerow([frame_counter, current_osc_value])
            frame_counter += 1

            # Gestione preview a schermo
            if selected_res["w"] > 1920:
                preview_image = cv2.resize(color_image, (1280, 720), interpolation=cv2.INTER_NEAREST)
            else:
                preview_image = color_image

            # Sovrascriviamo a schermo in piccolo il valore OSC per verificare che stia ricevendo i dati
            cv2.putText(preview_image, f"OSC: {current_osc_value:.4f}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

            cv2.imshow('Azure Kinect (Preview)', preview_image)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        pass
    finally:
        print("\nArresto della registrazione e salvataggio file...")
        
        # Rilascio pulito di tutte le risorse
        video_thread.stop()
        csv_file.close()
        osc_receiver.stop()
        device.close()
        cv2.destroyAllWindows()
        
        print(f"Registrazione salvata con successo!")
        print(f"Processati in totale {frame_counter} frame.")

if __name__ == "__main__":
    main()