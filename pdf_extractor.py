"""Extractor de texto y campos de facturas PDF"""
import re
import os
import json
from typing import Optional
import io
from models import Factura, FacturaCabecera, FacturaDetalle

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image, ImageEnhance, ImageFilter
    import numpy as np
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    Image = None
    ImageEnhance = None
    ImageFilter = None
    np = None

try:
    from openai import AzureOpenAI
    AZURE_OPENAI_AVAILABLE = True
except ImportError:
    AZURE_OPENAI_AVAILABLE = False


class PDFExtractor:
    """Clase para extraer información de facturas PDF"""
    
    def __init__(self, usar_ocr=True, idioma_ocr='spa+eng', ruta_tesseract=None, 
                 ocr_psm='6', ocr_dpi=300, ocr_config=None,
                 usar_azure_openai=False, modelo_azure='gpt-4o-mini', 
                 azure_endpoint=None, azure_api_key=None, azure_api_version='2024-02-15-preview'):
        if pdfplumber is None:
            raise ImportError(
                "pdfplumber no está instalado. "
                "Ejecuta: pip install pdfplumber"
            )
        
        self.usar_ocr = usar_ocr and OCR_AVAILABLE
        self.idioma_ocr = idioma_ocr
        self.ocr_psm = ocr_psm
        self.ocr_dpi = ocr_dpi
        self.ocr_config = ocr_config or f'--psm {ocr_psm}'
        self.texto_extraido = ""  # Guardar texto extraído para visualización
        self._datos_azure = None  # Guardar datos JSON de Azure OpenAI
        
        # Configuración de Azure OpenAI
        self.usar_azure_openai = usar_azure_openai and AZURE_OPENAI_AVAILABLE
        self.modelo_azure = modelo_azure
        self.azure_endpoint = azure_endpoint
        self.azure_api_key = azure_api_key
        self.azure_api_version = azure_api_version
        self.azure_client = None
        
        # Estadísticas de uso de tokens
        self._tokens_prompt = 0  # Tokens de entrada acumulados
        self._tokens_completion = 0  # Tokens de salida acumulados
        self._tokens_total = 0  # Total de tokens acumulados
        self._llamadas_azure = 0  # Número de llamadas a Azure OpenAI
        
        if self.usar_azure_openai:
            if not azure_endpoint or not azure_api_key:
                print("Advertencia: Azure OpenAI requiere endpoint y API key configurados")
                self.usar_azure_openai = False
            else:
                try:
                    # Configurar cliente de Azure OpenAI
                    self.azure_client = AzureOpenAI(
                        api_key=azure_api_key,
                        api_version=azure_api_version,
                        azure_endpoint=azure_endpoint
                    )
                except Exception as e:
                    print(f"Advertencia: No se pudo configurar Azure OpenAI: {e}")
                    self.usar_azure_openai = False
        
        # Configurar ruta de Tesseract si se proporciona
        if ruta_tesseract:
            pytesseract.pytesseract.tesseract_cmd = ruta_tesseract
        
        if self.usar_ocr:
            try:
                # Verificar que tesseract esté disponible
                pytesseract.get_tesseract_version()
            except Exception as e:
                # Intentar rutas comunes de Windows
                rutas_comunes = [
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                    r'C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'.format(
                        os.environ.get('USERNAME', '')
                    ),
                ]
                
                tesseract_encontrado = False
                for ruta in rutas_comunes:
                    if os.path.exists(ruta):
                        pytesseract.pytesseract.tesseract_cmd = ruta
                        try:
                            pytesseract.get_tesseract_version()
                            tesseract_encontrado = True
                            print(f"Tesseract encontrado en: {ruta}")
                            break
                        except:
                            continue
                
                if not tesseract_encontrado:
                    print(f"Advertencia: Tesseract OCR no está disponible: {e}")
                    print("Instala Tesseract desde: https://github.com/UB-Mannheim/tesseract/wiki")
                    print("O configura la ruta manualmente en el código o GUI")
                    self.usar_ocr = False
    
    def extraer_texto(self, pdf_path: str) -> str:
        """Extrae todo el texto de un PDF usando OCR siempre, opcionalmente formateado con Azure OpenAI"""
        texto_completo = ""
        
        # Usar OCR siempre si está disponible
        if self.usar_ocr:
            try:
                texto_ocr = self._extraer_texto_ocr(pdf_path)
                if texto_ocr and len(texto_ocr.strip()) > 10:
                    self.texto_extraido = texto_ocr  # Guardar texto crudo para visualización
                    
                    # Si Azure OpenAI está disponible, formatear el texto
                    if self.usar_azure_openai:
                        try:
                            texto_completo = self._formatear_con_azure(texto_ocr)
                        except Exception as e:
                            print(f"Advertencia: Error al formatear con Azure OpenAI: {e}")
                            print("Usando texto OCR sin formatear...")
                            texto_completo = texto_ocr
                    else:
                        texto_completo = texto_ocr
            except Exception as e:
                print(f"Advertencia al usar OCR: {e}")
                # Si OCR falla, intentar extracción directa como respaldo
                try:
                    with pdfplumber.open(pdf_path) as pdf:
                        for page in pdf.pages:
                            texto = page.extract_text()
                            if texto:
                                texto_completo += texto + "\n"
                    self.texto_extraido = texto_completo
                except Exception as e2:
                    raise Exception(f"No se pudo extraer texto del PDF con OCR ni método directo: {e2}")
        else:
            # Si OCR no está disponible, usar extracción directa
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        texto = page.extract_text()
                        if texto:
                            texto_completo += texto + "\n"
                self.texto_extraido = texto_completo
            except Exception as e:
                raise Exception(f"Error al extraer texto del PDF: {e}. Considera instalar Tesseract OCR para mejor extracción.")
        
        if not texto_completo or len(texto_completo.strip()) < 10:
            raise Exception("No se pudo extraer texto del PDF. El archivo puede estar corrupto o ser una imagen sin texto.")
        
        return texto_completo
    
    def _formatear_con_azure(self, texto_ocr: str) -> str:
        """Formatea el texto OCR usando Azure OpenAI con structured output para extraer cabecera y detalle"""
        # Limitar texto a 8000 caracteres para no exceder límites (aumentado para incluir detalle)
        texto_limite = texto_ocr[:8000] if len(texto_ocr) > 8000 else texto_ocr
        
        # Definir el esquema JSON para structured output
        json_schema = {
            "type": "object",
            "properties": {
                "cabecera": {
                    "type": "object",
                    "properties": {
                        "numero_factura": {"type": ["string", "null"]},
                        "tipo_documento": {"type": ["string", "null"]},
                        "fecha_emision": {"type": ["string", "null"]},
                        "fecha_vencimiento": {"type": ["string", "null"]},
                        "proveedor_nombre": {"type": ["string", "null"]},
                        "proveedor_rut": {"type": ["string", "null"]},
                        "proveedor_actividad": {"type": ["string", "null"]},
                        "proveedor_direccion": {"type": ["string", "null"]},
                        "proveedor_telefono": {"type": ["string", "null"]},
                        "proveedor_email": {"type": ["string", "null"]},
                        "cliente_nombre": {"type": ["string", "null"]},
                        "cliente_rut": {"type": ["string", "null"]},
                        "cliente_direccion": {"type": ["string", "null"]},
                        "cliente_comuna": {"type": ["string", "null"]},
                        "cliente_ciudad": {"type": ["string", "null"]},
                        "cliente_giro": {"type": ["string", "null"]},
                        "cliente_codigo": {"type": ["string", "null"]},
                        "cliente_telefono": {"type": ["string", "null"]},
                        "cliente_patente": {"type": ["string", "null"]},
                        "direccion_origen": {"type": ["string", "null"]},
                        "ciudad_origen": {"type": ["string", "null"]},
                        "comuna_origen": {"type": ["string", "null"]},
                        "direccion_destino": {"type": ["string", "null"]},
                        "ciudad_destino": {"type": ["string", "null"]},
                        "comuna_destino": {"type": ["string", "null"]},
                        "codigo_vendedor": {"type": ["string", "null"]},
                        "tipo_despacho": {"type": ["string", "null"]},
                        "forma_pago": {"type": ["string", "null"]},
                        "condiciones_pago": {"type": ["string", "null"]},
                        "observaciones": {"type": ["string", "null"]},
                        "subtotal": {"type": ["number", "null"]},
                        "descuento_total": {"type": ["number", "null"]},
                        "impuesto_porcentaje": {"type": ["number", "null"]},
                        "impuesto_monto": {"type": ["number", "null"]},
                        "total": {"type": ["number", "null"]}
                    },
                    "required": []
                },
                "detalle": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "codigo": {"type": ["string", "null"]},
                            "descripcion": {"type": ["string", "null"]},
                            "cantidad": {"type": ["number", "null"]},
                            "unidad_medida": {"type": ["string", "null"]},
                            "precio_unitario": {"type": ["number", "null"]},
                            "descuento": {"type": ["number", "null"]},
                            "subtotal": {"type": ["number", "null"]},
                            "impuesto": {"type": ["number", "null"]},
                            "total_item": {"type": ["number", "null"]}
                        },
                        "required": []
                    }
                }
            },
            "required": ["cabecera", "detalle"]
        }
        
        prompt = f"""Eres un asistente especializado en extraer información estructurada de facturas chilenas. 
Analiza el siguiente texto extraído por OCR de una factura y extrae TODOS los campos de la cabecera y el detalle completo.

El texto puede tener errores de OCR. Tu tarea es:
1. Identificar y corregir TODOS los campos de la cabecera (incluyendo información del proveedor, cliente, origen/destino, totales, etc.)
2. Extraer TODOS los items/productos del detalle con sus cantidades, precios y totales
3. Corregir errores obvios de OCR (ej: "0" por "O" en nombres, pero mantén números correctos)

CAMPOS DE CABECERA A EXTRAER:
- Información del documento: numero_factura, tipo_documento, fecha_emision, fecha_vencimiento
- Información del proveedor: proveedor_nombre, proveedor_rut, proveedor_actividad, proveedor_direccion, proveedor_telefono, proveedor_email
- Información del cliente: cliente_nombre, cliente_rut, cliente_direccion, cliente_comuna, cliente_ciudad, cliente_giro, cliente_codigo, cliente_telefono, cliente_patente
- Información de origen: direccion_origen, ciudad_origen, comuna_origen
- Información de destino: direccion_destino, ciudad_destino, comuna_destino
- Información adicional: codigo_vendedor, tipo_despacho, forma_pago, condiciones_pago, observaciones
- Totales: subtotal, descuento_total, impuesto_porcentaje, impuesto_monto, total

CAMPOS DE DETALLE A EXTRAER (para cada item):
- codigo, descripcion, cantidad, unidad_medida, precio_unitario, descuento, subtotal, impuesto, total_item

INSTRUCCIONES:
- Para fechas, normaliza al formato YYYY-MM-DD si es posible
- Para RUTs, usa el formato XX.XXX.XXX-X
- Para números monetarios, extrae solo el número (sin símbolos ni espacios)
- Si un campo no se encuentra, usa null
- Para el detalle, extrae TODOS los items/productos que encuentres en la factura
- Busca cuidadosamente en TODO el texto, no solo en las primeras líneas
- Los campos pueden estar en diferentes secciones de la factura
- El cliente debes homologarlo con "PRIZE PROSERVICE S.A" O "PRIZE PROSERVICE SPA"


Texto de la factura:
{texto_limite}"""

        try:
            # Intentar primero con json_schema structured output
            try:
                response = self.azure_client.chat.completions.create(
                    model=self.modelo_azure,
                    messages=[
                        {
                            "role": "system",
                            "content": "Eres un asistente especializado en extraer información estructurada de facturas chilenas. Debes extraer TODOS los campos de la cabecera (proveedor, cliente, origen, destino, totales) y TODOS los items del detalle. Busca cuidadosamente en todo el documento."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.1,
                    max_tokens=8000,  # Aumentado para facturas grandes
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "factura_schema",
                            "strict": False,
                            "schema": json_schema
                        }
                    }
                )
                
                # Obtener la respuesta
                respuesta = response.choices[0].message.content.strip()
                datos = json.loads(respuesta)
                
                # Capturar uso de tokens
                if hasattr(response, 'usage') and response.usage:
                    self._tokens_prompt += response.usage.prompt_tokens
                    self._tokens_completion += response.usage.completion_tokens
                    self._tokens_total += response.usage.total_tokens
                    self._llamadas_azure += 1
                    print(f"Tokens usados - Prompt: {response.usage.prompt_tokens}, Completion: {response.usage.completion_tokens}, Total: {response.usage.total_tokens}")
                
            except Exception as e_parse:
                # Si json_schema falla, usar json_object
                print(f"Advertencia: json_schema falló, usando json_object: {e_parse}")
                try:
                    response = self.azure_client.chat.completions.create(
                        model=self.modelo_azure,
                        messages=[
                            {
                                "role": "system",
                                "content": "Eres un asistente especializado en extraer información estructurada de facturas chilenas. Devuelve siempre un JSON válido con estructura: {'cabecera': {...}, 'detalle': [...]}. Debes extraer TODOS los campos: proveedor (nombre, rut, actividad, dirección), cliente (nombre, rut, dirección, comuna, ciudad, giro, código), origen (dirección, ciudad, comuna), destino, totales (subtotal, impuesto, total), y todos los items del detalle."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        temperature=0.1,
                        max_tokens=8000,
                        response_format={"type": "json_object"}
                    )
                    
                    respuesta = response.choices[0].message.content.strip()
                    datos = json.loads(respuesta)
                    
                    # Capturar uso de tokens
                    if hasattr(response, 'usage') and response.usage:
                        self._tokens_prompt += response.usage.prompt_tokens
                        self._tokens_completion += response.usage.completion_tokens
                        self._tokens_total += response.usage.total_tokens
                        self._llamadas_azure += 1
                        print(f"Tokens usados - Prompt: {response.usage.prompt_tokens}, Completion: {response.usage.completion_tokens}, Total: {response.usage.total_tokens}")
                except Exception as e2:
                    print(f"Advertencia: Error al formatear con Azure OpenAI: {e2}")
                    import traceback
                    traceback.print_exc()
                    self._datos_azure = None
                    return texto_ocr
            
            # Guardar datos para uso directo
            self._datos_azure = datos
            
            # Debug: imprimir qué campos se extrajeron
            if datos.get('cabecera'):
                campos_extraidos = [k for k, v in datos['cabecera'].items() if v is not None]
                print(f"Campos de cabecera extraídos: {len(campos_extraidos)} - {campos_extraidos[:10]}")
            elif isinstance(datos, dict):
                # Si no hay 'cabecera', los datos pueden estar directamente en el dict
                campos_extraidos = [k for k, v in datos.items() if v is not None and k != 'detalle']
                print(f"Campos extraídos (estructura plana): {len(campos_extraidos)} - {campos_extraidos[:10]}")
            if datos.get('detalle'):
                print(f"Items de detalle extraídos: {len(datos['detalle'])}")
            
            # Convertir el JSON a texto formateado para compatibilidad
            texto_formateado = self._json_a_texto_formateado(datos, texto_ocr)
            return texto_formateado
                
        except Exception as e:
            print(f"Advertencia: Error al formatear con Azure OpenAI: {e}")
            import traceback
            traceback.print_exc()
            self._datos_azure = None
            return texto_ocr
    
    def _json_a_texto_formateado(self, datos: dict, texto_original: str) -> str:
        """Convierte el JSON extraído por Azure OpenAI a texto formateado para el parser"""
        # Crear un texto estructurado que el parser pueda entender
        lineas = []
        
        # Manejar estructura con cabecera y detalle separados, o estructura plana
        cabecera_data = datos.get('cabecera', datos)  # Si hay 'cabecera', usarla, sino usar datos directamente
        
        # Agregar campos principales de forma estructurada
        if cabecera_data.get('tipo_documento'):
            lineas.append(f"TIPO DOCUMENTO: {cabecera_data['tipo_documento']}")
        if cabecera_data.get('numero_factura'):
            lineas.append(f"N° {cabecera_data['numero_factura']}")
        if cabecera_data.get('fecha_emision'):
            lineas.append(f"FECHA EMISIÓN: {cabecera_data['fecha_emision']}")
        if cabecera_data.get('fecha_vencimiento'):
            lineas.append(f"FECHA VENCIMIENTO: {cabecera_data['fecha_vencimiento']}")
        
        if cabecera_data.get('proveedor_nombre'):
            lineas.append(f"PROVEEDOR: {cabecera_data['proveedor_nombre']}")
        if cabecera_data.get('proveedor_rut'):
            lineas.append(f"R.U.T. {cabecera_data['proveedor_rut']}")
        if cabecera_data.get('proveedor_actividad'):
            lineas.append(f"ACTIVIDAD: {cabecera_data['proveedor_actividad']}")
        if cabecera_data.get('proveedor_direccion'):
            lineas.append(f"DIRECCIÓN: {cabecera_data['proveedor_direccion']}")
        
        if cabecera_data.get('cliente_nombre'):
            lineas.append(f"SEÑORES: {cabecera_data['cliente_nombre']}")
        if cabecera_data.get('cliente_rut'):
            lineas.append(f"R.U.T.: {cabecera_data['cliente_rut']}")
        if cabecera_data.get('cliente_direccion'):
            lineas.append(f"DIRECCIÓN: {cabecera_data['cliente_direccion']}")
        if cabecera_data.get('cliente_comuna'):
            lineas.append(f"COMUNA: {cabecera_data['cliente_comuna']}")
        if cabecera_data.get('cliente_ciudad'):
            lineas.append(f"CIUDAD: {cabecera_data['cliente_ciudad']}")
        if cabecera_data.get('cliente_giro'):
            lineas.append(f"GIRO: {cabecera_data['cliente_giro']}")
        if cabecera_data.get('cliente_codigo'):
            lineas.append(f"CÓDIGO: {cabecera_data['cliente_codigo']}")
        
        if cabecera_data.get('direccion_origen'):
            lineas.append(f"Dirección Origen: {cabecera_data['direccion_origen']}")
        if cabecera_data.get('ciudad_origen'):
            lineas.append(f"Ciudad: {cabecera_data['ciudad_origen']}")
        if cabecera_data.get('comuna_origen'):
            lineas.append(f"Comuna: {cabecera_data['comuna_origen']}")
        
        if cabecera_data.get('codigo_vendedor'):
            lineas.append(f"COD. VENDEDOR: {cabecera_data['codigo_vendedor']}")
        if cabecera_data.get('tipo_despacho'):
            lineas.append(f"TIPO DESPACHO: {cabecera_data['tipo_despacho']}")
        if cabecera_data.get('forma_pago'):
            lineas.append(f"FORMA DE PAGO: {cabecera_data['forma_pago']}")
        
        if cabecera_data.get('subtotal'):
            lineas.append(f"Subtotal: {cabecera_data['subtotal']}")
        if cabecera_data.get('impuesto_monto'):
            lineas.append(f"IVA: {cabecera_data['impuesto_monto']}")
        if cabecera_data.get('total'):
            lineas.append(f"Total: {cabecera_data['total']}")
        
        # Agregar información del detalle si está disponible
        detalle_data = datos.get('detalle', [])
        if detalle_data:
            lineas.append("\nDETALLE:")
            for item in detalle_data:
                if item.get('descripcion'):
                    item_line = item['descripcion']
                    if item.get('cantidad'):
                        item_line = f"{item['cantidad']} {item_line}"
                    if item.get('precio_unitario'):
                        item_line += f" ${item['precio_unitario']}"
                    if item.get('total_item'):
                        item_line += f" Total: ${item['total_item']}"
                    lineas.append(item_line)
        
        # Agregar el texto original al final para preservar información adicional
        texto_formateado = "\n".join(lineas) + "\n\n" + texto_original
        
        return texto_formateado
    
    def obtener_texto_extraido(self) -> str:
        """Retorna el texto crudo extraído por OCR"""
        return self.texto_extraido
    
    def obtener_estadisticas_tokens(self) -> dict:
        """Retorna estadísticas de uso de tokens de Azure OpenAI"""
        return {
            'tokens_prompt': self._tokens_prompt,
            'tokens_completion': self._tokens_completion,
            'tokens_total': self._tokens_total,
            'llamadas': self._llamadas_azure,
            'promedio_por_llamada': self._tokens_total / self._llamadas_azure if self._llamadas_azure > 0 else 0
        }
    
    def resetear_estadisticas_tokens(self):
        """Reinicia las estadísticas de tokens"""
        self._tokens_prompt = 0
        self._tokens_completion = 0
        self._tokens_total = 0
        self._llamadas_azure = 0
    
    def _preprocesar_imagen(self, imagen):
        """Preprocesa la imagen para mejorar la calidad del OCR"""
        if Image is None or np is None:
            return imagen  # Si no hay PIL/numpy, devolver imagen original
        
        # Convertir a RGB si es necesario
        if imagen.mode != 'RGB':
            imagen = imagen.convert('RGB')
        
        # Convertir a numpy array para procesamiento
        img_array = np.array(imagen)
        
        # Convertir a escala de grises
        if len(img_array.shape) == 3:
            # Promedio de canales RGB para escala de grises
            gray = np.mean(img_array, axis=2).astype(np.uint8)
        else:
            gray = img_array
        
        # Aplicar filtro para reducir ruido
        pil_gray = Image.fromarray(gray)
        pil_gray = pil_gray.filter(ImageFilter.MedianFilter(size=3))
        
        # Mejorar contraste
        enhancer = ImageEnhance.Contrast(pil_gray)
        pil_gray = enhancer.enhance(1.5)  # Aumentar contraste 50%
        
        # Mejorar nitidez
        enhancer = ImageEnhance.Sharpness(pil_gray)
        pil_gray = enhancer.enhance(1.2)  # Aumentar nitidez 20%
        
        # Binarización adaptativa (umbral)
        img_array = np.array(pil_gray)
        # Usar umbral adaptativo (Otsu-like)
        threshold = np.mean(img_array)
        binary = np.where(img_array > threshold, 255, 0).astype(np.uint8)
        
        # Convertir de vuelta a PIL Image
        imagen_procesada = Image.fromarray(binary)
        
        # Escalar si es muy pequeña (mejorar resolución)
        width, height = imagen_procesada.size
        if width < 1000 or height < 1000:
            # Escalar a al menos 2000px en la dimensión más grande
            scale = max(2000 / width, 2000 / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            imagen_procesada = imagen_procesada.resize((new_width, new_height), Image.LANCZOS)
        
        return imagen_procesada
    
    def _extraer_texto_ocr(self, pdf_path: str) -> str:
        """Extrae texto usando OCR de las páginas del PDF con preprocesamiento mejorado"""
        texto_completo = ""
        
        try:
            # Convertir PDF a imágenes usando pdf2image
            # Nota: requiere poppler instalado en el sistema
            imagenes = convert_from_path(pdf_path, dpi=self.ocr_dpi)
            
            for imagen in imagenes:
                # Preprocesar imagen para mejorar OCR
                imagen_procesada = self._preprocesar_imagen(imagen)
                
                # Configuración mejorada de Tesseract
                # PSM 6: Asumir un bloque uniforme de texto
                # PSM 11: Texto disperso (mejor para facturas con múltiples secciones)
                # PSM 12: OCR de texto disperso con OSD
                ocr_config_mejorado = f'--psm {self.ocr_psm} -c preserve_interword_spaces=1 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÁÉÍÓÚÑáéíóúñ.,:-/()&%$#@!?=+*[]{{}}|\\"\' '
                
                # Realizar OCR en la imagen preprocesada
                texto_pagina = pytesseract.image_to_string(
                    imagen_procesada, 
                    lang=self.idioma_ocr,
                    config=ocr_config_mejorado
                )
                
                # Post-procesamiento: corregir errores comunes
                texto_pagina = self._postprocesar_texto(texto_pagina)
                
                if texto_pagina:
                    texto_completo += texto_pagina + "\n"
        
        except Exception as e:
            # Si pdf2image falla, intentar con pdfplumber
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        # Convertir página a imagen
                        im = page.to_image(resolution=self.ocr_dpi)
                        pil_image = im.original
                        
                        # Preprocesar imagen
                        imagen_procesada = self._preprocesar_imagen(pil_image)
                        
                        # Configuración mejorada
                        ocr_config_mejorado = f'--psm {self.ocr_psm} -c preserve_interword_spaces=1 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÁÉÍÓÚÑáéíóúñ.,:-/()&%$#@!?=+*[]{{}}|\\"\' '
                        
                        # Realizar OCR
                        texto_pagina = pytesseract.image_to_string(
                            imagen_procesada,
                            lang=self.idioma_ocr,
                            config=ocr_config_mejorado
                        )
                        
                        # Post-procesamiento
                        texto_pagina = self._postprocesar_texto(texto_pagina)
                        
                        if texto_pagina:
                            texto_completo += texto_pagina + "\n"
            except Exception as e2:
                raise Exception(f"Error en OCR: {e2}")
        
        return texto_completo
    
    def _postprocesar_texto(self, texto: str) -> str:
        """Post-procesa el texto OCR solo para limpieza básica (sin correcciones de nombres)"""
        if not texto:
            return texto
        
        # Solo limpieza básica: espacios múltiples y espacios al inicio/final de líneas
        # NO corregir nombres de empresas - dejar que el LLM lo haga
        texto = re.sub(r' +', ' ', texto)
        
        # Corregir espacios al inicio y final de líneas
        lineas = texto.split('\n')
        lineas = [linea.strip() for linea in lineas]
        texto = '\n'.join(lineas)
        
        return texto
    
    def extraer_factura(self, pdf_path: str) -> Factura:
        """Extrae la información completa de una factura"""
        texto = self.extraer_texto(pdf_path)
        factura = Factura()
        
        # Si se usó Azure OpenAI, intentar extraer directamente desde JSON estructurado
        if self.usar_azure_openai and hasattr(self, '_datos_azure') and self._datos_azure:
            # Extraer cabecera desde JSON
            datos_cabecera = self._datos_azure.get('cabecera', self._datos_azure)
            factura.cabecera = self._llenar_cabecera_desde_json(datos_cabecera)
            
            # Extraer detalle desde JSON
            datos_detalle = self._datos_azure.get('detalle', [])
            factura.detalle = self._llenar_detalle_desde_json(datos_detalle)
        else:
            # Extraer cabecera usando patrones regex
            factura.cabecera = self._extraer_cabecera(texto)
            
            # Extraer detalle usando patrones regex
            factura.detalle = self._extraer_detalle(texto)
        
        return factura
    
    def _llenar_cabecera_desde_json(self, datos: dict) -> FacturaCabecera:
        """Llena el modelo de cabecera directamente desde el JSON de Azure OpenAI"""
        cabecera = FacturaCabecera()
        
        # Mapear campos del JSON al modelo
        cabecera.numero_factura = datos.get('numero_factura')
        cabecera.tipo_documento = datos.get('tipo_documento')
        cabecera.fecha_emision = datos.get('fecha_emision')
        cabecera.fecha_vencimiento = datos.get('fecha_vencimiento')
        
        cabecera.proveedor_nombre = datos.get('proveedor_nombre')
        cabecera.proveedor_rut = datos.get('proveedor_rut')
        cabecera.proveedor_actividad = datos.get('proveedor_actividad')
        cabecera.proveedor_direccion = datos.get('proveedor_direccion')
        cabecera.proveedor_telefono = datos.get('proveedor_telefono')
        cabecera.proveedor_email = datos.get('proveedor_email')
        
        cabecera.cliente_nombre = datos.get('cliente_nombre')
        cabecera.cliente_rut = datos.get('cliente_rut')
        cabecera.cliente_direccion = datos.get('cliente_direccion')
        cabecera.cliente_comuna = datos.get('cliente_comuna')
        cabecera.cliente_ciudad = datos.get('cliente_ciudad')
        cabecera.cliente_giro = datos.get('cliente_giro')
        cabecera.cliente_codigo = datos.get('cliente_codigo')
        cabecera.cliente_telefono = datos.get('cliente_telefono')
        cabecera.cliente_patente = datos.get('cliente_patente')
        
        cabecera.direccion_origen = datos.get('direccion_origen')
        cabecera.ciudad_origen = datos.get('ciudad_origen')
        cabecera.comuna_origen = datos.get('comuna_origen')
        cabecera.direccion_destino = datos.get('direccion_destino')
        cabecera.ciudad_destino = datos.get('ciudad_destino')
        cabecera.comuna_destino = datos.get('comuna_destino')
        
        cabecera.codigo_vendedor = datos.get('codigo_vendedor')
        cabecera.tipo_despacho = datos.get('tipo_despacho')
        cabecera.forma_pago = datos.get('forma_pago')
        cabecera.condiciones_pago = datos.get('condiciones_pago')
        cabecera.observaciones = datos.get('observaciones')
        
        # Convertir números (pueden venir como número o string)
        if datos.get('subtotal') is not None:
            cabecera.subtotal = float(datos['subtotal']) if isinstance(datos['subtotal'], (int, float)) else self._parsear_numero(str(datos['subtotal']))
        if datos.get('descuento_total') is not None:
            cabecera.descuento_total = float(datos['descuento_total']) if isinstance(datos['descuento_total'], (int, float)) else self._parsear_numero(str(datos['descuento_total']))
        if datos.get('impuesto_porcentaje') is not None:
            cabecera.impuesto_porcentaje = float(datos['impuesto_porcentaje']) if isinstance(datos['impuesto_porcentaje'], (int, float)) else self._parsear_numero(str(datos['impuesto_porcentaje']))
        if datos.get('impuesto_monto') is not None:
            cabecera.impuesto_monto = float(datos['impuesto_monto']) if isinstance(datos['impuesto_monto'], (int, float)) else self._parsear_numero(str(datos['impuesto_monto']))
        if datos.get('total') is not None:
            cabecera.total = float(datos['total']) if isinstance(datos['total'], (int, float)) else self._parsear_numero(str(datos['total']))
        
        return cabecera
    
    def _llenar_detalle_desde_json(self, datos_detalle: list) -> list:
        """Llena el detalle directamente desde el JSON de Azure OpenAI"""
        items = []
        
        if not datos_detalle:
            return items
        
        for item_data in datos_detalle:
            item = FacturaDetalle()
            
            item.codigo = item_data.get('codigo')
            item.descripcion = item_data.get('descripcion')
            item.unidad_medida = item_data.get('unidad_medida')
            
            # Convertir números (pueden venir como número o string)
            if item_data.get('cantidad') is not None:
                item.cantidad = float(item_data['cantidad']) if isinstance(item_data['cantidad'], (int, float)) else self._parsear_numero(str(item_data['cantidad']))
            if item_data.get('precio_unitario') is not None:
                item.precio_unitario = float(item_data['precio_unitario']) if isinstance(item_data['precio_unitario'], (int, float)) else self._parsear_numero(str(item_data['precio_unitario']))
            if item_data.get('descuento') is not None:
                item.descuento = float(item_data['descuento']) if isinstance(item_data['descuento'], (int, float)) else self._parsear_numero(str(item_data['descuento']))
            if item_data.get('subtotal') is not None:
                item.subtotal = float(item_data['subtotal']) if isinstance(item_data['subtotal'], (int, float)) else self._parsear_numero(str(item_data['subtotal']))
            if item_data.get('impuesto') is not None:
                item.impuesto = float(item_data['impuesto']) if isinstance(item_data['impuesto'], (int, float)) else self._parsear_numero(str(item_data['impuesto']))
            if item_data.get('total_item') is not None:
                item.total_item = float(item_data['total_item']) if isinstance(item_data['total_item'], (int, float)) else self._parsear_numero(str(item_data['total_item']))
            
            # Si no hay total_item pero hay cantidad y precio, calcularlo
            if not item.total_item and item.cantidad and item.precio_unitario:
                item.total_item = item.cantidad * item.precio_unitario
                if item.descuento:
                    item.total_item -= item.descuento
            
            items.append(item)
        
        return items
    
    def _extraer_cabecera(self, texto: str) -> FacturaCabecera:
        """Extrae los campos de la cabecera de la factura"""
        cabecera = FacturaCabecera()
        
        # Tipo de documento
        patrones_tipo = [
            r'(FACTURA\s+ELECTR[ÓO]NICA)',
            r'(Factura\s+Electr[óo]nica)',
            r'(?:Tipo\s+Documento|TIPO\s+DE\s+DOCUMENTO)[\s:]*([A-ZÁÉÍÓÚÑ\s]+)',
        ]
        cabecera.tipo_documento = self._buscar_patron(texto, patrones_tipo)
        
        # Número de factura - buscar patrones comunes
        patrones_numero = [
            r'N[°º]\s*([0-9]+)',
            r'(?:Factura|FACTURA|Fact\.|FACT\.|N°|Nº|No\.|Número)[\s:]*([0-9\-]+)',
            r'(?:Invoice|INVOICE|Inv\.)[\s:]*([A-Z0-9\-]+)',
            r'#[\s]*([0-9\-]+)',
        ]
        cabecera.numero_factura = self._buscar_patron(texto, patrones_numero)
        
        # Fecha de emisión
        patrones_fecha_emision = [
            r'FECHA\s+EMISI[ÓO]N\s*:\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
            r'(?:Fecha\s+Emisi[óo]n|FECHA\s+EMISI[ÓO]N|Date|DATE|Emitido|Emitida)[\s:]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        ]
        cabecera.fecha_emision = self._buscar_patron(texto, patrones_fecha_emision)
        
        # Fecha de vencimiento
        patrones_fecha_vencimiento = [
            r'FECHA\s+VENCIMIENTO\s*:\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
            r'(?:Fecha\s+Vencimiento|FECHA\s+VENCIMIENTO|Due\s+Date)[\s:]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        ]
        cabecera.fecha_vencimiento = self._buscar_patron(texto, patrones_fecha_vencimiento)
        
        # RUT/NIT del proveedor - buscar en la caja roja o al inicio
        patrones_rut_proveedor = [
            r'R\.U\.T\.\s*([0-9]{1,2}\.[0-9]{3}\.[0-9]{3}[-][0-9Kk])',
            r'(?:RUT|R\.U\.T\.|NIT|N\.I\.T\.|CUIT)[\s:]*([0-9\.\-]+[0-9Kk])',
            r'([0-9]{1,2}\.[0-9]{3}\.[0-9]{3}[-][0-9Kk])',
        ]
        cabecera.proveedor_rut = self._buscar_patron(texto, patrones_rut_proveedor)
        
        # Nombre del proveedor - buscar al inicio del documento
        patrones_nombre_proveedor = [
            r'^([A-ZÁÉÍÓÚÑ\s]+S\.A\.|S\.A\.C\.|LTDA\.|E\.I\.R\.L\.)',
            r'(?:Razón Social|Razon Social|Nombre|NOMBRE|Proveedor|PROVEEDOR)[\s:]*([A-ZÁÉÍÓÚÑ\s\.]+)',
            r'(?:Empresa|EMPRESA|Company|COMPANY)[\s:]*([A-ZÁÉÍÓÚÑ\s\.]+)',
        ]
        cabecera.proveedor_nombre = self._buscar_patron(texto, patrones_nombre_proveedor)
        
        # Actividad/Giro del proveedor
        patrones_actividad = [
            r'(?:AGROINDUSTRIA|Agroindustria|Actividad|ACTIVIDAD|Giro|GIRO)[\s:]*([A-ZÁÉÍÓÚÑ\s\.,]+)',
        ]
        cabecera.proveedor_actividad = self._buscar_patron(texto, patrones_actividad)
        
        # Dirección del proveedor
        patrones_direccion = [
            r'(?:Dirección|Direccion|DIRECCION|Address|ADDRESS)[\s:]*([A-Z0-9ÁÉÍÓÚÑ\s\.,#\-]+)',
        ]
        cabecera.proveedor_direccion = self._buscar_patron(texto, patrones_direccion)
        
        # Información del cliente - buscar en sección "SEÑORES"
        # Nombre del cliente
        patrones_nombre_cliente = [
            r'SE[ÑN]ORES\s*:\s*([A-ZÁÉÍÓÚÑ\s\.]+(?:S\.A\.|S\.A\.C\.|LTDA\.|E\.I\.R\.L\.)?)',
            r'(?:Cliente|CLIENTE|Customer|CUSTOMER|Señor|Sr\.|Sra\.)[\s:]*([A-ZÁÉÍÓÚÑ\s\.]+)',
        ]
        cabecera.cliente_nombre = self._buscar_patron(texto, patrones_nombre_cliente)
        
        # RUT del cliente
        patrones_rut_cliente = [
            r'R\.U\.T\.\s*:\s*([0-9\.\-]+[0-9Kk])',
            r'(?:Cliente|CLIENTE|Customer|CUSTOMER).*?R\.U\.T\.\s*:\s*([0-9\.\-]+[0-9Kk])',
        ]
        cabecera.cliente_rut = self._buscar_patron(texto, patrones_rut_cliente)
        
        # Dirección del cliente
        patrones_direccion_cliente = [
            r'DIRECCI[ÓO]N\s*:\s*([A-Z0-9ÁÉÍÓÚÑ\s\.,#\-KL]+)',
            r'(?:Cliente|CLIENTE).*?DIRECCI[ÓO]N\s*:\s*([A-Z0-9ÁÉÍÓÚÑ\s\.,#\-]+)',
        ]
        cabecera.cliente_direccion = self._buscar_patron(texto, patrones_direccion_cliente)
        
        # Comuna del cliente
        patrones_comuna_cliente = [
            r'COMUNA\s*:\s*([A-ZÁÉÍÓÚÑ\s]+)',
        ]
        cabecera.cliente_comuna = self._buscar_patron(texto, patrones_comuna_cliente)
        
        # Ciudad del cliente
        patrones_ciudad_cliente = [
            r'CIUDAD\s*:\s*([A-ZÁÉÍÓÚÑ\s]+)',
        ]
        cabecera.cliente_ciudad = self._buscar_patron(texto, patrones_ciudad_cliente)
        
        # Giro del cliente
        patrones_giro_cliente = [
            r'GIRO\s*:\s*([A-ZÁÉÍÓÚÑ\s]+)',
        ]
        cabecera.cliente_giro = self._buscar_patron(texto, patrones_giro_cliente)
        
        # Código del cliente
        patrones_codigo_cliente = [
            r'C[ÓO]DIGO\s*:\s*([0-9]+)',
        ]
        cabecera.cliente_codigo = self._buscar_patron(texto, patrones_codigo_cliente)
        
        # Teléfono del cliente
        patrones_telefono_cliente = [
            r'TELEFONO\s*:\s*([0-9\s\-\+\(\)]+)',
        ]
        cabecera.cliente_telefono = self._buscar_patron(texto, patrones_telefono_cliente)
        
        # Patente del cliente
        patrones_patente_cliente = [
            r'PATENTE\s*:\s*([A-Z0-9\s\-]+)',
        ]
        cabecera.cliente_patente = self._buscar_patron(texto, patrones_patente_cliente)
        
        # Dirección Origen
        patrones_direccion_origen = [
            r'Direcci[óo]n\s+Origen:\s*([A-Z0-9ÁÉÍÓÚÑ\s\.,#\-]+)',
            r'DIRECCI[ÓO]N\s+ORIGEN\s*:\s*([A-Z0-9ÁÉÍÓÚÑ\s\.,#\-]+)',
        ]
        cabecera.direccion_origen = self._buscar_patron(texto, patrones_direccion_origen)
        
        # Ciudad Origen
        patrones_ciudad_origen = [
            r'Ciudad:\s*([A-ZÁÉÍÓÚÑ\s]+)',
            r'CIUDAD\s*:\s*([A-ZÁÉÍÓÚÑ\s]+)',
        ]
        cabecera.ciudad_origen = self._buscar_patron(texto, patrones_ciudad_origen)
        
        # Comuna Origen
        patrones_comuna_origen = [
            r'Comuna\s*:\s*([A-ZÁÉÍÓÚÑ\s]+)',
            r'COMUNA\s*:\s*([A-ZÁÉÍÓÚÑ\s]+)',
        ]
        cabecera.comuna_origen = self._buscar_patron(texto, patrones_comuna_origen)
        
        # Dirección Destino
        patrones_direccion_destino = [
            r'Direcci[óo]n\s+Destino:\s*([A-Z0-9ÁÉÍÓÚÑ\s\.,#\-]+)',
            r'DIRECCI[ÓO]N\s+DESTINO\s*:\s*([A-Z0-9ÁÉÍÓÚÑ\s\.,#\-]+)',
        ]
        cabecera.direccion_destino = self._buscar_patron(texto, patrones_direccion_destino)
        
        # Ciudad Destino
        patrones_ciudad_destino = [
            r'Ciudad\s*:\s*([A-ZÁÉÍÓÚÑ\s]+)',
        ]
        cabecera.ciudad_destino = self._buscar_patron(texto, patrones_ciudad_destino)
        
        # Comuna Destino
        patrones_comuna_destino = [
            r'Comuna\s*:\s*([A-ZÁÉÍÓÚÑ\s]+)',
        ]
        cabecera.comuna_destino = self._buscar_patron(texto, patrones_comuna_destino)
        
        # Código Vendedor
        patrones_codigo_vendedor = [
            r'COD\.\s+VENDEDOR\s*:\s*([0-9]+)',
            r'C[ÓO]D\.\s+VENDEDOR\s*:\s*([0-9]+)',
        ]
        cabecera.codigo_vendedor = self._buscar_patron(texto, patrones_codigo_vendedor)
        
        # Tipo Despacho
        patrones_tipo_despacho = [
            r'TIPO\s+DESPACHO\s*:\s*([A-ZÁÉÍÓÚÑ\s]+)',
        ]
        cabecera.tipo_despacho = self._buscar_patron(texto, patrones_tipo_despacho)
        
        # Forma de pago
        patrones_pago = [
            r'FORMA\s+DE\s+PAGO\s*:\s*([A-ZÁÉÍÓÚÑ\s]+)',
            r'(?:Forma\s+de\s+Pago|Forma\s+Pago|Payment|PAYMENT)[\s:]*([A-ZÁÉÍÓÚÑ\s]+)',
        ]
        cabecera.forma_pago = self._buscar_patron(texto, patrones_pago)
        
        # Totales
        patrones_subtotal = [
            r'(?:Subtotal|SUBTOTAL|Sub\s+Total)[\s:]*\$?\s*([0-9.,]+)',
            r'(?:Subtotal|SUBTOTAL)[\s:]*([0-9.,]+)',
        ]
        subtotal_str = self._buscar_patron(texto, patrones_subtotal)
        cabecera.subtotal = self._parsear_numero(subtotal_str)
        
        patrones_impuesto = [
            r'(?:IVA|I\.V\.A\.|Impuesto|IMPUESTO|Tax|TAX)[\s:]*\$?\s*([0-9.,]+)',
            r'(?:IVA|I\.V\.A\.)[\s%]*([0-9.,]+)',
        ]
        impuesto_str = self._buscar_patron(texto, patrones_impuesto)
        cabecera.impuesto_monto = self._parsear_numero(impuesto_str)
        
        patrones_total = [
            r'(?:Total|TOTAL|Total\s+a\s+Pagar|TOTAL\s+A\s+PAGAR)[\s:]*\$?\s*([0-9.,]+)',
            r'(?:Total|TOTAL)[\s:]*([0-9.,]+)',
        ]
        total_str = self._buscar_patron(texto, patrones_total)
        cabecera.total = self._parsear_numero(total_str)
        
        return cabecera
    
    def _extraer_detalle(self, texto: str) -> list:
        """Extrae los items del detalle de la factura"""
        items = []
        
        # Buscar sección de detalle - comúnmente después de palabras clave
        secciones_detalle = [
            r'(?:Detalle|DETALLE|Items|ITEMS|Productos|PRODUCTOS|Descripción|DESCRIPCION)(.*?)(?:Subtotal|TOTAL|Total|$)',
            r'(?:Cant\.|Cantidad|CANTIDAD).*?(?:Descripción|DESCRIPCION).*?(?:Precio|PRECIO).*?(?:Total|TOTAL)(.*?)(?:Subtotal|TOTAL|Total|$)',
        ]
        
        texto_detalle = ""
        for patron in secciones_detalle:
            match = re.search(patron, texto, re.IGNORECASE | re.DOTALL)
            if match:
                texto_detalle = match.group(1)
                break
        
        if not texto_detalle:
            # Si no encontramos sección específica, buscar líneas que parezcan items
            # (líneas con números que podrían ser cantidades, precios, etc.)
            texto_detalle = texto
        
        # Buscar líneas que parezcan items de factura
        # Patrón: número (cantidad) seguido de texto (descripción) y números (precios)
        lineas = texto_detalle.split('\n')
        
        for linea in lineas:
            linea = linea.strip()
            if not linea or len(linea) < 10:
                continue
            
            # Buscar patrones de items
            # Ejemplo: "1.0 UN Producto XYZ $1000 $1000"
            patron_item = r'(\d+[.,]?\d*)\s+([A-Z0-9]+)?\s+([A-ZÁÉÍÓÚÑ0-9\s\.,\-]+?)\s+(\$?\s*\d+[.,]?\d*)\s+(\$?\s*\d+[.,]?\d*)?'
            match = re.search(patron_item, linea, re.IGNORECASE)
            
            if match:
                item = FacturaDetalle()
                item.cantidad = self._parsear_numero(match.group(1))
                item.unidad_medida = match.group(2) if match.group(2) else None
                item.descripcion = match.group(3).strip() if match.group(3) else None
                
                if match.group(4):
                    item.precio_unitario = self._parsear_numero(match.group(4))
                if match.group(5):
                    item.total_item = self._parsear_numero(match.group(5))
                
                # Si no encontramos total, calcularlo
                if item.cantidad and item.precio_unitario and not item.total_item:
                    item.total_item = item.cantidad * item.precio_unitario
                
                items.append(item)
            else:
                # Intentar extraer solo descripción y precio si la línea parece un item
                # Buscar líneas con al menos un número que podría ser precio
                if re.search(r'\d+[.,]\d+', linea):
                    item = FacturaDetalle()
                    # Extraer números de la línea
                    numeros = re.findall(r'\d+[.,]?\d*', linea)
                    texto_item = re.sub(r'\d+[.,]?\d*', '', linea).strip()
                    
                    if texto_item and len(texto_item) > 3:
                        item.descripcion = texto_item
                        if numeros:
                            # El último número suele ser el total
                            item.total_item = self._parsear_numero(numeros[-1])
                            if len(numeros) > 1:
                                item.precio_unitario = self._parsear_numero(numeros[-2])
                            if len(numeros) > 2:
                                item.cantidad = self._parsear_numero(numeros[0])
                        
                        items.append(item)
        
        return items
    
    def _buscar_patron(self, texto: str, patrones: list) -> Optional[str]:
        """Busca un patrón en el texto y retorna el primer match"""
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
            if match:
                resultado = match.group(1).strip()
                # Limpiar resultado - quitar espacios múltiples
                resultado = re.sub(r'\s+', ' ', resultado)
                return resultado
        return None
    
    def _parsear_numero(self, texto: Optional[str]) -> Optional[float]:
        """Convierte un string a número, manejando diferentes formatos"""
        if not texto:
            return None
        
        try:
            # Remover símbolos de moneda y espacios
            texto = re.sub(r'[\$€£¥\s]', '', texto)
            # Reemplazar coma por punto si hay punto como separador de miles
            if '.' in texto and ',' in texto:
                # Formato: 1.234,56
                texto = texto.replace('.', '').replace(',', '.')
            elif ',' in texto:
                # Podría ser 1234,56 o 1,234
                if texto.count(',') == 1 and len(texto.split(',')[1]) <= 2:
                    # Probablemente decimal
                    texto = texto.replace(',', '.')
                else:
                    # Probablemente separador de miles
                    texto = texto.replace(',', '')
            
            return float(texto)
        except (ValueError, AttributeError):
            return None

