FROM python:3.10-slim-bullseye

# Evitar mensajes interactivos durante la instalación
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar primero solo requirements.txt (para aprovechar cache)
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --upgrade pip \
    && pip install -v --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Exponer el puerto
EXPOSE 5000

# Comando por defecto
CMD ["python", "app.py"]
