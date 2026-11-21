import os, hmac, json, hashlib
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, session
import psycopg
from psycopg.types.json import Jsonb

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.environ.get('SESSION_SECRET') or hashlib.sha256((os.environ.get('UPLOAD_KEY','')+'|'+os.environ.get('VIEW_KEY','')).encode()).digest()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SECURE=True, SESSION_COOKIE_SAMESITE='Lax', PERMANENT_SESSION_LIFETIME=3600*12, MAX_CONTENT_LENGTH=18_000_000)
DATABASE_URL=os.environ.get('DATABASE_URL','')

def allowed(role):
    return session.get('role') == 'admin' or (role == 'viewer' and session.get('role') == 'viewer')

def guard(role):
    def deco(fn):
        @wraps(fn)
        def inner(*args,**kwargs):
            if not allowed(role): return jsonify(error='Acesso não autorizado'),401
            return fn(*args,**kwargs)
        return inner
    return deco

def conn():
    if not DATABASE_URL: raise RuntimeError('DATABASE_URL não configurada')
    return psycopg.connect(DATABASE_URL)

def init(c):
    c.execute('CREATE TABLE IF NOT EXISTS daily_data (day DATE PRIMARY KEY, separation JSONB NOT NULL, conference JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())')

@app.get('/')
def home(): return send_from_directory('.', 'index.html')

@app.post('/api/login')
def login():
    body=request.get_json(silent=True) or {}
    user=str(body.get('username','')).strip().lower()
    password=str(body.get('password',''))
    admin=os.environ.get('UPLOAD_KEY','')
    viewer=os.environ.get('VIEW_KEY','')
    role=None
    if user in ('admin','administrador') and admin and hmac.compare_digest(password,admin): role='admin'
    elif user in ('visualizador','viewer') and viewer and hmac.compare_digest(password,viewer): role='viewer'
    if not role: return jsonify(error='Usuário ou senha inválidos'),401
    session.clear();session['role']=role;session.permanent=True
    return jsonify(role=role)

@app.post('/api/logout')
def logout(): session.clear();return jsonify(ok=True)

@app.get('/api/me')
def me(): return jsonify(role=session.get('role'))

@app.get('/api/data')
@guard('viewer')
def data():
    try:
        with conn() as c:
            init(c)
            rows=c.execute('SELECT day,separation,conference,updated_at FROM daily_data ORDER BY day DESC LIMIT 35').fetchall()
        return jsonify(sep={str(r[0]):r[1] for r in rows},conf={str(r[0]):r[2] for r in rows},updated_at=max((r[3].isoformat() for r in rows),default=None))
    except Exception:
        app.logger.exception('Falha ao carregar dados')
        return jsonify(error='Banco de dados indisponível'),503

@app.post('/api/import')
@guard('admin')
def upload():
    payload=request.get_json(silent=True)
    if not isinstance(payload,dict): return jsonify(error='Arquivo inválido'),400
    sep,conf=payload.get('sep'),payload.get('conf')
    if not isinstance(sep,dict) or not isinstance(conf,dict): return jsonify(error='Bases ausentes'),400
    days=set(sep)|set(conf)
    if not days or len(days)>35: return jsonify(error='Quantidade de datas inválida'),400
    try:
        with conn() as c:
            init(c)
            for d in days:
                datetime.strptime(d,'%Y-%m-%d')
                a,b=sep.get(d,[]),conf.get(d,[])
                if not isinstance(a,list) or not isinstance(b,list) or len(a)+len(b)>200000: return jsonify(error='Dados inválidos'),400
                c.execute('INSERT INTO daily_data(day,separation,conference) VALUES (%s,%s,%s) ON CONFLICT(day) DO UPDATE SET separation=EXCLUDED.separation,conference=EXCLUDED.conference,updated_at=NOW()', (d,Jsonb(a),Jsonb(b)))
        return jsonify(ok=True,days=sorted(days))
    except Exception:
        app.logger.exception('Falha na importação')
        return jsonify(error='Não foi possível salvar no banco'),503

@app.get('/health')
def health(): return jsonify(ok=True)
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT','10000')))
