from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub

app = Flask(_name_)
CORS(app)

# PubNub
pnconfig = PNConfiguration()
pnconfig.subscribe_key = "sub-c-1e92505a-640c-4ca9-9af1-662633b2f61d"
pnconfig.publish_key = "pub-c-57a69d7b-e91e-4a3b-93ae-510b501b5535"
pnconfig.uuid = "rasp-irrigacao"
pubnub = PubNub(pnconfig)
CANAL = "irrigacao"

# DB
DB = "dados.db"

def init_db():
  conn = sqlite3.connect(DB)
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
  conn.commit()
  conn.close()

init_db()

def db_query(query, params=(), fetch=False):
  conn = sqlite3.connect(DB)
  c = conn.cursor()
  c.execute(query, params)
  if fetch:
    rows = c.fetchall()
    conn.close()
    return rows
  conn.commit()
  conn.close()
@app.route("/")
def home():
  return "<h1>Sistema de Irrigação Inteligente<h1><p>Use /api/historico ou /api/config</p>"

@app.route("/api/umidade", methods=["POST"])
def receber_umidade():
  data = request.get_json()
  valor = int(data.get("umidade"))
  db_query("INSERT INTO umidade (valor, data) VALUES (?, ?)", (valor, datetime.now().isoformat()))
  # publica em tempo real
  pubnub.publish().channel(CANAL).message({"umidade": valor}).sync()
  return jsonify({"status": "ok", "valor": valor})

@app.route("/api/historico", methods=["GET"])
def historico():
  rows = db_query("SELECT id, valor, data FROM umidade ORDER BY id DESC LIMIT 50", fetch=True)
  return jsonify([{"id": r[0], "valor": r[1], "data": r[2]} for r in rows])

@app.route("/api/config", methods=["GET", "POST"])
def config():
  if request.method == "POST":
    body = request.get_json()
    umidade_alvo = int(body.get("umidade_alvo", 600))
    intervalo = int(body.get("intervalo", 2))
    db_query("UPDATE config SET umidade_alvo=?, intervalo=? WHERE id=1", (umidade_alvo, intervalo))
    return jsonify({"status": "ok"})
  else:
    rows = db_query("SELECT umidade_alvo, intervalo FROM config WHERE id=1", fetch=True)
    umidade_alvo, intervalo = rows[0]
    return jsonify({"umidade_alvo": umidade_alvo, "intervalo": intervalo})

if _name_ == "_main_":
  app.run(host="0.0.0.0", port=5000, debug=True)