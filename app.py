from flask import Flask, request, render_template_string, redirect, make_response, session
import sqlite3
import secrets

app = Flask(__name__)
# 1. CLAVE SECRETA: Necesaria para manejar sesiones y tokens CSRF de forma segura
app.secret_key = 'clave_super_secreta_para_el_laboratorio_123'

# 2. CORRECCIÓN SQLi: db_query ahora acepta parámetros separados de la consulta
def db_query(query, params=()):
    """Función auxiliar segura contra SQL Injection"""
    conn = sqlite3.connect('vulnerable.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Se ejecuta la query y los parámetros por separado. El driver escapa todo.
    cursor.execute(query, params)
    result = cursor.fetchall()
    conn.commit()
    conn.close()
    return result

# Función para generar el token CSRF
def generar_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']

# --- LOGIN (Corregido) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username')
        pw = request.form.get('password')
        
        # CORRECCIÓN SQLi: Consulta parametrizada con '?'
        query = "SELECT * FROM usuarios WHERE username = ? AND password = ?"
        usuarios = db_query(query, (user, pw))
        
        if usuarios:
            usuario = usuarios[0]
            resp = make_response(redirect('/dashboard'))
            # 3. CORRECCIÓN COOKIES: Se añaden flags de seguridad
            # httponly=True evita que JS (XSS) lea la cookie
            # samesite='Lax' evita que se envíe en peticiones externas (CSRF)
            resp.set_cookie('user_session', usuario['username'], httponly=True, samesite='Lax')
            return resp
        return "<h3>Acceso denegado</h3><a href='/login'>Volver</a>", 401

    return '''
        <h2>Login del Sistema Académico</h2>
        <form method="post">
            Usuario: <input type="text" name="username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Ingresar">
        </form>
    '''

# --- DASHBOARD (Corregido) ---
@app.route('/dashboard')
def dashboard():
    username = request.cookies.get('user_session')
    if not username:
        return redirect('/login')

    # CORRECCIÓN SQLi: Consulta parametrizada
    datos = db_query("SELECT * FROM usuarios WHERE username = ?", (username,))[0]
    
    # Generamos el token para el formulario
    csrf_token = generar_csrf_token()

    # 4. CORRECCIÓN XSS: Usamos plantillas Jinja2 ({{ variable }}) en lugar de f-strings.
    # Jinja2 escapa automáticamente caracteres como < > y evita que se ejecute JS.
    html = """
    <h1>Panel de {{ username }}</h1>
    <p><b>Rol:</b> {{ rol }}</p>
    <p><b>Biografía:</b> {{ bio }}</p>
    <hr>
    <h3>Actualizar Biografía</h3>
    <form action="/update_bio" method="POST">
        <!-- 5. CORRECCIÓN CSRF: Campo oculto con el token -->
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
    username = request.cookies.get('user_session')
    if username:
        # 6. CORRECCIÓN CSRF: Validación del token
        token_form = request.form.get('csrf_token')
        if not token_form or token_form != session.get('csrf_token'):
            return "<h3>Error 403: Petición CSRF bloqueada (Token inválido o ausente)</h3><a href='/dashboard'>Volver</a>", 403
            
        nueva_bio = request.form.get('nueva_bio')
        
        # CORRECCIÓN SQLi: Consulta parametrizada
        db_query("UPDATE usuarios SET bio = ? WHERE username = ?", (nueva_bio, username))
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    resp = make_response(redirect('/login'))
    resp.set_cookie('user_session', '', expires=0)
    session.pop('csrf_token', None) # Limpiamos el token de la sesión
    return resp

@app.route('/')
def home():
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
