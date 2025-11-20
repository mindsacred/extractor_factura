# Extractor de Facturas PDF

Aplicación con interfaz gráfica para extraer información de facturas PDF de distintos proveedores y generar archivos Excel con los datos extraídos.

## Características

- Extracción automática de datos de facturas PDF
- Interfaz gráfica simple e intuitiva
- Previsualización de datos antes de exportar
- Generación de archivos Excel con dos hojas:
  - **Cabecera**: Información general de la factura
  - **Detalle**: Items/productos de la factura
- Soporte para múltiples formatos de factura

## Requisitos

- Python 3.7 o superior
- Dependencias listadas en `requirements.txt`
- **Para OCR (opcional)**: Tesseract OCR instalado en el sistema
  - Windows: Descargar desde [UB Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
  - Durante la instalación, asegúrate de instalar los paquetes de idioma español e inglés

## Instalación

1. Clonar o descargar el proyecto
2. Instalar las dependencias:

```bash
pip install -r requirements.txt
```

## Uso

Ejecutar la aplicación:

```bash
python main.py
```

### Pasos para usar la aplicación:

1. Hacer clic en "Seleccionar PDF" y elegir el archivo de factura
2. Hacer clic en "Extraer Datos" para procesar el PDF
3. Revisar los datos extraídos en las pestañas "Cabecera" y "Detalle"
4. Hacer clic en "Generar Excel" para exportar los datos a un archivo Excel

## Estructura del Proyecto

```
extractor_factura/
├── main.py                 # Punto de entrada
├── gui.py                  # Interfaz gráfica
├── pdf_extractor.py        # Extracción de texto de PDFs
├── models.py               # Modelos de datos
├── excel_generator.py      # Generación de archivos Excel
├── requirements.txt        # Dependencias
└── README.md              # Este archivo
```

## Modelos de Datos

### FacturaCabecera
Contiene información general de la factura:
- Número de factura, fecha, tipo de documento
- Información del proveedor (nombre, RUT, dirección, etc.)
- Información del cliente (nombre, RUT, dirección)
- Totales (subtotal, impuestos, total)
- Forma de pago, condiciones, observaciones

### FacturaDetalle
Contiene información de cada item/producto:
- Código, descripción
- Cantidad, unidad de medida
- Precio unitario, descuento
- Subtotal, impuesto, total del item

## Notas

- La extracción de datos utiliza patrones de expresiones regulares para identificar campos comunes
- Si los formatos de factura varían significativamente, puede ser necesario ajustar los patrones en `pdf_extractor.py`
- Los campos no encontrados se dejarán vacíos en el Excel

## Instalación

### Requisitos previos
- Python 3.8 o superior
- Tesseract OCR instalado en el sistema (para funcionalidad OCR)

### Pasos de instalación

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/mindsacred/extractor_factura.git
   cd extractor_factura
   ```

2. **Crear y activar entorno virtual** (recomendado):
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno**:
   - Copia el archivo `.env.example` a `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edita el archivo `.env` y configura tus credenciales de Azure OpenAI y la ruta de Tesseract si es necesario.

5. **Ejecutar la aplicación**:
   ```bash
   python main.py
   ```

   O en Windows, simplemente ejecuta:
   ```bash
   instalar_y_ejecutar.bat
   ```

## Configuración

### Variables de entorno (.env)

Crea un archivo `.env` en la raíz del proyecto basándote en `.env.example`:

```env
# Tesseract OCR
RUTA_TESSERACT=C:\Program Files\Tesseract-OCR\tesseract.exe
IDIOMA_OCR=spa+eng
OCR_PSM=11
OCR_DPI=400

# Azure OpenAI
USAR_AZURE_OPENAI=True
MODELO_AZURE=gpt-4o-mini
AZURE_ENDPOINT=https://tu-endpoint.openai.azure.com/
AZURE_API_KEY=tu_api_key_aqui
AZURE_API_VERSION=2025-01-01-preview
```

**Nota**: El archivo `.env` contiene información sensible y NO debe ser subido al repositorio. Ya está incluido en `.gitignore`.

## Dependencias

- `pdfplumber`: Extracción de texto de archivos PDF
- `openpyxl`: Generación y manipulación de archivos Excel
- `pandas`: Procesamiento de datos (opcional, para método alternativo)
- `PyQt5`: Interfaz gráfica
- `pytesseract`: Interfaz Python para Tesseract OCR (para PDFs escaneados)
- `pdf2image`: Conversión de PDF a imágenes para OCR
- `openai`: Cliente para Azure OpenAI (para formatear texto OCR)
- `python-dotenv`: Carga de variables de entorno desde archivo .env

## Funcionalidad OCR

La aplicación incluye soporte para OCR (Reconocimiento Óptico de Caracteres) para extraer texto de PDFs escaneados o basados en imágenes. 

**Nota importante**: Para usar OCR, necesitas tener Tesseract OCR instalado en tu sistema:
- **Windows**: Descarga e instala desde [UB Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
- Durante la instalación, selecciona los paquetes de idioma español (`spa`) e inglés (`eng`)

Si Tesseract no está instalado, la aplicación funcionará normalmente con PDFs que tienen texto extraíble, pero no podrá procesar PDFs escaneados.

### Ajustar parámetros de OCR

Puedes ajustar los parámetros de OCR editando el archivo `.env`:

- **OCR_PSM**: Modo de segmentación de página (Page Segmentation Mode)
  - `'6'`: Asumir un bloque uniforme de texto (recomendado para facturas)
  - `'3'`: Segmentación automática sin OSD
  - `'11'`: Texto disperso
  - `'12'`: OCR de texto disperso con OSD
  
- **OCR_DPI**: Resolución para conversión de PDF a imagen
  - `300`: Calidad estándar (recomendado)
  - `400-600`: Mayor calidad pero más lento
  - `200`: Más rápido pero menor calidad

- **OCR_CONFIG**: Configuración adicional de Tesseract
  - Puedes agregar opciones personalizadas aquí

### Visualizar texto extraído

La aplicación incluye una pestaña "Texto OCR" que muestra el texto crudo extraído por OCR antes de procesarlo. Esto te permite:
- Verificar qué texto se está extrayendo
- Identificar problemas en la extracción
- Ajustar los parámetros de OCR según sea necesario

### Formateo con Azure OpenAI (Opcional)

La aplicación puede usar Azure OpenAI con el modelo GPT-4o-mini para formatear y extraer campos estructurados del texto OCR. Esto mejora significativamente la precisión de la extracción de campos.

**Requisitos para usar Azure OpenAI:**
1. Tener una cuenta de Azure con un recurso de Azure OpenAI configurado
2. Obtener el endpoint y la API key de tu recurso de Azure OpenAI
3. Configurar en `config.py`:
   - `USAR_AZURE_OPENAI = True`
   - `MODELO_AZURE = 'gpt-4o-mini'` (recomendado, modelo pequeño y económico)
   - `AZURE_ENDPOINT = 'https://tu-recurso.openai.azure.com/'`
   - `AZURE_API_KEY = 'tu-api-key-aqui'`
   - `AZURE_API_VERSION = '2024-02-15-preview'` (o la versión más reciente)

**Ventajas del formateo con Azure OpenAI:**
- Extracción directa de campos estructurados según el modelo de cabecera
- Corrige errores comunes de OCR automáticamente
- Mayor precisión en la identificación de campos
- Respuesta en formato JSON estructurado

## Licencia

Este proyecto es de uso interno.

