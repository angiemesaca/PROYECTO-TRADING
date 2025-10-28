from firebase.auth_service import AuthService
from firebase.db_service import DBService
from firebase.bot_service import BotService

class MainViewModel:
    
    def __init__(self):
        self.auth_service = AuthService()
        self.db_service = DBService()
        self.bot_service = BotService()

    def login(self, email, password):
        user = self.auth_service.login_user(email, password)
        if user:
            user['localId'] = user.get('localId')
            return user
        return None

    def register(self, email, password, username):
        user_id = self.auth_service.register_user(email, password)
        if user_id:
            self.db_service.create_user_profile(user_id, email, username)
            self.bot_service.initialize_bot_settings(user_id)
            return True
        return False

    def get_profile(self, user_id, token):
        profile = self.db_service.get_user_profile(user_id, token)
        return profile if profile else {}

    def get_profile_page_data(self, user_id, token):
        profile = self.get_profile(user_id, token)
        markets = self.db_service.get_available_markets()
        return {"profile": profile, "markets": markets}

    def update_profile(self, user_id, username, risk, experience, market, token):
        data = {
            "username": username, "risk": risk, 
            "experience": experience, "selected_market": market
        }
        return self.db_service.update_user_profile(user_id, data, token)

    def delete_profile(self, user_id, token):
        return self.db_service.delete_user_profile(user_id, token)

    # --- Métodos del Bot actualizados ---
    def get_bot_settings_data(self, user_id, token):
        settings = self.bot_service.get_bot_settings(user_id, token)
        return settings if settings else {}
        
    def update_bot_settings(self, user_id, data, token):
        return self.bot_service.update_bot_settings(user_id, data, token)
    
    def generate_mock_trades(self, user_id, token):
        """
        Llama al servicio para poblar el log de trades,
        pero primero lee los ajustes del bot para saber QUÉ activo generar.
        """
        # 1. Lee los ajustes del usuario
        settings = self.get_bot_settings_data(user_id, token)
        
        # 2. Obtiene el activo seleccionado (default a BTC si algo falla)
        asset_seleccionado = settings.get("activo", "BTC/USD")
        
        # 3. Llama al servicio con el activo correcto
        return self.bot_service.generate_mock_trade_log(user_id, token, asset_seleccionado)
        
    def get_performance_data(self, user_id, token):
        trade_log = self.bot_service.get_trade_log(user_id, token)
        trade_list, labels_grafica, data_grafica = [], [], []

        if trade_log:
            try:
                sorted_trades = sorted(trade_log.values(), key=lambda x: x.get('timestamp', ''))
            except Exception:
                sorted_trades = trade_log.values()

            for trade in sorted_trades:
                trade_list.append(trade) 
                ts = trade.get('timestamp', 'N/A').split(' ')
                etiqueta_corta = ts[1] if len(ts) == 2 else ts[0] 
                labels_grafica.append(etiqueta_corta)
                data_grafica.append(trade.get('pnl_acumulado', 0))
        return {
            "all_trades": trade_list, "grafica_labels": labels_grafica,
            "grafica_data": data_grafica
        }

    # --- Métodos de Auth (no cambian) ---
    def update_password(self, id_token, new_password):
        return self.auth_service.change_password(id_token, new_password)

    def update_email(self, id_token, new_email):
        return self.auth_service.change_email(id_token, new_email)