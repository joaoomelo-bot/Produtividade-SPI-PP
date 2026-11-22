import os, hmac, hashlib
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, session
import psycopg
from psycopg.types.json import Jsonb

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.environ.get('SESSION_SECRET') or hashlib.sha256((os.environ.get('UPLOAD_KEY','')+'|'+os.environ.get('VIEW_KEY','')).encode()).digest()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SECURE=True, SESSION_COOKIE_SAMESITE='Lax', PERMANENT_SESSION_LIFETIME=3600*12, MAX_CONTENT_LENGTH=18_000_000)
DATABASE_URL = os.environ.get('DATABASE_URL','')

def guard(role):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args,**kwargs):
            current=session.get('role')
            if current != 'admin' and not (role == 'viewer' and current == 'viewer'):
                return jsonify(error='Acesso não autorizado'),403
            return fn(*args,**kwargs)
        return wrapped
    return decorator

def conn():
    if not DATABASE_URL: raise RuntimeError('DATABASE_URL não configurada')
    return psycopg.connect(DATABASE_URL)

def init(c):
    c.execute('CREATE TABLE IF NOT EXISTS daily_data (day DATE PRIMARY KEY, separation JSONB NOT NULL, conference JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())')
    c.execute('CREATE TABLE IF NOT EXISTS productivity_targets (effective_date DATE PRIMARY KEY, separation INTEGER NOT NULL, conference INTEGER NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())')
    c.execute('CREATE TABLE IF NOT EXISTS staffing_override (day DATE NOT NULL, hour INTEGER NOT NULL, operation TEXT NOT NULL, staff INTEGER NOT NULL, PRIMARY KEY(day,hour,operation))')

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
    elif user in ('indicador','visualizador','viewer') and viewer and hmac.compare_digest(password,viewer): role='viewer'
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
            targets=c.execute('SELECT effective_date,separation,conference FROM productivity_targets ORDER BY effective_date').fetchall()
            staff=c.execute('SELECT day,hour,operation,staff FROM staffing_override').fetchall()
        return jsonify(sep={str(r[0]):r[1] for r in rows},conf={str(r[0]):r[2] for r in rows},targets=[{'date':str(r[0]),'sep':r[1],'conf':r[2]} for r in targets],staff=[{'date':str(r[0]),'hour':r[1],'type':r[2],'count':r[3]} for r in staff],updated_at=max((r[3].isoformat() for r in rows),default=None))
    except Exception:
        app.logger.exception('Falha ao carregar dados')
        return jsonify(error='Banco de dados indisponível'),503

@app.post('/api/targets')
@guard('admin')
def targets():
    body=request.get_json(silent=True) or {}
    try:
        d=datetime.strptime(str(body.get('date','')),'%Y-%m-%d').date()
        sep=int(body.get('sep')); conf=int(body.get('conf'))
        if not 1<=sep<=100000 or not 1<=conf<=100000: raise ValueError()
    except (ValueError,TypeError): return jsonify(error='Data ou metas inválidas'),400
    try:
        with conn() as c:
            init(c)
            c.execute('INSERT INTO productivity_targets(effective_date,separation,conference) VALUES (%s,%s,%s) ON CONFLICT(effective_date) DO UPDATE SET separation=EXCLUDED.separation,conference=EXCLUDED.conference,updated_at=NOW()', (d,sep,conf))
        return jsonify(ok=True)
    except Exception:
        app.logger.exception('Falha ao salvar metas')
        return jsonify(error='Não foi possível salvar as metas'),503

@app.post('/api/staff')
@guard('admin')
def staff():
    body=request.get_json(silent=True) or {}
    try:
        d=datetime.strptime(str(body.get('date','')),'%Y-%m-%d').date()
        h=int(body.get('hour')); operation=str(body.get('type',''))
        count=body.get('count')
        if h not in range(24) or operation not in ('sep','conf'): raise ValueError()
        if count is not None:
            count=int(count)
            if not 0<=count<=10000: raise ValueError()
    except (ValueError,TypeError): return jsonify(error='Dados de efetivo inválidos'),400
    try:
        with conn() as c:
            init(c)
            if count is None: c.execute('DELETE FROM staffing_override WHERE day=%s AND hour=%s AND operation=%s',(d,h,operation))
            else: c.execute('INSERT INTO staffing_override(day,hour,operation,staff) VALUES (%s,%s,%s,%s) ON CONFLICT(day,hour,operation) DO UPDATE SET staff=EXCLUDED.staff',(d,h,operation,count))
        return jsonify(ok=True)
    except Exception:
        app.logger.exception('Falha ao salvar efetivo')
        return jsonify(error='Não foi possível salvar o efetivo'),503

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
