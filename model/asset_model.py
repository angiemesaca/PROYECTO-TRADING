from abc import ABC, abstractmethod
import random

# --- CLASE PADRE (ABSTRACCIÓN) ---
# Esta es la clase base que define qué debe tener cualquier activo
class ActivoFinanciero(ABC):
    def __init__(self, nombre, simbolo, riesgo_perfil):
        self.nombre = nombre
        self.simbolo = simbolo
        self.riesgo_perfil = riesgo_perfil

    # POLIMORFISMO: Cada hijo debe implementar este método a su manera
    @abstractmethod
    def generar_analisis_ia(self, indicadores):
        pass

    # HERENCIA: Este método es igual para todos los hijos
    def obtener_consejo_riesgo(self):
        if self.riesgo_perfil == 'alto':
            return "⚠️ Modo Agresivo: Usa Stop Loss ajustados (máx 2%). Busca ratios Riesgo/Beneficio de 1:3."
        elif self.riesgo_perfil == 'medio':
            return "⚖️ Modo Balanceado: Busca confirmación de doble indicador (ej: RSI + Cruce EMA). Riesgo sugerido 1% por operación."
        else:
            return "🛡️ Modo Conservador: Espera retrocesos a zonas de valor (Soportes Semanales). Prioriza la preservación de capital."

# --- CLASES HIJAS (HERENCIA Y POLIMORFISMO) ---

class CriptoActivo(ActivoFinanciero):
    def generar_analisis_ia(self, indicadores):
        volatilidad = random.choice(["Alta", "Extrema", "Moderada"])
        return (
            f"**Análisis Cripto ({self.nombre}):**\n"
            f"La volatilidad actual es **{volatilidad}**. El análisis On-Chain muestra movimientos de 'ballenas'. "
            f"Tus indicadores ({indicadores}) deben filtrarse con el volumen."
        )

class ForexActivo(ActivoFinanciero):
    def generar_analisis_ia(self, indicadores):
        sesion = random.choice(["Londres", "Nueva York", "Asiática"])
        return (
            f"**Análisis Forex ({self.nombre}):**\n"
            f"Par influenciado por la sesión de **{sesion}**. "
            f"Revisa el calendario económico para noticias de alto impacto (NFP/FOMC)."
        )

class StockActivo(ActivoFinanciero):
    def generar_analisis_ia(self, indicadores):
        return (
            f"**Análisis Bursátil ({self.nombre}):**\n"
            f"El precio está reaccionando a los reportes trimestrales (Earnings). "
            f"El volumen institucional es clave aquí. {indicadores} muestra divergencia."
        )

class CommodityActivo(ActivoFinanciero):
    def generar_analisis_ia(self, indicadores):
        return (
            f"**Análisis Materias Primas ({self.nombre}):**\n"
            f"Activo refugio. Correlación inversa con el DXY (Dólar). "
            f"Vigila zonas de oferta y demanda macroeconómicas."
        )

# --- FACTORY (Patrón de Diseño) ---
# Esta clase decide qué objeto crear según el código del activo
class ActivoFactory:
    @staticmethod
    def crear_activo(asset_code, riesgo):
        try:
            # Lógica para detectar el tipo de activo según el nombre (ej: "crypto_btc")
            if "crypto" in asset_code:
                nombre = asset_code.split('_')[1].upper() if len(asset_code.split('_')) > 1 else "CRYPTO"
                return CriptoActivo(nombre, asset_code, riesgo)
            
            elif "forex" in asset_code:
                parts = asset_code.split('_')
                nombre = f"{parts[1].upper()}/{parts[2].upper()}" if len(parts) > 2 else "FOREX"
                return ForexActivo(nombre, asset_code, riesgo)
            
            elif "stock" in asset_code or "index" in asset_code:
                nombre = asset_code.split('_')[1].upper() if len(asset_code.split('_')) > 1 else "STOCK"
                return StockActivo(nombre, asset_code, riesgo)
                
            else:
                return CommodityActivo("Oro (XAU)", asset_code, riesgo)
        except Exception:
            # Fallback por seguridad por si acaso
            return CriptoActivo("ACTIVO", asset_code, riesgo)