# Importamos el 'auth' de Pyrebase
from firebase_config import auth
import traceback

class AuthService:
    
    def __init__(self):
        # Guardamos la instancia de auth de pyrebase
        self.auth = auth

    def login(self, email, password):
        """
        Intenta iniciar sesión con email/pass.
        Devuelve los datos del usuario si es exitoso, o None si falla.
        """
        try:
            user = self.auth.sign_in_with_email_and_password(email, password)
            return user
        except Exception as e:
            print(f"Error en login: {e}")
            return None

    def register(self, email, password):
        """
        Intenta registrar un nuevo usuario.
        Devuelve los datos del usuario si es exitoso, o None si falla.
        """
        try:
            user = self.auth.create_user_with_email_and_password(email, password)
            # Podríamos enviar un email de verificación aquí si quisiéramos
            # self.auth.send_email_verification(user['idToken'])
            return user
        except Exception as e:
            print(f"Error en registro: {e}")
            return None

    def change_password(self, id_token, new_password):
        """
        Cambia la contraseña de un usuario logueado.
        """
        try:
            self.auth.change_password(id_token, new_password)
            return True
        except Exception as e:
            print(f"Error al cambiar contraseña: {e}")
            return False
            
    def change_email(self, id_token, new_email):
        """
        Cambia el email de un usuario logueado.
        """
        try:
            self.auth.change_email(id_token, new_email)
            return True
        except Exception as e:
            print(f"Error al cambiar email: {e}")
            return False
            
    # --- ¡ESTA ES LA FUNCIÓN QUE PEDISTE! ---
    def reset_password(self, email):
        """
        Envía el correo de restablecimiento de contraseña.
        Firebase (Pyrebase) maneja esto por nosotros.
        """
        try:
            # Esta es la función mágica de Firebase:
            self.auth.send_password_reset_email(email)
            return True
        except Exception as e:
            # Imprimimos el error en la consola del servidor
            print(f"Error al enviar correo de reseteo: {e}")
            # NOTA: No devolvemos False aquí a propósito.
            # Por seguridad, no queremos decirle al usuario
            # si el correo "no existe". Simplemente
            # le decimos que "si existe, se enviará".
            # El 'flash' en tu app.py maneja esto bien.
            return False