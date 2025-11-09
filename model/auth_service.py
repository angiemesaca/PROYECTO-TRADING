from firebase_config import auth
import traceback

class AuthService:
    def __init__(self):
        self.auth = auth

    def register(self, email, password):
        """Crea un usuario en Firebase Auth. Devuelve el diccionario del usuario o None."""
        try:
            # Devolvemos el diccionario completo para que el ViewModel obtenga el ID y el token
            user = self.auth.create_user_with_email_and_password(email, password)
            return user
        except Exception as e:
            print("🔥 ERROR REGISTRO (AUTH):", traceback.format_exc())
            return None

    def login(self, email, password):
        """Autentica un usuario. Devuelve los datos del usuario o None."""
        try:
            user = self.auth.sign_in_with_email_and_password(email, password)
            return user
        except Exception as e:
            print("🔥 ERROR LOGIN (AUTH):", traceback.format_exc())
            return None
    
    def reset_password(self, email):
        """Envía un correo de restablecimiento de contraseña."""
        try:
            self.auth.send_password_reset_email(email)
            return True
        except Exception as e:
            print(f"Error al enviar correo de reseteo: {e}")
            return False
            
    def change_password(self, id_token, new_password):
        """Cambia la contraseña de un usuario logueado."""
        try:
            self.auth.change_password(id_token, new_password)
            return True
        except Exception as e:
            print(f"Error al cambiar password: {e}")
            return False

    def change_email(self, id_token, new_email):
        """Cambia el email de un usuario logueado."""
        try:
            self.auth.change_email(id_token, new_email)
            return True
        except Exception as e:
            print(f"Error al cambiar email: {e}")
            return False