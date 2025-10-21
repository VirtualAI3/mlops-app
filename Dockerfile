# Usamos la imagen base con CUDA 11.8 runtime y cuDNN en Ubuntu 22.04
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Evitar mensajes interactivos durante la instalación
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Instalar Python 3.10 y herramientas básicas
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3.10-venv \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    gcc \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Crear enlace python para python3.10
RUN ln -s /usr/bin/python3.10 /usr/bin/python

# Establecer directorio de trabajo
WORKDIR /app

# Copiar solo requirements.txt para aprovechar cache
COPY requirements.txt .

# Actualizar pip e instalar PyTorch con CUDA 11.8 explícitamente
RUN pip install --upgrade pip && \
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Instalar el resto de dependencias sin PyTorch (no lo incluyas en requirements.txt)
RUN pip install -r requirements.txt

# Copiar el resto del código
COPY . .

# Exponer puerto 5000
EXPOSE 5000

# Comando por defecto
CMD ["python", "app.py"]
