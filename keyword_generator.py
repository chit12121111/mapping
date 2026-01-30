"""
AI Keyword Generator using Gemini API
สร้าง search query variations สำหรับ Google Maps scraping
"""

import os
from typing import List, Optional

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False


class KeywordGenerator:
    """Generate search query variations using Gemini AI"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini API
        
        Args:
            api_key: Gemini API key (if None, will use GEMINI_API_KEY env var)
        """
        if not GENAI_AVAILABLE or genai is None:
            raise ValueError(
                "❌ google-generativeai is not installed.\n"
                "Install with: pip install google-generativeai"
            )
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key or self.api_key == "YOUR_API_KEY_HERE":
            raise ValueError(
                "❌ Gemini API key not found!\n"
                "Please set GEMINI_API_KEY environment variable or pass api_key parameter.\n"
                "Get your API key from: https://makersuite.google.com/app/apikey"
            )
        genai.configure(api_key=self.api_key)
        # ใช้ gemini-2.5-flash (model ล่าสุด)
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    def generate_variations(
        self, 
        original_query: str, 
        num_variations: int = 10,
        include_original: bool = True
    ) -> List[str]:
        """
        สร้าง search query variations จากคำค้นหาเดิม
        
        Args:
            original_query: คำค้นหาเดิม เช่น "ร้านอาหาร สายไหม"
            num_variations: จำนวน variations ที่ต้องการ (default: 10)
            include_original: รวมคำค้นหาเดิมด้วยหรือไม่ (default: True)
        
        Returns:
            List[str]: รายการคำค้นหาที่ต่างกัน
        
        Example:
            >>> generator = KeywordGenerator()
            >>> queries = generator.generate_variations("ร้านอาหาร สายไหม", num_variations=10)
            >>> print(queries)
            ['ร้านอาหาร สายไหม', 'ร้านอาหาร สายไหม กรุงเทพ', 'restaurant sai mai bangkok', ...]
        """
        
        # สร้าง prompt สำหรับ Gemini
        prompt = f"""คุณเป็นผู้เชี่ยวชาญด้านการสร้าง search queries สำหรับค้นหาสถานที่ใน Google Maps

คำค้นหาเดิม: "{original_query}"

กรุณาสร้าง {num_variations} search query variations ที่แตกต่างกัน โดยมีกลยุทธ์ดังนี้:

1. **เพิ่มสถานที่เฉพาะเจาะจง**: เช่น เพิ่มชื่อเขต/จังหวัด
2. **แปลภาษา**: ทั้งภาษาไทยและอังกฤษ
3. **ระบุประเภทเฉพาะ**: เช่น แทน "ร้านอาหาร" ด้วย "ร้านก่วยเตี๋ยว", "ร้านข้าวราดแกง", "ร้านอาหารญี่ปุ่น"
4. **คำศัพท์ทางเลือก**: เช่น "ร้าน", "shop", "store", "restaurant", "cafe"
5. **รูปแบบผสม**: ผสมภาษาไทย-อังกฤษ หรือเพิ่มคำค้นหาที่เกี่ยวข้อง

**กฎสำคัญ:**
- ตอบเป็น **LIST เท่านั้น** แต่ละบรรทัด 1 query
- **ไม่ต้องมีเลขข้อ** (ไม่ต้องมี 1. 2. 3.)
- **ไม่ต้องอธิบาย** เพิ่มเติม
- แต่ละ query ต้อง**แตกต่างกัน**และมีความหมาย
- ให้ความสำคัญกับ queries ที่น่าจะได้ผลลัพธ์ดีใน Google Maps
- **ห้ามใช้เครื่องหมายอัญประกาศ** (" หรือ ')

ตัวอย่างรูปแบบที่ถูกต้อง:
ร้านอาหาร สายไหม กรุงเทพ
restaurant sai mai bangkok
ร้านก่วยเตี๋ยว สายไหม
food shop sai mai

เริ่มสร้าง {num_variations} queries เลย:"""

        try:
            # เรียก Gemini API
            response = self.model.generate_content(prompt)
            
            # แยก response เป็น list
            variations = []
            for line in response.text.strip().split('\n'):
                # ลบช่องว่าง, เลขข้อ, และ bullet points
                cleaned = line.strip()
                
                # ลบเลขข้อและ bullet points
                if cleaned:
                    # ลบรูปแบบ "1. ", "2. ", "- ", "* ", "• " ฯลฯ
                    import re
                    cleaned = re.sub(r'^[\d\.\-\*\•\)\]\s]+', '', cleaned).strip()
                    
                    # ลบเครื่องหมายอัญประกาศ
                    cleaned = cleaned.strip('"\'')
                    
                    if cleaned and len(cleaned) > 2:  # ต้องมีความยาวมากกว่า 2 ตัวอักษร
                        variations.append(cleaned)
            
            # ลบ duplicates
            variations = list(dict.fromkeys(variations))  # เก็บ order
            
            # จำกัดจำนวนตามที่ต้องการ
            variations = variations[:num_variations]
            
            # เพิ่มคำค้นหาเดิมไว้หน้าสุด (ถ้าต้องการ)
            if include_original and original_query not in variations:
                variations.insert(0, original_query)
            
            return variations
            
        except Exception as e:
            raise Exception(f"❌ Error generating variations: {str(e)}")
    
    def generate_variations_simple(self, original_query: str) -> List[str]:
        """
        เวอร์ชันง่ายที่ไม่ต้องระบุพารามิเตอร์เยอะ
        
        Returns: 10 variations รวมคำค้นหาเดิม
        """
        return self.generate_variations(original_query, num_variations=10, include_original=True)


def test_generator():
    """ฟังก์ชันทดสอบ"""
    import sys
    
    # Fix encoding for Windows console
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("🧪 Testing Keyword Generator\n")
    
    try:
        generator = KeywordGenerator()
        
        # Test case 1: ภาษาไทย
        print("Test 1: ร้านอาหาร สายไหม")
        queries = generator.generate_variations("ร้านอาหาร สายไหม", num_variations=8)
        for i, q in enumerate(queries, 1):
            print(f"  {i}. {q}")
        
        print("\n" + "="*50 + "\n")
        
        # Test case 2: ภาษาอังกฤษ
        print("Test 2: coffee shop bangkok")
        queries = generator.generate_variations("coffee shop bangkok", num_variations=8)
        for i, q in enumerate(queries, 1):
            print(f"  {i}. {q}")
        
        print("\n✅ Test completed successfully!")
        
    except ValueError as e:
        print(f"\n{e}")
        print("\n💡 วิธีตั้งค่า API Key:")
        print("   Windows PowerShell: $env:GEMINI_API_KEY='your-api-key'")
        print("   Windows CMD: set GEMINI_API_KEY=your-api-key")
        print("   Linux/Mac: export GEMINI_API_KEY='your-api-key'")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    test_generator()
