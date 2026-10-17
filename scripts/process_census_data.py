"""
ZELIA - Census Data Processor
Processes SECC census data and integrates with scheme eligibility
"""
import pandas as pd
import json
import os

def load_census_data():
    """Load and process SECC census data"""
    census_file = "dataset/govt/census/Socio Economic and Caste Census (SECC).csv"
    
    try:
        df = pd.read_csv(census_file)
        print(f"✓ Loaded census data: {len(df)} records")
        print(f"✓ Columns: {', '.join(df.columns.tolist())}")
        return df
    except Exception as e:
        print(f"✗ Error loading census data: {e}")
        return None

def analyze_census_data(df):
    """Analyze census data for scheme eligibility patterns"""
    if df is None:
        return
    
    print("\n=== Census Data Analysis ===\n")
    
    # Display basic info
    print(f"Total Records: {len(df)}")
    print(f"\nData Preview:")
    print(df.head())
    
    print(f"\nData Types:")
    print(df.dtypes)
    
    print(f"\nSummary Statistics:")
    print(df.describe())
    
    # Save processed data
    output_file = "schemes_data/census_processed.json"
    os.makedirs("schemes_data", exist_ok=True)
    
    # Convert to JSON format
    census_json = df.to_dict(orient='records')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_records": len(census_json),
            "data": census_json[:100]  # Save first 100 records
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved processed data to: {output_file}")

def map_census_to_schemes(df):
    """Map census data to scheme eligibility"""
    if df is None:
        return
    
    print("\n=== Mapping Census Data to Schemes ===\n")
    
    # Example: Identify eligible populations for different schemes
    mappings = {
        "Old Age Pension": "Age > 60 and BPL",
        "Widow Pension": "Widows and BPL",
        "Disability Pension": "Persons with Disabilities",
        "Housing Schemes": "Homeless or inadequate housing",
        "Employment Schemes": "Unemployed rural households"
    }
    
    for scheme, criteria in mappings.items():
        print(f"  {scheme}: {criteria}")
    
    print("\n✓ Census data can help identify eligible beneficiaries")

if __name__ == "__main__":
    print("=" * 70)
    print("ZELIA Census Data Processor")
    print("=" * 70)
    print()
    
    # Load census data
    df = load_census_data()
    
    # Analyze
    analyze_census_data(df)
    
    # Map to schemes
    map_census_to_schemes(df)
    
    print("\n" + "=" * 70)
    print("Processing Complete!")
    print("=" * 70)
