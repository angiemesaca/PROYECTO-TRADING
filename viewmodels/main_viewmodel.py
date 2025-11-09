from model.auth_service import AuthService
from model.db_service import DBService
from model.bot_service import BotService
import datetime
import os
# ¡CAMBIOS! Ya no usamos 'google.generativeai'
# import google.generativeai as genai
# ¡NUEVOS! Usamos 'requests' y 'json'
import requests
import json

class MainViewModel:
    def __init__(self):
        self.auth_service = AuthService()
        self.db_service = DBService()
        self.bot_service = BotService()
        self.markets = self.db_service.get_markets()
        
        # ¡CAMBIO! Solo guardamos la clave, no inicializamos el modelo
        self.gemini_api_key = os.environ.get('GEMINI_API_KEY')
        if not self.gemini_api_key:
             print("[AI ERROR] GEMINI_API_KEY no encontrada.")

    # ... (El resto de tus funciones como login, register, etc. se quedan igual) ...
    
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
                "isActive": False
            }
            self.bot_service.save_bot_settings(uid, default_settings, id_token)
            return user
        return None

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
        data['isActive'] = current_settings.get('isActive', False)
        return self.bot_service.save_bot_settings(user_id, data, token)

    def get_performance_data(self, user_id, token):
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

    def get_api_keys_data(self, user_id, token):
        keys = self.bot_service.get_api_keys(user_id, token)
        return [value for key, value in keys.items()] if keys else []

    def save_api_key(self, user_id, exchange, api_key, api_secret, token):
        data = {"exchange": exchange, "api_key": api_key, "api_secret": api_secret}
        return self.bot_service.save_api_key(user_id, data, token)
        
    def delete_api_key(self, user_id, exchange_name, token):
        return self.bot_service.delete_api_key(user_id, exchange_name, token)

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
            
    def generate_mock_trades(self, user_id, token):
        settings = self.get_bot_settings_data(user_id, token)
        asset_seleccionado = settings.get("activo", "crypto_btc_usd")
        return self.bot_service.generate_mock_trade_log(user_id, token, asset_seleccionado)
    
    def clear_trades(self, user_id, token):
        return self.bot_service.clear_trade_log(user_id, token)

    # --- ¡FUNCIÓN DE IA REESCRITA! ---
    def get_ai_analysis(self, user_id, token, asset_name):
        if not self.gemini_api_key:
            return "Error: El modelo de IA no está configurado (GEMINI_API_KEY no encontrada)."
            
        settings = self.get_bot_settings_data(user_id, token)
        
        prompt = (
            "Eres un analista de trading experto. "
            f"Mi perfil de riesgo es '{settings.get('risk', 'medio')}' y mi experiencia es '{settings.get('experience', 'novato')}'. "
            f"Mi estrategia se basa en los indicadores '{settings.get('indicadores', 'RSI, MACD')}' "
            f"y opero en el activo '{asset_name}'.\n\n"
            "Dame un análisis de mercado corto (un 'snippet') y una sugerencia para este activo. "
            "Basa tu respuesta en conocimiento general de trading. "
            "Responde en español y NO uses markdown."
        )
        
        # Usamos la API REST de gemini-pro (v1beta)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.gemini_api_key}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        try:
            # ¡La llamada de REPSUESTA!
            response = requests.post(url, headers=headers, data=json.dumps(data), timeout=20)
            
            # Si Google nos da un error (como 404, 500, etc.)
            if response.status_code != 200:
                print(f"[AI ERROR] La API REST de Gemini falló con status {response.status_code}:")
                print(response.text)
                return f"Error: La API de IA devolvió un error {response.status_code}. (Posiblemente el Error 2025 de nuevo)"

            # Si funciona, extraemos el texto
            result = response.json()
            text = result['candidates'][0]['content']['parts'][0]['text']
            return text
            
        except requests.exceptions.RequestException as e:
            print(f"[AI ERROR] Falló la llamada a Gemini (Requests): {e}")
            return f"Error de conexión al generar análisis: {e}"
        except Exception as e:
            print(f"[AI ERROR] Falló al procesar la respuesta de Gemini: {e}")
            return f"Error al procesar respuesta de IA: {e}"