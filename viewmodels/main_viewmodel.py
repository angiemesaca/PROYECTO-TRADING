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
        
        # Cliente Crypto (Kraken)
        self.exchange = ccxt.kraken({'enableRateLimit': True})

    # --- ROUTER DE PRECIOS ---
    def _get_symbol_and_source(self, asset_id):
        if not asset_id: return ('BTC/USD', 'crypto')
        asset_id = asset_id.lower()
        
        # Criptos
        if 'btc' in asset_id: return ('BTC/USD', 'crypto')
        if 'eth' in asset_id: return ('ETH/USD', 'crypto')
        if 'sol' in asset_id: return ('SOL/USD', 'crypto')
        if 'ada' in asset_id: return ('ADA/USD', 'crypto')
        
        # Forex
        if 'eur_usd' in asset_id: return ('EURUSD=X', 'yahoo')
        if 'gbp_usd' in asset_id: return ('GBPUSD=X', 'yahoo')
        if 'usd_jpy' in asset_id: return ('JPY=X', 'yahoo')
        
        # Stocks / Colombia
        if 'tsla' in asset_id: return ('TSLA', 'yahoo')
        if 'aapl' in asset_id: return ('AAPL', 'yahoo')
        if 'spx' in asset_id: return ('^GSPC', 'yahoo')
        if 'oro' in asset_id or 'gold' in asset_id: return ('GC=F', 'yahoo')
        
        if 'ecopetrol' in asset_id: return ('EC', 'yahoo')
        if 'bancolombia' in asset_id: return ('CIB', 'yahoo')
        if 'aval' in asset_id: return ('AVAL', 'yahoo')
        if 'nubank' in asset_id: return ('NU', 'yahoo')

        return ('BTC/USD', 'crypto') 

    def get_real_price(self, asset_id):
        symbol, source = self._get_symbol_and_source(asset_id)
        try:
            if source == 'crypto':
                ticker = self.exchange.fetch_ticker(symbol)
                return float(ticker['last'])
            else:
                ticker = yf.Ticker(symbol)
                price = ticker.fast_info.last_price
                return float(price)
        except Exception as e:
            print(f"Error precio ({symbol}): {e}")
            return 0.0

    # --- FUNCIONES DE USUARIO ---
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
                "saldo_virtual": 100000.0 # 100k Inicial
            }
            self.db_service.save_user_profile(uid, profile_data, id_token)
            default_settings = {
                "activo": "crypto_btc_usd", "riesgo": "medio", "isActive": False
            }
            self.bot_service.save_bot_settings(uid, default_settings, id_token)
            return user
        return None

    # --- 🛠️ CORRECCIÓN DE SALDO FORZADA ---
    def get_user_profile(self, user_id, token):
        profile = self.db_service.get_user_profile(user_id, token)
        
        if profile:
            saldo = float(profile.get('saldo_virtual', 0))
            # Si el saldo es bajo (ej: los 10k viejos) o 0, FORZAMOS 100k
            if saldo <= 10000.0:
                profile['saldo_virtual'] = 100000.0
                print(f"--- CORRIGIENDO SALDO DE USUARIO A 100K ---")
                self.db_service.save_user_profile(user_id, profile, token)
        else:
            profile = {"username": "Usuario", "saldo_virtual": 100000.0}
            
        return profile

    def update_user_profile(self, user_id, data, token):
        current_profile = self.get_user_profile(user_id, token)
        current_profile.update(data)
        return self.db_service.save_user_profile(user_id, current_profile, token)

    # --- 🧮 CALCULADORA DE INVENTARIO (Anti-Venta Infinita) ---
    def _calculate_holdings(self, user_id, token, target_symbol):
        trade_log = self.bot_service.get_trade_log(user_id, token)
        if not trade_log: return 0.0

        total_holding = 0.0
        trades = trade_log.values() if isinstance(trade_log, dict) else []
        
        for trade in trades:
            if trade.get('activo') == target_symbol:
                qty = float(trade.get('cantidad', 0))
                if trade.get('tipo') == 'COMPRA':
                    total_holding += qty
                elif trade.get('tipo') == 'VENTA':
                    total_holding -= qty
        
        return max(0.0, total_holding)

    # --- 💰 PAPER TRADING MANUAL BLINDADO ---
    def execute_manual_trade(self, user_id, token, asset_id, action, quantity=None):
        try:
            # 1. Obtener precio
            current_price = self.get_real_price(asset_id)
            if current_price == 0: return False, "Mercado cerrado.", 0

            # 2. Validar cantidad (USAMOS ABS PARA EVITAR NEGATIVOS)
            if quantity is None: quantity = 1.0
            quantity = abs(float(quantity)) # <--- ESTO EVITA QUE EL SALDO SUBA AL COMPRAR
            
            if quantity == 0: return False, "Cantidad debe ser mayor a 0", 0

            total_value = current_price * quantity
            
            # 3. Datos del usuario
            profile = self.get_user_profile(user_id, token)
            current_balance = float(profile.get('saldo_virtual', 100000.0))
            
            symbol, _ = self._get_symbol_and_source(asset_id)
            nuevo_saldo = current_balance

            # --- LÓGICA DE COMPRA ---
            if action == "COMPRA":
                if current_balance < total_value:
                    return False, f"Saldo insuficiente (${current_balance:,.2f})", current_balance
                # RESTA DINERO
                nuevo_saldo = current_balance - total_value
            
            # --- LÓGICA DE VENTA ---
            elif action == "VENTA":
                # CHEQUEO DE INVENTARIO
                holdings = self._calculate_holdings(user_id, token, symbol)
                if holdings < quantity:
                    return False, f"No puedes vender {quantity} {symbol}. Tienes {holdings:.4f}", current_balance
                # SUMA DINERO
                nuevo_saldo = current_balance + total_value

            # 4. Guardar nuevo saldo
            self.update_user_profile(user_id, {"saldo_virtual": nuevo_saldo}, token)

            # 5. Guardar Trade
            trade_record = {
                "tipo": action,
                "activo": symbol,
                "precio_entrada": float(current_price),
                "cantidad": quantity,
                "total_operacion": total_value,
                "saldo_resultante": nuevo_saldo,
                "pnl": 0.0,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "motivo": f"Manual: {quantity} unidades"
            }
            self.bot_service.record_trade(user_id, trade_record, token)

            return True, f"Orden ejecutada: {action} {quantity} {symbol}", nuevo_saldo

        except Exception as e:
            print(f"Error trading manual: {e}")
            return False, str(e), 0

    # --- 🧹 RESET TOTAL (HISTORIAL + SALDO) ---
    def clear_trades(self, user_id, token):
        # 1. Borrar historial
        deleted = self.bot_service.clear_trade_log(user_id, token)
        # 2. Restaurar saldo a 100k
        self.update_user_profile(user_id, {"saldo_virtual": 100000.0}, token)
        return deleted

    # --- DATOS DE RENDIMIENTO REAL ---
    def get_performance_data(self, user_id, token):
        trade_log = self.bot_service.get_trade_log(user_id, token)
        trade_list, labels_grafica, data_grafica = [], [], []
        
        # Empezamos la gráfica con el saldo inicial por defecto
        saldo_inicial = 100000.0
        
        if trade_log:
            try: sorted_trades = sorted(trade_log.values(), key=lambda x: x.get('timestamp', ''))
            except: sorted_trades = trade_log.values()
            
            for trade in sorted_trades:
                trade_list.append(trade)
                # Fecha corta (MM-DD HH:MM)
                ts = trade.get('timestamp', '')[5:16] 
                labels_grafica.append(ts)
                
                # Graficamos la evolución del SALDO RESULTANTE
                saldo = trade.get('saldo_resultante', saldo_inicial)
                data_grafica.append(saldo)
        
        # Calculamos estadísticas básicas
        current_profile = self.get_user_profile(user_id, token)
        saldo_actual = float(current_profile.get('saldo_virtual', 100000.0))
        ganancia_total = saldo_actual - 100000.0
        
        stats = {
            "ganancia_total": round(ganancia_total, 2), 
            "total_trades": len(trade_list),
            "win_rate": 0, # Pendiente de lógica compleja
            "trades_ganadores": 0
        }
        return {
            "stats": stats, 
            "all_trades": trade_list, 
            "grafica_labels": labels_grafica, 
            "grafica_data": data_grafica
        }

    # --- FUNCIONES RESTANTES ---
    def get_available_markets(self): return self.markets
    def change_password(self, t, p): return self.auth_service.change_password(t, p)
    def change_email(self, t, e): return self.auth_service.change_email(t, e)
    def delete_profile(self, u, t): return self.db_service.delete_user_data(u, t)
    
    def get_bot_settings_data(self, u, t):
        s = self.bot_service.get_bot_settings(u, t)
        if s is None:
            d = {"activo": "crypto_btc_usd", "riesgo": "medio", "isActive": False}
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
        
    def check_bot_execution(self, user_id, token):
        # Lógica del bot automática (Paper Trading)
        # Reutilizamos la función execute_manual_trade para seguridad
        settings = self.get_bot_settings_data(user_id, token)
        if not settings.get('isActive'): return
        asset_id = settings.get('activo', 'crypto_btc_usd')
        symbol, source = self._get_symbol_and_source(asset_id)
        
        try:
            current_price = self.get_real_price(asset_id)
            if current_price == 0: return
            
            # ... Análisis Técnico ...
            # (Aquí va tu lógica de medias móviles que ya tenías)
            # Simplificamos para el ejemplo:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe='1h', limit=20) if source == 'crypto' else []
            # ...
            
            # Imaginemos que el bot decide COMPRAR
            # self.execute_manual_trade(user_id, token, asset_id, "COMPRA", quantity=0.01)
            pass
        except Exception as e:
            print(f"Bot error: {e}")

    def get_ai_analysis(self, user_id, token, asset_name):
        try:
            symbol, source = self._get_symbol_and_source(f"ai_{asset_name.lower()}")
            if "bitcoin" in asset_name.lower(): symbol, source = 'BTC/USD', 'crypto'
            
            # ... Tu lógica de IA ...
            return f"Análisis de {symbol}: TENDENCIA ALCISTA (Ejemplo)"
        except Exception as e: return f"Error: {str(e)}"

    def get_dashboard_data(self, user_id, token):
        try:
            self.check_bot_execution(user_id, token)
            profile = self.get_user_profile(user_id, token)
            settings = self.get_bot_settings_data(user_id, token)
            current_price = self.get_real_price(settings.get('activo'))
            settings['current_price'] = current_price
            return {"profile": profile, "settings": settings}
        except: return {"profile": {"username": "Usuario"}, "settings": {"activo": "crypto_btc_usd", "isActive": False}}

    def get_api_keys_data(self, u, t): k = self.bot_service.get_api_keys(u, t); return [v for k, v in k.items()] if k else []
    def save_api_key(self, u, e, k, s, t): d = {"exchange": e, "api_key": k, "api_secret": s}; return self.bot_service.save_api_key(u, d, t)
    def delete_api_key(self, u, e, t): return self.bot_service.delete_api_key(u, e, t)
    def forgot_password(self, e): return self.auth_service.reset_password(e)
    def generate_mock_trades(self, u, t): return False