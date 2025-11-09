from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from viewmodels.main_viewmodel import MainViewModel
import os 

# Importaciones para el bot en segundo plano
from apscheduler.schedulers.background import BackgroundScheduler
from model.bot_service import BotService 

app = Flask(__name__)
app.secret_key = os.urandom(24) 
vm = MainViewModel()

# --- INICIALIZACIÓN DEL SCHEDULER (BOT) ---
scheduler_bot_service = BotService()

def bot_task():
    """Función que el scheduler llamará."""
    print(f"--- [SCHEDULER] Iniciando ciclo del bot... ---")
    with app.app_context():
        scheduler_bot_service.execute_bot_cycle()
    print(f"--- [SCHEDULER] Ciclo del bot finalizado. ---")

scheduler = BackgroundScheduler(daemon=True)
# Frecuencia del bot (ej: cada 30 segundos para pruebas)
scheduler.add_job(bot_task, 'interval', seconds=30) 

try:
    scheduler.start()
    print("--- Scheduler (Bot en segundo plano) iniciado correctamente. ---")
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown() 
# --- FIN DEL BLOQUE DEL SCHEDULER ---


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
        flash("Correo o contraseña incorrectos", "danger")
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

# --- ¡RUTA DEL DASHBOARD MODIFICADA! ---
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    user_id = session['user_id']
    token = session['id_token']
    
    # 1. Obtenemos los datos normales
    data = vm.get_dashboard_data(user_id, token)
    
    # 2. Obtenemos el activo seleccionado para la IA
    selected_asset_id = data['settings'].get('activo', 'crypto_btc_usd')
    # Formateamos el nombre (ej: 'crypto_btc_usd' -> 'Bitcoin (BTC)')
    try:
        asset_name = selected_asset_id.split('_')[1].upper()
    except:
        asset_name = selected_asset_id.replace('_', ' ').title()
    
    # 3. Obtenemos el snippet de la IA
    ai_snippet = ""
    try:
        ai_snippet = vm.get_ai_analysis(user_id, token, asset_name)
    except Exception as e:
        print(f"Error al obtener AI snippet para dashboard: {e}")
        ai_snippet = "Error al cargar análisis de IA."

    return render_template(
        'dashboard.html', 
        profile=data['profile'], 
        settings=data['settings'],
        ai_snippet=ai_snippet # <-- ¡Le pasamos el snippet!
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


@app.route('/activate_bot', methods=['POST'])
def activate_bot():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    user_id = session['user_id']
    token = session['id_token']
    
    if vm.activate_bot(user_id, token):
        flash("Bot activado. El bot comenzará a operar en el próximo ciclo (aprox. 30 seg).", "success")
    else:
        flash("Error al activar el bot.", "danger")
    return redirect(url_for('dashboard'))

@app.route('/deactivate_bot', methods=['POST'])
def deactivate_bot():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    user_id = session['user_id']
    token = session['id_token']
    
    if vm.deactivate_bot(user_id, token):
        flash("Bot desactivado. El bot dejará de operar y guardará su historial.", "info")
    else:
        flash("Error al desactivar el bot.", "danger")
    return redirect(url_for('dashboard'))


@app.route('/performance')
def performance():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    
    user_id = session['user_id']
    token = session['id_token']
    data = vm.get_performance_data(user_id, token)
    
    return render_template(
        'rendimientos.html', 
        stats=data.get('stats', {}),
        trades=data.get('all_trades', []),
        labels=data.get('grafica_labels', []),
        pnl_data=data.get('grafica_data', [])
    )

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session: return redirect(url_for('home'))
    id_token = session['id_token']
    if vm.change_password(id_token, request.form['new_password']):
        flash("Contraseña actualizada con éxito. Por favor, inicia sesión de nuevo.", "success")
        return redirect(url_for('logout'))
    else:
        flash("Error al cambiar la contraseña.", "danger")
        # --- ¡CORREGIDO DEFINITIVAMENTE! ---
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
    # El template ahora tiene su propia lógica
    return render_template('sugerencias.html')

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
        
    # Llamamos al ViewModel para obtener la sugerencia
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
    app.run(debug=True, use_reloader=False)