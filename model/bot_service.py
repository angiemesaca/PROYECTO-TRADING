import random
from datetime import datetime, timedelta
# ¡SOLO IMPORTAMOS 'db' (pyrebase)
from firebase_config import db

class BotService:
    def __init__(self):
        # Conexión Pyrebase (para operaciones con token)
        self.db = db
        # ¡ELIMINADO! self.admin_db ya no se usa

    # -----------------------------------------------------------------
    # --- FUNCIONES LLAMADAS POR EL VIEWMODEL (USAN TOKEN) ---
    # (Todas estas ya las tenías y funcionan)
    # -----------------------------------------------------------------

    def get_bot_settings(self, user_id, token):
        try:
            data = self.db.child("bot_settings").child(user_id).get(token=token)
            return data.val()
        except Exception as e:
            print(f"Error al leer ajustes del bot: {e}")
            return None

    def save_bot_settings(self, user_id, data, token):
        try:
            self.db.child("bot_settings").child(user_id).set(data, token=token)
            return True
        except Exception as e:
            print(f"Error al guardar ajustes del bot: {e}")
            return False

    def get_trade_log(self, user_id, token):
        try:
            data = self.db.child("trade_log").child(user_id).get(token=token)
            return data.val()
        except Exception as e:
            print(f"Error al leer trade log: {e}")
            return {}
    
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
        """Borra el historial de trades de un usuario."""
        try:
            self.db.child("trade_log").child(user_id).remove(token=token)
            return True
        except Exception as e:
            print(f"Error al borrar trade log: {e}")
            return False
            
    # --- ¡NUESTRA FUNCIÓN DE BACKTEST! ---
    def generate_mock_trade_log(self, user_id, token, asset_name="crypto_btc_usd"):
        """
        Simula un historial de operaciones (log) para el bot.
        ¡Usa .set() para REEMPLAZAR el log anterior (es un backtest nuevo!)
        """
        print(f"--- Generando historial mock de trades para {user_id} con {asset_name} ---")
        try:
            log_ref = self.db.child("trade_log").child(user_id)
            new_log_data = {}
            
            # Lógica de Precio
            base_price = 60000 
            price_fluctuation = 500
            decimals = 2
            asset_display_name = "BTC/USD"

            if "eth" in asset_name:
                base_price = 3000
                price_fluctuation = 100
                asset_display_name = "ETH/USD"
            elif "sol" in asset_name:
                base_price = 150
                price_fluctuation = 10
                asset_display_name = "SOL/USD"
            elif "eur" in asset_name:
                base_price = 1.10
                price_fluctuation = 0.01
                decimals = 4
                asset_display_name = "EUR/USD"
            elif "oro" in asset_name:
                base_price = 2300
                price_fluctuation = 20
                asset_display_name = "Oro (XAU)"
            elif "spx" in asset_name:
                base_price = 5000
                price_fluctuation = 50
                asset_display_name = "S&P 500"
            
            pnl_total = 0
            current_time = datetime.now() - timedelta(days=5)

            # Generamos 30 trades
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
                # Usamos generate_key para crear un ID único
                new_log_data[self.db.generate_key()] = trade_data
                base_price = current_price
                
            # ¡IMPORTANTE! Usamos .set() para REEMPLAZAR el historial
            # con este nuevo backtest.
            log_ref.set(new_log_data, token=token)
            print("--- Historial mock de trades generado (Backtest). ---")
            return True
        except Exception as e:
            print(f"Error al generar log mock: {e}")
            import traceback
            print(traceback.format_exc())
            return False