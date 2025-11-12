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
    # --- FUNCIONES LLAMADAS POR EL VIEWMODEL (USAN TOKEN) ---
    # (Todas estas ya las tenías y funcionan - NO CAMBIAN)
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
    # --- ¡MODIFICADA! ---
    def generate_mock_trade_log(self, user_id, token, asset_name="crypto_btc_usd"):
        """
        ¡YA NO SIMULA!
        Se conecta a un broker real (Alpaca Paper Trading), ejecuta
        un trade rápido (scalp) y guarda el resultado en el trade log.
        ¡Usa .set() para REEMPLAZAR el log anterior!
        """
        print(f"--- Conectando a Broker Real para {user_id} con {asset_name} ---")
        try:
            log_ref = self.db.child("trade_log").child(user_id)
            
            # ¡Llamamos a nuestro cliente de broker!
            # Esta función se conecta a Alpaca, hace el trade y nos
            # devuelve el diccionario de log listo para Firebase.
            new_log_data = self.broker.ejecutar_trade_y_obtener_log(asset_name)

            if not new_log_data:
                # El trade falló (ej: mercado cerrado)
                print("El broker no devolvió datos (trade fallido o mercado cerrado).")
                # Devolvemos False para que la UI pueda mostrar un error
                return False

            # ¡IMPORTANTE! Usamos .set() para REEMPLAZAR el historial
            # con este nuevo trade REAL.
            log_ref.set(new_log_data, token=token)
            
            print("--- ¡Trade real (paper) ejecutado y guardado en Firebase! ---")
            return True
        
        except Exception as e:
            print(f"Error al generar log con broker real: {e}")
            import traceback
            print(traceback.format_exc())
            return False