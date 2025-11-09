import random
from datetime import datetime, timedelta
import traceback # Para ver errores más fácil

# ¡Importamos AMBAS conexiones!
from firebase_config import db, admin_db_ref

class BotService:
    def __init__(self):
        # Conexión Pyrebase (para operaciones con token)
        self.db = db
        # Conexión Admin (para operaciones del bot sin token)
        self.admin_db = admin_db_ref

    # -----------------------------------------------------------------
    # --- FUNCIONES LLAMADAS POR EL VIEWMODEL (USAN TOKEN) ---
    # (Estas funciones se quedan EXACTAMENTE IGUAL)
    # -----------------------------------------------------------------

    def get_bot_settings(self, user_id, token):
        """Obtiene la configuración del bot para un usuario (autenticado)."""
        try:
            data = self.db.child("bot_settings").child(user_id).get(token=token)
            return data.val()
        except Exception as e:
            print(f"Error al leer ajustes del bot: {e}")
            return None

    def save_bot_settings(self, user_id, data, token):
        """Guarda o REEMPLAZA la configuración del bot (autenticado)."""
        try:
            self.db.child("bot_settings").child(user_id).set(data, token=token)
            return True
        except Exception as e:
            print(f"Error al guardar ajustes del bot: {e}")
            return False

    def get_trade_log(self, user_id, token):
        """Obtiene el historial de trades para un usuario (autenticado)."""
        try:
            data = self.db.child("trade_log").child(user_id).get(token=token)
            return data.val()
        except Exception as e:
            print(f"Error al leer trade log: {e}")
            return {}

    def clear_trade_log(self, user_id, token):
        """Borra el historial de trades de un usuario (autenticado)."""
        try:
            # Esta función es llamada por el ViewModel, por eso usa token
            self.db.child("trade_log").child(user_id).remove(token=token)
            return True
        except Exception as e:
            print(f"Error al borrar trade log: {e}")
            return False

    # ... (El resto de tus funciones de 'pyrebase' como save_api_key, etc. van aquí) ...
    
    # Copiamos las que faltaban de tu archivo original
    def generate_mock_trade_log(self, user_id, token, asset_name="crypto_btc_usd"):
        """Simula un historial de operaciones (log) para el bot."""
        print(f"--- Generando historial mock de trades para {user_id} con el activo {asset_name} ---")
        try:
            log_ref = self.db.child("trade_log").child(user_id)
            new_log_data = {}
            
            base_price = 60000 
            price_fluctuation = 500
            decimals = 2
            asset_display_name = "BTC/USD"

            if "forex_eur_usd" in asset_name:
                base_price = 1.10
                price_fluctuation = 0.01
                decimals = 4
                asset_display_name = "EUR/USD"
            elif "commodity_oro" in asset_name:
                base_price = 2300
                price_fluctuation = 20
                decimals = 2
                asset_display_name = "Oro (XAU)"
            elif "crypto_eth_usd" in asset_name:
                base_price = 3000
                price_fluctuation = 100
                decimals = 2
                asset_display_name = "ETH/USD"
            elif "crypto_sol_usd" in asset_name:
                base_price = 150
                price_fluctuation = 10
                decimals = 2
                asset_display_name = "SOL/USD"
            elif "index_spx_500" in asset_name:
                base_price = 5000
                price_fluctuation = 50
                decimals = 2
                asset_display_name = "S&P 500"

            pnl_total = 0
            current_time = datetime.now() - timedelta(days=5)

            for i in range(30):
                current_time += timedelta(hours=random.randint(2, 6))
                pnl = round(random.uniform(-150, 250), 2)
                pnl_total += pnl
                current_price = base_price + random.uniform(-price_fluctuation, price_fluctuation)
                
                trade_data = {
                    "timestamp": current_time.strftime("%Y-%m-%d %H:%M"),
                    "asset": asset_display_name,
                    "type": random.choice(["buy", "sell"]),
                    "price": round(current_price, decimals),
                    "pnl": pnl,
                    "pnl_acumulado": round(pnl_total, 2)
                }
                # Usamos .push() para generar IDs únicos
                log_ref.push(trade_data, token=token)
                base_price = current_price
            
            # log_ref.set(new_log_data, token=token) # Error, .set() no funciona con .push()
            print("--- Historial mock de trades generado. ---")
            return True
        except Exception as e:
            print(f"Error al generar log mock: {e}")
            print(traceback.format_exc())
            return False

    def get_api_keys(self, user_id, token):
        """Obtiene todas las API keys de un usuario."""
        try:
            data = self.db.child("api_keys").child(user_id).get(token=token)
            return data.val()
        except Exception as e:
            print(f"Error al leer API keys: {e}")
            return None

    def save_api_key(self, user_id, key_data, token):
        """Guarda o actualiza una API key."""
        try:
            exchange_name = key_data['exchange'].lower()
            self.db.child("api_keys").child(user_id).child(exchange_name).set(key_data, token=token)
            return True
        except Exception as e:
            print(f"Error al guardar API key: {e}")
            return False
            
    def delete_api_key(self, user_id, exchange_name, token):
        """Borra una API key."""
        try:
            self.db.child("api_keys").child(user_id).child(exchange_name.lower()).remove(token=token)
            return True
        except Exception as e:
            print(f"Error al borrar API key: {e}")
            return False

    # -----------------------------------------------------------------
    # --- ¡NUEVO! FUNCIONES LLAMADAS POR EL SCHEDULER (SIN TOKEN) ---
    # -----------------------------------------------------------------

    def execute_bot_cycle(self):
        """
        Esta es la función MAESTRA que llama el scheduler.
        NO usa token porque es el servidor.
        """
        if self.admin_db is None:
            print("Ciclo del bot omitido: Firebase Admin SDK no está inicializado.")
            return

        print(f"[{datetime.now()}] Ejecutando ciclo del bot...")
        try:
            all_settings = self.admin_db.child("bot_settings").get()

            if not all_settings:
                print("No hay configuraciones de bot en la DB.")
                return

            for user_id, settings in all_settings.items():
                if settings and settings.get('isActive', False):
                    print(f"Bot activo detectado para usuario: {user_id}. Ejecutando estrategia...")
                    # --- ¡LÓGICA MEJORADA! ---
                    self.run_live_simulation(user_id, settings)
                
        except Exception as e:
            print(f"Error en el ciclo del bot: {e}")

    # --- ¡FUNCIÓN MODIFICADA Y MEJORADA! ---
    def run_live_simulation(self, user_id, settings):
        """
        Simula UN solo trade "en vivo" basándose en el trade ANTERIOR.
        Usa .push() en lugar de .set() para no borrar lo anterior.
        """
        try:
            # 1. Obtenemos el nombre del activo
            asset_name = settings.get("activo", "crypto_btc_usd")
            asset_display_name = "SIMULADO"
            default_start_price = 60000
            
            try:
                asset_parts = asset_name.split('_')
                asset_display_name = asset_parts[1].upper() + "/" + asset_parts[2].upper()
                if asset_parts[1] == "eth": default_start_price = 3000
                if asset_parts[1] == "sol": default_start_price = 150
                if asset_parts[1] == "eur": default_start_price = 1.1
            except Exception:
                pass

            # --- ¡NUEVA LÓGICA DE PNL Y PRECIO! ---
            last_price = default_start_price
            last_pnl_acumulado = 0

            # 2. Intentamos leer el último trade para obtener el precio y pnl anterior
            # Usamos .order_by_key().limit_to_last(1) para obtener el último trade añadido
            last_trade_query = self.admin_db.child("trade_log").child(user_id).order_by_key().limit_to_last(1).get()
            
            if last_trade_query:
                try:
                    # last_trade_query es un dict como {'-M...abc': {...}}
                    last_trade_key = list(last_trade_query.keys())[0]
                    last_trade_data = last_trade_query[last_trade_key]
                    
                    last_price = last_trade_data.get("price", last_price)
                    last_pnl_acumulado = last_trade_data.get("pnl_acumulado", 0)
                except Exception as e:
                    print(f"Advertencia: No se pudo leer el último trade para {user_id}. {e}")


            # 3. Simulamos un nuevo precio (ligera variación del anterior)
            price_change_percent = random.uniform(-0.005, 0.005) # +/- 0.5%
            new_price = round(last_price * (1 + price_change_percent), 4)
            
            # 4. Simulamos un nuevo PNL
            new_pnl = round(random.uniform(-50, 75), 2)
            
            # 5. Calculamos el PNL Acumulado (¡EL PASO MÁS IMPORTANTE!)
            new_pnl_acumulado = round(last_pnl_acumulado + new_pnl, 2)

            # 6. Preparamos el nuevo trade
            new_trade_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "asset": asset_display_name,
                "type": random.choice(["buy", "sell"]),
                "price": new_price,
                "pnl": new_pnl,
                "pnl_acumulado": new_pnl_acumulado # ¡Corregido!
            }
            
            # 7. Usamos el Admin SDK para AÑADIR (push) el nuevo trade
            self.admin_db.child("trade_log").child(user_id).push(new_trade_data)
            print(f"Trade (realista) añadido para {user_id}. PNL Acum: {new_pnl_acumulado}")

        except Exception as e:
            print(f"Error crítico en run_live_simulation para {user_id}: {e}")
            print(traceback.format_exc()) # Imprime el error completo