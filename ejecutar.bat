@echo off
chcp 65001 >nul
echo ========================================
echo  Extractor de Facturas PDF
echo  Ejecutando aplicación...
echo ========================================
echo.

REM Verificar si existe el entorno virtual
if not exist "venv\" (
    echo [ERROR] El entorno virtual no existe
    echo Por favor, ejecuta primero: instalar_y_ejecutar.bat
    pause
    exit /b 1
)

REM Activar entorno virtual
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] No se pudo activar el entorno virtual
    pause
    exit /b 1
)

REM Verificar que main.py existe
if not exist "main.py" (
    echo [ERROR] No se encontró main.py
    pause
    exit /b 1
)

REM Ejecutar la aplicación
python main.py

REM Si la aplicación se cierra, mantener la ventana abierta
if errorlevel 1 (
    echo.
    echo [ERROR] La aplicación se cerró con un error
    pause
)

