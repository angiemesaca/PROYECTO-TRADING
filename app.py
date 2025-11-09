from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from viewmodels.main_viewmodel import MainViewModel
import os 
# ¡ELIMINADO! Ya no necesitamos APScheduler ni el BotService aquí
# from apscheduler.schedulers.background import BackgroundScheduler
# from model.bot_service import BotService 

app = Flask(__name__)
app.secret_key = os.urandom(24) 
vm = MainViewModel()

# --- ¡BLOQUE DEL SCHEDULER ELIMINADO! ---
# El bot en segundo plano fallaba por la fecha de 2025.
# Lo reemplazamos por un botón de "Backtest".

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    user = vm.login(email, password) 
    
    if user:
        session['user_id'] = user['localId']
        session['email'] = user['email']
        session['id_token'] = user['idToken'] 
        flash("Inicio de sesión exitoso", "success")
        return redirect(url_for('dashboard'))
    else:
        # El error de "Error en login: 503" que viste
        # puede ser por la fecha de 2025.
        flash("Correo o contraseña incorrectos (o error 503 del servidor)", "danger")
        return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        username = request.form['username']
        
        if vm.register(email, password, username): 
            flash("Usuario registrado con éxito, ahora inicia sesión", "success")
            return redirect(url_for('home'))
        else:
            flash("Error al registrar usuario", "danger")
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    user_id = session['user_id']
    token = session['id_token']
    
    data = vm.get_dashboard_data(user_id, token)
    
    selected_asset_id = data['settings'].get('activo', 'crypto_btc_usd')
    try:
        asset_name = selected_asset_id.split('_')[1].upper()
    except:
        asset_name = selected_asset_id.replace('_', ' ').title()
    
    ai_snippet = ""
    try:
        # El snippet de IA SÍ usa el token del usuario, que
        # puede fallar si el login falló, pero lo intentamos.
        ai_snippet = vm.get_ai_analysis(user_id, token, asset_name)
    except Exception as e:
        print(f"Error al obtener AI snippet para dashboard: {e}")
        ai_snippet = "Error al cargar análisis de IA."

    return render_template(
        'dashboard.html', 
        profile=data['profile'], 
        settings=data['settings'],
        ai_snippet=ai_snippet
    )

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('email', None)
    session.pop('id_token', None)
    flash("Sesión cerrada correctamente", "info")
    return redirect(url_for('home'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    user_id = session['user_id']
    token = session['id_token']
    
    if request.method == 'POST':
        data = {
            "username": request.form['username'],
            "risk": request.form['risk'],
            "experience": request.form['experience'],
            "selected_market": request.form['market']
        }
        if vm.update_user_profile(user_id, data, token):
            flash("Perfil actualizado correctamente", "success")
        else:
            flash("Error al actualizar el perfil", "danger")
        return redirect(url_for('profile'))

    profile_data = vm.get_user_profile(user_id, token)
    markets = vm.get_available_markets()
    profile_data['email'] = session.get('email', 'N/A')
    
    return render_template(
        'profile.html', 
        profile=profile_data, 
        markets=markets
    )

# ... (tus otras rutas como /delete_profile se quedan igual) ...
@app.route('/delete_profile', methods=['POST'])
def delete_profile():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    user_id = session['user_id']
    token = session['id_token']
    
    if vm.delete_profile(user_id, token):
        flash("Tu perfil ha sido eliminado correctamente.", "success")
        return redirect(url_for('logout'))
    else:
        flash("Error al eliminar tu perfil.", "danger")
        return redirect(url_for('profile'))


@app.route('/ajustes', methods=['GET', 'POST'])
def bot_settings():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    user_id = session['user_id']
    token = session['id_token']
    
    if request.method == 'POST':
        data = {
            "riesgo": request.form['riesgo'],
            "activo": request.form['activo'],
            "indicadores": request.form['indicadores'],
            "horario": request.form['horario']
        }
        update_success = vm.save_bot_settings_data(user_id, data, token)
        if update_success:
            flash("Ajustes del bot actualizados correctamente", "success")
        else:
            flash("Error al actualizar los ajustes", "danger")
        return redirect(url_for('bot_settings'))

    settings = vm.get_bot_settings_data(user_id, token)
    return render_template('ajustes.html', settings=settings)


# --- RUTAS DEL BOT MODIFICADAS ---
# Ya no son un "interruptor", solo están ahí
# por si la lógica los necesita, pero no hacen nada.

@app.route('/activate_bot', methods=['POST'])
def activate_bot():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    # ¡MODIFICADO! Esta ruta ya no hace nada en vivo.
    flash("Bot 'Activado'. Ve a Rendimientos para ejecutar una simulación.", "info")
    return redirect(url_for('dashboard'))

@app.route('/deactivate_bot', methods=['POST'])
def deactivate_bot():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    # ¡MODIFICADO! Esta ruta ya no hace nada.
    flash("Bot 'Desactivado'.", "info")
    return redirect(url_for('dashboard'))


@app.route('/performance')
def performance():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    
    user_id = session['user_id']
    token = session['id_token']
    # ¡MODIFICADO! Esta función ahora solo LEE los datos
    data = vm.get_performance_data(user_id, token)
    
    return render_template(
        'rendimientos.html', 
        stats=data.get('stats', {}),
        trades=data.get('all_trades', []),
        labels=data.get('grafica_labels', []),
        pnl_data=data.get('grafica_data', [])
    )

# --- ¡NUEVA RUTA DE BACKTEST! ---
# Esta ruta REEMPLAZA al scheduler roto.
@app.route('/run_backtest', methods=['POST'])
def run_backtest():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    
    user_id = session['user_id']
    token = session['id_token']
    
    # ¡Aquí está la magia!
    # Llamamos a la función que genera los 30 trades falsos.
    # Esta usa el 'token' del usuario, no el 'admin_db' roto.
    if vm.generate_mock_trades(user_id, token):
        flash("Simulación de backtest completada.", "success")
    else:
        flash("Error al ejecutar la simulación.", "danger")
        
    return redirect(url_for('performance'))

# --- ¡NUEVA RUTA DE LIMPIEZA! ---
@app.route('/clear_history', methods=['POST'])
def clear_history():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    
    user_id = session['user_id']
    token = session['id_token']
    
    if vm.clear_trades(user_id, token):
        flash("Historial de trades limpiado.", "info")
    else:
        flash("Error al limpiar el historial.", "danger")
        
    return redirect(url_for('performance'))


# ... (El resto de tus rutas: /change_password, /change_email, /forgot_password) ...
# ... (Se quedan igual) ...

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session: return redirect(url_for('home'))
    id_token = session['id_token']
    if vm.change_password(id_token, request.form['new_password']):
        flash("Contraseña actualizada con éxito. Por favor, inicia sesión de nuevo.", "success")
        return redirect(url_for('logout'))
    else:
        flash("Error al cambiar la contraseña.", "danger")
        return redirect(url_for('profile'))

@app.route('/change_email', methods=['POST'])
def change_email():
    if 'user_id' not in session: return redirect(url_for('home'))
    id_token = session['id_token']
    if vm.change_email(id_token, request.form['new_email']):
        flash("Email actualizado con éxito. Por favor, inicia sesión de nuevo.", "success")
        return redirect(url_for('logout'))
    else:
        flash("Error al cambiar el email.", "danger")
        return redirect(url_for('profile'))
    
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        if vm.forgot_password(email):
            flash("Enlace enviado. Revisa tu bandeja de entrada (y spam).", "success")
        else:
            flash("Si tu correo está registrado, recibirás un enlace en breve.", "info")
        return redirect(url_for('home'))
    return render_template('forgot_password.html')


@app.route('/sugerencias')
def sugerencias():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    return render_template('sugerencias.html')

# ... (El resto de tus rutas: /get_ai_suggestion, /api_keys, /delete_api_key) ...
# ... (Se quedan igual) ...
@app.route('/get_ai_suggestion', methods=['POST'])
def get_ai_suggestion():
    if 'user_id' not in session:
        return jsonify({"error": "No autenticado"}), 401
        
    user_id = session['user_id']
    token = session['id_token']
    
    data = request.json
    asset_id = data.get('asset_id')
    asset_name = data.get('asset_name')
    
    if not asset_id:
        return jsonify({"error": "No se proporcionó activo"}), 400
        
    suggestion_text = ""
    try:
        suggestion_text = vm.get_ai_analysis(user_id, token, asset_name)
    except Exception as e:
        print(f"Error en la ruta /get_ai_suggestion: {e}")
        suggestion_text = f"Error: {e}"

    if "Error:" in suggestion_text:
        return jsonify({"error": suggestion_text})
    
    return jsonify({"suggestion": suggestion_text})


@app.route('/api_keys', methods=['GET', 'POST'])
def api_keys():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    user_id = session['user_id']
    token = session['id_token']

    if request.method == 'POST':
        exchange = request.form['exchange']
        api_key = request.form['api_key']
        api_secret = request.form['api_secret']
        
        if vm.save_api_key(user_id, exchange, api_key, api_secret, token):
            flash("API Key guardada correctamente.", "success")
        else:
            flash("Error al guardar la API Key.", "danger")
        return redirect(url_for('api_keys'))

    keys_list = vm.get_api_keys_data(user_id, token)
    return render_template('api_keys.html', keys=keys_list)

@app.route('/delete_api_key', methods=['POST'])
def delete_api_key():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    user_id = session['user_id']
    token = session['id_token']
    exchange_name = request.form['exchange_name']
    
    if vm.delete_api_key(user_id, exchange_name, token):
        flash("API Key eliminada correctamente.", "success")
    else:
        flash("Error al eliminar la API Key.", "danger")
    
    return redirect(url_for('api_keys'))

if __name__ == "__main__":
    print("Iniciando servidor...")
    # 'use_reloader=False' ya no es necesario, ¡el scheduler se fue!
    app.run(debug=True)