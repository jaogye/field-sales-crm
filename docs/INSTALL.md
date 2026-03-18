# Guía de Instalación Completa

## Field Sales CRM — De cero a funcionando

Esta guía te lleva paso a paso desde una laptop Windows limpia hasta tener todo corriendo: backend, dashboard y app móvil.

---

## Paso 0: Lo que necesitas antes de empezar

### En la laptop del dueño (Windows 10/11)

Descarga e instala estos 3 programas:

**1. Python 3.11+**
- Ve a https://www.python.org/downloads/
- Descarga la última versión (3.12 o 3.13)
- Al instalar, MARCA la casilla "Add Python to PATH" (muy importante)
- Verifica abriendo CMD y escribiendo: `python --version`

**2. Git**
- Ve a https://git-scm.com/download/win
- Instala con las opciones por defecto
- Verifica: `git --version`

**3. Node.js 18+ (para la app móvil, se puede instalar después)**
- Ve a https://nodejs.org/
- Descarga la versión LTS
- Verifica: `node --version`

### Cuenta de OpenAI
- Ve a https://platform.openai.com/
- Crea una cuenta
- Ve a API Keys → Create new secret key
- Guarda la key (empieza con `sk-...`), la necesitarás luego
- Agrega crédito: $10 es suficiente para meses de uso

---

## Paso 1: Descargar el proyecto

Abre **CMD** o **PowerShell** y ejecuta:

```cmd
cd C:\
git clone https://github.com/jaogye/field-sales-crm.git
cd field-sales-crm
```

Si no tienes Git, puedes descargar el ZIP desde GitHub y descomprimirlo en `C:\field-sales-crm`.

---

## Paso 2: Crear las carpetas de datos

```cmd
mkdir C:\ventas
mkdir C:\ventas\audios
```

Aquí vivirán:
- `C:\ventas\crm.db` — la base de datos (se crea automáticamente)
- `C:\ventas\audios\` — los archivos de audio de las visitas

---

## Paso 3: Configurar el backend

```cmd
cd C:\field-sales-crm\backend

:: Crear entorno virtual de Python
python -m venv venv

:: Activar el entorno virtual
venv\Scripts\activate

:: Instalar dependencias
pip install -r requirements.txt
```

Si ves un error con `pip`, prueba: `python -m pip install -r requirements.txt`

### Configurar las variables de entorno

```cmd
copy .env.example .env
notepad .env
```

En el Bloc de Notas, edita estas líneas:

```
OPEN_API_KEY=sk-TU-API-KEY-AQUI
DATABASE_PATH=C:/ventas/crm.db
AUDIO_STORAGE_PATH=C:/ventas/audios
```

Guarda y cierra.

---

## Paso 4: Inicializar la base de datos

### Opción A: Base de datos vacía (empezar de cero)

```cmd
python -m app.core.init_db
```

Esto crea `C:\ventas\crm.db` con las tablas vacías.

### Opción B: Importar el Excel existente

Si tienes el Excel con los clientes actuales:

```cmd
python -m app.core.init_db "C:\ruta\a\tu\excel.xlsx"
```

Esto lee el Excel, detecta los colores de las filas (rojo, verde, morado, etc.) y los convierte en estados del CRM. Los clientes se importan con nombre, teléfono, zona, dirección y estado.

---

## Paso 5: Arrancar el servidor

```cmd
cd C:\field-sales-crm\backend
venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Deberías ver:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

### Verificar que funciona

Abre el navegador y ve a: http://localhost:8000

Deberías ver:

```json
{"app": "Field Sales CRM", "version": "0.1.0", "status": "running"}
```

También puedes ver la documentación interactiva de la API en: http://localhost:8000/docs

---

## Paso 6: Arrancar el dashboard

Abre una **nueva ventana de CMD** (deja el servidor corriendo en la otra):

```cmd
cd C:\field-sales-crm\backend
venv\Scripts\activate
streamlit run dashboard.py
```

Se abrirá automáticamente en el navegador: http://localhost:8501

Este es el dashboard que reemplaza el Excel. Muestra clientes, llamadas, visitas, estadísticas y la tabla con colores por estado.

---

## Paso 7: Exponer el servidor a internet (para los vendedores)

Los 50 vendedores necesitan conectarse al servidor desde sus teléfonos. Como el servidor está en tu laptop, necesitas exponerlo a internet.

### Opción A: Cloudflare Tunnel (recomendada, gratis)

1. Descarga cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

2. Instala y ejecuta:
```cmd
cloudflared tunnel --url http://localhost:8000
```

3. Te dará una URL como: `https://random-name.trycloudflare.com`

4. Esa URL es la que configuras en la app móvil (ver Paso 8).

### Opción B: ngrok (alternativa simple)

1. Descarga ngrok: https://ngrok.com/download
2. Crea una cuenta gratuita y copia tu authtoken
3. Ejecuta:
```cmd
ngrok config add-authtoken TU-TOKEN
ngrok http 8000
```
4. Te dará una URL como: `https://abc123.ngrok-free.app`

