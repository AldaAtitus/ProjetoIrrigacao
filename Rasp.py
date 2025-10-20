import serial
import requests
import time

ARDUINO_PORT = "/dev/ttyACM0"  # ajuste para /dev/ttyUSB0 se necessário
BAUD = 9600
BACKEND_BASE = "http://localhost:5000"
UMIDADE_ENDPOINT = f"{BACKEND_BASE}/api/umidade"
CONFIG_ENDPOINT = f"{BACKEND_BASE}/api/config"

ser = serial.Serial(ARDUINO_PORT, BAUD, timeout=1)
time.sleep(2)  # estabilizar serial

def get_config():
  try:
    r = requests.get(CONFIG_ENDPOINT, timeout=3)
    data = r.json()
    return data.get("intervalo", 2)  # segundos
  except Exception:
    return 2

while True:
  intervalo = get_config()
  if ser.in_waiting > 0:
    try:
      leitura = ser.readline().decode().strip()
      if leitura.isdigit():
        umidade = int(leitura)
        print("Umidade:", umidade)
        requests.post(UMIDADE_ENDPOINT, json={"umidade": umidade}, timeout=3)
    except Exception as e:
      print("Erro:", e)
  time.sleep(intervalo)
