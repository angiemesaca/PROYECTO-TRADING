💼 Wallet Trainer: Bot de Trading Algorítmico
Wallet Trainer es una aplicación web robusta construida en Flask (Python) que permite a los usuarios diseñar, probar y desplegar estrategias de trading. La plataforma se conecta a un broker real (Alpaca) para ejecutar operaciones en un entorno de "paper trading" y utiliza Firebase para la gestión de usuarios y datos.

(Acción requerida: Reemplaza esta URL de Imgur con la captura de pantalla de tu dashboard, como image_ac3b82.png. Súbela a un sitio como Imgur o usa un enlace directo si tu repo es público).

✨ Características Principales
Autenticación de Usuarios: Sistema completo de registro, inicio de sesión (Login), recuperación de contraseña y gestión de perfiles de usuario.

Configuración del Bot: Interfaz para que los usuarios definan su estrategia, incluyendo el activo a operar (ej. SPY), el riesgo y los indicadores.

Sugerencias con IA: Integración con la API de Gemini (Google) para proveer análisis y sugerencias de trading basadas en el activo seleccionado por el usuario.

Panel de Rendimiento: Un dashboard dinámico que muestra el historial de operaciones, el PNL (Profit/Loss) total y acumulado, y un gráfico de rendimiento en tiempo real (Chart.js).

Conexión con Broker Real: A diferencia de una simulación simple, la app se conecta directamente a la API de Alpaca para ejecutar trades reales en un entorno de "paper trading".

🏛️ Arquitectura del Proyecto (MVVM)
El proyecto sigue una arquitectura Model-View-ViewModel (MVVM), que separa las responsabilidades de la siguiente manera:

app.py (Controlador/Router):

Es el punto de entrada principal de Flask.

Define todas las rutas (endpoints) de la aplicación (ej. /login, /dashboard, /run_backtest).

Maneja las solicitudes y respuestas HTTP.

Actúa como el pegamento que inicializa y conecta el ViewModel.

viewmodels/main_viewmodel.py (ViewModel):

Es el "cerebro" de la aplicación.

Contiene toda la lógica de negocio (ej. login(), get_performance_data(), generate_mock_trades()).

Nunca interactúa directamente con el HTML.

Llama a los Servicios en el model para obtener o guardar datos (ej. bot_service.get_trade_log()).

model/ (Model):

Contiene todos los servicios de datos. Es la única capa que "habla" con el exterior.

auth_service.py: Maneja la lógica de autenticación con Firebase.

bot_service.py: Maneja la lógica de la base de datos para el bot (guardar trades, obtener ajustes).

broker_client.py: (¡Componente Clave!) Servicio dedicado que maneja toda la comunicación con la API del broker Alpaca.

templates/ (View):

Contiene todos los archivos HTML (.html) que el usuario ve.

Utiliza el motor de plantillas Jinja2 para mostrar datos dinámicos que le pasa app.py.

Ejemplos: rendimientos.html, ajustes.html, login.html.

static/ (View):

Contiene los archivos estáticos como style.css y cualquier archivo JavaScript.

💻 Tecnologías Utilizadas
Backend: Python 3.10+, Flask, Gunicorn

Frontend: HTML5, CSS3, Bootstrap 5, JavaScript ES6+

Base de Datos: Firebase Realtime Database (a través de Pyrebase4)

Broker API: Alpaca Trade API (alpaca-trade-api)

IA (Sugerencias): Google Gemini API (google-generativeai)

Gráficos: Chart.js

🚀 Instalación y Despliegue
1. Configuración Local
Sigue estos pasos para correr el proyecto en tu máquina local.

Clonar el repositorio:

Bash

git clone https://tu-repositorio-url.com/wallet-trainer.git
cd wallet-trainer
Crear un entorno virtual:

Bash

python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
Instalar dependencias:

Bash

pip install -r requirements.txt
Configurar variables de entorno: Crea un archivo llamado .env en la raíz del proyecto y añade tus claves API:

Fragmento de código

GEMINI_API_KEY="tu_clave_de_gemini_aqui"
ALPACA_KEY_ID="tu_key_id_de_alpaca_paper_trading"
ALPACA_SECRET_KEY="tu_secret_key_de_alpaca_paper_trading"
Configurar Firebase: Coloca tu archivo de configuración de Firebase (obtenido de tu consola de Firebase) en la raíz del proyecto con el nombre: firebase_config.json.

Ejecutar la aplicación:

Bash

python app.py
La app estará disponible en http://127.0.0.1:5000.

2. Despliegue en Render
Este proyecto está configurado para desplegarse fácilmente en Render.

Servicio: Crea un nuevo "Web Service" en Render y conéctalo a tu repositorio de GitHub.

Comando de Build:

Bash

pip install -r requirements.txt
Comando de Inicio:

Bash

gunicorn app:app
Variables de Entorno: Ve a la pestaña "Environment" y añade las siguientes variables:

GEMINI_API_KEY

ALPACA_KEY_ID

ALPACA_SECRET_KEY

PYTHON_VERSION (ej. 3.10.0)

Archivos Secretos (Secret Files): Añade un nuevo "Secret File" llamado firebase_config.json y pega el contenido de tu JSON de configuración de Firebase.

📈 Flujo de Conexión con el Broker (¡IMPORTANTE!)
La característica principal de esta versión es la conexión a un broker real, cumpliendo con la retroalimentación del Sprint. Así es como funciona el flujo de "Ejecutar Simulación":

1. El Desafío: El Mercado Cerrado
El mercado de acciones (ej. SPY, el activo que mejor funciona con la cuenta de Alpaca) opera de 9:30 AM a 4:00 PM (Hora del Este). La mayoría del tiempo, la app será probada con el mercado cerrado.

2. La Solución: Lógica de Demo Inteligente
El código en model/broker_client.py maneja esta situación de forma robusta:

Intento de Trade: Cuando el usuario presiona "Ejecutar Simulación", la app se conecta a Alpaca y envía una orden de compra real para 1 acción de SPY.

Respuesta del Broker: El broker recibe la orden y responde con el status accepted. Esto confirma que la conexión, las claves API y el símbolo (SPY) son correctos, pero la orden no se llena (filled) porque el mercado está cerrado.

Detección y Cancelación: Nuestro código detecta el status accepted (en lugar de filled). Para prevenir que la orden se ejecute al día siguiente, la app cancela la orden inmediatamente (self.api.cancel_order(...)).

Registro de Demo: Para que el usuario vea un resultado en el dashboard, la app genera un PNL aleatorio (ej. -$2.38 o +$3.64) y lo guarda en Firebase.

Este flujo demuestra que la conexión con el broker es 100% funcional, al mismo tiempo que permite hacer demos de la app 24/7 sin depender del horario del mercado.

3. Cuando el Mercado está Abierto
Si el botón se presiona durante horas de mercado:

El status de la orden será filled.

El código ejecutará la lógica real: comprará la acción, la venderá 5 segundos después, y registrará el PNL real (ej. +$0.01 o -$0.01) en la base de datos.

En este caso, el balance de la cuenta de "Paper Trading" en Alpaca se modificará.

(Fin del README)