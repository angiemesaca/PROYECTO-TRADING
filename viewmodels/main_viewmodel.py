from model.auth_service import AuthService
from model.db_service import DBService
from model.bot_service import BotService
import datetime
import os
import time
import ccxt 
import pandas as pd 
import yfinance as yf # Librería para Stocks y Forex
import traceback

class MainViewModel:
    def __init__(self):
        self.auth_service = AuthService()
        self.db_service = DBService()
        self.bot_service = BotService()
        self.markets = self.db_service.get_markets()
        
        # Cliente Crypto (Kraken) - No bloquea en EE.UU.
        self.exchange = ccxt.kraken({
            'enableRateLimit': True
        })

    # --- LÓGICA HÍBRIDA (ROUTER) ---
    def _get_symbol_and_source(self, asset_id):
        # ... (inicio de la función) ...
        if not asset_id: return ('BTC/USD', 'crypto')
        asset_id = asset_id.lower()
        
        # --- COLOMBIA (ADRs en NYSE) ---
        if 'ecopetrol' in asset_id: return ('EC', 'yahoo')
        if 'bancolombia' in asset_id: return ('CIB', 'yahoo')
        if 'aval' in asset_id: return ('AVAL', 'yahoo')
        if 'nubank' in asset_id: return ('NU', 'yahoo') # NuBank también es popular

        # --- CRIPTOS (Kraken) ---
        if 'btc' in asset_id: return ('BTC/USD', 'crypto')
        if 'eth' in asset_id: return ('ETH/USD', 'crypto')
        if 'sol' in asset_id: return ('SOL/USD', 'crypto')
        if 'ada' in asset_id: return ('ADA/USD', 'crypto')
        
        # --- FOREX (Yahoo Finance) ---
        if 'eur_usd' in asset_id: return ('EURUSD=X', 'yahoo')
        if 'gbp_usd' in asset_id: return ('GBPUSD=X', 'yahoo')
        if 'usd_jpy' in asset_id: return ('JPY=X', 'yahoo')
        
        # --- STOCKS / INDICES / COMMODITIES (Yahoo Finance) ---
        if 'tsla' in asset_id: return ('TSLA', 'yahoo')
        if 'aapl' in asset_id: return ('AAPL', 'yahoo')
        if 'spx' in asset_id: return ('^GSPC', 'yahoo') # S&P 500
        if 'oro' in asset_id or 'gold' in asset_id: return ('GC=F', 'yahoo') # Futuros Oro

        # Default
        return ('BTC/USD', 'crypto') 

    def get_real_price(self, asset_id):
        """Obtiene el precio REAL actual de la fuente correcta"""
        symbol, source = self._get_symbol_and_source(asset_id)
        try:
            if source == 'crypto':
                ticker = self.exchange.fetch_ticker(symbol)
                return float(ticker['last'])
            else:
                # Yahoo Finance
                ticker = yf.Ticker(symbol)
                # fast_info es mucho más rápido que descargar el historial
                price = ticker.fast_info.last_price
                return float(price)
        except Exception as e:
            print(f"Error obteniendo precio ({symbol}): {e}")
            return 0.0

    # --- FUNCIONES DE USUARIO (STANDARD) ---
    def login(self, email, password):
        return self.auth_service.login(email, password)

    def register(self, email, password, username):
        user = self.auth_service.register(email, password)
        if user and user.get('localId'):
            uid = user['localId']
            id_token = user['idToken']
            profile_data = {
                "username": username, "email": email,
                "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "selected_market": "crypto", "risk": "medio", "experience": "novato",
                "saldo_virtual": 100000.0 # <--- ¡AHORA SON 100K!
            }
            self.db_service.save_user_profile(uid, profile_data, id_token)
            # ... (resto igual) ...
            return user
        return None

    # --- CAMBIO 2: SALDO POR DEFECTO 100K ---
    def get_user_profile(self, user_id, token):
        profile = self.db_service.get_user_profile(user_id, token)
        if profile and 'saldo_virtual' not in profile:
            profile['saldo_virtual'] = 100000.0 # <--- 100K AQUÍ TAMBIÉN
        return profile if profile else {"username": "Usuario", "saldo_virtual": 100000.0}

    def update_user_profile(self, user_id, data, token):
        current_profile = self.get_user_profile(user_id, token)
        current_profile.update(data)
        return self.db_service.save_user_profile(user_id, current_profile, token)

    def get_available_markets(self):
        return self.markets

    def change_password(self, id_token, new_password):
        return self.auth_service.change_password(id_token, new_password)

    def change_email(self, id_token, new_email):
        return self.auth_service.change_email(id_token, new_email)

    def delete_profile(self, user_id, id_token):
        return self.db_service.delete_user_data(user_id, id_token)

    # --- FUNCIONES DEL BOT ---
    def get_bot_settings_data(self, user_id, token):
        settings = self.bot_service.get_bot_settings(user_id, token)
        if settings is None:
            default_settings = {
                "activo": "crypto_btc_usd", "riesgo": "medio",
                "horario": "00:00-23:59", "indicadores": "RSI, MACD", "isActive": False
            }
            self.bot_service.save_bot_settings(user_id, default_settings, token)
            return default_settings
        return settings

    def save_bot_settings_data(self, user_id, data, token):
        current_settings = self.get_bot_settings_data(user_id, token)
        data['isActive'] = current_settings.get('isActive', False)
        current_settings.update(data) 
        return self.bot_service.save_bot_settings(user_id, current_settings, token)

    def activate_bot(self, user_id, token):
        try:
            settings = self.get_bot_settings_data(user_id, token)
            settings['isActive'] = True
            return self.bot_service.save_bot_settings(user_id, settings, token)
        except Exception as e:
            return False

    def deactivate_bot(self, user_id, token):
        try:
            settings = self.get_bot_settings_data(user_id, token)
            settings['isActive'] = False
            return self.bot_service.save_bot_settings(user_id, settings, token)
        except Exception as e:
            return False

    # --- PAPER TRADING HÍBRIDO (El corazón del sistema) ---
    def check_bot_execution(self, user_id, token):
        """
        Ejecuta estrategias tanto para Crypto como para Stocks/Forex.
        """
        settings = self.get_bot_settings_data(user_id, token)
        if not settings.get('isActive'): return

        asset_id = settings.get('activo', 'crypto_btc_usd')
        symbol, source = self._get_symbol_and_source(asset_id)
        
        try:
            # 1. Precio Real
            current_price = self.get_real_price(asset_id)
            if current_price == 0: return

            df = pd.DataFrame()

            # 2. Obtener Historial (Velas) según la fuente
            if source == 'crypto':
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe='1h', limit=20)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            else:
                # Yahoo Finance
                ticker = yf.Ticker(symbol)
                # Pedimos 2 días para asegurar tener las últimas 20 horas hábiles
                hist = ticker.history(period="2d", interval="1h")
                if hist.empty: return
                df = hist.reset_index()
                # Estandarizamos nombres de columnas
                df.rename(columns={'Close': 'close', 'Open': 'open', 'High': 'high', 'Low': 'low'}, inplace=True)

            if df.empty: return

            # 3. Estrategia Técnica (Cruce de Medias)
            sma_14 = df['close'].rolling(window=14).mean().iloc[-1]
            last_close = df['close'].iloc[-1]
            
            accion = "MANTENER"
            motivo = "Mercado lateral"
            
            # Umbral de sensibilidad: 0.2%
            if last_close > (sma_14 * 1.002):
                accion = "COMPRA"
                motivo = f"Precio ({round(last_close, 2)}) rompe SMA14 al alza"
            elif last_close < (sma_14 * 0.998):
                accion = "VENTA"
                motivo = f"Precio ({round(last_close, 2)}) pierde SMA14 a la baja"
            
            # 4. Guardar Trade si hubo acción
            if accion != "MANTENER":
                nuevo_trade = {
                    "tipo": accion,
                    "activo": symbol,
                    "precio_entrada": float(current_price),
                    "cantidad": 1 if source == 'yahoo' else 0.01, # Lógica: 1 acción o 0.01 BTC
                    "pnl": 0.0,
                    "pnl_acumulado": 0.0,
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "motivo": motivo
                }
                
                self.bot_service.record_trade(user_id, nuevo_trade, token)
                print(f"✅ Trade Híbrido Ejecutado: {accion} {symbol} a ${current_price}")
                
        except Exception as e:
            print(f"Error ejecución bot: {e}")
            traceback.print_exc()

    # --- ANÁLISIS IA HÍBRIDO ---
    def get_ai_analysis(self, user_id, token, asset_name):
        try:
            # Determinamos qué es
            symbol, source = self._get_symbol_and_source(f"ai_{asset_name.lower()}")
            
            # Parche rápido por si el nombre viene sucio del frontend
            if "bitcoin" in asset_name.lower(): symbol, source = 'BTC/USD', 'crypto'
            if "ethereum" in asset_name.lower(): symbol, source = 'ETH/USD', 'crypto'
            if "eur" in asset_name.lower(): symbol, source = 'EURUSD=X', 'yahoo'
            if "oro" in asset_name.lower(): symbol, source = 'GC=F', 'yahoo'

            df = pd.DataFrame()

            # Obtención de datos para Análisis
            if source == 'crypto':
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe='4h', limit=50)
                if not ohlcv: return "Datos insuficientes (Crypto)."
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            else:
                ticker = yf.Ticker(symbol)
                # Para análisis usamos velas diarias (más fiables en stocks)
                hist = ticker.history(period="2mo", interval="1d") 
                if hist.empty: return "Mercado cerrado o datos no disponibles."
                df = hist.reset_index()
                df.rename(columns={'Close': 'close'}, inplace=True)

            current_price = df['close'].iloc[-1]
            
            # Cálculos Técnicos
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            # Medias Móviles
            sma_short = df['close'].rolling(window=20).mean().iloc[-1]
            sma_long = df['close'].rolling(window=50).mean().iloc[-1]
            
            tendencia = "ALCISTA 🟢" if sma_short > sma_long else "BAJISTA 🔴"
            
            analisis = f"""
            <strong>Análisis Híbrido ({source.upper()}) para {symbol}</strong><br>
            Precio: ${current_price:,.2f}<br>
            Tendencia: <strong>{tendencia}</strong><br>
            RSI (14): {round(rsi, 2)}<br>
            <br>
            Algoritmo ejecutado sobre datos reales de {source.title()}.
            {'Atención: Alta volatilidad detectada.' if rsi > 70 or rsi < 30 else 'Mercado en rango operativo normal.'}
            """
            return analisis

        except Exception as e:
            return f"Error en análisis: {str(e)}"

    def get_dashboard_data(self, user_id, token):
        try:
            self.check_bot_execution(user_id, token)
            profile = self.get_user_profile(user_id, token)
            settings = self.get_bot_settings_data(user_id, token)
            current_price = self.get_real_price(settings.get('activo'))
            settings['current_price'] = current_price
            return {"profile": profile, "settings": settings}
        except Exception:
            return {
                "profile": {"username": "Usuario"},
                "settings": {"activo": "crypto_btc_usd", "isActive": False}
            }

    # --- RESTO DE FUNCIONES (API KEYS, ETC) ---
    def get_api_keys_data(self, user_id, token):
        keys = self.bot_service.get_api_keys(user_id, token)
        return [value for key, value in keys.items()] if keys else []

    def save_api_key(self, user_id, exchange, api_key, api_secret, token):
        data = {"exchange": exchange, "api_key": api_key, "api_secret": api_secret}
        return self.bot_service.save_api_key(user_id, data, token)
        
    def delete_api_key(self, user_id, exchange_name, token):
        return self.bot_service.delete_api_key(user_id, exchange_name, token)

    def generate_mock_trades(self, user_id, token):
        settings = self.get_bot_settings_data(user_id, token)
        asset_seleccionado = settings.get("activo", "crypto_btc_usd")
        return self.bot_service.generate_mock_trade_log(user_id, token, asset_seleccionado)
    
    def clear_trades(self, user_id, token):
        return self.bot_service.clear_trade_log(user_id, token)

    def forgot_password(self, email):
        return self.auth_service.reset_password(email)

    # --- DATOS DE RENDIMIENTO (LÓGICA REAL RESTAURADA) ---
    def get_performance_data(self, user_id, token):
        trade_log = self.bot_service.get_trade_log(user_id, token)
        trade_list, labels_grafica, data_grafica = [], [], []
        ganancia_total, trades_ganadores, total_trades = 0.0, 0, 0

        if trade_log:
            try:
                # Ordenar trades por fecha
                sorted_trades = sorted(trade_log.values(), key=lambda x: x.get('timestamp', ''))
            except Exception:
                sorted_trades = trade_log.values()
            
            total_trades = len(sorted_trades) 
            acumulado = 0
            
            for trade in sorted_trades:
                trade_list.append(trade)
                ts = trade.get('timestamp', 'N/A').split(' ')
                etiqueta_corta = ts[1] if len(ts) == 2 else ts[0] 
                labels_grafica.append(etiqueta_corta)
                
                # Cálculo de PnL (si ya está calculado en el trade, lo usa, si no, lo estima)
                pnl = trade.get('pnl', 0)
                
                # Si el trade tiene un PnL Acumulado guardado, lo usamos
                if 'pnl_acumulado' in trade and trade['pnl_acumulado'] != 0:
                    acumulado = trade['pnl_acumulado']
                else:
                    # Si no, sumamos el PnL simple
                    acumulado += pnl
                
                data_grafica.append(acumulado)
                
                if pnl > 0: trades_ganadores += 1
                ganancia_total = acumulado 

        win_rate = (trades_ganadores / total_trades) * 100 if total_trades > 0 else 0
        stats = {
            "ganancia_total": round(ganancia_total, 2), "total_trades": total_trades,
            "win_rate": round(win_rate, 2), "trades_ganadores": trades_ganadores
        }
        return {
            "stats": stats, "all_trades": trade_list,
            "grafica_labels": labels_grafica, "grafica_data": data_grafica
        }
        
    # --- PAPER TRADING MANUAL (TIPO ETORO) ---
    def execute_manual_trade(self, user_id, token, asset_id, action, quantity=None):
        try:
            # 1. Obtener precio real
            current_price = self.get_real_price(asset_id)
            if current_price == 0: return False, "Mercado cerrado o error de precio.", 0

            # 2. Cantidad: Si viene del frontend, usala. Si no, default.
            if quantity is None or float(quantity) <= 0:
                quantity = 1.0 

            quantity = float(quantity)
            total_value = current_price * quantity
            
            profile = self.get_user_profile(user_id, token)
            current_balance = float(profile.get('saldo_virtual', 100000.0))

            nuevo_saldo = current_balance
            
            if action == "COMPRA":
                if current_balance < total_value:
                    return False, f"Saldo insuficiente (${current_balance:,.2f}) para operar ${total_value:,.2f}", current_balance
                nuevo_saldo = current_balance - total_value
            elif action == "VENTA":
                # Venta suma al saldo
                nuevo_saldo = current_balance + total_value

            # 3. Guardar nuevo saldo
            self.update_user_profile(user_id, {"saldo_virtual": nuevo_saldo}, token)

            # 4. Guardar Trade
            symbol, _ = self._get_symbol_and_source(asset_id)
            trade_record = {
                "tipo": action,
                "activo": symbol,
                "precio_entrada": float(current_price),
                "cantidad": quantity,
                "total_operacion": total_value,
                "saldo_resultante": nuevo_saldo, # Guardamos cuánto quedó
                "pnl": 0.0,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "motivo": f"Manual: {quantity} unidades"
            }
            self.bot_service.record_trade(user_id, trade_record, token)

            # Retornamos EXITO, MENSAJE, y el NUEVO SALDO para actualizar el frontend
            return True, f"Orden ejecutada: {action} {quantity} {symbol}", nuevo_saldo

        except Exception as e:
            print(f"Error trading manual: {e}")
            return False, str(e), 0