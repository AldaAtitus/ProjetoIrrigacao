import serial
import requests
import time

# Configurações da porta serial
ARDUINO_PORT = "/dev/ttyACM0"  # ou /dev/ttyUSB0 dependendo do Arduino
BAUD = 9600

# Endpoints do backend Flask (ajuste IP se rodar em outra máquina)
BACKEND_BASE = "http://192.168.103.155:5000"
UMIDADE_ENDPOINT = f"{BACKEND_BASE}/api/umidade"
CONFIG_ENDPOINT = f"{BACKEND_BASE}/api/config"

# Inicializa conexão serial
ser = serial.Serial(ARDUINO_PORT, BAUD, timeout=1)
time.sleep(2)  # tempo para estabilizar a porta

def get_config():
    """Busca configuração atual do backend Flask"""
    try:
        r = requests.get(CONFIG_ENDPOINT, timeout=3)
        data = r.json()
        umidade_alvo = data.get("umidade_alvo", 600)
        intervalo = data.get("intervalo", 2)
        return umidade_alvo, intervalo
    except Exception as e:
        print("Erro ao buscar config:", e)
        return 600, 2  # valores padrão

def enviar_config(umidade_alvo, intervalo):
    """Envia parâmetros para o Arduino via serial"""
    try:
        ser.write(f"ALVO:{umidade_alvo}\n".encode())
        ser.write(f"INTERVALO:{intervalo}\n".encode())
    except Exception as e:
        print("Erro ao enviar config para Arduino:", e)

while True:
    # Busca config no backend
    umidade_alvo, intervalo = get_config()
    enviar_config(umidade_alvo, intervalo)
    print(f"Config atual -> alvo: {umidade_alvo}, intervalo: {intervalo}s")

    # Lê dados do Arduino
    if ser.in_waiting > 0:
        try:
            leitura = ser.readline().decode().strip()
            if leitura.isdigit():
                umidade = int(leitura)
                print("Umidade lida:", umidade)
                # Envia leitura para o backend
                resp = requests.post(UMIDADE_ENDPOINT, json={"umidade": umidade}, timeout=3)
                print("POST status:", resp.status_code)
        except Exception as e:
            print("Erro ao processar leitura:", e)

    # Aguarda o intervalo definido no backend
    time.sleep(intervalo)