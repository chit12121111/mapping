# 🚀 เตรียมความพร้อม Deploy ขึ้นโดเมน

คู่มือตั้งค่า OAuth, Redirect URI และ deploy แอป Google Maps Email Scraper บน production (โดเมนจริง)

---

## 1. ตั้งค่า Google OAuth สำหรับ Production

เมื่อ deploy ขึ้นโดเมน (เช่น `https://yourdomain.com`) ต้องให้ Google OAuth รู้จัก URL นี้

### ขั้นตอนใน Google Cloud Console

1. เปิด **[Google Cloud Console](https://console.cloud.google.com/)** → โปรเจกต์ที่ใช้ OAuth
2. ไปที่ **APIs & Services** → **Credentials**
3. เลือก **OAuth 2.0 Client ID** ที่ใช้กับแอป (ประเภท Web application)
4. ใน **Authorized redirect URIs** ให้เพิ่ม:
   - **Production:** `https://yourdomain.com/`  
     (ใส่โดเมนจริง มี **/** ท้ายเสมอ)
   - **Local (ทดสอบ):** `http://localhost:8501/`  
     (เก็บไว้ถ้ายังรัน local)
5. กด **Save**

### หมายเหตุ

- Redirect URI ต้องตรงกับที่แอปใช้ **ทุกตัวอักษร** (รวม `/` ท้าย)
- ใช้ **HTTPS** บน production
- ถ้าแอปอยู่ใต้ path เช่น `https://yourdomain.com/app/` ให้ใช้  
  `https://yourdomain.com/app/` เป็น Redirect URI

---

## 2. ตัวแปรสภาพแวดล้อม (Environment) บน Production

สร้างหรือแก้ไข `.env` บนเซิร์ฟเวอร์:

```env
# AI Keywords (Tools → AI Keywords)
GEMINI_API_KEY=your_gemini_api_key_here

# Google OAuth — ใช้ URL โดเมนจริง (HTTPS, มี / ท้าย)
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxx
GOOGLE_REDIRECT_URI=https://yourdomain.com/
```

- แทนที่ `https://yourdomain.com/` ด้วยโดเมนจริงที่ deploy
- **GOOGLE_REDIRECT_URI** ต้องตรงกับที่ใส่ใน Google Console

---

## 3. Deploy ด้วย Docker Compose

### บนเซิร์ฟเวอร์ (Linux)

1. Clone โปรเจกต์และเข้าโฟลเดอร์:
   ```bash
   git clone <repo-url> .
   cd <project-folder>
   ```

2. สร้าง `.env` จากตัวอย่างแล้วแก้ค่า:
   ```bash
   cp .env.example .env
   # แก้ GOOGLE_REDIRECT_URI และค่าอื่นใน .env
   ```

3. Build และรัน:
   ```bash
   docker compose up -d --build
   ```

4. แอปจะรันที่พอร์ต **8501**  
   ใช้ Nginx หรือ reverse proxy อื่นนำ traffic จากโดเมน + HTTPS มาที่ `http://localhost:8501`

### ตัวอย่าง Nginx (HTTPS + โดเมน)

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate     /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

หลังแก้ Nginx ให้ reload: `sudo nginx -s reload`

---

## 4. โครงสร้างโฟลเดอร์ที่ใช้บน Production

- **config/queries.txt** — คำค้นหา
- **data/** — ข้อมูล (เช่น `th_locations.json`)
- **output/** — ไฟล์ export (เช่น `results.csv`)
- **pipeline.db** — สร้างอัตโนมัติเมื่อรัน (ควร backup เป็นระยะ)
- **.env** — ตัวแปรสภาพแวดล้อม (ไม่ commit)
- **.gmail_oauth.json** — สร้างเมื่อผู้ใช้ล็อกอิน Gmail (ไม่ commit)

---

## 5. ความปลอดภัย

| รายการ | แนะนำ |
|--------|--------|
| **.env** | ไม่ commit ใน Git, เก็บบนเซิร์ฟเวอร์เท่านั้น |
| **.gmail_oauth.json** | อยู่ใน .gitignore แล้ว — เก็บเฉพาะบนเครื่องที่รันแอป |
| **HTTPS** | ใช้ SSL/TLS บน production เสมอ |
| **OAuth Client Secret** | เก็บใน .env ไม่ใส่ในโค้ด |

---

## 6. ตรวจสอบหลัง Deploy

1. เปิด `https://yourdomain.com/` ให้โหลด Streamlit ได้
2. ไปที่ **Login Gmail** → กด **ลงชื่อเข้าใช้ด้วย Google**
3. หลังเลือกบัญชี Google ควร redirect กลับมาที่แอปและล็อกอินสำเร็จ
4. ถ้า redirect ผิดหรือขึ้น error เกี่ยวกับ redirect_uri ให้ตรวจสอบ:
   - **GOOGLE_REDIRECT_URI** ใน `.env` ตรงกับ `https://yourdomain.com/` หรือไม่
   - ใน Google Console มี Redirect URI นี้ในรายการแล้วหรือไม่

---

## สรุป Checklist

- [ ] เพิ่ม **Authorized redirect URI** ใน Google Console เป็น `https://yourdomain.com/`
- [ ] ตั้ง **GOOGLE_REDIRECT_URI=https://yourdomain.com/** ใน `.env` บนเซิร์ฟเวอร์
- [ ] ใช้ Nginx (หรือ reverse proxy อื่น) ให้โดเมนชี้ไปที่แอป + เปิด HTTPS
- [ ] ไม่ commit `.env` และ `.gmail_oauth.json`
