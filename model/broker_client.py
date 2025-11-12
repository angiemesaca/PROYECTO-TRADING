import alpaca_trade_api as tradeapi
import os
from datetime import datetime
import time
import uuid # Para generar IDs únicos para Firebase

class BrokerClient:
    def __init__(self):
        self.api = None
        try:
            # ¡Lee las claves de las variables de entorno de Render!
            key_id = os.environ.get('ALPACA_KEY_ID')
            secret_key = os.environ.get('ALPACA_SECRET_KEY')
            
            if not key_id or not secret_key:
                print("ERROR: Faltan las variables de entorno de Alpaca (ALPACA_KEY_ID o ALPACA_SECRET_KEY)")
                return

            # Nos conectamos al endpoint de "paper trading" (simulación)
            base_url = "https://paper-api.alpaca.markets"
            
            self.api = tradeapi.REST(key_id, secret_key, base_url, api_version='v2')
            
            # Verificamos la conexión
            account = self.api.get_account()
            print(f"--- Conexión exitosa a Alpaca. Cuenta de Paper Trading: ${account.equity} ---")

        except Exception as e:
            print(f"Error al inicializar el cliente de Alpaca: {e}")

    def _traducir_asset(self, asset_name):
        """Traduce el nombre de tu app a un símbolo de Alpaca."""
        traducciones = {
            "crypto_btc_usd": "BTC/USD",
            "crypto_eth_usd": "ETH/USD",
            "crypto_sol_usd": "SOL/USD",
            "forex_eur_usd": "EUR/USD",
            "commodities_oro": "XAU/USD",
            "indices_spx500": "SPY"  # Usamos el ETF SPY para el S&P 500
        }
        
        # Por defecto, usamos SPY si no se encuentra
        simbolo = traducciones.get(asset_name, "SPY")
        
        # Alpaca usa 'BTCUSD' para crypto, no 'BTC/USD'
        if "crypto" in asset_name:
            simbolo = simbolo.replace('/', '')
            
        return simbolo

    def ejecutar_trade_y_obtener_log(self, asset_name):
        """
        La función principal. Ejecuta un trade y devuelve el log
        en el formato que tu app espera.
        """
        if not self.api:
            print("Error: El cliente de Alpaca no está inicializado.")
            return {}

        simbolo = self._traducir_asset(asset_name)
        
        try:
            print(f"--- Intentando ejecutar trade en Alpaca para: {simbolo} ---")
            
            # 1. Obtenemos el PNL de la cuenta ANTES del trade
            #    (En una app real, esto sería más complejo)
            #    Por ahora, nos enfocamos en ejecutar.
            
            # 2. Ejecutamos una orden de compra (ej: 1 unidad o $100)
            #    Para cryptos, usamos 'notional' (cantidad en USD)
            #    Para acciones (SPY), usamos 'qty' (cantidad de acciones)
            
            tipo_orden = 'market'
            lado = 'buy'
            time_in_force = 'gtc'
            
            if simbolo in ['BTCUSD', 'ETHUSD', 'SOLUSD']:
                qty_o_notional = {'notional': 100} # Compra $100 de crypto
            else:
                qty_o_notional = {'qty': 1} # Compra 1 acción de SPY o 1 unidad de Forex

            print(f"Enviando orden: {lado} {simbolo} ({qty_o_notional})")

            orden = self.api.submit_order(
                symbol=simbolo,
                side=lado,
                type=tipo_orden,
                time_in_force=time_in_force,
                **qty_o_notional
            )
            
            # 3. Esperamos un segundo para que la orden se ejecute (solo para demo)
            time.sleep(2)
            
            # 4. Obtenemos la orden ejecutada para saber el precio y PNL
            orden_ejecutada = self.api.get_order(orden.id)
            
            if orden_ejecutada.status != 'filled':
                print(f"La orden no se completó (status: {orden_ejecutada.status}). Se intentará de nuevo más tarde.")
                return {} # Devolvemos un log vacío

            precio_compra = float(orden_ejecutada.filled_avg_price)
            
            # 5. ¡Cerramos la posición inmediatamente para saber el PNL!
            #    Esto es un "scalp" solo para demostrar el PNL.
            print(f"Cerrando posición para {simbolo}...")
            posicion_cerrada = self.api.close_position(simbolo)
            
            # 6. Esperamos a que se cierre
            time.sleep(2)
            
            # 7. Obtenemos el PNL de la posición cerrada
            #    Alpaca lo devuelve en 'unrealized_pl' justo antes de cerrar, 
            #    o en 'pl' en la orden de cierre.
            
            # Vamos a buscar la última posición cerrada en el log de actividades
            actividades = self.api.get_activities(activity_types='FILL', direction='desc', page_size=10)
            
            pnl_trade = 0.0
            for act in actividades:
                if act.symbol == simbolo and act.side == 'sell':
                    pnl_trade = float(act.pl)
                    break # Encontramos el PNL de nuestro trade
            
            if pnl_trade == 0.0:
                 print("No se pudo determinar el PNL inmediato, se registrará como 0.")

            print(f"--- Trade completado. PNL: ${pnl_trade} ---")

            # 8. Creamos el registro para Firebase (en el formato que ya tienes)
            trade_id = str(uuid.uuid4()) # ID único
            trade_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "asset": simbolo,
                "type": "buy-sell (scalp)",
                "price": precio_compra,
                "pnl": round(pnl_trade, 2),
                "pnl_acumulado": round(pnl_trade, 2) # Es el primer y único trade
            }
            
            # Devolvemos el log en el formato que Firebase espera ({id: data})
            new_log_data = {
                trade_id: trade_data
            }
            
            return new_log_data

        except Exception as e:
            print(f"Error al ejecutar trade en Alpaca: {e}")
            # Si el error es "market is closed", infórmalo
            if "market is closed" in str(e):
                 print("El mercado está cerrado. No se puede ejecutar el trade.")
            return {}