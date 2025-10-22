from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
import os
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PubNub
pnconfig = PNConfiguration()
pnconfig.subscribe_key = "sub-c-1e92505a-640c-4ca9-9af1-662633b2f61d"
pnconfig.publish_key = "pub-c-57a69d7b-e91e-4a3b-93ae-510b501b5535"
pnconfig.uuid = "rasp-irrigacao"
pubnub = PubNub(pnconfig)
CANAL = "irrigacao"

# DB (caminho absoluto relativo a este arquivo)
DB = os.path.join(os.path.dirname(__file__), "dados.db")

def init_db():
  # cria DB e aplica configurações iniciais
  with sqlite3.connect(DB, timeout=10) as conn:
    # reduz chance de locking em escrita concorrente
    try:
      conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
      # alguns ambientes podem não suportar WAL, não bloqueia
      pass
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS umidade (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        valor INTEGER NOT NULL,
        data TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS config (
        id INTEGER PRIMARY KEY CHECK (id=1),
        umidade_alvo INTEGER DEFAULT 600,
        intervalo INTEGER DEFAULT 2
    )""")
    # garante registro único de config
    c.execute("INSERT OR IGNORE INTO config (id, umidade_alvo, intervalo) VALUES (1, 600, 2)")

init_db()

def db_query(query, params=(), fetch=False):
  # usa context manager para garantir fechamento
  with sqlite3.connect(DB, timeout=10) as conn:
    c = conn.cursor()
    c.execute(query, params)
    if fetch:
      return c.fetchall()
    conn.commit()
@app.route("/")
def home():
  return "<h1>Sistema de Irrigação Inteligente</h1><p>Use /api/historico ou /api/config</p>"

@app.route("/api/umidade", methods=["POST"])
def receber_umidade():
  data = request.get_json(silent=True)
  if not data:
    return jsonify({"error": "JSON body required"}), 400

  raw = data.get("umidade")
  if raw is None:
    return jsonify({"error": "campo 'umidade' ausente"}), 400

  try:
    valor = int(raw)
  except (TypeError, ValueError):
    return jsonify({"error": "campo 'umidade' deve ser um inteiro"}), 400

  # salva no banco
  try:
    db_query("INSERT INTO umidade (valor, data) VALUES (?, ?)", (valor, datetime.now().isoformat()))
  except Exception as e:
    logger.exception("Erro ao salvar umidade no banco")
    return jsonify({"error": "erro ao salvar no banco"}), 500

  # publica em tempo real (não falha a API se PubNub tiver problema)
  try:
    pubnub.publish().channel(CANAL).message({"umidade": valor}).sync()
  except Exception:
    logger.exception("Falha ao publicar no PubNub")

  return jsonify({"status": "ok", "valor": valor})

@app.route("/api/historico", methods=["GET"])
def historico():
  rows = db_query("SELECT id, valor, data FROM umidade ORDER BY id DESC LIMIT 50", fetch=True)
  return jsonify([{"id": r[0], "valor": r[1], "data": r[2]} for r in rows])

@app.route("/api/config", methods=["GET", "POST"])
def config():
  if request.method == "POST":
    body = request.get_json(silent=True)
    if not body:
      return jsonify({"error": "JSON body required"}), 400

    try:
      umidade_alvo = int(body.get("umidade_alvo", 600))
      intervalo = int(body.get("intervalo", 2))
    except (TypeError, ValueError):
      return jsonify({"error": "umidade_alvo e intervalo devem ser inteiros"}), 400

    try:
      db_query("UPDATE config SET umidade_alvo=?, intervalo=? WHERE id=1", (umidade_alvo, intervalo))
    except Exception:
      logger.exception("Erro ao atualizar config")
      return jsonify({"error": "erro ao atualizar config"}), 500

    return jsonify({"status": "ok"})
  else:
    rows = db_query("SELECT umidade_alvo, intervalo FROM config WHERE id=1", fetch=True)
    if not rows:
      # retorna valores padrão se algo der errado
      return jsonify({"umidade_alvo": 600, "intervalo": 2})

    umidade_alvo, intervalo = rows[0]
    return jsonify({"umidade_alvo": umidade_alvo, "intervalo": intervalo})

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)