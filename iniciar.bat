@echo off
echo.
echo  ========================================
echo   Field Sales CRM - Iniciando servicios
echo  ========================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no esta en PATH.
    echo Descarga Python desde https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check if venv exists
if not exist "C:\field-sales-crm\backend\venv\Scripts\activate.bat" (
    echo [SETUP] Creando entorno virtual por primera vez...
    cd C:\field-sales-crm\backend
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
    echo [SETUP] Dependencias instaladas.
)

:: Check if .env exists
if not exist "C:\field-sales-crm\backend\.env" (
    echo [ERROR] Archivo .env no encontrado.
    echo Copia .env.example a .env y agrega tu OPEN_API_KEY.
    echo.
    echo   copy C:\field-sales-crm\backend\.env.example C:\field-sales-crm\backend\.env
    echo   notepad C:\field-sales-crm\backend\.env
    echo.
    pause
    exit /b 1
)

:: Check if database exists, if not initialize
if not exist "C:\ventas\crm.db" (
    echo [SETUP] Creando base de datos...
    mkdir C:\ventas 2>nul
    mkdir C:\ventas\audios 2>nul
    cd C:\field-sales-crm\backend
    call venv\Scripts\activate
    python -m app.core.init_db
    echo [SETUP] Base de datos creada en C:\ventas\crm.db
)

echo.
echo [1/3] Iniciando servidor API (puerto 8000)...
start "CRM - API Server" cmd /k "cd C:\field-sales-crm\backend && call venv\Scripts\activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: Wait for server to start
timeout /t 4 /nobreak > nul

echo [2/3] Iniciando dashboard (puerto 8501)...
start "CRM - Dashboard" cmd /k "cd C:\field-sales-crm\backend && call venv\Scripts\activate && streamlit run dashboard.py --server.headless true"

:: Check if cloudflared is available
where cloudflared >nul 2>&1
if %errorlevel% equ 0 (
    echo [3/3] Iniciando tunnel de Cloudflare...
    start "CRM - Tunnel" cmd /k "cloudflared tunnel --url http://localhost:8000"
) else (
    echo [3/3] cloudflared no encontrado. Los vendedores solo pueden conectar por red local.
    echo      Descarga: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
)

echo.
echo  ========================================
echo   Todo iniciado correctamente!
echo  ========================================
echo.
echo   API Server:  http://localhost:8000
echo   API Docs:    http://localhost:8000/docs
echo   Dashboard:   http://localhost:8501
echo   Base datos:  C:\ventas\crm.db
echo.
echo   Para detener: cierra las ventanas de CMD
echo.
pause
