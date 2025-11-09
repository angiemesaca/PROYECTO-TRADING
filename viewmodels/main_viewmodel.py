from model.auth_service import AuthService
from model.db_service import DBService
from model.bot_service import BotService
import datetime
import os
import time # Para simular el tiempo de carga

# Quitamos las librerías de Google
# import requests
# import json

class MainViewModel:
    def __init__(self):
        self.auth_service = AuthService()
        self.db_service = DBService()
        self.bot_service = BotService()
        self.markets = self.db_service.get_markets()
        
        # Ya no necesitamos configurar Gemini
        # print("[AI INFO] Modo de IA Simulada activado.")

    # ... (login, register, y todas las demás funciones se quedan igual) ...
    
    def login(self, email, password):
        # (código de login sin cambios)
        return self.auth_service.login(email, password)

    def register(self, email, password, username):
        # (código de register sin cambios)
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
        # (código sin cambios)
        profile = self.db_service.get_user_profile(user_id, token)
        return profile if profile else {"username": "Usuario"}

    def update_user_profile(self, user_id, data, token):
        # (código sin cambios)
        current_profile = self.get_user_profile(user_id, token)
        current_profile.update(data)
        return self.db_service.save_user_profile(user_id, current_profile, token)

    def get_available_markets(self):
        # (código sin cambios)
        return self.markets

    def change_password(self, id_token, new_password):
        # (código sin cambios)
        return self.auth_service.change_password(id_token, new_password)

    def change_email(self, id_token, new_email):
        # (código sin cambios)
        return self.auth_service.change_email(id_token, new_email)

    def delete_profile(self, user_id, id_token):
        # (código sin cambios)
        return self.db_service.delete_user_data(user_id, id_token)

    def get_bot_settings_data(self, user_id, token):
        # (código sin cambios)
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
        # (código sin cambios)
        current_settings = self.get_bot_settings_data(user_id, token)
        data['isActive'] = current_settings.get('isActive', False)
        # --- ¡IMPORTANTE! ---
        # Asegúrate de que el 'name' en tu formulario HTML sea 'riesgo', no 'risk'
        # Esta línea asume que el formulario envía 'riesgo'
        current_settings.update(data) 
        return self.bot_service.save_bot_settings(user_id, current_settings, token)

    def get_performance_data(self, user_id, token):
        # (código sin cambios)
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
        # (código sin cambios)
        return self.auth_service.reset_password(email)

    def get_dashboard_data(self, user_id, token):
        # (código sin cambios)
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
        # (código sin cambios)
        keys = self.bot_service.get_api_keys(user_id, token)
        return [value for key, value in keys.items()] if keys else []

    def save_api_key(self, user_id, exchange, api_key, api_secret, token):
        # (código sin cambios)
        data = {"exchange": exchange, "api_key": api_key, "api_secret": api_secret}
        return self.bot_service.save_api_key(user_id, data, token)
        
    def delete_api_key(self, user_id, exchange_name, token):
        # (código sin cambios)
        return self.bot_service.delete_api_key(user_id, exchange_name, token)

    def activate_bot(self, user_id, token):
        # (código sin cambios)
        try:
            settings = self.get_bot_settings_data(user_id, token)
            settings['isActive'] = True
            return self.bot_service.save_bot_settings(user_id, settings, token)
        except Exception as e:
            print(f"Error al activar el bot: {e}")
            return False

    def deactivate_bot(self, user_id, token):
        # (código sin cambios)
        try:
            settings = self.get_bot_settings_data(user_id, token)
            settings['isActive'] = False
            return self.bot_service.save_bot_settings(user_id, settings, token)
        except Exception as e:
            print(f"Error al desactivar el bot: {e}")
            return False
            
    def generate_mock_trades(self, user_id, token):
        # (código sin cambios)
        settings = self.get_bot_settings_data(user_id, token)
        asset_seleccionado = settings.get("activo", "crypto_btc_usd")
        return self.bot_service.generate_mock_trade_log(user_id, token, asset_seleccionado)
    
    def clear_trades(self, user_id, token):
        # (código sin cambios)
        return self.bot_service.clear_trade_log(user_id, token)

    # --- ¡FUNCIÓN DE IA MEJORADA! ---
    def get_ai_analysis(self, user_id, token, asset_name):
        try:
            settings = self.get_bot_settings_data(user_id, token)
            
            # Simulamos la carga
            time.sleep(2) 
            
            # ¡IMPORTANTE! El 'name' en tu formulario de 'ajustes.html' debe ser 'riesgo'
            risk = settings.get('riesgo', 'medio') 
            indicadores = settings.get('indicadores', 'RSI, MACD')

            # --- 1. Definimos las SUGERENCIAS por Nivel de Riesgo ---
            risk_suggestions = {
                "bajo": (
                    f"**Sugerencia (Perfil Conservador):**\n"
                    f"Para tu perfil **bajo**, la paciencia es clave. Tu estrategia con {indicadores} es buena, pero espera señales *muy* confirmadas (ej: cruces dobles, salida clara de sobreventa). Es preferible perder una oportunidad que entrar en una mala operación. Considera usar un Stop Loss más holgado para evitar ser sacado por volatilidad, pero con un tamaño de posición más pequeño."
                ),
                "medio": (
                    f"**Sugerencia (Perfil Balanceado):**\n"
                    f"Para tu perfil **medio**, tu estrategia con {indicadores} es sólida. Busca confirmaciones en tus indicadores (como un cruce de MACD o salida de sobreventa en RSI) para entrar. No olvides tomar ganancias parciales en objetivos de resistencia clave y mover tu Stop Loss a 'break-even' (precio de entrada) cuando sea posible."
                ),
                "alto": (
                    f"**Sugerencia (Perfil Agresivo):**\n"
                    f"Para tu perfil **alto**, la velocidad es importante. Tu estrategia con {indicadores} te permitirá capturar movimientos rápidos. Dado que este activo es volátil, considera 'scalping' o 'day trading' si tus indicadores lo confirman en temporalidades más bajas. Un Stop Loss ajustado es crucial para proteger tu capital y asegurar ganancias rápidas."
                )
            }

            # --- 2. Definimos los ANÁLISIS por Activo ---
            # Las 'keys' (ej: "Bitcoin") deben coincidir con lo que pasamos desde el botón de la UI
            asset_analysis = {
                "Bitcoin": (
                    "**Análisis de Bitcoin (BTC/USD):**\n"
                    "Bitcoin muestra una fuerte consolidación por encima de su media móvil de 50 días. El volumen ha disminuido, lo que sugiere una posible 'calma antes de la tormenta'. Los indicadores (RSI, MACD) están en territorio neutral."
                ),
                "Ethereum": (
                    "**Análisis de Ethereum (ETH/USD):**\n"
                    "Ethereum está mostrando una fortaleza relativa mayor que Bitcoin, posiblemente debido a actualizaciones de la red. El par ETH/BTC está en una tendencia alcista a corto plazo."
                ),
                "Solana": (
                    "**Análisis de Solana (SOL/USD):**\n"
                    "Solana es un activo de alta volatilidad (Beta alta). Su rendimiento reciente ha sido explosivo, pero el indicador RSI muestra signos de sobrecompra extrema, lo que advierte de una posible corrección a corto plazo."
                ),
                "Forex": (
                    "**Análisis de Forex (EUR/USD):**\n"
                    "El par EUR/USD está reaccionando a los datos de inflación de la zona euro y las minutas de la FED. Se encuentra en un canal lateral, esperando un catalizador que rompa el soporte o la resistencia."
                ),
                "Commodity": (
                    "**Análisis de Commodity (Oro):**\n"
                    "El Oro está actuando como refugio de valor. La incertidumbre geopolítica y los movimientos en las tasas de interés están dictando su precio. Técnicamente, se acerca a una zona de resistencia histórica."
                ),
                "Índice": (
                    "**Análisis de Índice (S&P 500):**\n"
                    "El índice S&P 500 está en una tendencia alcista clara, pero muestra signos de 'exuberancia'. Los reportes de ganancias corporativas serán clave esta semana. Tus indicadores podrían detectar una divergencia bajista."
                )
            }

            # --- 3. Buscamos y Combinamos ---
            
            # Buscar el análisis (buscamos la 'key' dentro del 'asset_name' que viene del botón)
            chosen_analysis = f"**Análisis para {asset_name}:**\nNo hay un análisis enlatado para este activo. Aplica tu estrategia con cautela."
            for key, text in asset_analysis.items():
                if key.lower() in asset_name.lower():
                    chosen_analysis = text
                    break
            
            # Buscar la sugerencia (buscamos el 'risk' en nuestro dict, si no, usamos 'medio')
            chosen_suggestion = risk_suggestions.get(risk, risk_suggestions["medio"]) 
            
            # Combinar
            return f"{chosen_analysis}\n\n{chosen_suggestion}"

        except Exception as e:
            print(f"[AI ERROR SIMULADO] Falló la lógica local: {e}")
            return f"Error al generar análisis simulado: {e}"