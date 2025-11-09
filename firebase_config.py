# firebase_config.py (MODO HÍBRIDO)

import pyrebase
import firebase_admin
from firebase_admin import credentials, db as admin_db
import os

# --- 1. CONFIGURACIÓN PYREBASE (CLIENTE WEB) ---
# (Esto es lo que ya tenías. No se toca nada)
firebaseConfig = {
    "apiKey": "AIzaSyB6JH7VHDIGHB4MQ_uXWYjQOMITp8XWTYA",
    "authDomain": "trading-279b6.firebaseapp.com",
    "databaseURL": "https://trading-279b6-default-rtdb.firebaseio.com",
    "projectId": "trading-279b6",
    "storageBucket": "trading-279b6.appspot.com",
    "messagingSenderId": "812149328395",
    "appId": "1:812149328395:web:4c1015c75465b73df1550e",
    "measurementId": "G-SCZQCKSZPB"
}

firebase = pyrebase.initialize_app(firebaseConfig)

# Exportaciones para el ViewModel y las rutas (lo que ya usas)
auth = firebase.auth()
db = firebase.database()
print("--- Firebase Configurado (Modo Usuario Normal) ---")


# --- 2. ¡NUEVO! CONFIGURACIÓN FIREBASE-ADMIN (SERVIDOR) ---
# (Esto es lo que usará el bot en segundo plano)

SERVICE_ACCOUNT_KEY = 'firebase_config.json'

# Comprobamos si el archivo existe
if os.path.exists(SERVICE_ACCOUNT_KEY):
    try:
        cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
        
        # Evita inicializar la app de admin si ya se inicializó
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {
                'databaseURL': firebaseConfig['databaseURL'] # Usamos la misma URL
            })
            print("--- Firebase Admin SDK (Modo Servidor) INICIALIZADO ---")
        
        # Exportamos la referencia de la DB de Admin
        # La llamamos 'admin_db_ref' para no confundirla con 'db'
        admin_db_ref = admin_db.reference()

    except Exception as e:
        print(f"Error al inicializar Firebase Admin SDK: {e}")
        print("El bot en segundo plano NO funcionará.")
        admin_db_ref = None
else:
    print(f"ADVERTENCIA: No se encontró '{SERVICE_ACCOUNT_KEY}'.")
    print("El bot en segundo plano NO funcionará.")
    admin_db_ref = None