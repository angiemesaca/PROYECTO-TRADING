import random
from datetime import datetime, timedelta
# ¡SOLO IMPORTAMOS 'db' (pyrebase)
from firebase_config import db
# --- ¡NUEVO! ---
# Importamos nuestro nuevo cliente de broker
from model.broker_client import BrokerClient
# --- ¡FIN NUEVO! ---

class BotService:
    def __init__(self):
        # Conexión Pyrebase (para operaciones con token)
        self.db = db
        # --- ¡NUEVO! ---
        # Inicializamos el cliente del broker
        self.broker = BrokerClient()
        # --- ¡FIN NUEVO! ---

    # -----------------------------------------------------------------
    # (TODAS LAS OTRAS FUNCIONES: get_bot_settings, save_bot_settings, 
    #  get_trade_log, get_api_keys, etc. SIGUEN IGUAL. 
    #  Solo reemplaza la función 'generate_mock_trade_log' de abajo)
    # -----------------------------------------------------------------
    
    def get_bot_settings(self, user_id, token):
        try:
            data = self.db.child("bot_settings").child(user_id).get(token=token)
            return data.val()
        except Exception as e:
            print(f"Error al leer ajustes del bot: {e}")
            return None

    def save_bot_settings(self, user_id, data, token):
        try:
            self.db.child("bot_settings").child(user_id).set(data, token=token)
            return True
        except Exception as e:
            print(f"Error al guardar ajustes del bot: {e}")
            return False

    def get_trade_log(self, user_id, token):
        try:
            data = self.db.child("trade_log").child(user_id).get(token=token)
            return data.val()
        except Exception as e:
            print(f"Error al leer trade log: {e}")
            return {}
    
    def get_api_keys(self, user_id, token):
        try:
            data = self.db.child("api_keys").child(user_id).get(token=token)
            return data.val()
        except Exception as e:
            print(f"Error al leer API keys: {e}")
            return None

    def save_api_key(self, user_id, key_data, token):
        try:
            exchange_name = key_data['exchange'].lower()
            self.db.child("api_keys").child(user_id).child(exchange_name).set(key_data, token=token)
            return True
        except Exception as e:
            print(f"Error al guardar API key: {e}")
            return False
            
    def delete_api_key(self, user_id, exchange_name, token):
        try:
            self.db.child("api_keys").child(user_id).child(exchange_name.lower()).remove(token=token)
            return True
        except Exception as e:
            print(f"Error al borrar API key: {e}")
            return False
            
    def clear_trade_log(self, user_id, token):
        """Borra el historial de trades de un usuario."""
        try:
            self.db.child("trade_log").child(user_id).remove(token=token)
            return True
        except Exception as e:
            print(f"Error al borrar trade log: {e}")
            return False
            
    # --- ¡NUESTRA FUNCIÓN DE BACKTEST! ---
    # --- ¡MODIFICADA PARA GUARDAR MÚLTIPLES TRADES! ---
    def generate_mock_trade_log(self, user_id, token, asset_name="crypto_btc_usd"):
        """
        ¡YA NO ES UN MOCK!
        Se conecta a Alpaca, ejecuta un trade (o simula uno si el mercado
        está cerrado) y ¡AÑADE EL RESULTADO AL LOG!
        """
        print(f"--- Conectando a Broker Real para {user_id} con {asset_name} ---")
        try:
            # Apuntamos a la raíz del log del usuario
            log_ref = self.db.child("trade_log").child(user_id)
            
            # --- ¡LÓGICA REEMPLAZADA! ---
            # Llamamos a nuestro cliente de broker.
            # Ahora devuelve solo el diccionario del trade, o None si falla.
            trade_data = self.broker.ejecutar_trade_y_obtener_log(asset_name)
            # --- FIN DE LÓGICA REEMPLAZADA ---

            if not trade_data:
                # El trade falló (ej: mercado cerrado o error de API)
                print("El broker no devolvió datos (trade fallido o mercado cerrado).")
                return False

            # --- ¡CAMBIO CLAVE! ---
            # ¡Usamos .push() para AÑADIR el trade al historial!
            # .set() BORRABA el historial anterior.
            log_ref.push(trade_data, token=token)
            # --- FIN DEL CAMBIO ---
            
            print("--- ¡Trade real (paper) ejecutado y guardado en Firebase! ---")
            return True
        
        except Exception as e:
            print(f"Error al generar log con broker real: {e}")
            import traceback
            print(traceback.format_exc())
            return False