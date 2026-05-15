import pandas as pd
import requests
import json
import time

# ============================================
# CONFIGURATION — UPDATE THESE
# ============================================
ENTITY_RESOLVER_URL = "http://localhost:3000/api/v1/prediction/dffb0020-ff61-4fa4-b36e-85f84f39c417"
GOLDEN_RECORD_URL = "http://localhost:3000/api/v1/prediction/3a7142a5-829e-471a-90fd-c021736501b7"
INPUT_FILE = r"C:\Users\irajp\mdm_input.xlsx"
OUTPUT_FILE = r"C:\Users\irajp\mdm_output.xlsx"


# ============================================
# STEP 1: READ EXCEL
# ============================================
print("Reading Excel file...")
df = pd.read_excel(INPUT_FILE)
print(f"Found {len(df)} records to process")

# ============================================
# STEP 2: PROCESS EACH RECORD
# ============================================
results = []

for index, row in df.iterrows():
    print(f"\nProcessing record {index + 1}: {row['Name']} (ID: {row['ID']})")
    
    # Format record with ID
    record_text = f"""
    Resolve this entity:
    ID: {row['ID']}
    Name: {row['Name']}
    Address: {row['Address']}
    Phone: {row['Phone']}
    Email: {row['Email']}
    Company: {row['Company']}
    Tax ID: {row['Tax_ID']}
    Source: {row['Source']}
    Last Updated: {row['Last_Updated']}
    
    IMPORTANT RULES:
    - Only recommend auto_merge if match comes from a DIFFERENT source system
    - If match has the same ID or same Source, it is the same record — recommend keep_separate
    - Never merge a record with itself
    """
    
    # ============================================
    # STEP 3: CALL ENTITY RESOLVER
    # ============================================
    try:
        resolver_response = requests.post(
            ENTITY_RESOLVER_URL,
            json={"question": record_text},
            headers={"Content-Type": "application/json"}
        )
        
        resolver_result = resolver_response.json()
        resolver_text = resolver_result.get("text", "")
        
        print(f"Entity Resolver response received")
        
        # Parse JSON from response
        try:
            start = resolver_text.find("{")
            end = resolver_text.rfind("}") + 1
            resolver_json = json.loads(resolver_text[start:end])
            
            recommended_action = resolver_json.get("recommended_action", "unknown")
            confidence = resolver_json.get("confidence", 0)
            matches = resolver_json.get("matches", [])
            explanation = resolver_json.get("explanation", "")
            
            print(f"Action: {recommended_action}, Confidence: {confidence}")
            
        except:
            recommended_action = "parse_error"
            confidence = 0
            matches = []
            explanation = "Could not parse response"
            resolver_json = {}
        
        # ============================================
        # STEP 4: IF AUTO MERGE — CALL GOLDEN RECORD
        # ============================================
        golden_record = {}
        golden_name = ""
        golden_address = ""
        golden_phone = ""
        golden_email = ""
        golden_company = ""
        golden_tax_id = ""
        
        if recommended_action == "auto_merge" and matches:
            print(f"Auto merge — calling Golden Record flow...")
            
            merge_text = f"""
            Merge these duplicate records:
            
            Record 1 (ID: {row['ID']}, Source: {row['Source']}):
            Name: {row['Name']}
            Address: {row['Address']}
            Phone: {row['Phone']}
            Email: {row['Email']}
            Company: {row['Company']}
            Tax ID: {row['Tax_ID']}
            Last Updated: {row['Last_Updated']}
            
            Record 2 (Existing Match):
            {json.dumps(matches[0].get('record', {}), indent=2)}
            """
            
            golden_response = requests.post(
                GOLDEN_RECORD_URL,
                json={"question": merge_text},
                headers={"Content-Type": "application/json"}
            )
            
            golden_result = golden_response.json()
            golden_text = golden_result.get("text", "")
            
            try:
                start = golden_text.find("{")
                end = golden_text.rfind("}") + 1
                golden_json = json.loads(golden_text[start:end])
                golden_record = golden_json.get("golden_record", {})
                
                golden_name = golden_record.get("name", "")
                golden_address = golden_record.get("address", {}).get("full", "")
                golden_phone = golden_record.get("phone", "")
                golden_email = golden_record.get("email", "")
                golden_company = golden_record.get("company", "")
                golden_tax_id = golden_record.get("tax_id", "")
                
            except:
                golden_record = {}
        
        # ============================================
        # STEP 5: DETERMINE STATUS
        # ============================================
        if recommended_action == "auto_merge":
            status = "✅ Auto Merged"
        elif recommended_action == "human_review":
            status = "⚠️ Needs Review"
        elif recommended_action == "keep_separate":
            status = "✋ Keep Separate"
        else:
            status = "❌ Error"

        # ============================================
        # STEP 6: COLLECT RESULTS
        # ============================================
        results.append({
            "ID": row['ID'],
            "Original_Name": row['Name'],
            "Original_Address": row['Address'],
            "Original_Phone": row['Phone'],
            "Original_Email": row['Email'],
            "Original_Company": row['Company'],
            "Original_Tax_ID": row['Tax_ID'],
            "Source": row['Source'],
            "Recommended_Action": recommended_action,
            "Confidence": confidence,
            "Matches_Found": len(matches),
            "Explanation": explanation,
            "Golden_Name": golden_name,
            "Golden_Address": golden_address,
            "Golden_Phone": golden_phone,
            "Golden_Email": golden_email,
            "Golden_Company": golden_company,
            "Golden_Tax_ID": golden_tax_id,
            "Status": status
        })
        
    except Exception as e:
        print(f"Error processing record {index + 1}: {e}")
        results.append({
            "ID": row.get('ID', 'unknown'),
            "Original_Name": row['Name'],
            "Recommended_Action": "error",
            "Status": f"❌ Error: {str(e)}"
        })
    
    # Small delay between API calls
    time.sleep(1)

# ============================================
# STEP 7: WRITE OUTPUT EXCEL
# ============================================
print("\nWriting results to Excel...")
output_df = pd.DataFrame(results)
output_df.to_excel(OUTPUT_FILE, index=False)
print(f"✅ Done! Results saved to {OUTPUT_FILE}")
print(f"\n📊 Summary:")
print(f"Total records processed: {len(results)}")
print(f"✅ Auto merged: {sum(1 for r in results if r.get('Recommended_Action') == 'auto_merge')}")
print(f"⚠️  Needs review: {sum(1 for r in results if r.get('Recommended_Action') == 'human_review')}")
print(f"✋ Keep separate: {sum(1 for r in results if r.get('Recommended_Action') == 'keep_separate')}")
print(f"❌ Errors: {sum(1 for r in results if r.get('Recommended_Action') == 'error')}")