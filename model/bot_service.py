import random
from datetime import datetime, timedelta

# Importamos AMBAS conexiones
from firebase_config import db, admin_db_ref

class BotService:
    def __init__(self):
        self.db = db
        self.admin_db = admin_db_ref

    # ... (Todas las funciones que usan TOKEN se quedan igual) ...
    
    def get_bot_settings(self, user_id, token):
        try:
            data = self.db.child("bot_settings").child(user_id).get(token=token)
            return data.val()
        except Exception as e:
            print(f"[ERROR] get_bot_settings (con token): {e}")
            return None

    def save_bot_settings(self, user_id, data, token):
        try:
            self.db.child("bot_settings").child(user_id).set(data, token=token)
            return True
        except Exception as e:
            print(f"[ERROR] save_bot_settings (con token): {e}")
            return False

    def get_trade_log(self, user_id, token):
        try:
            data = self.db.child("trade_log").child(user_id).get(token=token)
            return data.val()
        except Exception as e:
            print(f"[ERROR] get_trade_log (con token): {e}")
            return {}
    
    # ... (El resto de tus funciones con token: get_api_keys, save_api_key, etc.) ...
    
    def get_api_keys(self, user_id, token):
        try:
            data = self.db.child("api_keys").child(user_id).get(token=token)
            return data.val()
        except Exception as e:
            print(f"Error al leer API keys: {e}")
            return None

    def save_api_key(self, user_id, key_data, token):
        try:
            exchange_name = key_data['exchange'].lower()
            self.db.child("api_keys").child(user_id).child(exchange_name).set(key_data, token=token)
            return True
        except Exception as e:
            print(f"Error al guardar API key: {e}")
            return False
            
    def delete_api_key(self, user_id, exchange_name, token):
        try:
            self.db.child("api_keys").child(user_id).child(exchange_name.lower()).remove(token=token)
            return True
        except Exception as e:
            print(f"Error al borrar API key: {e}")
            return False
            
    def clear_trade_log(self, user_id, token):
        try:
            self.db.child("trade_log").child(user_id).remove(token=token)
            return True
        except Exception as e:
            print(f"Error al borrar trade log: {e}")
            return False
            
    def generate_mock_trade_log(self, user_id, token, asset_name="crypto_btc_usd"):
        # Esta función ya no se usa, pero la dejamos por si acaso
        print(f"--- Generando historial mock (función antigua) ---")
        return True

    # -----------------------------------------------------------------
    # --- ¡FUNCIONES DEL BOT (SIN TOKEN) CON MÁS LOGS! ---
    # -----------------------------------------------------------------

    def execute_bot_cycle(self):
        """
        Esta es la función MAESTRA que llama el scheduler.
        NO usa token porque es el servidor.
        """
        
        # ¡NUEVO LOG!
        print("[BOT_CYCLE] ¡Iniciando ciclo! Verificando Admin DB...")
        
        if self.admin_db is None:
            print("[BOT_CYCLE_ERROR] ¡Admin DB es None! El bot no puede leer.")
            return

        print("[BOT_CYCLE] Admin DB OK. Intentando leer 'bot_settings'...")
        
        try:
            all_settings = self.admin_db.child("bot_settings").get()

            if not all_settings:
                # ¡NUEVO LOG!
                print("[BOT_CYCLE] No se encontraron 'bot_settings' en la base de datos.")
                return

            # ¡NUEVO LOG!
            print(f"[BOT_CYCLE] Encontrados {len(all_settings)} perfiles de settings. Iterando...")

            active_bots_found = 0
            for user_id, settings in all_settings.items():
                
                # ¡NUEVO LOG!
                # print(f"[BOT_CYCLE] Chequeando User: {user_id}...") # (Demasiado ruidoso)

                if settings and settings.get('isActive', False):
                    # ¡NUEVO LOG!
                    print(f"[BOT_CYCLE_ACTIVE] ¡Bot ACTIVO detectado para {user_id}! Ejecutando simulación...")
                    active_bots_found += 1
                    self.run_live_simulation(user_id, settings)
                
            if active_bots_found == 0:
                print("[BOT_CYCLE] Ciclo terminado. No se encontraron bots activos.")

        except Exception as e:
            # ¡NUEVO LOG!
            print(f"[BOT_CYCLE_ERROR] ¡CRASH! El ciclo del bot falló: {e}")

    def run_live_simulation(self, user_id, settings):
        """
        Simula UN solo trade "en vivo" y lo AÑADE al historial.
        """
        try:
            # ¡NUEVO LOG!
            print(f"[SIMULATION] Iniciando simulación para {user_id}...")
            
            # --- Lógica de PNL Acumulado ---
            last_trade = None
            last_pnl_acumulado = 0.0
            last_price = 0.0

            # 1. Leer el último trade (si existe)
            log_ref = self.admin_db.child("trade_log").child(user_id)
            # 'limitToLast(1)' es la forma eficiente de obtener solo el último
            last_trade_query = log_ref.order_by_key().limit_to_last(1).get()

            if last_trade_query:
                # 'last_trade_query' es un diccionario, ej: {'trade_id_xyz': {...}}
                trade_id, trade_data = last_trade_query.popitem()
                last_trade = trade_data
                last_pnl_acumulado = last_trade.get("pnl_acumulado", 0.0)
                last_price = last_trade.get("price", 0.0)
                
                # ¡NUEVO LOG!
                print(f"[SIMULATION] Último trade encontrado. PNL Acum: {last_pnl_acumulado}, Precio: {last_price}")

            # 2. Determinar precio base
            asset_name = settings.get("activo", "crypto_btc_usd")
            base_price = 60000
            price_fluctuation = 500
            asset_display_name = "BTC/USD"
            
            if "eth" in asset_name:
                base_price = 3000
                price_fluctuation = 100
                asset_display_name = "ETH/USD"
            elif "sol" in asset_name:
                base_price = 150
                price_fluctuation = 10
                asset_display_name = "SOL/USD"
            
            # Si ya teníamos un precio, lo usamos como base. Si no, usamos el default.
            if last_price > 0:
                base_price = last_price
            
            # 3. Simular el nuevo trade
            current_price = round(base_price + random.uniform(-price_fluctuation, price_fluctuation), 2)
            pnl_nuevo = round(random.uniform(-50, 75), 2)
            nuevo_pnl_acumulado = round(last_pnl_acumulado + pnl_nuevo, 2)
            
            new_trade_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "asset": asset_display_name,
                "type": random.choice(["buy", "sell"]),
                "price": current_price,
                "pnl": pnl_nuevo,
                "pnl_acumulado": nuevo_pnl_acumulado
            }
            
            # 4. Guardar el nuevo trade usando .push()
            log_ref.push(new_trade_data)
            
            # ¡NUEVO LOG!
            print(f"[SIMULATION] ¡Éxito! Nuevo trade guardado para {user_id}. Nuevo PNL Acum: {nuevo_pnl_acumulado}")

        except Exception as e:
            # ¡NUEVO LOG!
            print(f"[SIMULATION_ERROR] ¡CRASH! Falló la simulación para {user_id}: {e}")