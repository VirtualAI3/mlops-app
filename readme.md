# 🥔 Detector de Enfermedades en Hojas de Papa con YOLOv11n

## 📌 Descripción

Este proyecto utiliza el modelo **YOLOv11n** para detectar enfermedades en hojas de papa a través de imágenes. Está diseñado para apoyar a agricultores, investigadores y desarrolladores en la identificación automática de problemas fitosanitarios mediante visión por computadora, facilitando el monitoreo de cultivos de forma eficiente y precisa.

---

## ⚙️ Instrucciones de instalación y despliegue

### 1. Instalar **Python 3.10**

Descarga e instala la versión 3.10 de Python desde la página oficial:

🔗 [https://www.python.org/downloads/release/python-3100/](https://www.python.org/downloads/release/python-3100/)

---

### 2. Instalar **Chocolatey**

Chocolatey es un gestor de paquetes para Windows. Para instalarlo:

* Abre **PowerShell como administrador**
* Ejecuta el siguiente comando:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; `
[System.Net.ServicePointManager]::SecurityProtocol = `
[System.Net.ServicePointManager]::SecurityProtocol -bor 3072; `
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

---

### 3. Instalar **ngrok** con Chocolatey

Una vez instalado Chocolatey, instala ngrok ejecutando:

```powershell
choco install ngrok
```

---

### 4. Crear cuenta en **ngrok** y obtener el **Auth Token**

* Ve a [https://ngrok.com/](https://ngrok.com/)
* Regístrate con tu cuenta de **Gmail**
* Una vez dentro, ve a tu dashboard: [https://dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)
* Copia tu **Auth Token** (lo necesitarás al ejecutar el script)

---

### 5. Descargar el archivo `deploy.ps1`

Descarga el archivo `deploy.ps1` desde el servidor del proyecto o el repositorio correspondiente.

---

### 6. Ejecutar `deploy.ps1` en PowerShell

* Abre PowerShell en la carpeta donde descargaste `deploy.ps1`
* Ejecuta el script con:

```powershell
./deploy.ps1
```

Durante la ejecución, se te pedirá que ingreses tu **ngrok Auth Token**. Esto permitirá exponer el servicio local a través de un túnel público.

---

¡Listo! El sistema estará desplegado localmente y accesible vía una URL pública generada por ngrok. Puedes usar esta URL para acceder a la interfaz desde cualquier dispositivo.

---