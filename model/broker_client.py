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
        """Traduce el nombre de tu app (ej: crypto_btc_usd) 
           a un símbolo que Alpaca entiende (ej: BTCUSD)."""
        
        traducciones = {
            "crypto_btc_usd": "BTC/USD",
            "crypto_eth_usd": "ETH/USD",
            "crypto_sol_usd": "SOL/USD",
            "forex_eur_usd": "EUR/USD",
            "commodities_oro": "XAU/USD", # Oro
            "indices_spx500": "SPY"  # Usamos el ETF SPY para el S&P 500
        }
        
        # Si no lo encontramos, usamos SPY como default
        simbolo = traducciones.get(asset_name, "SPY")
        
        # Importante: Alpaca usa 'BTCUSD' (sin /) para crypto, oro y FOREX
        if "crypto" in asset_name or "oro" in asset_name or "forex" in asset_name:
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
            
            # 1. Ejecutamos una orden de compra
            tipo_orden = 'market'
            lado = 'buy'
            time_in_force = 'gtc'
            
            if simbolo in ['BTCUSD', 'ETHUSD', 'SOLUSD']:
                qty_o_notional = {'notional': 100} # Compra $100 de crypto
            else:
                qty_o_notional = {'qty': 1} # Compra 1 acción de SPY o 1 unidad de EURUSD

            print(f"Enviando orden: {lado} {simbolo} ({qty_o_notional})")

            orden = self.api.submit_order(
                symbol=simbolo,
                side=lado,
                type=tipo_orden,
                time_in_force=time_in_force,
                **qty_o_notional
            )
            
            # 2. Esperamos 5 segundos
            print("Esperando 5 segundos para que la orden se llene...")
            time.sleep(5)
            
            # 3. Obtenemos la orden ejecutada para saber el precio
            orden_ejecutada = self.api.get_order(orden.id)
            
            print(f"--- Status de la orden después de 5s: {orden_ejecutada.status} ---")

            # --- ¡LÓGICA MEJORADA! ---
            
            # CASO 1: ¡ÉXITO REAL! (El mercado está abierto y la orden se llenó)
            if orden_ejecutada.status == 'filled':
                print("--- ¡Orden 'filled'! El mercado está abierto. Calculando PNL... ---")
                precio_compra = float(orden_ejecutada.filled_avg_price)
                
                # Cerramos la posición para calcular PNL
                print(f"Cerrando posición para {simbolo} para calcular PNL...")
                posicion_cerrada = self.api.close_position(simbolo)
                print("Esperando 5 segundos para que la posición se cierre...")
                time.sleep(5)
                
                # Obtenemos el PNL
                actividades = self.api.get_activities(activity_types='FILL', direction='desc', page_size=10)
                pnl_trade = 0.0
                for act in actividades:
                    if act.symbol == simbolo and act.side == 'sell':
                        if hasattr(act, 'pl'):
                            pnl_trade = float(act.pl)
                            break
                print(f"--- Trade real (paper) completado. PNL: ${pnl_trade} ---")

            # CASO 2: ¡ÉXITO DE DEMO! (El mercado está cerrado, la orden fue 'accepted')
            elif orden_ejecutada.status == 'accepted':
                print("--- ¡Orden 'accepted'! (Mercado cerrado). ---")
                print("--- Cancelando la orden y registrando un trade de demo (PNL $0.0) ---")
                
                # 1. Cancelamos la orden para que no se ejecute mañana
                self.api.cancel_order(orden.id)
                
                # 2. Obtenemos el precio de la última cotización (solo para mostrar algo)
                ultimo_trade = self.api.get_latest_trade(simbolo)
                precio_compra = ultimo_trade.p
                pnl_trade = 0.0 # Es una demo, no hay PNL
                
                print(f"--- Trade de demo (mercado cerrado) registrado. ---")

            # CASO 3: ¡FALLO! (Como el 'new' de Crypto)
            else:
                print(f"La orden no se completó (status: {orden_ejecutada.status}).")
                if orden_ejecutada.status == 'new':
                    self.api.cancel_order(orden.id)
                    print("--- Orden 'new' cancelada. ---")
                raise Exception("La orden no se completó a tiempo.")

            # --- FIN DE LÓGICA MEJORADA ---

            # 7. Creamos el registro para Firebase (para los casos 1 y 2)
            trade_id = str(uuid.uuid4()) # ID único
            trade_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "asset": simbolo,
                "type": "buy-sell (real)",
                "price": precio_compra,
                "pnl": round(pnl_trade, 2),
                "pnl_acumulado": round(pnl_trade, 2)
            }
            
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