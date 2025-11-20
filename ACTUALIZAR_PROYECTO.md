# Cómo actualizar el proyecto en otro computador

## Opción 1: Si ya tienes el proyecto clonado

1. Abre una terminal/PowerShell en la carpeta del proyecto
2. Asegúrate de estar en la rama `main`:
   ```bash
   git checkout main
   ```
3. Descarga los cambios del repositorio:
   ```bash
   git pull origin main
   ```
   O simplemente:
   ```bash
   git pull
   ```

## Opción 2: Si es la primera vez en ese computador

1. Clona el repositorio:
   ```bash
   git clone https://github.com/mindsacred/extractor_factura.git
   ```
2. Entra a la carpeta:
   ```bash
   cd extractor_factura
   ```

## Después de actualizar

1. **Asegúrate de tener el archivo `.env`** con tus credenciales:
   - Si no existe, créalo copiando desde `.env.example` o `INSTRUCCIONES_ENV.txt`
   - Configura tus credenciales de Azure OpenAI

2. **Activa el entorno virtual** (si ya lo creaste):
   ```bash
   venv\Scripts\activate
   ```

3. **Actualiza las dependencias** (por si hay nuevas):
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecuta la aplicación**:
   ```bash
   python main.py
   ```
   O usa el script:
   ```bash
   ejecutar.bat
   ```

## Si hay conflictos

Si tienes cambios locales que no has guardado y hay conflictos:

1. Guarda tus cambios locales primero:
   ```bash
   git stash
   ```

2. Trae los cambios:
   ```bash
   git pull
   ```

3. Recupera tus cambios locales:
   ```bash
   git stash pop
   ```

## Verificar que estás actualizado

Para ver el último commit:
```bash
git log -1
```

Deberías ver: "Agregar seguimiento y visualización de tokens de Azure OpenAI"

