import os
from crewai import Agent, Task, Crew, Process

# ============================================
# SIMPLE MDM CREW — 3 AGENTS
# ============================================

# AGENT 1 — Normalizer
normalizer = Agent(
    role='Data Normalizer',
    goal='Clean and standardize raw entity data into consistent format',
    backstory="""You are an expert data quality specialist with 15 years 
    of experience in Master Data Management. You know how to standardize 
    names, addresses, phone numbers, and company names into consistent 
    formats.""",
    verbose=True,
    allow_delegation=False
)

# AGENT 2 — Entity Resolver
resolver = Agent(
    role='Entity Resolver',
    goal='Determine if two entity records represent the same real-world entity',
    backstory="""You are an expert in entity resolution and duplicate 
    detection. You compare records and score their similarity using 
    name matching, address comparison, and contact information analysis. 
    You always return a confidence score between 0-100.""",
    verbose=True,
    allow_delegation=False
)

# AGENT 3 — Data Steward
steward = Agent(
    role='Data Steward',
    goal='Make final decisions on entity merges and create golden records',
    backstory="""You are a senior MDM data steward at a financial services 
    firm. You review entity resolution results and make final decisions 
    on whether to merge records, keep them separate, or escalate for 
    human review. You create golden records by selecting the best 
    attributes from duplicate records.""",
    verbose=True,
    allow_delegation=False
)

# ============================================
# TASKS
# ============================================

# TASK 1 — Normalize the entity
normalize_task = Task(
    description="""Normalize this raw entity record:
    
    Name: JOHN SMITH
    Address: 123 main st, sf ca
    Phone: (415) 555.1234
    Email: JSMITH@EMAIL.COM
    Company: ACME CORP
    Tax ID: 123456789
    
    Standardize:
    - Name to Title Case
    - Phone to E.164 format (+1XXXXXXXXXX)
    - Email to lowercase
    - Address expanded (St → Street, abbreviations)
    - Company to proper case
    - Tax ID formatted (XXX-XX-XXXX)
    
    Return the normalized record as clean JSON.""",
    expected_output="A clean JSON object with normalized entity fields",
    agent=normalizer
)

# TASK 2 — Resolve against existing record
resolve_task = Task(
    description="""Compare the normalized entity from the previous task 
    against this existing record in our database:
    
    Existing Record:
    Name: John Smith
    Address: 123 Main Street, San Francisco CA 94105
    Phone: +14155551234
    Email: john.smith@email.com
    Company: Acme Corporation
    Tax ID: 123-45-6789
    Source: ERP System
    
    Analyze:
    1. Name similarity
    2. Address match
    3. Phone match
    4. Email similarity
    5. Company match
    6. Tax ID match
    
    Return JSON with:
    - similarity_score (0-100)
    - match_type (exact/probable/possible/no_match)
    - matching_fields (list)
    - conflicting_fields (list)
    - recommended_action (auto_merge/human_review/keep_separate)
    - reasoning (explanation)""",
    expected_output="JSON with similarity score and match recommendation",
    agent=resolver
)

# TASK 3 — Create golden record
steward_task = Task(
    description="""Based on the entity resolution results from the 
    previous task, make a final decision and create the golden record.
    
    If recommended action is auto_merge or human_review with high confidence:
    - Select the best value for each field
    - Prefer more complete and recent data
    - Document which source each field came from
    
    Return JSON with:
    - final_decision (merged/keep_separate/escalate)
    - golden_record (the best combined record)
    - survivorship_decisions (which source won for each field)
    - confidence (0-100)
    - explanation""",
    expected_output="Final golden record with survivorship decisions",
    agent=steward
)

# ============================================
# CREW — PUT IT ALL TOGETHER
# ============================================
mdm_crew = Crew(
    agents=[normalizer, resolver, steward],
    tasks=[normalize_task, resolve_task, steward_task],
    process=Process.sequential,  # run tasks in order
    verbose=True
)

# ============================================
# RUN THE CREW
# ============================================
print("\n" + "="*60)
print("🚀 MDM CREW STARTING...")
print("="*60 + "\n")

result = mdm_crew.kickoff()

print("\n" + "="*60)
print("✅ MDM CREW COMPLETE")
print("="*60)
print("\nFINAL RESULT:")
print(result)