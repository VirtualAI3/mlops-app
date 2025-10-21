# ============================
# setup_local_ngrok.ps1 (FINAL)
# ============================

# ------------------ VARIABLES ------------------ #
$PYTHON_PATH = "C:\Users\HP\AppData\Local\Programs\Python\Python310\python.exe"
$BASE_DIR = "D:\potato_app"
$APP_DIR = "$BASE_DIR\mlops-app"
$VENV_DIR = "$BASE_DIR\venv"
$REPO_URL = "https://github.com/VirtualAI3/mlops-app.git"

# ------------------ FUNCIONES ------------------ #
function Run-Command($cmd) {
    Write-Host "Ejecutando: $cmd"
    iex $cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Error ejecutando: $cmd"
        exit 1
    }
}

# ------------------ CLONAR REPOSITORIO ------------------ #
if (!(Test-Path $APP_DIR)) {
    Write-Host "Clonando repositorio desde GitHub..."
    Run-Command "git clone `"$REPO_URL`" `"$APP_DIR`""
} else {
    Write-Host "Repositorio ya existe, actualizando..."
    Set-Location $APP_DIR
    Run-Command "git pull"
}

Set-Location $BASE_DIR

# ------------------ CREAR ENTORNO VIRTUAL ------------------ #
if (!(Test-Path $VENV_DIR)) {
    Write-Host "Creando entorno virtual..."
    Run-Command "$PYTHON_PATH -m venv `"$VENV_DIR`""
} else {
    Write-Host "Entorno virtual ya existe."
}

# ------------------ ACTIVAR ENTORNO ------------------ #
Write-Host "Activando entorno virtual..."
$activateScript = Join-Path $VENV_DIR "Scripts\Activate.ps1"

if (!(Test-Path $activateScript)) {
    Write-Error "No se encontro el script de activacion: $activateScript"
    exit 1
}

# ✅ Activar en el mismo contexto actual
. $activateScript

# ------------------ ACTUALIZAR PIP ------------------ #
Run-Command "python -m pip install --upgrade pip"

# ------------------ INSTALAR DEPENDENCIAS ------------------ #
Set-Location $APP_DIR
if (Test-Path "requirements.txt") {
    Write-Host "Instalando dependencias desde requirements.txt..."
    Run-Command "pip install -r requirements.txt"
} else {
    Write-Host "Archivo requirements.txt no encontrado, omitiendo..."
}

# ------------------ INSTALAR NGROK ------------------ #
if (!(Get-Command ngrok -ErrorAction SilentlyContinue)) {
    Write-Host "Instalando ngrok..."
    Invoke-WebRequest https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-stable-windows-amd64.zip -OutFile ngrok.zip
    Expand-Archive ngrok.zip -DestinationPath $BASE_DIR -Force
    Remove-Item ngrok.zip
    Write-Host "ngrok instalado en $BASE_DIR"
}

# ------------------ CONFIGURAR TOKEN ------------------ #
if (!(Test-Path "$HOME\.ngrok2\ngrok.yml")) {
    Write-Host "Ingresa tu ngrok authtoken (desde https://dashboard.ngrok.com/get-started/your-authtoken)"
    $token = Read-Host "Token ngrok"
    if ($token -ne "") {
        Run-Command " ngrok config add-authtoken $token"
    }
}

# ------------------ LANZAR APP ------------------ #
Write-Host "Iniciando aplicacion Python (app.py)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$APP_DIR'; & '$VENV_DIR\Scripts\activate.ps1'; python app.py"

Start-Sleep -Seconds 5

# ------------------ EXPONER PUERTO ------------------ #
Write-Host "Exponiendo el puerto 5000 con ngrok..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "ngrok http 5000"

Start-Sleep -Seconds 7

# ------------------ MOSTRAR URL ------------------ #
try {
    $response = Invoke-RestMethod http://127.0.0.1:4040/api/tunnels
    $publicUrl = $response.tunnels[0].public_url
    Write-Host "Aplicacion disponible en: $publicUrl" -ForegroundColor Green
}
catch {
    Write-Host "No se pudo obtener la URL publica de ngrok todavia."
}

Write-Host "Logs del servidor en las ventanas abiertas."
