from firebase_config import db

class BotService:
    def __init__(self):
        # Conexión Pyrebase
        self.db = db

    # --- LECTURA DE DATOS ---
    def get_bot_settings(self, user_id, token):
        try:
            data = self.db.child("bot_settings").child(user_id).get(token=token)
            return data.val()
        except Exception as e:
            print(f"Error settings: {e}")
            return None

    def save_bot_settings(self, user_id, data, token):
        try:
            self.db.child("bot_settings").child(user_id).set(data, token=token)
            return True
        except Exception as e:
            return False

    def get_trade_log(self, user_id, token):
        try:
            data = self.db.child("trade_log").child(user_id).get(token=token)
            return data.val()
        except Exception as e:
            return {}

    # --- API KEYS (Si decides usarlas a futuro) ---
    def get_api_keys(self, user_id, token):
        try:
            data = self.db.child("api_keys").child(user_id).get(token=token)
            return data.val()
        except Exception:
            return None

    def save_api_key(self, user_id, key_data, token):
        try:
            exchange = key_data['exchange'].lower()
            self.db.child("api_keys").child(user_id).child(exchange).set(key_data, token=token)
            return True
        except Exception:
            return False
            
    def delete_api_key(self, user_id, exchange_name, token):
        try:
            self.db.child("api_keys").child(user_id).child(exchange_name.lower()).remove(token=token)
            return True
        except Exception:
            return False

    # --- ¡LA PARTE IMPORTANTE: GUARDAR TRADES! ---
    def record_trade(self, user_id, trade_data, token):
        """
        Recibe un diccionario con los datos del trade REAL (Paper Trading)
        y lo empuja al historial de Firebase.
        """
        try:
            # Usamos push() para que cree un ID único automáticamente
            self.db.child("trade_log").child(user_id).push(trade_data, token=token)
            print(f"✅ Trade guardado en Firebase: {trade_data.get('activo')} - {trade_data.get('tipo')}")
            return True
        except Exception as e:
            print(f"❌ Error al guardar trade: {e}")
            return False

    def clear_trade_log(self, user_id, token):
        try:
            self.db.child("trade_log").child(user_id).remove(token=token)
            return True
        except Exception:
            return False
    
    # Mantenemos esta por compatibilidad, pero ahora usa la lógica interna
    def generate_mock_trade_log(self, user_id, token, asset_name):
        return False # Desactivamos la simulación vieja