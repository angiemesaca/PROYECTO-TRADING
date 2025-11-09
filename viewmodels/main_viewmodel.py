from model.auth_service import AuthService
from model.db_service import DBService
from model.bot_service import BotService
import datetime
import os
import google.generativeai as genai

class MainViewModel:
    def __init__(self):
        self.auth_service = AuthService()
        self.db_service = DBService()
        self.bot_service = BotService() # Todavía lo usamos para get/save
        self.markets = self.db_service.get_markets()
        
        try:
            gemini_api_key = os.environ.get('GEMINI_API_KEY')
            if gemini_api_key:
                genai.configure(api_key=gemini_api_key)
                self.ai_model = genai.GenerativeModel('gemini-1.5-flash')
            else:
                self.ai_model = None
                print("[AI ERROR] GEMINI_API_KEY no encontrada.")
        except Exception as e:
            self.ai_model = None
            print(f"[AI ERROR] No se pudo configurar Gemini: {e}")

    def login(self, email, password):
        return self.auth_service.login(email, password)

    def register(self, email, password, username):
        user = self.auth_service.register(email, password)
        if user and user.get('localId'):
            uid = user['localId']
            id_token = user['idToken']
            
            profile_data = {
                "username": username, "email": email,
                "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "selected_market": "crypto", "risk": "medio", "experience": "novato"
            }
            self.db_service.save_user_profile(uid, profile_data, id_token)
            
            default_settings = {
                "activo": "crypto_btc_usd", "riesgo": "medio",
                "horario": "00:00-23:59", "indicadores": "RSI, MACD",
                "isActive": False # El bot empieza apagado por defecto
            }
            # ¡MODIFICADO! Usamos el bot_service normal (con token)
            self.bot_service.save_bot_settings(uid, default_settings, id_token)
            return user
        return None

    # ... (get_user_profile, update_user_profile, etc. se quedan igual) ...
    def get_user_profile(self, user_id, token):
        profile = self.db_service.get_user_profile(user_id, token)
        return profile if profile else {"username": "Usuario"}

    def update_user_profile(self, user_id, data, token):
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
        settings = self.bot_service.get_bot_settings(user_id, token)
        if settings is None:
            default_settings = {
                "activo": "crypto_btc_usd", "riesgo": "medio",
                "horario": "00:00-23:59", "indicadores": "RSI, MACD",
                "isActive": False
            }
            self.bot_service.save_bot_settings(user_id, default_settings, token)
            return default_settings
        return settings

    def save_bot_settings_data(self, user_id, data, token):
        current_settings = self.get_bot_settings_data(user_id, token)
        # Mantenemos el 'isActive' por si acaso
        data['isActive'] = current_settings.get('isActive', False)
        return self.bot_service.save_bot_settings(user_id, data, token)

    def get_performance_data(self, user_id, token):
        # Esta función ahora SÓLO LEE. El cálculo se hace
        # en generate_mock_trades
        trade_log = self.bot_service.get_trade_log(user_id, token)
        
        trade_list, labels_grafica, data_grafica = [], [], []
        ganancia_total, trades_ganadores, total_trades = 0.0, 0, 0

        if trade_log:
            try:
                sorted_trades = sorted(trade_log.values(), key=lambda x: x.get('timestamp', ''))
            except Exception:
                sorted_trades = trade_log.values()

            total_trades = len(sorted_trades) 

            for trade in sorted_trades:
                trade_list.append(trade)
                ts = trade.get('timestamp', 'N/A').split(' ')
                etiqueta_corta = ts[1] if len(ts) == 2 else ts[0] 
                labels_grafica.append(etiqueta_corta)
                
                pnl_acumulado = trade.get('pnl_acumulado', 0)
                data_grafica.append(pnl_acumulado)

                if trade.get('pnl', 0) > 0:
                    trades_ganadores += 1
                ganancia_total = pnl_acumulado 

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
        try:
            profile = self.get_user_profile(user_id, token)
            settings = self.get_bot_settings_data(user_id, token)
            return {"profile": profile, "settings": settings}
        except Exception:
            return {
                "profile": {"username": "Usuario"},
                "settings": {"activo": "crypto_btc_usd", "isActive": False}
            }

    # ... (get_api_keys_data, save_api_key, delete_api_key se quedan igual) ...
    def get_api_keys_data(self, user_id, token):
        keys = self.bot_service.get_api_keys(user_id, token)
        return [value for key, value in keys.items()] if keys else []

    def save_api_key(self, user_id, exchange, api_key, api_secret, token):
        data = {"exchange": exchange, "api_key": api_key, "api_secret": api_secret}
        return self.bot_service.save_api_key(user_id, data, token)
        
    def delete_api_key(self, user_id, exchange_name, token):
        return self.bot_service.delete_api_key(user_id, exchange_name, token)

    # --- ¡LÓGICA DEL BOT MODIFICADA! ---
    # activate y deactivate solo cambian el 'flag'
    def activate_bot(self, user_id, token):
        try:
            settings = self.get_bot_settings_data(user_id, token)
            settings['isActive'] = True
            return self.bot_service.save_bot_settings(user_id, settings, token)
        except Exception as e:
            print(f"Error al activar el bot: {e}")
            return False

    def deactivate_bot(self, user_id, token):
        try:
            settings = self.get_bot_settings_data(user_id, token)
            settings['isActive'] = False
            return self.bot_service.save_bot_settings(user_id, settings, token)
        except Exception as e:
            print(f"Error al desactivar el bot: {e}")
            return False
            
    # --- ¡NUESTRO BACKTESTER! ---
    def generate_mock_trades(self, user_id, token):
        """
        Llama al servicio para POBLAR el log de trades.
        ¡Usa el token del usuario, así que no falla por el 2025!
        """
        settings = self.get_bot_settings_data(user_id, token)
        asset_seleccionado = settings.get("activo", "crypto_btc_usd")
        
        # ¡IMPORTANTE! Ahora llamamos a 'generate_mock_trade_log'
        # del bot_service, que usa el TOKEN.
        return self.bot_service.generate_mock_trade_log(user_id, token, asset_seleccionado)
    
    def clear_trades(self, user_id, token):
        """Llama al servicio para borrar el historial de trades."""
        return self.bot_service.clear_trade_log(user_id, token)

    # --- LÓGICA DE IA (Se queda igual) ---
    def get_ai_analysis(self, user_id, token, asset_name):
        if not self.ai_model:
            return "Error: El modelo de IA no está configurado."
            
        settings = self.get_bot_settings_data(user_id, token)
        
        prompt = (
            "Eres un analista de trading experto. "
            f"Mi perfil de riesgo es '{settings.get('risk', 'medio')}' y mi experiencia es '{settings.get('experience', 'novato')}'. "
            f"Mi estrategia se basa en los indicadores '{settings.get('indicadores', 'RSI, MACD')}' "
            f"y opero en el activo '{asset_name}'.\n\n"
            "Dame un análisis de mercado corto (un 'snippet') y una sugerencia para este activo. "
            "No uses 'google_search'. Basa tu respuesta en conocimiento general de trading. "
            "Responde en español."
        )
        
        try:
            response = self.ai_model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"[AI ERROR] Falló la llamada a Gemini: {e}")
            # El error "google_search" ocurría aquí
            if "google_search" in str(e):
                return "Error: El modelo intentó usar una herramienta no permitida (google_search). Reintentando sin la herramienta..."
            return f"Error al generar análisis: {e}"