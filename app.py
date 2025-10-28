from flask import Flask, render_template, request, redirect, url_for, session, flash
from viewmodels.main_viewmodel import MainViewModel

app = Flask(__name__)
app.secret_key = "clave_secreto_seguro"
vm = MainViewModel()

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

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    user_id = session['user_id']
    token = session['id_token'] # <--- Saca el token
    
    profile_data = vm.get_profile(user_id, token) # <--- Pasa el token
    bot_settings = vm.get_bot_settings_data(user_id, token) # <--- Pasa el token
    
    return render_template(
        'dashboard.html', 
        profile=profile_data,
        settings=bot_settings
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
    token = session['id_token'] # <--- Saca el token
    
    if request.method == 'POST':
        username = request.form['username']
        risk = request.form['risk']
        experience = request.form['experience']
        market = request.form['market']
        
        # <--- Pasa el token
        if vm.update_profile(user_id, username, risk, experience, market, token):
            flash("Perfil actualizado correctamente", "success")
        else:
            flash("Error al actualizar el perfil", "danger")
        return redirect(url_for('profile'))

    data = vm.get_profile_page_data(user_id, token) # <--- Pasa el token
    data['profile']['email'] = session.get('email', 'N/A')
    return render_template('profile.html', profile=data['profile'], markets=data['markets'])

@app.route('/delete_profile', methods=['POST'])
def delete_profile():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    user_id = session['user_id']
    token = session['id_token'] # <--- Saca el token
    
    if vm.delete_profile(user_id, token): # <--- Pasa el token
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
            "activo": request.form['activo'], # Ej: "commodity_oro"
            "indicadores": request.form['indicadores'],
            "horario": request.form['horario']
        }
        
        # 1. Actualiza los ajustes (como antes)
        update_success = vm.update_bot_settings(user_id, data, token)
        
        if update_success:
            flash("Ajustes del bot actualizados correctamente", "success")
            
            # --- ¡NUEVA LÓGICA! ---
            # 2. Inmediatamente genera un nuevo historial de trades
            #    basado en los ajustes que acabamos de guardar.
            print(f"Detectado cambio de ajustes. Generando nuevo historial mock para: {data['activo']}")
            vm.generate_mock_trades(user_id, token)
            
        else:
            flash("Error al actualizar los ajustes", "danger")
            
        return redirect(url_for('bot_settings'))

    # El método GET no cambia
    settings = vm.get_bot_settings_data(user_id, token)
    return render_template('ajustes.html', settings=settings)

@app.route('/activate_bot', methods=['POST'])
def activate_bot():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    user_id = session['user_id']
    token = session['id_token'] # <--- Saca el token
    
    # <--- Pasa el token Y REVISA EL RESULTADO (ARREGLA EL FALSO POSITIVO)
    if vm.update_bot_settings(user_id, {"isActive": True}, token):
        flash("Bot activado correctamente.", "success")
    else:
        flash("Error al activar el bot.", "danger")
    return redirect(url_for('dashboard'))

@app.route('/deactivate_bot', methods=['POST'])
def deactivate_bot():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    user_id = session['user_id']
    token = session['id_token'] # <--- Saca el token

    # <--- Pasa el token Y REVISA EL RESULTADO
    if vm.update_bot_settings(user_id, {"isActive": False}, token):
        flash("Bot desactivado.", "info")
    else:
        flash("Error al desactivar el bot.", "danger")
    return redirect(url_for('dashboard'))

@app.route('/performance')
def performance():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    user_id = session['user_id']
    token = session['id_token'] # <--- Saca el token
    
    data = vm.get_performance_data(user_id, token) # <--- Pasa el token
    return render_template(
        'rendimientos.html', 
        trades=data['all_trades'], labels=data['grafica_labels'], pnl_data=data['grafica_data']
    )

# --- (Rutas para cambiar email/pass) ---
@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session: return redirect(url_for('home'))
    id_token = session['id_token']
    if vm.update_password(id_token, request.form['new_password']):
        flash("Contraseña actualizada con éxito. Por favor, inicia sesión de nuevo.", "success")
        return redirect(url_for('logout'))
    else:
        flash("Error al cambiar la contraseña.", "danger")
        return redirect(url_for('profile'))

@app.route('/change_email', methods=['POST'])
def change_email():
    if 'user_id' not in session: return redirect(url_for('home'))
    id_token = session['id_token']
    if vm.update_email(id_token, request.form['new_email']):
        flash("Email actualizado con éxito. Por favor, inicia sesión de nuevo.", "success")
        return redirect(url_for('logout'))
    else:
        flash("Error al cambiar el email.", "danger")
        return redirect(url_for('profile'))
    
@app.route('/generate_mock', methods=['POST'])
def generate_mock():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    
    user_id = session['user_id']
    token = session['id_token']
    
    if vm.generate_mock_trades(user_id, token):
        flash("Datos de historial falsos generados con éxito.", "success")
    else:
        flash("Error al generar datos falsos.", "danger")
    return redirect(url_for('performance'))

# --- ELIMINAMOS EL GENERADOR DE DATOS DE AQUÍ ---
# Lo movimos a un botón
if __name__ == "__main__":
    print("Iniciando servidor...")
    app.run(debug=True)