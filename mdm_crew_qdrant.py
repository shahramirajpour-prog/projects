import os
from crewai import Agent, Task, Crew, Process
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import json

# ============================================
# SETUP QDRANT CONNECTION
# ============================================
qdrant_client = QdrantClient(host="localhost", port=6333)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
COLLECTION = "mdm_entities"

# ============================================
# QDRANT SEARCH FUNCTION
# ============================================
def search_similar_entities(entity_text, top_k=3):
    """Search Qdrant for similar entities"""
    vector = embedding_model.encode(entity_text).tolist()
    
    results = qdrant_client.query_points(
        collection_name=COLLECTION,
        query=vector,
        limit=top_k
    )
    
    matches = []
    for r in results.points:
        matches.append({
            'score': round(r.score, 3),
            'entity': r.payload
        })
    
    return matches    
    return matches    

# ============================================
# TEST THE SEARCH FIRST
# ============================================
print("\n🔍 Testing Qdrant search...")
test_query = "J Smith ACME 415-555-1234 jsmith@email.com"
matches = search_similar_entities(test_query)
print(f"Query: '{test_query}'")
print(f"Found {len(matches)} matches:")
for m in matches:
    print(f"  Score: {m['score']} — {m['entity']['name']} at {m['entity']['company']}")

# Format matches for agent
matches_text = json.dumps(matches, indent=2)

# ============================================
# AGENTS
# ============================================

normalizer = Agent(
    role='Data Normalizer',
    goal='Clean and standardize raw entity data',
    backstory="""You are an expert data quality specialist with 15 years 
    of MDM experience. You standardize names, addresses, phones, emails 
    and company names into consistent formats.""",
    verbose=True,
    allow_delegation=False
)

resolver = Agent(
    role='Entity Resolver',
    goal='Determine if the new entity matches any existing database records',
    backstory="""You are an expert in entity resolution. You analyze 
    similarity scores from vector search results and make precise 
    matching decisions. You understand that scores above 0.85 indicate 
    strong matches, 0.70-0.85 are probable matches, and below 0.70 
    are weak matches.""",
    verbose=True,
    allow_delegation=False
)

steward = Agent(
    role='Data Steward',
    goal='Make final merge decisions and create golden records',
    backstory="""You are a senior MDM data steward. You review entity 
    resolution results and create golden records by selecting the best 
    attributes from matching records. You always explain your decisions 
    clearly.""",
    verbose=True,
    allow_delegation=False
)

# ============================================
# TASKS
# ============================================

normalize_task = Task(
    description="""Normalize this raw entity record:

    RAW INPUT:
    Name: J. SMITH
    Address: 123 main st, sf ca
    Phone: (415) 555.1234  
    Email: JSMITH@EMAIL.COM
    Company: ACME CORP
    Tax ID: 123456789

    Standardize:
    - Name: Title Case, expand abbreviations
    - Phone: E.164 format (+1XXXXXXXXXX)
    - Email: lowercase
    - Address: expand abbreviations (St→Street, etc)
    - Company: proper case
    - Tax ID: XXX-XX-XXXX format

    Return clean JSON with normalized fields.""",
    expected_output="Clean JSON with normalized entity fields",
    agent=normalizer
)

resolve_task = Task(
    description=f"""Compare the normalized entity against these 
    Qdrant vector search results from our master database:

    QDRANT SEARCH RESULTS:
    {matches_text}

    The similarity score is cosine similarity (0-1):
    - Score > 0.85: Strong match — likely same entity
    - Score 0.70-0.85: Probable match — needs review  
    - Score < 0.70: Weak match — likely different entity

    Analyze each result against the normalized entity.
    For the top match, evaluate:
    1. Name similarity
    2. Phone match (exact?)
    3. Email similarity
    4. Address match
    5. Company name match
    6. Tax ID match

    Return JSON with:
    - best_match (the top matching record)
    - similarity_score (from Qdrant)
    - match_type (exact/probable/possible/no_match)
    - matching_fields (list)
    - conflicting_fields (list)
    - recommended_action (auto_merge/human_review/keep_separate)
    - confidence (0-100)
    - reasoning""",
    expected_output="JSON with match analysis and recommendation",
    agent=resolver
)

steward_task = Task(
    description="""Based on the entity resolution results, make a 
    final decision and create the golden record.

    Golden record rules:
    1. ERP source beats CRM source
    2. More recent data beats older data
    3. More complete record beats incomplete
    4. Exact matches override fuzzy matches

    Return JSON with:
    - final_decision (auto_merged/sent_to_review/kept_separate)
    - golden_record (best combined record with all fields)
    - survivorship_decisions (field by field — which source won and why)
    - confidence (0-100)
    - requires_human_review (true/false)
    - explanation""",
    expected_output="Final golden record with survivorship decisions",
    agent=steward
)

# ============================================
# CREW
# ============================================
mdm_crew = Crew(
    agents=[normalizer, resolver, steward],
    tasks=[normalize_task, resolve_task, steward_task],
    process=Process.sequential,
    verbose=True
)

# ============================================
# RUN
# ============================================
print("\n" + "="*60)
print("🚀 MDM CREW WITH QDRANT STARTING...")
print("="*60 + "\n")

result = mdm_crew.kickoff()

print("\n" + "="*60)
print("✅ MDM CREW COMPLETE")
print("="*60)
print("\n📋 FINAL GOLDEN RECORD:")
print(result)

# ============================================
# SAVE RESULT TO FILE
# ============================================
with open(r'C:\Users\irajp\mdm_result.json', 'w') as f:
    f.write(str(result))
print(f"\n💾 Result saved to C:\\Users\\irajp\\mdm_result.json")