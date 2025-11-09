from model.auth_service import AuthService
from model.db_service import DBService
from model.bot_service import BotService
import datetime
import traceback

# --- ¡NUEVO! IMPORTACIÓN DE IA ---
import google.generativeai as genai
import os # Para la API Key

# --- ¡NUEVO! CONFIGURACIÓN DE IA ---
# DEBES añadir 'GEMINI_API_KEY' a tus variables de entorno en Render
# (Igual que hiciste con el Secret File, pero esta vez en "Environment Variables")
try:
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        print("--- Modelo de IA (Gemini) configurado ---")
    else:
        print("ADVERTENCIA: GEMINI_API_KEY no encontrada. La IA no funcionará.")
except Exception as e:
    print(f"Error al configurar Gemini: {e}")

class MainViewModel:
    def __init__(self):
        self.auth_service = AuthService()
        self.db_service = DBService()
        self.bot_service = BotService()
        self.markets = self.db_service.get_markets()
        
        # --- ¡NUEVO! Inicializar el modelo de IA ---
        try:
            self.ai_model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')
        except Exception:
            self.ai_model = None

    # ... (El resto de tus funciones: login, register, get_user_profile, etc. se quedan IGUAL) ...
    # ... (pega aquí todas tus funciones desde login() hasta clear_trades()) ...

    def login(self, email, password):
        """Maneja el login. Llama al auth_service."""
        return self.auth_service.login(email, password)

    def register(self, email, password, username):
        """Maneja el registro. Llama a auth y db services."""
        user = self.auth_service.register(email, password)
        if user and user.get('localId'):
            uid = user['localId']
            id_token = user['idToken']
            
            # 1. Preparamos perfil inicial
            profile_data = {
                "username": username,
                "email": email,
                "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "selected_market": "crypto",
                "risk": "medio",
                "experience": "novato"
            }
            self.db_service.save_user_profile(uid, profile_data, id_token)
            
            # 2. Preparamos AJUSTES INICIALES DEL BOT
            default_settings = {
                "activo": "crypto_btc_usd",
                "riesgo": "medio",
                "horario": "00:00-23:59",
                "indicadores": "RSI, MACD",
                "isActive": False
            }
            self.bot_service.save_bot_settings(uid, default_settings, id_token)
            
            return user
        return None

    def get_user_profile(self, user_id, token):
        profile = self.db_service.get_user_profile(user_id, token)
        return profile if profile else {"username": "Usuario"}

    def update_user_profile(self, user_id, data, token):
        """Actualiza el perfil del usuario (merge)."""
        current_profile = self.get_user_profile(user_id, token)
        current_profile.update(data)
        return self.db_service.save_user_profile(user_id, current_profile, token)

    def get_available_markets(self):
        return self.markets

    def change_password(self, id_token, new_password):
        return self.auth_service.change_password(id_token, new_password)

    def change_email(self, id_token, new_email):
        return self.auth_service.change_email(id_token, new_email)

    def delete_profile(self, user_id, id_token):
        return self.db_service.delete_user_data(user_id, id_token)

    def get_bot_settings_data(self, user_id, token):
        """Obtiene los ajustes del bot. Si no existen, crea y devuelve los defaults."""
        settings = self.bot_service.get_bot_settings(user_id, token)
        
        if settings is None:
            print("--- No se encontraron settings. Creando defaults. ---")
            default_settings = {
                "activo": "crypto_btc_usd",
                "riesgo": "medio",
                "horario": "00:00-23:59",
                "indicadores": "RSI, MACD",
                "isActive": False
            }
            self.bot_service.save_bot_settings(user_id, default_settings, token)
            return default_settings
            
        return settings

    def save_bot_settings_data(self, user_id, data, token):
        """Guarda los ajustes del formulario, pero mantiene el estado 'isActive'."""
        current_settings = self.get_bot_settings_data(user_id, token)
        data['isActive'] = current_settings.get('isActive', False)
        
        return self.bot_service.save_bot_settings(user_id, data, token)

    def get_performance_data(self, user_id, token):
        """Prepara los datos para la página de rendimientos."""
        trade_log = self.bot_service.get_trade_log(user_id, token)
        
        trade_list, labels_grafica, data_grafica = [], [], []
        ganancia_total, trades_ganadores, total_trades = 0.0, 0, 0

        if trade_log:
            try:
                sorted_trades = sorted(trade_log.values(), key=lambda x: x.get('timestamp', ''))
            except Exception:
                sorted_trades = trade_log.values()

            total_trades = len(sorted_trades) 
            
            # ¡Corregido! Reiniciamos pnl_total para recalcularlo
            pnl_total_recalculado = 0
            for trade in sorted_trades:
                # Recalculamos el PNL acumulado por si el bot se reinició
                pnl_trade = trade.get('pnl', 0)
                pnl_total_recalculado += pnl_trade
                trade['pnl_acumulado'] = round(pnl_total_recalculado, 2)
                
                trade_list.append(trade)
                
                # Usamos una etiqueta de fecha más corta para la gráfica
                try:
                    ts_obj = datetime.datetime.strptime(trade.get('timestamp', ''), "%Y-%m-%d %H:%M:%S")
                    etiqueta_corta = ts_obj.strftime("%m-%d %H:%M")
                except ValueError:
                    etiqueta_corta = trade.get('timestamp', 'N/A').split(' ')[0]
                
                labels_grafica.append(etiqueta_corta)
                data_grafica.append(trade['pnl_acumulado'])

                if pnl_trade > 0:
                    trades_ganadores += 1
            
            ganancia_total = pnl_total_recalculado

        win_rate = (trades_ganadores / total_trades) * 100 if total_trades > 0 else 0

        stats = {
            "ganancia_total": round(ganancia_total, 2), "total_trades": total_trades,
            "win_rate": round(win_rate, 2), "trades_ganadores": trades_ganadores
        }

        return {
            "stats": stats, "all_trades": trade_list,
            "grafica_labels": labels_grafica, "grafica_data": data_grafica
        }

    def forgot_password(self, email):
        return self.auth_service.reset_password(email)

    def get_dashboard_data(self, user_id, token):
        """Obtiene todos los datos necesarios para el dashboard (Inicio)."""
        try:
            profile = self.get_user_profile(user_id, token)
            settings = self.get_bot_settings_data(user_id, token)
            return {"profile": profile, "settings": settings}
        except Exception:
            return {
                "profile": {"username": "Usuario"},
                "settings": {"activo": "crypto_btc_usd", "isActive": False}
            }

    def get_api_keys_data(self, user_id, token):
        keys = self.bot_service.get_api_keys(user_id, token)
        return [value for key, value in keys.items()] if keys else []

    def save_api_key(self, user_id, exchange, api_key, api_secret, token):
        data = {"exchange": exchange, "api_key": api_key, "api_secret": api_secret}
        return self.bot_service.save_api_key(user_id, data, token)
        
    def delete_api_key(self, user_id, exchange_name, token):
        return self.bot_service.delete_api_key(user_id, exchange_name, token)

    def activate_bot(self, user_id, token):
        """Lee los ajustes, los pone en 'True' y guarda el objeto completo."""
        try:
            settings = self.get_bot_settings_data(user_id, token)
            settings['isActive'] = True
            return self.bot_service.save_bot_settings(user_id, settings, token)
        except Exception as e:
            print(f"Error al activar el bot: {e}")
            return False

    def deactivate_bot(self, user_id, token):
        """Lee los ajustes, los pone en 'False' y guarda el objeto completo."""
        try:
            settings = self.get_bot_settings_data(user_id, token)
            settings['isActive'] = False
            return self.bot_service.save_bot_settings(user_id, settings, token)
        except Exception as e:
            print(f"Error al desactivar el bot: {e}")
            return False
            
    def generate_mock_trades(self, user_id, token):
        """Llama al servicio para poblar el log de trades."""
        settings = self.get_bot_settings_data(user_id, token)
        asset_seleccionado = settings.get("activo", "crypto_btc_usd")
        return self.bot_service.generate_mock_trade_log(user_id, token, asset_seleccionado)
    
    def clear_trades(self, user_id, token):
        """Lmanda a llamar el servicio para borrar el historial de trades."""
        return self.bot_service.clear_trade_log(user_id, token)

    # --- ¡NUEVA FUNCIÓN DE IA! ---
    def get_ai_analysis(self, user_id, token, asset_name):
        """
        Llama a la IA de Gemini para obtener un análisis del portafolio.
        """
        if not self.ai_model:
            return "Error: El servicio de IA no está configurado en el servidor. Falta la GEMINI_API_KEY."

        # 1. Obtenemos los datos del usuario
        profile = self.get_user_profile(user_id, token)
        performance_data = self.get_performance_data(user_id, token)
        
        # 2. Resumimos los datos para la IA
        stats = performance_data.get('stats', {})
        profile_summary = f"Perfil del usuario: Nivel de experiencia '{profile.get('experience', 'no definido')}' con tolerancia al riesgo '{profile.get('risk', 'no definida')}'."
        performance_summary = f"Rendimiento actual: Ganancia neta de ${stats.get('ganancia_total', 0)}, con un Win Rate del {stats.get('win_rate', 0)}% sobre {stats.get('total_trades', 0)} operaciones."
        
        # 3. Creamos el prompt para Gemini
        prompt = f"""
        Actúa como un "Expert Advisor" de trading para un usuario de la app "Wallet Trainer".
        El usuario está pidiendo un análisis sobre el activo: {asset_name}.
        
        Aquí tienes un resumen de su perfil y rendimiento general:
        - {profile_summary}
        - {performance_summary}
        
        Por favor, genera un análisis corto (2-3 párrafos) para el usuario.
        El análisis debe incluir:
        1.  Una breve opinión (alcista/bajista/neutral) sobre el estado actual del mercado para {asset_name}, basándote en información pública reciente. (Usa la herramienta de búsqueda si es necesario).
        2.  Un consejo o sugerencia para el usuario sobre cómo podría operar este activo, teniendo en cuenta su perfil de riesgo y su rendimiento actual.
        
        Usa un tono profesional, alentador y directo. Formatea tu respuesta con saltos de línea y usa **negritas** para las ideas clave.
        """

        try:
            # 4. Habilitamos Google Search en la herramienta
            tools = [{"google_search": {}}]
            
            # 5. Generamos el contenido
            response = self.ai_model.generate_content(prompt, tools=tools)
            
            return response.text
        
        except Exception as e:
            print(f"Error al llamar a Gemini: {e}")
            print(traceback.format_exc())
            return f"Error: No se pudo conectar con el servicio de IA. {e}"