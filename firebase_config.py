# firebase_config.py (CORREGIDO - Versión Simple)

import pyrebase

# Esta es la configuración web simple.
# NO carga el serviceAccount.json
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

# Inicializa la app (ahora como un cliente normal, no admin)
firebase = pyrebase.initialize_app(firebaseConfig)

# El resto es igual
auth = firebase.auth()
db = firebase.database()
# storage = firebase.storage() # (Sigue comentado, está bien)

print("--- Firebase Configurado (Modo Usuario Normal) ---")