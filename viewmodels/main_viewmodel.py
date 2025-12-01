from model.auth_service import AuthService
from model.db_service import DBService
from model.bot_service import BotService
import datetime
import os
import time
import ccxt 
import pandas as pd 
import yfinance as yf
import traceback

class MainViewModel:
    def __init__(self):
        self.auth_service = AuthService()
        self.db_service = DBService()
        self.bot_service = BotService()
        self.markets = self.db_service.get_markets()
        
        # Cliente Crypto (Kraken) - Configurado para no bloquear IPs de EE.UU.
        self.exchange = ccxt.kraken({
            'enableRateLimit': True
        })

    # ==============================================================================
    # 1. GESTIÓN DE PRECIOS Y MERCADOS (CEREBRO HÍBRIDO)
    # ==============================================================================

    def _get_symbol_and_source(self, asset_id):
        """
        Determina qué activo es y de dónde sacar el precio (Kraken o Yahoo).
        """
        if not asset_id: return ('BTC/USD', 'crypto')
        asset_id = asset_id.lower()
        
        # --- CRIPTOMONEDAS (Kraken) ---
        if 'btc' in asset_id: return ('BTC/USD', 'crypto')
        if 'eth' in asset_id: return ('ETH/USD', 'crypto')
        if 'sol' in asset_id: return ('SOL/USD', 'crypto')
        if 'ada' in asset_id: return ('ADA/USD', 'crypto')
        
        # --- FOREX (Yahoo Finance) ---
        if 'eur_usd' in asset_id: return ('EURUSD=X', 'yahoo')
        if 'gbp_usd' in asset_id: return ('GBPUSD=X', 'yahoo')
        if 'usd_jpy' in asset_id: return ('JPY=X', 'yahoo')
        
        # --- STOCKS / INDICES (Yahoo Finance) ---
        if 'tsla' in asset_id: return ('TSLA', 'yahoo')
        if 'aapl' in asset_id: return ('AAPL', 'yahoo')
        if 'spx' in asset_id: return ('^GSPC', 'yahoo') # S&P 500
        if 'oro' in asset_id or 'gold' in asset_id: return ('GC=F', 'yahoo') # Futuros Oro
        
        # --- COLOMBIA (ADRs en NYSE) ---
        if 'ecopetrol' in asset_id: return ('EC', 'yahoo')
        if 'bancolombia' in asset_id: return ('CIB', 'yahoo')
        if 'aval' in asset_id: return ('AVAL', 'yahoo')
        if 'nubank' in asset_id: return ('NU', 'yahoo')

        # Default
        return ('BTC/USD', 'crypto') 

    def get_real_price(self, asset_id):
        """Obtiene el precio numérico exacto en tiempo real."""
        symbol, source = self._get_symbol_and_source(asset_id)
        try:
            if source == 'crypto':
                # Usamos Kraken para criptos
                ticker = self.exchange.fetch_ticker(symbol)
                return float(ticker['last'])
            else:
                # Usamos Yahoo Finance para acciones y forex
                ticker = yf.Ticker(symbol)
                # 'fast_info' es más rápido y fiable para el precio actual
                price = ticker.fast_info.last_price
                return float(price)
        except Exception as e:
            print(f"Error obteniendo precio para {symbol}: {e}")
            return 0.0

    # ==============================================================================
    # 2. GESTIÓN DE USUARIOS Y PERFIL (CON CORRECCIÓN DE SALDO)
    # ==============================================================================

    def login(self, email, password):
        return self.auth_service.login(email, password)

    def register(self, email, password, username):
        user = self.auth_service.register(email, password)
        if user and user.get('localId'):
            uid = user['localId']
            id_token = user['idToken']
            
            # CONFIGURACIÓN INICIAL DEL PERFIL
            profile_data = {
                "username": username,
                "email": email,
                "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "selected_market": "crypto",
                "risk": "medio",
                "experience": "novato",
                "saldo_virtual": 100000.0 # <--- ¡100K INICIALES OBLIGATORIOS!
            }
            self.db_service.save_user_profile(uid, profile_data, id_token)
            
            # CONFIGURACIÓN INICIAL DEL BOT
            default_settings = {
                "activo": "crypto_btc_usd",
                "riesgo": "medio",
                "horario": "00:00-23:59",
                "indicadores": "RSI, MACD",
                "isActive": False
            }
            self.bot_service.save_bot_settings(uid, default_settings, id_token)
            return user
        return None

    def get_user_profile(self, user_id, token):
        """Obtiene el perfil y CORRIGE el saldo si es antiguo."""
        profile = self.db_service.get_user_profile(user_id, token)
        
        if profile:
            # Leemos el saldo actual, si no existe asumimos 0
            saldo_actual = float(profile.get('saldo_virtual', 0))
            
            # LÓGICA DE CORRECCIÓN:
            # Si el saldo es menor o igual a 10,000 (el valor viejo por defecto),
            # lo actualizamos a 100,000 y lo GUARDAMOS en la base de datos.
            if saldo_actual <= 10000.0:
                print(f"--- CORRIGIENDO SALDO ANTIGUO ({saldo_actual}) A 100,000 ---")
                profile['saldo_virtual'] = 100000.0
                self.db_service.save_user_profile(user_id, profile, token)
        else:
            # Si por alguna razón no hay perfil, devolvemos uno temporal
            profile = {"username": "Usuario", "saldo_virtual": 100000.0}
            
        return profile

    def update_user_profile(self, user_id, data, token):
        """Actualiza datos del perfil (incluyendo el saldo tras operar)."""
        current_profile = self.get_user_profile(user_id, token)
        current_profile.update(data)
        return self.db_service.save_user_profile(user_id, current_profile, token)

    # ==============================================================================
    # 3. LÓGICA DE TRADING (PAPER TRADING BLINDADO)
    # ==============================================================================

    def _calculate_holdings(self, user_id, token, target_symbol):
        """
        Calcula cuánto tienes realmente de un activo (Inventario).
        Suma todas las compras y resta todas las ventas.
        """
        trade_log = self.bot_service.get_trade_log(user_id, token)
        if not trade_log: return 0.0

        total_holding = 0.0
        # Convertimos el diccionario de firebase a lista
        trades = trade_log.values() if isinstance(trade_log, dict) else []
        
        for trade in trades:
            # Solo miramos el activo que nos interesa (ej: BTC/USD)
            if trade.get('activo') == target_symbol:
                qty = float(trade.get('cantidad', 0))
                
                if trade.get('tipo') == 'COMPRA':
                    total_holding += qty
                elif trade.get('tipo') == 'VENTA':
                    total_holding -= qty
        
        # Evitamos errores de redondeo negativo (ej: -0.0000001)
        return max(0.0, total_holding)

    def execute_manual_trade(self, user_id, token, asset_id, action, quantity=None):
        """
        Ejecuta una operación manual verificando saldo e inventario.
        """
        try:
            # 1. OBTENER PRECIO REAL
            current_price = self.get_real_price(asset_id)
            if current_price == 0: 
                return False, "Mercado cerrado o sin conexión.", 0

            # 2. VALIDAR CANTIDAD (Anti-Negativos)
            if quantity is None: quantity = 1.0
            
            # ¡IMPORTANTE! Usamos abs() para asegurar que el número sea positivo.
            # Esto evita que alguien ponga "-50" para sumar saldo comprando.
            quantity = abs(float(quantity)) 
            
            if quantity == 0: 
                return False, "La cantidad debe ser mayor a 0", 0

            # Calcular costo total de la operación
            total_value = current_price * quantity
            
            # 3. OBTENER ESTADO ACTUAL DEL USUARIO
            profile = self.get_user_profile(user_id, token)
            current_balance = float(profile.get('saldo_virtual', 100000.0))
            
            symbol, _ = self._get_symbol_and_source(asset_id)
            nuevo_saldo = current_balance

            # 4. LÓGICA DE COMPRA (Restar Saldo)
            if action == "COMPRA":
                if current_balance < total_value:
                    return False, f"Saldo insuficiente (${current_balance:,.2f}) para esta operación.", current_balance
                
                nuevo_saldo = current_balance - total_value
            
            # 5. LÓGICA DE VENTA (Sumar Saldo + Verificar Inventario)
            elif action == "VENTA":
                # Verificamos si realmente tienes el activo
                holdings = self._calculate_holdings(user_id, token, symbol)
                
                if holdings < quantity:
                    return False, f"No puedes vender {quantity} {symbol}. Solo tienes {holdings:.4f} en cartera.", current_balance
                
                nuevo_saldo = current_balance + total_value

            # 6. GUARDAR NUEVO SALDO (Persistencia Inmediata)
            self.update_user_profile(user_id, {"saldo_virtual": nuevo_saldo}, token)

            # 7. GUARDAR REGISTRO DEL TRADE (Log)
            trade_record = {
                "tipo": action,
                "activo": symbol,
                "precio_entrada": float(current_price),
                "cantidad": quantity,
                "total_operacion": total_value,
                "saldo_resultante": nuevo_saldo, # Guardamos el saldo histórico
                "pnl": 0.0, # (Opcional) PnL realizado
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "motivo": f"Manual: {quantity} unidades"
            }
            self.bot_service.record_trade(user_id, trade_record, token)

            return True, f"Orden ejecutada: {action} {quantity} {symbol} a ${current_price:,.2f}", nuevo_saldo

        except Exception as e:
            print(f"Error crítico en trading: {e}")
            traceback.print_exc()
            return False, f"Error del sistema: {str(e)}", 0

    def clear_trades(self, user_id, token):
        """Borra el historial y reinicia el saldo a 100k."""
        # 1. Borrar tabla de trades
        self.bot_service.clear_trade_log(user_id, token)
        # 2. Restaurar saldo
        self.update_user_profile(user_id, {"saldo_virtual": 100000.0}, token)
        return True

    # ==============================================================================
    # 4. ANÁLISIS DE IA Y DASHBOARD
    # ==============================================================================

    def get_ai_analysis(self, user_id, token, asset_name):
        try:
            symbol, source = self._get_symbol_and_source(f"ai_{asset_name.lower()}")
            
            # Normalización de nombres para el título
            display_name = symbol
            if "bitcoin" in asset_name.lower(): symbol, source = 'BTC/USD', 'crypto'
            if "ethereum" in asset_name.lower(): symbol, source = 'ETH/USD', 'crypto'
            if "eur" in asset_name.lower(): symbol, source = 'EURUSD=X', 'yahoo'
            if "oro" in asset_name.lower(): symbol, source = 'GC=F', 'yahoo'

            df = pd.DataFrame()

            # Obtención de datos históricos
            if source == 'crypto':
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe='4h', limit=50)
                if not ohlcv: return "Datos insuficientes para análisis técnico."
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            else:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1mo", interval="1d") 
                if hist.empty: return "Mercado cerrado o datos no disponibles."
                df = hist.reset_index()
                df.rename(columns={'Close': 'close'}, inplace=True)

            current_price = df['close'].iloc[-1]
            
            # Cálculos Técnicos (RSI + Medias Móviles)
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            sma_short = df['close'].rolling(window=20).mean().iloc[-1]
            sma_long = df['close'].rolling(window=50).mean().iloc[-1]
            
            tendencia = "ALCISTA 🟢" if sma_short > sma_long else "BAJISTA 🔴"
            
            if rsi > 70: sentimiento = "SOBRECOMPRA ⚠️"
            elif rsi < 30: sentimiento = "SOBREVENTA 🚀"
            else: sentimiento = "NEUTRAL ⚖️"
            
            # --- SALIDA DE TEXTO COMPLETA (HTML) ---
            analisis = f"""
            <strong>Análisis Técnico: {symbol}</strong><br>
            <br>
            Precio Actual: <strong>${current_price:,.2f}</strong><br>
            Tendencia (MA20/50): <strong>{tendencia}</strong><br>
            RSI (14): <strong>{round(rsi, 2)}</strong> ({sentimiento})<br>
            <br>
            <strong>Conclusión de la IA:</strong><br>
            El activo muestra una estructura {tendencia.split(' ')[0].lower()}. 
            {'Los compradores mantienen el control.' if sma_short > sma_long else 'Presión de venta dominante.'}
            {'Alerta de posible reversión por RSI alto.' if rsi > 70 else 'Posible zona de compra por RSI bajo.' if rsi < 30 else 'Zona de consolidación, esperar ruptura.'}
            """
            return analisis

        except Exception as e:
            return f"Error generando análisis: {str(e)}"

    def get_dashboard_data(self, user_id, token):
        try:
            # Revisamos si el bot debe operar automáticamente
            self.check_bot_execution(user_id, token)
            
            profile = self.get_user_profile(user_id, token)
            settings = self.get_bot_settings_data(user_id, token)
            
            # Obtenemos precio actual para mostrar en el dashboard
            current_price = self.get_real_price(settings.get('activo'))
            settings['current_price'] = current_price
            
            return {"profile": profile, "settings": settings}
        except: 
            return {
                "profile": {"username": "Usuario", "saldo_virtual": 100000.0}, 
                "settings": {"activo": "crypto_btc_usd", "isActive": False}
            }

    def get_performance_data(self, user_id, token):
        trade_log = self.bot_service.get_trade_log(user_id, token)
        trade_list, labels_grafica, data_grafica = [], [], []
        
        # Estructura: {'BTC/USD': {'qty': 0.5, 'total_cost': 25000.0}}
        holdings = {} 
        
        profile = self.get_user_profile(user_id, token)
        saldo_cash = float(profile.get('saldo_virtual', 100000.0))
        
        if trade_log:
            try: sorted_trades = sorted(trade_log.values(), key=lambda x: x.get('timestamp', ''))
            except: sorted_trades = trade_log.values()
            
            for trade in sorted_trades:
                trade_list.append(trade)
                labels_grafica.append(trade.get('timestamp', '')[5:16]) 
                data_grafica.append(trade.get('saldo_resultante', 0))
                
                # --- CÁLCULO DE INVENTARIO Y COSTO PROMEDIO ---
                asset = trade.get('activo')
                qty = float(trade.get('cantidad', 0))
                price = float(trade.get('precio_entrada', 0))
                tipo = trade.get('tipo')
                
                if asset not in holdings: 
                    holdings[asset] = {'qty': 0.0, 'total_cost': 0.0}
                
                if tipo == 'COMPRA':
                    holdings[asset]['qty'] += qty
                    holdings[asset]['total_cost'] += (qty * price)
                elif tipo == 'VENTA':
                    # Al vender, reducimos el costo proporcionalmente para mantener el precio promedio
                    # Evitamos div/0
                    if holdings[asset]['qty'] > 0:
                        avg_price = holdings[asset]['total_cost'] / holdings[asset]['qty']
                        holdings[asset]['total_cost'] -= (qty * avg_price)
                    
                    holdings[asset]['qty'] -= qty

        # Preparar datos para la vista
        portfolio_labels = ["Efectivo (USD)"]
        portfolio_data = [saldo_cash]
        total_portfolio_value = saldo_cash
        lista_posiciones = [] 

        for asset, data in holdings.items():
            qty = data['qty']
            cost_basis = data['total_cost']
            
            if qty > 0.00001: 
                try:
                    # 1. Obtener Precio Actual Real
                    current_price = 0
                    if "BTC" in asset: current_price = self.get_real_price("crypto_btc_usd")
                    elif "ETH" in asset: current_price = self.get_real_price("crypto_eth_usd")
                    elif "SOL" in asset: current_price = self.get_real_price("crypto_sol_usd")
                    elif "EUR" in asset: current_price = self.get_real_price("forex_eur_usd")
                    elif "EC" in asset: current_price = self.get_real_price("stock_ecopetrol")
                    elif "CIB" in asset: current_price = self.get_real_price("stock_bancolombia")
                    elif "AVAL" in asset: current_price = self.get_real_price("stock_aval")
                    
                    if current_price == 0: current_price = 1 
                    
                    # 2. Calcular Valores
                    valor_mercado = qty * current_price
                    precio_promedio_compra = cost_basis / qty
                    
                    # 3. Calcular PnL de la posición (No realizado)
                    pnl_unrealized = valor_mercado - cost_basis
                    pnl_percent = (pnl_unrealized / cost_basis) * 100 if cost_basis > 0 else 0

                    total_portfolio_value += valor_mercado
                    portfolio_labels.append(asset)
                    portfolio_data.append(round(valor_mercado, 2))
                    
                    lista_posiciones.append({
                        "activo": asset,
                        "cantidad": qty,
                        "precio_compra": precio_promedio_compra, # <--- NUEVO
                        "precio_actual": current_price,
                        "valor_total": valor_mercado,
                        "pnl_percent": pnl_percent # <--- NUEVO (Para ponerlo verde/rojo)
                    })
                except Exception as e:
                    print(f"Error calculando posición {asset}: {e}")

        ganancia_total = total_portfolio_value - 100000.0 

        stats = {
            "ganancia_total": round(ganancia_total, 2), 
            "total_trades": len(trade_list),
            "equity": total_portfolio_value 
        }
        
        return {
            "stats": stats, 
            "all_trades": trade_list, 
            "current_holdings": lista_posiciones, 
            "grafica_labels": labels_grafica, 
            "grafica_data": data_grafica,
            "pie_labels": portfolio_labels, 
            "pie_data": portfolio_data
        }

    # ==============================================================================
    # 5. FUNCIONES AUXILIARES (API KEYS, AUTH, ETC)
    # ==============================================================================
    
    def get_available_markets(self): 
        return self.markets
        
    def get_api_keys_data(self, u, t): 
        k = self.bot_service.get_api_keys(u, t)
        return [v for k, v in k.items()] if k else []
        
    def save_api_key(self, u, e, k, s, t): 
        d = {"exchange": e, "api_key": k, "api_secret": s}
        return self.bot_service.save_api_key(u, d, t)
        
    def delete_api_key(self, u, e, t): 
        return self.bot_service.delete_api_key(u, e, t)
        
    def change_password(self, t, p): 
        return self.auth_service.change_password(t, p)
        
    def change_email(self, t, e): 
        return self.auth_service.change_email(t, e)
        
    def delete_profile(self, u, t): 
        return self.db_service.delete_user_data(u, t)
        
    def forgot_password(self, e): 
        return self.auth_service.reset_password(e)
    
    def generate_mock_trades(self, u, t): 
        return False # Desactivado porque ahora usamos trading real

    # --- BOT SETTINGS ---
    def get_bot_settings_data(self, u, t):
        s = self.bot_service.get_bot_settings(u, t)
        if s is None:
            d = {"activo": "crypto_btc_usd", "riesgo": "medio", "horario": "00:00-23:59", "indicadores": "RSI, MACD", "isActive": False}
            self.bot_service.save_bot_settings(u, d, t); return d
        return s
        
    def save_bot_settings_data(self, u, d, t):
        c = self.get_bot_settings_data(u, t)
        d['isActive'] = c.get('isActive', False)
        c.update(d); return self.bot_service.save_bot_settings(u, c, t)
        
    def activate_bot(self, u, t):
        try: s = self.get_bot_settings_data(u, t); s['isActive'] = True; return self.bot_service.save_bot_settings(u, s, t)
        except: return False
        
    def deactivate_bot(self, u, t):
        try: s = self.get_bot_settings_data(u, t); s['isActive'] = False; return self.bot_service.save_bot_settings(u, s, t)
        except: return False
        
    # --- EJECUCIÓN AUTOMÁTICA (BOT) ---
    def check_bot_execution(self, user_id, token):
        """
        Versión simplificada del bot automático.
        Usa la misma lógica de seguridad que el manual.
        """
        settings = self.get_bot_settings_data(user_id, token)
        if not settings.get('isActive'): return
        
        asset_id = settings.get('activo', 'crypto_btc_usd')
        symbol, source = self._get_symbol_and_source(asset_id)
        
        try:
            current_price = self.get_real_price(asset_id)
            if current_price == 0: return
            
            df = pd.DataFrame()
            if source == 'crypto':
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe='1h', limit=20)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            else:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="2d", interval="1h")
                if hist.empty: return
                df = hist.reset_index()
                df.rename(columns={'Close': 'close'}, inplace=True)
            
            if df.empty: return
            
            # Lógica simple de cruce
            sma_14 = df['close'].rolling(window=14).mean().iloc[-1]
            last_close = df['close'].iloc[-1]
            
            accion = "MANTENER"
            if last_close > (sma_14 * 1.002): accion = "COMPRA"
            elif last_close < (sma_14 * 0.998): accion = "VENTA"
            
            if accion != "MANTENER":
                # Cantidad pequeña para el bot automático
                qty = 1.0 if source == 'yahoo' else 0.001
                
                # Ejecutamos usando la función segura
                success, msg, _ = self.execute_manual_trade(user_id, token, asset_id, accion, quantity=qty)
                if success: print(f"🤖 Bot Trade: {msg}")
                
        except Exception as e:
            print(f"Bot error: {e}")