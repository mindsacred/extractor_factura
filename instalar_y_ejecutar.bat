@echo off
chcp 65001 >nul
echo ========================================
echo  Extractor de Facturas PDF
echo  Instalación y Ejecución
echo ========================================
echo.

REM Verificar si Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no está instalado o no está en el PATH
    echo Por favor, instala Python 3.8 o superior desde https://www.python.org/
    pause
    exit /b 1
)

echo [1/4] Verificando Python...
python --version
echo.

REM Verificar si existe el entorno virtual
if not exist "venv\" (
    echo [2/4] Creando entorno virtual...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual
        pause
        exit /b 1
    )
    echo [OK] Entorno virtual creado
) else (
    echo [2/4] Entorno virtual ya existe
)
echo.

REM Activar entorno virtual
echo [3/4] Activando entorno virtual...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] No se pudo activar el entorno virtual
    pause
    exit /b 1
)
echo [OK] Entorno virtual activado
echo.

REM Actualizar pip
echo [3.5/4] Actualizando pip...
python -m pip install --upgrade pip --quiet
echo.

REM Instalar dependencias
echo [4/4] Instalando dependencias...
if exist "requirements.txt" (
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Error al instalar dependencias
        pause
        exit /b 1
    )
    echo [OK] Dependencias instaladas
) else (
    echo [ADVERTENCIA] No se encontró requirements.txt
    echo Instalando dependencias básicas...
    python -m pip install pdfplumber openpyxl pandas PyQt5 pytesseract pdf2image openai numpy Pillow
)
echo.

REM Verificar que main.py existe
if not exist "main.py" (
    echo [ERROR] No se encontró main.py
    pause
    exit /b 1
)

echo ========================================
echo  Iniciando aplicación...
echo ========================================
echo.

REM Ejecutar la aplicación
python main.py

REM Si la aplicación se cierra, mantener la ventana abierta
if errorlevel 1 (
    echo.
    echo [ERROR] La aplicación se cerró con un error
    pause
)

