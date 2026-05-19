import pytesseract
from PIL import Image
import json
import os
import sys
from crewai import Agent, Task, Crew, Process

# ============================================
# CONFIGURE TESSERACT PATH
# ============================================
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ============================================
# STEP 1: EXTRACT TEXT FROM IMAGE USING CNN/OCR
# ============================================
def extract_text_from_image(image_path):
    print(f"\n🔍 CNN/OCR Processing: {image_path}")
    img = Image.open(image_path)
    
    # Enhance image for better OCR accuracy
    img = img.convert('L')  # grayscale
    
    # Run CNN-based OCR
    raw_text = pytesseract.image_to_string(img)
    
    print(f"\n📄 Raw text extracted by CNN:")
    print("-" * 40)
    print(raw_text)
    print("-" * 40)
    
    return raw_text

# ============================================
# STEP 2: CREWAI MDM PROCESSES EXTRACTED TEXT
# ============================================
def process_with_mdm_crew(raw_text):

    extractor = Agent(
        role='Entity Extractor',
        goal='Extract structured entity fields from raw OCR text',
        backstory="""You are an expert at reading business cards and 
        extracting structured data from messy OCR text. You handle 
        OCR errors, formatting issues, and extract clean entity fields.""",
        verbose=True,
        allow_delegation=False
    )
    
    normalizer = Agent(
        role='Data Normalizer',
        goal='Normalize and standardize extracted entity data',
        backstory="""You are an MDM data quality expert who standardizes
        entity data — names to Title Case, phones to E.164 format,
        emails to lowercase, addresses expanded.""",
        verbose=True,
        allow_delegation=False
    )
    
    steward = Agent(
        role='Data Steward',
        goal='Validate the entity and prepare it for the master database',
        backstory="""You are a senior MDM data steward who reviews 
        extracted and normalized entity data, flags missing fields,
        assesses data quality, and prepares the final record.""",
        verbose=True,
        allow_delegation=False
    )
    
    extract_task = Task(
        description=f"""Extract entity fields from this raw OCR text 
        from a business card:

        RAW OCR TEXT:
        {raw_text}

        Extract these fields if present:
        - name (person full name)
        - title (job title)
        - company (company name)
        - phone (any phone number)
        - email (email address)
        - address (full street address)
        - website (URL if present)
        - tax_id (EIN or SSN if present)

        Note: OCR may have errors — use context to correct them.
        Example: "Pala & Analytics" likely means "VP Data & Analytics"
        Return as clean JSON.""",
        expected_output="JSON with extracted entity fields",
        agent=extractor
    )
    
    normalize_task = Task(
        description="""Normalize the extracted entity fields:
        - Name: Title Case
        - Phone: E.164 format (+1XXXXXXXXXX)
        - Email: lowercase
        - Address: expand abbreviations (St→Street, CA→California optional)
        - Company: proper case
        - Tax ID: XX-XXXXXXX for EIN, XXX-XX-XXXX for SSN
        
        Return normalized JSON.""",
        expected_output="JSON with normalized entity fields",
        agent=normalizer
    )
    
    steward_task = Task(
        description="""Review the normalized entity and:
        1. Check for missing required fields (name, phone or email)
        2. Flag any suspicious or unusual values
        3. Calculate data quality score (0-100)
        4. Determine if ready for master database

        Return ONLY this JSON:
        {{
          "entity": {{
            "name": "",
            "title": "",
            "company": "",
            "phone": "",
            "email": "",
            "address": "",
            "website": "",
            "tax_id": ""
          }},
          "quality_score": 0-100,
          "missing_fields": [],
          "flags": [],
          "ready_for_database": true/false,
          "recommendation": ""
        }}""",
        expected_output="Final validated entity with quality score",
        agent=steward
    )
    
    crew = Crew(
        agents=[extractor, normalizer, steward],
        tasks=[extract_task, normalize_task, steward_task],
        process=Process.sequential,
        verbose=True
    )
    
    result = crew.kickoff()
    return result

# ============================================
# MAIN PIPELINE
# ============================================
def business_card_to_mdm(image_path):
    print("\n" + "="*60)
    print("📇 BUSINESS CARD → MDM PIPELINE")
    print("="*60)
    
    # Verify file exists
    if not os.path.exists(image_path):
        print(f"❌ File not found: {image_path}")
        return
    
    print(f"📎 Processing: {image_path}")
    
    # STEP 1: CNN/OCR
    raw_text = extract_text_from_image(image_path)
    
    if not raw_text.strip():
        print("❌ No text detected in image. Try a clearer image.")
        return
    
    # STEP 2: CrewAI MDM
    print("\n🚀 Starting MDM Crew processing...")
    result = process_with_mdm_crew(raw_text)
    
    # STEP 3: Display result
    print("\n" + "="*60)
    print("✅ FINAL MDM RECORD:")
    print("="*60)
    print(result)
    
    # Save result
    output_file = r'C:\Users\irajp\business_card_result.json'
    with open(output_file, 'w') as f:
        f.write(str(result))
    print(f"\n💾 Saved to {output_file}")
    
    return result

# ============================================
# RUN — accepts image path as argument
# ============================================
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Image path provided as command line argument
        image_path = sys.argv[1]
    else:
        # Ask user for image path
        print("\n📇 BUSINESS CARD MDM PROCESSOR")
        print("="*40)
        print("Supported formats: JPG, PNG, BMP, TIFF")
        print()
        image_path = input("Enter full path to business card image: ").strip()
        
        # Remove quotes if user included them
        image_path = image_path.strip('"').strip("'")
    
    business_card_to_mdm(image_path)
