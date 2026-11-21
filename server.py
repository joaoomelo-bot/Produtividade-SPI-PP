import os, json, hmac
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory
import psycopg

app=Flask(__name__,static_folder='.',static_url_path='')
DATABASE_URL=os.environ.get('DATABASE_URL','')
UPLOAD_KEY=os.environ.get('UPLOAD_KEY','')
VIEW_KEY=os.environ.get('VIEW_KEY','')

def authorized(secret):
    provided=request.headers.get('X-Access-Key','')
    return bool(secret) and hmac.compare_digest(provided,secret)

def conn():
    if not DATABASE_URL: raise RuntimeError('DATABASE_URL não configurada')
    return psycopg.connect(DATABASE_URL)

def init(c):
    c.execute('CREATE TABLE IF NOT EXISTS daily_data (day DATE PRIMARY KEY, separation JSONB NOT NULL, conference JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())')

@app.get('/')
def index(): return send_from_directory('.', 'index.html')

@app.get('/api/data')
def data():
    if not authorized(VIEW_KEY): return jsonify(error='Acesso não autorizado'),401
    try:
        with conn() as c:
            init(c)
            rows=c.execute('SELECT day, separation, conference, updated_at FROM daily_data ORDER BY day DESC LIMIT 35').fetchall()
        return jsonify(sep={str(r[0]):r[1] for r in rows},conf={str(r[0]):r[2] for r in rows},updated_at=max((r[3].isoformat() for r in rows),default=None))
    except Exception:
        app.logger.exception('Falha ao carregar dados')
        return jsonify(error='Banco de dados indisponível'),503

@app.post('/api/import')
def upload():
    if not authorized(UPLOAD_KEY): return jsonify(error='Importação não autorizada'),401
    payload=request.get_json(silent=True)
    if not isinstance(payload,dict): return jsonify(error='JSON inválido'),400
    sep,conf=payload.get('sep'),payload.get('conf')
    if not isinstance(sep,dict) or not isinstance(conf,dict): return jsonify(error='Bases ausentes'),400
    days=set(sep)|set(conf)
    if not days or len(days)>35: return jsonify(error='Quantidade de datas inválida'),400
    if request.content_length and request.content_length>18_000_000: return jsonify(error='Arquivo muito grande'),413
    try:
        with conn() as c:
            init(c)
            for d in days:
                datetime.strptime(d,'%Y-%m-%d')
                a,b=sep.get(d,[]),conf.get(d,[])
                if not isinstance(a,list) or not isinstance(b,list) or len(a)+len(b)>200000: return jsonify(error='Dados inválidos'),400
                c.execute('INSERT INTO daily_data(day,separation,conference) VALUES (%s,%s,%s) ON CONFLICT(day) DO UPDATE SET separation=EXCLUDED.separation, conference=EXCLUDED.conference, updated_at=NOW()', (d,psycopg.types.json.Jsonb(a),psycopg.types.json.Jsonb(b)))
        return jsonify(ok=True,days=sorted(days))
    except Exception:
        app.logger.exception('Falha na importação')
        return jsonify(error='Não foi possível salvar no banco'),503

@app.get('/health')
def health(): return jsonify(ok=True)

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT','10000')))
