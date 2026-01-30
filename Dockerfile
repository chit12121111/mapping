# ใช้ Python base image
FROM python:3.11-slim

# ตั้งค่า working directory
WORKDIR /app

# ติดตั้ง system dependencies สำหรับ Playwright และ Selenium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    curl \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# ติดตั้ง Docker CLI
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y docker-ce-cli && \
    rm -rf /var/lib/apt/lists/*

# คัดลอกไฟล์ requirements
COPY requirements_gui.txt requirements_stage2.txt ./

# ติดตั้ง Python dependencies
RUN pip install --no-cache-dir -r requirements_gui.txt && \
    pip install --no-cache-dir python-dotenv

# ติดตั้ง Playwright browsers (ต้องรอให้ playwright package ติดตั้งก่อน)
RUN python -m playwright install chromium && \
    python -m playwright install-deps chromium

# คัดลอกไฟล์โปรเจกต์ทั้งหมด
COPY . .

# สร้างโฟลเดอร์สำหรับเก็บข้อมูล
RUN mkdir -p /app/data

# ตั้งค่า environment variables
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Expose port สำหรับ Streamlit
EXPOSE 8501

# Default command: รัน Streamlit GUI
CMD ["streamlit", "run", "gui_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
