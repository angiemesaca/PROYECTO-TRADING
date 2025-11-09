from firebase_config import db

class DBService:
    def __init__(self):
        self.db = db

    def save_user_profile(self, user_id, data, token):
        """Crea o actualiza el perfil de un usuario (autenticado)."""
        try:
            # .set() crea o reemplaza completamente.
            self.db.child("users").child(user_id).set(data, token=token)
            return True
        except Exception as e:
            print("Error creando/actualizando perfil de usuario:", e)
            return False

    def get_user_profile(self, user_id, token):
        """Obtiene los datos de un usuario de la DB (autenticado)."""
        try:
            data = self.db.child("users").child(user_id).get(token=token)
            return data.val()
        except Exception as e:
            print("Error al leer perfil:", e)
            return {} # Devuelve dict vacío en lugar de None

    def delete_user_data(self, user_id, token):
        """Elimina todos los datos de un usuario (perfil, bot, logs, keys)."""
        try:
            self.db.child("users").child(user_id).remove(token=token)
            self.db.child("bot_settings").child(user_id).remove(token=token)
            self.db.child("trade_log").child(user_id).remove(token=token)
            self.db.child("api_keys").child(user_id).remove(token=token)
            return True
        except Exception as e:
            print(f"Error al eliminar datos de usuario: {e}")
            return False

    def get_markets(self):
        """Función 'dummy' (simulada) para la página de perfil (legacy)."""
        return [
            {"id": "crypto", "name": "Criptomonedas"},
            {"id": "forex", "name": "Forex"},
            {"id": "stocks", "name": "Acciones"}
        ]