### Nota importante
Cada vez que reinicies el tunnel, la URL cambia (en la versión gratuita). Para una URL fija, puedes usar un dominio propio con Cloudflare ($0) o ngrok ($8/mes).

---

## Paso 8: Configurar la app móvil

### Instalar dependencias

Abre una **nueva ventana de CMD**:

```cmd
cd C:\field-sales-crm\mobile
npm install
```

### Configurar la URL del servidor

Edita `mobile/services/api.js` y cambia la URL:

```javascript
const BASE_URL = __DEV__ 
  ? 'http://192.168.1.100:8000'           // Tu IP local (para desarrollo)
  : 'https://tu-tunnel-url.trycloudflare.com';  // URL del tunnel
```

Para encontrar tu IP local: `ipconfig` en CMD, busca "IPv4 Address".

### Correr en modo desarrollo

```cmd
npx expo start
```

Esto mostrará un QR code en la terminal.

### En el teléfono del vendedor

1. Instala la app **Expo Go** desde la App Store (iPhone) o Play Store (Android)
2. Abre Expo Go y escanea el QR code
3. La app se cargará en el teléfono

### Para producción (sin Expo Go)

Cuando estés listo para distribuir a los 50 vendedores sin Expo Go:

```cmd
:: Crear build para Android
npx eas build --platform android --profile production

:: Crear build para iOS
npx eas build --platform ios --profile production
```

Necesitarás una cuenta de Expo (gratis para desarrollo, $99/mes para builds de producción).

---

## Paso 9: Correr los tests

Para verificar que todo funciona correctamente:

```cmd
cd C:\field-sales-crm\backend
venv\Scripts\activate
pytest -v
```

Deberías ver algo como:

```
tests/test_clientes.py::TestVendedores::test_crear_vendedor PASSED
tests/test_clientes.py::TestClientes::test_crear_cliente PASSED
tests/test_clientes.py::TestClientes::test_buscar_cliente PASSED
tests/test_llamadas_visitas.py::TestLlamadas::test_registrar_llamada_cita PASSED
...
20 passed in 2.3s
```

---

## Resumen: qué dejas corriendo

En la laptop del dueño necesitas **3 ventanas de CMD** abiertas:

| Ventana | Comando | URL |
|---------|---------|-----|
| 1. Servidor API | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | http://localhost:8000 |
| 2. Dashboard | `streamlit run dashboard.py` | http://localhost:8501 |
| 3. Tunnel | `cloudflared tunnel --url http://localhost:8000` | https://xxx.trycloudflare.com |

### Script para arrancarlo todo de una vez

Crea un archivo `C:\field-sales-crm\iniciar.bat`:

```bat
@echo off
echo === Iniciando Field Sales CRM ===

:: Arrancar servidor API
start "API Server" cmd /k "cd C:\field-sales-crm\backend && venv\Scripts\activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: Esperar 3 segundos
timeout /t 3 /nobreak > nul

:: Arrancar dashboard
start "Dashboard" cmd /k "cd C:\field-sales-crm\backend && venv\Scripts\activate && streamlit run dashboard.py"

:: Arrancar tunnel
start "Tunnel" cmd /k "cloudflared tunnel --url http://localhost:8000"

echo.
echo Todo iniciado. Ventanas abiertas:
echo   - API Server: http://localhost:8000
echo   - Dashboard:  http://localhost:8501
echo   - Tunnel:     (ver la URL en la ventana del tunnel)
echo.
pause
```

Doble clic en `iniciar.bat` y todo arranca.

---

## Backups

La base de datos es un solo archivo. Para hacer backup:

```cmd
copy C:\ventas\crm.db C:\ventas\backup\crm_%date:~-4%-%date:~4,2%-%date:~7,2%.db
```

O simplemente copia `C:\ventas\crm.db` a un USB, Dropbox, Google Drive, etc.

---

## Troubleshooting

**"python no se reconoce como comando"**
→ Reinstala Python y marca "Add Python to PATH".

**"Error: OPEN_API_KEY not set"**
→ Revisa el archivo `.env`. Asegúrate de que la key no tenga espacios.

**"Los vendedores no pueden conectarse"**
→ Verifica que el tunnel esté corriendo. La URL cambia cada vez que reincias.

**"La base de datos está bloqueada"**
→ Cierra el dashboard de Streamlit y reinícialo. SQLite solo permite un escritor a la vez; WAL mode debería manejarlo, pero si hay problemas, reiniciar resuelve.

**"El audio no se transcribe"**
→ Revisa que tengas crédito en tu cuenta de OpenAI (platform.openai.com → Usage).

**"Error al importar el Excel"**
→ Asegúrate de que el Excel tenga la misma estructura: columnas B-I con nombre, teléfono, fuente, zona, dirección, notas vendedor, notas telemarketing, resultados. Los headers deben estar en la fila 8.
