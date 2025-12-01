from model.auth_service import AuthService
from model.db_service import DBService
from model.bot_service import BotService
import datetime
import os
import time
import ccxt 
import pandas as pd 
import traceback

class MainViewModel:
    def __init__(self):
        self.auth_service = AuthService()
        self.db_service = DBService()
        self.bot_service = BotService()
        self.markets = self.db_service.get_markets()
        
        # --- CAMBIO IMPORTANTE: USAMOS KRAKEN EN LUGAR DE BINANCE ---
        # Kraken no bloquea servidores de EE.UU. (como los de Render)
        self.exchange = ccxt.kraken({
            'enableRateLimit': True
        })

    def _get_ccxt_symbol(self, asset_id):
        """
        Mapea tus IDs internos a los símbolos de Kraken.
        Nota: Kraken opera principalmente con USD real, no USDT.
        """
        if not asset_id: return 'BTC/USD'
        
        asset_id = asset_id.lower()
        
        # Criptomonedas (Kraken)
        if 'btc' in asset_id: return 'BTC/USD'
        if 'eth' in asset_id: return 'ETH/USD'
        if 'sol' in asset_id: return 'SOL/USD'
        if 'ada' in asset_id: return 'ADA/USD'
        
        # Kraken tiene algunos pares Forex, pero son limitados.
        # Si pide algo que no es Cripto, devolvemos BTC por defecto para que no falle.
        return 'BTC/USD'

    def get_real_price(self, asset_id):
        """Obtiene el precio REAL actual de Kraken"""
        try:
            # Si es un activo que no es cripto (ej: S&P 500), simulamos un precio
            # porque Kraken es solo de Criptos.
            if "index" in asset_id or "stock" in asset_id or "commodity" in asset_id:
                # Simulación básica para no romper la app en stocks
                return 0.0 
            
            symbol = self._get_ccxt_symbol(asset_id)
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            print(f"Error obteniendo precio ({asset_id}): {e}")
            return 0.0

    # --- FUNCIONES DE USUARIO (SIN CAMBIOS) ---
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
                "saldo_virtual": 10000.0
            }
            self.db_service.save_user_profile(uid, profile_data, id_token)
            default_settings = {
                "activo": "crypto_btc_usd", "riesgo": "medio",
                "horario": "00:00-23:59", "indicadores": "RSI, MACD", "isActive": False
            }
            self.bot_service.save_bot_settings(uid, default_settings, id_token)
            return user
        return None

    def get_user_profile(self, user_id, token):
        profile = self.db_service.get_user_profile(user_id, token)
        if profile and 'saldo_virtual' not in profile:
            profile['saldo_virtual'] = 10000.0
        return profile if profile else {"username": "Usuario", "saldo_virtual": 10000.0}

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
            print(f"Error al activar el bot: {e}")
            return False

    def deactivate_bot(self, user_id, token):
        try:
            settings = self.get_bot_settings_data(user_id, token)
            settings['isActive'] = False
            return self.bot_service.save_bot_settings(user_id, settings, token)
        except Exception as e:
            print(f"Error al desactivar el bot: {e}")
            return False

    # --- PAPER TRADING / BOT REAL ---
    def check_bot_execution(self, user_id, token):
        settings = self.get_bot_settings_data(user_id, token)
        if not settings.get('isActive'): return

        asset_id = settings.get('activo', 'crypto_btc_usd')
        
        # Kraken no tiene stocks/indices, así que evitamos ejecutar el bot ahí para no dar error
        if "crypto" not in asset_id and "forex" not in asset_id:
            return 

        symbol = self._get_ccxt_symbol(asset_id)
        
        try:
            current_price = self.get_real_price(asset_id)
            if current_price == 0: return # Precio inválido

            # Obtenemos velas históricas para decidir (1 hora)
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe='1h', limit=20)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            sma_14 = df['close'].rolling(window=14).mean().iloc[-1]
            last_close = df['close'].iloc[-1]
            
            accion = "MANTENER"
            motivo = "Mercado lateral"
            
            # Estrategia Básica
            if last_close > (sma_14 * 1.002): # 0.2% arriba
                accion = "COMPRA"
                motivo = f"Precio ({last_close}) supera SMA14 ({round(sma_14, 2)})"
            elif last_close < (sma_14 * 0.998):
                accion = "VENTA"
                motivo = f"Precio ({last_close}) cae bajo SMA14 ({round(sma_14, 2)})"
            
            if accion != "MANTENER":
                nuevo_trade = {
                    "tipo": accion,
                    "activo": symbol,
                    "precio_entrada": float(current_price),
                    "cantidad": 0.01,
                    "pnl": 0.0,
                    "pnl_acumulado": 0.0,
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "motivo": motivo
                }
                self.bot_service.record_trade(user_id, nuevo_trade, token)
                print(f"✅ Paper Trade: {accion} {symbol}")
                
        except Exception as e:
            print(f"Bot execution error: {e}")


    def get_dashboard_data(self, user_id, token):
        try:
            self.check_bot_execution(user_id, token)
            profile = self.get_user_profile(user_id, token)
            settings = self.get_bot_settings_data(user_id, token)
            current_price = self.get_real_price(settings.get('activo'))
            settings['current_price'] = current_price
            return {"profile": profile, "settings": settings}
        except Exception as e:
            print(f"Error dashboard: {e}")
            return {
                "profile": {"username": "Usuario"},
                "settings": {"activo": "crypto_btc_usd", "isActive": False}
            }

    # --- ANÁLISIS IA REAL (CON KRAKEN) ---
    def get_ai_analysis(self, user_id, token, asset_name):
        try:
            # Filtro de Seguridad: Si no es Cripto, damos un mensaje genérico simulado
            # (Porque Kraken fallará con stocks)
            if "stock" in asset_name.lower() or "index" in asset_name.lower() or "oro" in asset_name.lower():
                return f"""
                <strong>Análisis de Mercado para {asset_name}</strong><br>
                <br>
                NOTA: Datos en tiempo real solo disponibles para Criptomonedas por ahora.<br>
                Tendencia proyectada: <strong>NEUTRAL</strong><br>
                Se recomienda consultar fuentes externas para Stocks y Commodities.
                """

            symbol = self._get_ccxt_symbol(f"crypto_{asset_name.lower()}")
            
            # Datos de Kraken
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe='4h', limit=50)
            if not ohlcv: return "Datos insuficientes para análisis."
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            current_price = df['close'].iloc[-1]
            
            # Indicadores
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            sma_20 = df['close'].rolling(window=20).mean().iloc[-1]
            sma_50 = df['close'].rolling(window=50).mean().iloc[-1]
            
            tendencia = "ALCISTA 🟢" if sma_20 > sma_50 else "BAJISTA 🔴"
            sentimiento = "NEUTRAL"
            if rsi > 70: sentiment = "SOBRECOMPRA ⚠️"
            elif rsi < 30: sentiment = "SOBREVENTA 🚀"
            else: sentiment = "ESTABLE"
            
            analisis = f"""
            <strong>Análisis Técnico (Kraken Feed) para {symbol}</strong><br>
            Precio: ${current_price:,.2f}<br>
            Tendencia: <strong>{tendencia}</strong><br>
            RSI (14): {round(rsi, 2)} ({sentiment})<br>
            <br>
            Análisis algorítmico basado en velas de 4 horas. 
            {'Alta probabilidad de corrección.' if rsi > 70 else 'Posible oportunidad de entrada.' if rsi < 30 else 'El mercado espera confirmación de volumen.'}
            """
            return analisis

        except Exception as e:
            # Dejamos el print para logs, pero retornamos un mensaje amigable
            print(f"Error AI: {e}")
            return f"Error de conexión con el mercado: {str(e)}"

    # --- RESTO DE FUNCIONES ---
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

    def get_performance_data(self, user_id, token):
        trade_log = self.bot_service.get_trade_log(user_id, token)
        trade_list, labels_grafica, data_grafica = [], [], []
        ganancia_total, trades_ganadores, total_trades = 0.0, 0, 0

        if trade_log:
            try:
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
                
                pnl = trade.get('pnl', 0)
                if 'pnl_acumulado' in trade:
                    acumulado = trade['pnl_acumulado']
                else:
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