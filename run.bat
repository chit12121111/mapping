@echo off
chcp 65001 >nul
cls
echo ========================================
echo 🚀 Google Maps Email Scraper Pipeline
echo ========================================
echo.

REM ตรวจสอบ Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ไม่พบ Python! กรุณารัน install.bat ก่อน
    pause
    exit /b 1
)

REM ตรวจสอบว่าติดตั้งแล้วหรือยัง
python -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  ไม่พบ Streamlit! กรุณารัน install.bat ก่อน
    pause
    exit /b 1
)

REM เริ่มรันแอป
echo 🌐 กำลังเริ่ม Streamlit GUI...
echo.
echo เมื่อแอปเริ่มทำงาน ให้เปิดเบราว์เซอร์ที่:
echo    👉 http://localhost:8502
echo.
echo กด Ctrl+C เพื่อหยุดแอป
echo ========================================
echo.

REM รัน Streamlit (bypass email prompt)
echo. | python -m streamlit run gui_app.py --server.port=8502

REM ถ้ารันไม่สำเร็จ ลองอีกครั้งโดยไม่ bypass
if %errorlevel% neq 0 (
    echo.
    echo กำลังลองอีกครั้ง...
    python -m streamlit run gui_app.py --server.port=8502
)

pause
