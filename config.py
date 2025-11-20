"""Archivo de configuración para el extractor de facturas"""
import os
from pathlib import Path

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    # Cargar archivo .env si existe
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Si no existe .env, intentar cargar desde variables de entorno del sistema
        load_dotenv()
except ImportError:
    # Si python-dotenv no está instalado, solo usar variables de entorno del sistema
    pass

# Configuración de Tesseract OCR
# Si Tesseract no está en el PATH, especifica la ruta completa aquí
# Se puede configurar en .env como RUTA_TESSERACT o como variable de entorno
RUTA_TESSERACT = os.getenv('RUTA_TESSERACT', None)
if RUTA_TESSERACT == '':
    RUTA_TESSERACT = None

# Idioma para OCR (spa = español, eng = inglés)
IDIOMA_OCR = os.getenv('IDIOMA_OCR', 'spa+eng')

# Configuración de OCR
# PSM (Page Segmentation Mode):
# 0 = Orientación y detección de script (OSD)
# 1 = Segmentación automática con OSD
# 3 = Segmentación automática sin OSD
# 6 = Asumir un bloque uniforme de texto
# 11 = Texto disperso (recomendado para facturas con múltiples secciones)
# 12 = OCR de texto disperso con OSD
OCR_PSM = os.getenv('OCR_PSM', '11')

# DPI para conversión de PDF a imagen (mayor = mejor calidad pero más lento)
# 300 = Calidad estándar
# 400-600 = Mayor calidad (más lento)
OCR_DPI = int(os.getenv('OCR_DPI', '400'))

# Configuración adicional de Tesseract
OCR_CONFIG = '--psm ' + OCR_PSM + ' -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÁÉÍÓÚÑáéíóúñ.,:-/() '

# Configuración de Azure OpenAI para formatear texto OCR
USAR_AZURE_OPENAI = os.getenv('USAR_AZURE_OPENAI', 'True').lower() in ('true', '1', 'yes', 'on')
MODELO_AZURE = os.getenv('MODELO_AZURE', 'gpt-4o-mini')
AZURE_ENDPOINT = os.getenv('AZURE_ENDPOINT', '')
AZURE_API_KEY = os.getenv('AZURE_API_KEY', '')
AZURE_API_VERSION = os.getenv('AZURE_API_VERSION', '2025-01-01-preview')
