from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from viewmodels.main_viewmodel import MainViewModel
import os # Para la clave secreta
import time # Para añadir el "freno"
import datetime # Para el reporte y fechas

# --- ¡CORRECCIÓN AQUÍ! ---
# Quitamos template_folder='app/templates' y static_folder='app/static'
# Al dejarlo vacío, Flask buscará automáticamente en las carpetas './templates' y './static'
# que están en la raíz, que es donde realmente las tienes.
app = Flask(__name__)

app.secret_key = os.urandom(24) # Clave segura
vm = MainViewModel()

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # --- AGREGAR ESTE BLOQUE ---
    if request.method == 'GET':
        return redirect(url_for('home'))
    # ---------------------------

    # ... aquí sigue tu código normal de login (email = request.form...) ...
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

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    user_id = session['user_id']
    token = session['id_token']
    
    # Esta función obtiene los datos (incluyendo el 'settings' actualizado)
    data = vm.get_dashboard_data(user_id, token)
    
    # Lógica para el snippet de IA en el dashboard
    selected_asset_id = data['settings'].get('activo', 'crypto_btc_usd')
    try:
        if "_" in selected_asset_id:
            asset_name = selected_asset_id.split('_')[1].upper()
        else:
            asset_name = selected_asset_id
    except:
        asset_name = "Activo"
    
    ai_snippet = ""
    try:
        ai_snippet = vm.get_ai_analysis(user_id, token, asset_name)
    except Exception as e:
        print(f"Error dashboard IA: {e}")
        ai_snippet = "No disponible."

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
            "risk": request.form['risk'], # Asegúrate de que el formulario envíe 'risk' o mapealo
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
        flash("Bot Activado.", "success")
        # --- ¡AQUÍ ESTÁ EL FRENO! ---
        # Espera 1 segundo para darle tiempo a Firebase a actualizarse
        time.sleep(1)
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
        flash("Bot Desactivado.", "info")
        # --- ¡AQUÍ ESTÁ EL FRENO! ---
        # Espera 1 segundo para darle tiempo a Firebase a actualizarse
        time.sleep(1)
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
    return render_template('rendimientos.html', **data)

@app.route('/update_dashboard_asset', methods=['POST'])
def update_dashboard_asset():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    
    user_id = session['user_id']
    token = session['id_token']
    new_asset = request.form['activo']
    
    # Solo actualizamos el campo 'activo', manteniendo lo demás igual
    # El ViewModel se encarga de mezclarlo con la config existente
    data = {"activo": new_asset}
    vm.save_bot_settings_data(user_id, data, token)
    
    return redirect(url_for('dashboard'))

@app.route('/run_backtest', methods=['POST'])
def run_backtest():
    """Ejecuta el backtest (simulación)"""
    if 'user_id' not in session:
        return redirect(url_for('home'))
    
    user_id = session['user_id']
    token = session['id_token']
    
    if vm.generate_mock_trades(user_id, token):
        flash("Simulación de backtest generada con éxito.", "success")
    else:
        flash("Error al generar la simulación.", "danger")
    return redirect(url_for('performance'))
    
@app.route('/clear_history', methods=['POST'])
def clear_history():
    """Borra el historial de trades (backtest)"""
    if 'user_id' not in session:
        return redirect(url_for('home'))
    
    user_id = session['user_id']
    token = session['id_token']
    
    if vm.clear_trades(user_id, token):
        flash("Historial de simulación borrado.", "info")
    else:
        flash("Error al borrar el historial.", "danger")
    return redirect(url_for('performance'))

# --- RUTA DE DESCARGA CSV ---
@app.route('/download_report')
def download_report():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    
    user_id = session['user_id']
    token = session['id_token']
    
    # 1. Obtener el contenido CSV del ViewModel
    # (Asegúrate de que vm.generate_csv_report exista en tu MainViewModel)
    try:
        csv_content = vm.generate_csv_report(user_id, token)
        
        # 2. Devolverlo como un archivo descargable
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=reporte_trading.csv"}
        )
    except AttributeError:
        # Si no has actualizado el ViewModel con la función CSV todavía
        flash("Función de descarga no disponible aún.", "warning")
        return redirect(url_for('performance'))


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
    
    user_id = session['user_id']
    token = session['id_token']
    
    # --- CORRECCIÓN: OBTENER PERFIL COMPLETO (SALDO) ---
    data = vm.get_dashboard_data(user_id, token)
    
    # Pasamos 'profile' (donde está el dinero) y 'settings'
    return render_template(
        'sugerencias.html', 
        settings=data['settings'], 
        profile=data['profile'] 
    )

@app.route('/get_ai_suggestion', methods=['POST'])
def get_ai_suggestion():
    """Ruta API para que el Javascript de 'sugerencias.html' llame."""
    if 'user_id' not in session:
        return jsonify({"error": "No autenticado"}), 401
    
    user_id = session['user_id']
    token = session['id_token']
    
    # Obtenemos el activo del JSON que nos envía el Javascript
    data = request.get_json()
    asset_name = data.get('asset_name') # Ojo: en tu JS puede ser 'asset_name' o 'asset'
    if not asset_name:
        asset_name = data.get('asset')

    if not asset_name:
        return jsonify({"error": "Activo no especificado"}), 400
    
    # Llamamos a nuestra función de IA simulada
    analysis = vm.get_ai_analysis(user_id, token, asset_name)
    
    if "Error" in analysis:
        return jsonify({"error": analysis}), 500
    
    return jsonify({"suggestion": analysis}) # En tu JS esperas 'suggestion'

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

@app.route('/manual_trade', methods=['POST'])
def manual_trade():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "No autorizado"}), 401
    
    user_id = session['user_id']
    token = session['id_token']
    
    data = request.get_json()
    asset_id = data.get('asset')
    action = data.get('action')
    
    # --- CAMBIO: LEER CANTIDAD ---
    try:
        quantity = float(data.get('quantity', 0))
    except:
        quantity = 0
    
    # Pasamos quantity y recibimos el nuevo saldo (new_balance)
    success, message, new_balance = vm.execute_manual_trade(user_id, token, asset_id, action, quantity)
    
    return jsonify({
        "success": success, 
        "message": message, 
        "new_balance": new_balance # Enviamos el nuevo saldo al JS
    })


if __name__ == "__main__":
    print("Iniciando servidor...")
    app.run(debug=True, use_reloader=False)