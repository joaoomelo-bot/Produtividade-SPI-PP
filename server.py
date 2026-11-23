import os,hmac,hashlib
from datetime import date
from functools import wraps
from flask import Flask,request,jsonify,send_from_directory,session
import psycopg
from psycopg.types.json import Jsonb
app=Flask(__name__,static_folder=None)
app.secret_key=os.getenv('SESSION_SECRET') or hashlib.sha256((os.getenv('UPLOAD_KEY','')+'|'+os.getenv('VIEW_KEY','')).encode()).digest()
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SECURE=True,SESSION_COOKIE_SAMESITE='Lax',MAX_CONTENT_LENGTH=18000000)
def db():return psycopg.connect(os.environ['DATABASE_URL'])
def init(c):
 c.execute('CREATE TABLE IF NOT EXISTS daily_data (day DATE PRIMARY KEY, separation JSONB NOT NULL, conference JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())')
 c.execute('CREATE TABLE IF NOT EXISTS productivity_targets (effective_date DATE PRIMARY KEY, separation INTEGER NOT NULL, conference INTEGER NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())')
 c.execute('CREATE TABLE IF NOT EXISTS staffing_override (day DATE NOT NULL, hour INTEGER NOT NULL, operation TEXT NOT NULL, staff INTEGER NOT NULL, PRIMARY KEY(day,hour,operation))')
 c.execute('CREATE TABLE IF NOT EXISTS staffing_daily (day DATE NOT NULL, operation TEXT NOT NULL, staff INTEGER NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), PRIMARY KEY(day,operation))')
def auth(admin=False):
 def deco(fn):
  @wraps(fn)
  def wrapped(*a,**kw):
   if session.get('role') not in (('admin',) if admin else ('admin','viewer')):return jsonify(error='Acesso não autorizado'),403
   return fn(*a,**kw)
  return wrapped
 return deco
@app.get('/')
def home():return send_from_directory(app.root_path,'index.html')
@app.get('/<name>')
def logo(name):
 if name not in ('gruposc.png','panpharma.png'):return '',404
 return send_from_directory(app.root_path,name)
@app.post('/api/viewer')
def viewer():
 if session.get('role')!='admin':session['role']='viewer'
 return jsonify(role=session['role'])
@app.post('/api/login')
def login():
 p=request.get_json(silent=True) or {};pwd=str(p.get('password',''));key=os.getenv('UPLOAD_KEY')
 if not key or not hmac.compare_digest(pwd,key):return jsonify(error='Senha inválida'),401
 session.clear();session['role']='admin';return jsonify(role='admin')
@app.get('/api/me')
def me():return jsonify(role=session.get('role'))
@app.post('/api/logout')
def logout():session.clear();return jsonify(ok=True)
@app.get('/api/data')
@auth()
def data():
 with db() as c:
  init(c);rows=c.execute('SELECT day,separation,conference,updated_at FROM daily_data ORDER BY day DESC LIMIT 35').fetchall();targets=c.execute('SELECT effective_date,separation,conference FROM productivity_targets ORDER BY effective_date').fetchall();daily=c.execute('SELECT day,operation,staff FROM staffing_daily').fetchall();hourly=c.execute('SELECT day,hour,operation,staff FROM staffing_override').fetchall()
 return jsonify(sep={str(x[0]):x[1] for x in rows},conf={str(x[0]):x[2] for x in rows},targets=[dict(date=str(x[0]),sep=x[1],conf=x[2]) for x in targets],daily_staff=[dict(date=str(x[0]),type=x[1],count=x[2]) for x in daily],staff=[dict(date=str(x[0]),hour=x[1],type=x[2],count=x[3]) for x in hourly],updated_at=max((x[3].isoformat() for x in rows),default=None))
@app.post('/api/targets')
@auth(True)
def targets():
 p=request.get_json(silent=True) or {}
 try:
  d=date.fromisoformat(p['date']);a=int(p['sep']);b=int(p['conf']);assert 1<=a<=100000 and 1<=b<=100000
 except (ValueError,KeyError,TypeError,AssertionError):return jsonify(error='Metas inválidas'),400
 with db() as c:
  init(c);c.execute('INSERT INTO productivity_targets(effective_date,separation,conference) VALUES (%s,%s,%s) ON CONFLICT(effective_date) DO UPDATE SET separation=EXCLUDED.separation,conference=EXCLUDED.conference,updated_at=NOW()',(d,a,b))
 return jsonify(ok=True)
@app.post('/api/staff')
@auth(True)
def staff():
 p=request.get_json(silent=True) or {}
 try:
  d=date.fromisoformat(p['date']);t=p['type'];n=p['count'];assert t in ('sep','conf') and (n is None or isinstance(n,int) and 0<=n<=10000)
 except (ValueError,KeyError,TypeError,AssertionError):return jsonify(error='HC inválido'),400
 with db() as c:
  init(c)
  if n is None:c.execute('DELETE FROM staffing_daily WHERE day=%s AND operation=%s',(d,t))
  else:c.execute('INSERT INTO staffing_daily(day,operation,staff) VALUES (%s,%s,%s) ON CONFLICT(day,operation) DO UPDATE SET staff=EXCLUDED.staff,updated_at=NOW()',(d,t,n))
 return jsonify(ok=True)
@app.post('/api/import')
@auth(True)
def upload():
 p=request.get_json(silent=True) or {};sep=p.get('sep');conf=p.get('conf');staffing=p.get('staffing')
 if not all(isinstance(x,dict) for x in (sep,conf,staffing)):return jsonify(error='Bases e HC fixo obrigatórios'),400
 days=set(sep)|set(conf)
 if not days or len(days)>35:return jsonify(error='Datas inválidas'),400
 try:
  with db() as c:
   init(c)
   for d in sorted(days):
    dt=date.fromisoformat(d);a=sep.get(d,[]);b=conf.get(d,[]);hc=staffing[d];sc=int(hc['sep']);cc=int(hc['conf'])
    if not isinstance(a,list) or not isinstance(b,list) or len(a)+len(b)>200000 or not 0<=sc<=10000 or not 0<=cc<=10000:raise ValueError('Base ou HC inválido')
    for t,n in [('sep',sc),('conf',cc)]:c.execute('INSERT INTO staffing_daily(day,operation,staff) VALUES (%s,%s,%s) ON CONFLICT(day,operation) DO UPDATE SET staff=EXCLUDED.staff,updated_at=NOW()',(dt,t,n))
    c.execute('INSERT INTO daily_data(day,separation,conference) VALUES (%s,%s,%s) ON CONFLICT(day) DO UPDATE SET separation=EXCLUDED.separation,conference=EXCLUDED.conference,updated_at=NOW()',(dt,Jsonb(a),Jsonb(b)))
  return jsonify(ok=True,days=sorted(days))
 except (ValueError,KeyError,TypeError):return jsonify(error='Informe HC fixo válido para todas as datas'),400
@app.errorhandler(500)
def error(e):return jsonify(error='Falha no servidor'),500
@app.get('/health')
def health():return jsonify(ok=True)
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','10000')))
