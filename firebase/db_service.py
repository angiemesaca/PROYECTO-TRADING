from firebase_config import db

class DBService:
    def __init__(self):
        self.db = db

    def create_user_profile(self, user_id, email, username):
        """Crea el perfil inicial de un usuario en la DB."""
        try:
            data = {"email": email, "username": username, "risk": "medio", "experience": "novato", "selected_market": "crypto"}
            # La creación inicial no necesita token, pero el resto sí.
            self.db.child("users").child(user_id).set(data)
            return True
        except Exception as e:
            print("Error creando perfil de usuario:", e)
            return False

    def get_user_profile(self, user_id, token):
        """Obtiene los datos de un usuario de la DB (autenticado)."""
        try:
            data = self.db.child("users").child(user_id).get(token=token)
            return data.val()
        except Exception as e:
            print("Error al leer perfil:", e)
            return {}

    def update_user_profile(self, user_id, data, token):
        """Actualiza el perfil de un usuario (autenticado)."""
        try:
            self.db.child("users").child(user_id).update(data, token=token)
            return True
        except Exception as e:
            print("Error al actualizar perfil:", e)
            return False
            
    def delete_user_profile(self, user_id, token):
        """Elimina el perfil de un usuario de la DB (autenticado)."""
        try:
            self.db.child("users").child(user_id).remove(token=token)
            return True
        except Exception as e:
            print(f"Error al eliminar perfil: {e}")
            return False

    def get_available_markets(self):
        """Simula la obtención de una lista de mercados."""
        return [
            {"id": "crypto", "name": "Criptomonedas"},
            {"id": "stocks", "name": "Acciones"},
            {"id": "forex", "name": "Divisas (Forex)"}
        ]
        
