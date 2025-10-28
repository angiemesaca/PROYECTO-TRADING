from firebase_config import auth

class AuthService:
    def __init__(self):
        self.auth = auth

    def register_user(self, email, password):
        """Crea un usuario en Firebase Auth. Devuelve el user_id o None."""
        try:
            user = self.auth.create_user_with_email_and_password(email, password)
            return user["localId"]
        except Exception as e:
            import traceback
            print("🔥 ERROR REGISTRO (AUTH):", traceback.format_exc())
            return None

    def login_user(self, email, password):
        """Autentica un usuario. Devuelve los datos del usuario o None."""
        try:
            user = self.auth.sign_in_with_email_and_password(email, password)
            return user
        except Exception as e:
            import traceback
            print("🔥 ERROR LOGIN (AUTH):", traceback.format_exc())
            return None