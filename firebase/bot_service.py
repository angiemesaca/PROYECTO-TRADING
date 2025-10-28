import random
from datetime import datetime, timedelta
from firebase_config import db

class BotService:
    def __init__(self):
        self.db = db

    def get_bot_settings(self, user_id, token):
        """Obtiene la configuración del bot para un usuario (autenticado)."""
        try:
            data = self.db.child("bot_settings").child(user_id).get(token=token)
            return data.val()
        except Exception as e:
            print(f"Error al leer ajustes del bot: {e}")
            return {}

    def update_bot_settings(self, user_id, data, token):
        """Actualiza la configuración del bot para un usuario (autenticado)."""
        try:
            self.db.child("bot_settings").child(user_id).update(data, token=token)
            return True
        except Exception as e:
            print(f"Error al actualizar ajustes del bot: {e}")
            return False

    def initialize_bot_settings(self, user_id):
        """Crea ajustes por defecto cuando un usuario se registra."""
        try:
            default_settings = {
                "isActive": False, "riesgo": "medio", "indicadores": "RSI, MACD",
                "horario": "09:00-17:00", "activo": "crypto_btc_usd"
            }
            self.db.child("bot_settings").child(user_id).set(default_settings)
            return True
        except Exception as e:
            print(f"Error al inicializar ajustes del bot: {e}")
            return False

    def generate_mock_trade_log(self, user_id, token, asset_name="crypto_btc_usd"):
        """
        Simula un historial de operaciones (log) para el bot.
        Usa el asset_name (activo) proporcionado para ajustar precios.
        """
        print(f"--- Generando historial mock de trades para {user_id} con el activo {asset_name} ---")
        try:
            log_ref = self.db.child("trade_log").child(user_id)
            new_log_data = {}
            
            # --- LÓGICA DE PRECIO MEJORADA ---
            base_price = 60000         # Default para BTC
            price_fluctuation = 500  # Fluctuación de +/- 500 para BTC
            decimals = 2             # Decimales para el precio
            asset_display_name = "BTC/USD" # Nombre a mostrar en la tabla

            if "forex_eur_usd" in asset_name:
                base_price = 1.10
                price_fluctuation = 0.01 # Fluctuación de +/- 0.01 para EUR
                decimals = 4 # Forex usa más decimales
                asset_display_name = "EUR/USD"
            elif "commodity_oro" in asset_name: # Coincide con el value="commodity_oro"
                base_price = 2300
                price_fluctuation = 20 # Fluctuación de +/- 20 para Oro
                decimals = 2
                asset_display_name = "Oro (XAU)"
            # --- FIN LÓGICA MEJORADA ---

            pnl_total = 0
            current_time = datetime.now() - timedelta(days=5)

            for i in range(30):
                current_time += timedelta(hours=random.randint(2, 6))
                pnl = round(random.uniform(-150, 250), 2)
                pnl_total += pnl
                
                # El precio fluctúa alrededor del precio anterior
                current_price = base_price + random.uniform(-price_fluctuation, price_fluctuation)
                
                trade_data = {
                    "timestamp": current_time.strftime("%Y-%m-%d %H:%M"),
                    "asset": asset_display_name, # Usa el nombre "bonito"
                    "type": random.choice(["buy", "sell"]),
                    "price": round(current_price, decimals),
                    "pnl": pnl,
                    "pnl_acumulado": round(pnl_total, 2)
                }
                new_log_data[self.db.generate_key()] = trade_data
                base_price = current_price # El siguiente precio se basa en este
                
            log_ref.set(new_log_data, token=token)

            print("--- Historial mock de trades generado. ---")
            return True
        except Exception as e:
            print(f"Error al generar log mock: {e}")
            import traceback
            print(traceback.format_exc())
            return False

    def get_trade_log(self, user_id, token):
        """Obtiene el historial de trades para un usuario (autenticado)."""
        try:
            data = self.db.child("trade_log").child(user_id).get(token=token)
            return data.val()
        except Exception as e:
            print(f"Error al leer trade log: {e}")
            return {}