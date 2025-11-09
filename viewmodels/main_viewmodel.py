from model.auth_service import AuthService
from model.db_service import DBService
from model.bot_service import BotService
import datetime
import os
import time # ¡NUEVO! Para simular el tiempo de carga

# --- ¡ELIMINADOS! ---
# Ya no necesitamos llamar a Google, así que quitamos sus librerías
# import requests
# import json
# import google.generativeai as genai

class MainViewModel:
    def __init__(self):
        self.auth_service = AuthService()
        self.db_service = DBService()
        self.bot_service = BotService()
        self.markets = self.db_service.get_markets()
        
        # --- ¡ELIMINADO! ---
        # Ya no necesitamos configurar Gemini
        # self.gemini_api_key = os.environ.get('GEMINI_API_KEY')
        # if not self.gemini_api_key:
        #      print("[AI ERROR] GEMINI_API_KEY no encontrada.")

    # ... (login, register, y todas las demás funciones se quedan igual) ...
    
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

    # --- ¡FUNCIÓN DE IA SIMULADA! ---
    def get_ai_analysis(self, user_id, token, asset_name):
        # Esta función ya no llama a Google. Es 100% local.
        # No puede fallar por el 2025.
        
        try:
            settings = self.get_bot_settings_data(user_id, token)
            
            # ¡SIMULAMOS LA CARGA!
            time.sleep(2) 
            
            risk = settings.get('risk', 'medio')
            
            # Respuestas "enlatadas"
            canned_responses = {
                "Bitcoin": (
                    "**Análisis de Bitcoin (BTC):**\n"
                    "Bitcoin muestra una fuerte consolidación por encima de su media móvil de 50 días. El volumen ha disminuido, lo que sugiere una posible 'calma antes de la tormenta'. Los indicadores (RSI, MACD) están en territorio neutral.\n\n"
                    f"**Sugerencia (Perfil {risk}):**\n"
                    f"Dado tu perfil **{risk}**, la estrategia actual con {settings.get('indicadores')} es apropiada. Considera buscar una ruptura por encima de la resistencia clave. La paciencia es vital en este momento; evita operar en el 'ruido' del mercado."
                ),
                "Ethereum": (
                    "**Análisis de Ethereum (ETH):**\n"
                    "Ethereum está mostrando una fortaleza relativa mayor que Bitcoin, posiblemente debido a actualizaciones de la red. El par ETH/BTC está en una tendencia alcista a corto plazo.\n\n"
                    f"**Sugerencia (Perfil {risk}):**\n"
                    f"Tu estrategia basada en {settings.get('indicadores')} es sólida. Con un perfil **{risk}**, podrías considerar tomar ganancias parciales si el RSI entra en sobrecompra, o esperar una confirmación de soporte para añadir a la posición."
                ),
                "Solana": (
                    "**Análisis de Solana (SOL):**\n"
                    "Solana es un activo de alta volatilidad (Beta alta). Su rendimiento reciente ha sido explosivo, pero el indicador RSI muestra signos de sobrecompra extrema, lo que advierte de una posible corrección a corto plazo.\n\n"
                    f"**Sugerencia (Perfil {risk}):**\n"
                    f"Este activo es volátil. Para un perfil **{risk}**, es crucial usar un Stop Loss estricto. No persigas el precio ('FOMO'). Espera un retroceso a una zona de soporte (como una EMA) antes de considerar una entrada basada en tus indicadores."
                )
            }
            
            # Buscar la respuesta por el nombre
            for key, response_text in canned_responses.items():
                if key.lower() in asset_name.lower():
                    return response_text
            
            # Respuesta por defecto si no lo encontramos
            return (
                f"**Análisis para {asset_name}:**\n"
                f"Este activo ({asset_name}) es un mercado volátil. La estrategia debe ser aplicada con cautela.\n\n"
                f"**Sugerencia (Perfil {risk}):**\n"
                f"Asegúrate de que tus indicadores ({settings.get('indicadores')}) den señales claras antes de entrar. Gestiona tu riesgo."
            )

        except Exception as e:
            print(f"[AI ERROR SIMULADO] Falló la lógica local: {e}")
            return f"Error al generar análisis simulado: {e}"