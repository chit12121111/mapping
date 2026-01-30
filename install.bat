@echo off
chcp 65001 >nul
echo ========================================
echo 🛠️  ติดตั้ง Google Maps Email Scraper
echo ========================================
echo.

REM ตรวจสอบ Python
echo [1/6] ตรวจสอบ Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ไม่พบ Python! กรุณาติดตั้ง Python 3.8+ ก่อน
    echo    ดาวน์โหลดได้ที่: https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo ✅ พบ Python แล้ว
echo.

REM ตรวจสอบ Docker
echo [2/6] ตรวจสอบ Docker...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  ไม่พบ Docker! Stage 1 (Google Maps Scraper) จะใช้งานไม่ได้
    echo    ดาวน์โหลดได้ที่: https://www.docker.com/products/docker-desktop/
    echo    คุณยังสามารถใช้งาน Stage 2-4 ได้ตามปกติ
) else (
    docker --version
    echo ✅ พบ Docker แล้ว
)
echo.

REM ติดตั้ง Python Dependencies
echo [3/6] ติดตั้ง Python Dependencies...
echo กำลังติดตั้ง requirements_gui.txt...
python -m pip install --upgrade pip
python -m pip install -r requirements_gui.txt
if %errorlevel% neq 0 (
    echo ❌ ติดตั้ง dependencies ไม่สำเร็จ
    pause
    exit /b 1
)
echo ✅ ติดตั้ง Python packages สำเร็จ
echo.

REM ติดตั้ง Playwright Browsers
echo [4/6] ติดตั้ง Playwright Browsers...
python -m playwright install
if %errorlevel% neq 0 (
    echo ⚠️  ติดตั้ง Playwright browsers ไม่สำเร็จ
    echo    Stage 3 (Facebook Scraper) อาจใช้งานไม่ได้
) else (
    echo ✅ ติดตั้ง Playwright browsers สำเร็จ
)
echo.

REM Pull Docker Image
echo [5/6] ดาวน์โหลด Docker Image...
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    docker pull gosom/google-maps-scraper
    if %errorlevel% neq 0 (
        echo ⚠️  ดาวน์โหลด Docker image ไม่สำเร็จ
    ) else (
        echo ✅ ดาวน์โหลด Docker image สำเร็จ
    )
) else (
    echo ⏭️  ข้าม Docker image (Docker ไม่พร้อมใช้งาน)
)
echo.

REM สร้างไฟล์ .env
echo [6/6] ตั้งค่า Environment Variables...
if not exist .env (
    copy .env.example .env >nul
    echo ✅ สร้างไฟล์ .env จาก .env.example
    echo ⚠️  กรุณาแก้ไขไฟล์ .env เพื่อเพิ่ม API keys:
    echo    - GEMINI_API_KEY (สำหรับ AI Keywords)
    echo    - GOOGLE_CLIENT_ID และ GOOGLE_CLIENT_SECRET (สำหรับส่งอีเมล)
) else (
    echo ℹ️  ไฟล์ .env มีอยู่แล้ว
)
echo.

echo ========================================
echo ✅ ติดตั้งเสร็จสมบูรณ์!
echo ========================================
echo.
echo 🚀 เริ่มใช้งาน: ดับเบิลคลิกที่ run.bat
echo 📝 แก้ไข API keys: แก้ไขไฟล์ .env
echo.
pause
