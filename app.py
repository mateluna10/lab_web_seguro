import os
import secrets
import sqlite3
from werkzeug.serving import WSGIRequestHandler
from flask import Flask, request, render_template_string, redirect, make_response, session
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)

# Mitigación: no exponer versión de Werkzeug/Python en header Server
WSGIRequestHandler.version_string = lambda self: "SecureDev"

# Secret key desde entorno (nunca hardcodeada)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

# Flags de cookies de sesión (aplican a la cookie 'session' firmada)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
)

# Métricas para Prometheus/Grafana
metrics = PrometheusMetrics(app)

@app.after_request
def security_headers(resp):
    resp.headers["Content-Security-Policy"] = "default-src 'self'"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
    return resp

def db_query(query, params=()):
    conn = sqlite3.connect('vulnerable.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = cursor.fetchall()
    conn.commit()
    conn.close()
    return result

def generar_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username', '')
        pw = request.form.get('password', '')
        query = "SELECT * FROM usuarios WHERE username = ? AND password = ?"
        usuarios = db_query(query, (user, pw))
        if usuarios:
            usuario = usuarios[0]
            # Sesión firmada por secret_key (no falsificable)
            session['user_session'] = usuario['username']
            return redirect('/dashboard')
        return "<h3>Acceso denegado</h3><a href='/login'>Volver</a>", 401
    return '''
        <h2>Login del Sistema Académico</h2>
        <form method="post">
            Usuario: <input type="text" name="username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Ingresar">
        </form>
    '''

@app.route('/dashboard')
def dashboard():
    username = session.get('user_session')
    if not username:
        return redirect('/login')

    datos = db_query("SELECT * FROM usuarios WHERE username = ?", (username,))
    if not datos:
        return redirect('/logout')
    datos = datos[0]

    csrf_token = generar_csrf_token()

    html = """
    <h1>Panel de {{ username }}</h1>
    <p><b>Rol:</b> {{ rol }}</p>
    <p><b>Biografía:</b> {{ bio }}</p>
    <hr>
    <h3>Actualizar Biografía</h3>
    <form action="/update_bio" method="POST">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <input type="text" name="nueva_bio" placeholder="Escribe algo...">
        <input type="submit" value="Guardar Cambios">
    </form>
    <br><a href="/logout">Cerrar Sesión</a>
    """
    return render_template_string(html,
                                  username=datos['username'],
                                  rol=datos['rol'],
                                  bio=datos['bio'],
                                  csrf_token=csrf_token)

@app.route('/update_bio', methods=['POST'])
def update_bio():
    username = session.get('user_session')
    if not username:
        return redirect('/login')

    token_form = request.form.get('csrf_token', '')
    token_ses  = session.get('csrf_token', '')
    if not token_form or not secrets.compare_digest(token_form, token_ses):
        return "<h3>Error 403: Petición CSRF bloqueada</h3><a href='/dashboard'>Volver</a>", 403

    nueva_bio = request.form.get('nueva_bio', '')
    db_query("UPDATE usuarios SET bio = ? WHERE username = ?", (nueva_bio, username))
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/')
def home():
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)