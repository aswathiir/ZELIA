#!/usr/bin/env python3
"""
ZELIA Database Seed Script
Populates database with realistic test data for integration testing
"""

import psycopg2
from psycopg2.extras import Json
import json
import os
from datetime import datetime, timedelta
import random

# Database connection
DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB', 'zelia'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres_secure_2024'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432))
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def create_tables():
    """Create necessary tables if they don't exist"""
    commands = [
        """
        DROP TABLE IF EXISTS submissions CASCADE;
        DROP TABLE IF EXISTS schemes CASCADE;
        DROP TABLE IF EXISTS citizens CASCADE;
        DROP TABLE IF EXISTS profile_assessments CASCADE;
        """,
        """
        CREATE TABLE IF NOT EXISTS schemes (
            scheme_id VARCHAR(50) PRIMARY KEY,
            scheme_name TEXT NOT NULL,
            state_code VARCHAR(10),
            category VARCHAR(50),
            description TEXT,
            benefits TEXT,
            eligibility_rules JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS citizens (
            citizen_id VARCHAR(50) PRIMARY KEY,
            name TEXT NOT NULL,
            profile_data JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS submissions (
            submission_id SERIAL PRIMARY KEY,
            scheme_id VARCHAR(50) REFERENCES schemes(scheme_id),
            citizen_id VARCHAR(50) REFERENCES citizens(citizen_id),
            status VARCHAR(20) DEFAULT 'pending',
            submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            form_data JSONB,
            score FLOAT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS profile_assessments (
            assessment_id SERIAL PRIMARY KEY,
            citizen_id VARCHAR(50) REFERENCES citizens(citizen_id),
            eligible_schemes JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    ]
    
    conn = get_connection()
    cursor = conn.cursor()
    
    for command in commands:
        cursor.execute(command)
        
    conn.commit()
    cursor.close()
    conn.close()
    print("✓ Created tables: schemes, citizens, submissions, profile_assessments")

def seed_schemes():
    """Populate schemes table with government schemes"""
    
    schemes = [
        {
            'scheme_id': 'ka-widow-pension',
            'scheme_name': 'Karnataka Widow Pension Scheme',
            'state_code': 'KA',
            'category': 'social_welfare',
            'description': 'Monthly pension for widows in Karnataka',
            'benefits': '₹1,000 per month',
            'eligibility_rules': [
                {'field': 'age', 'operator': '>=', 'value': 18},
                {'field': 'age', 'operator': '<=', 'value': 60},
                {'field': 'marital_status', 'operator': '==', 'value': 'widowed'},
                {'field': 'monthly_income', 'operator': '<=', 'value': 4166},  # ₹50K annually
                {'field': 'state_code', 'operator': '==', 'value': 'KA'}
            ]
        },
        {
            'scheme_id': 'ka-old-age-pension',
            'scheme_name': 'Karnataka Old Age Pension',
            'state_code': 'KA',
            'category': 'social_welfare',
            'description': 'Pension for senior citizens',
            'benefits': '₹1,000 per month',
            'eligibility_rules': [
                {'field': 'age', 'operator': '>=', 'value': 60},
                {'field': 'monthly_income', 'operator': '<=', 'value': 2083},  # ₹25K annually
                {'field': 'state_code', 'operator': '==', 'value': 'KA'}
            ]
        },
        {
            'scheme_id': 'ka-disability-pension',
            'scheme_name': 'Karnataka Disability Pension',
            'state_code': 'KA',
            'category': 'disability',
            'description': 'Pension for persons with disabilities',
            'benefits': '₹1,000 per month',
            'eligibility_rules': [
                {'field': 'disability_status', 'operator': '==', 'value': True},
                {'field': 'disability_percentage', 'operator': '>=', 'value': 40},
                {'field': 'state_code', 'operator': '==', 'value': 'KA'}
            ]
        },
        {
            'scheme_id': 'pmjay',
            'scheme_name': 'PM-JAY Ayushman Bharat',
            'state_code': 'ALL',
            'category': 'health',
            'description': 'Health insurance coverage',
            'benefits': '₹5 lakh health coverage per family per year',
            'eligibility_rules': [
                {'field': 'annual_income', 'operator': '<=', 'value': 100000}
            ]
        },
        {
            'scheme_id': 'pm-kisan',
            'scheme_name': 'PM-Kisan Samman Nidhi',
            'state_code': 'ALL',
            'category': 'farmer_support',
            'description': 'Income support to farmers',
            'benefits': '₹6,000 per year',
            'eligibility_rules': [
                {'field': 'occupation', 'operator': '==', 'value': 'farmer'},
                {'field': 'land_ownership', 'operator': '==', 'value': True}
            ]
        }
    ]
    
    conn = get_connection()
    cursor = conn.cursor()
    
    for scheme in schemes:
        cursor.execute("""
            INSERT INTO schemes (
                scheme_id, scheme_name, state_code, category,
                description, benefits, eligibility_rules, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (scheme_id) DO UPDATE SET
                scheme_name = EXCLUDED.scheme_name,
                eligibility_rules = EXCLUDED.eligibility_rules,
                updated_at = NOW()
        """, (
            scheme['scheme_id'],
            scheme['scheme_name'],
            scheme['state_code'],
            scheme['category'],
            scheme['description'],
            scheme['benefits'],
            Json(scheme['eligibility_rules'])
        ))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"✓ Seeded {len(schemes)} schemes")

def seed_citizens():
    """Populate citizens table with test users"""
    
    citizens = [
        {
            'citizen_id': 'CIT_WIDOW_001',
            'name': 'Rajeshwari Devi',
            'age': 55,
            'gender': 'female',
            'marital_status': 'widowed',
            'phone_number': '+919876543210',
            'aadhar_number': '123456789012',
            'monthly_income': 3000,
            'occupation': 'tailoring',
            'state_code': 'KA',
            'district': 'Bengaluru Urban',
            'education': '5th_standard'
        },
        {
            'citizen_id': 'CIT_SENIOR_001',
            'name': 'Ramesh Kumar',
            'age': 68,
            'gender': 'male',
            'marital_status': 'married',
            'phone_number': '+919876543211',
            'aadhar_number': '123456789013',
            'monthly_income': 2000,
            'occupation': 'retired',
            'state_code': 'KA',
            'district': 'Mysuru'
        },
        {
            'citizen_id': 'CIT_FARMER_001',
            'name': 'Gowda',
            'age': 52,
            'gender': 'male',
            'marital_status': 'married',
            'phone_number': '+919876543212',
            'aadhar_number': '123456789014',
            'monthly_income': 3500,
            'occupation': 'farmer',
            'state_code': 'KA',
            'district': 'Mandya',
            'land_ownership': True
        },
        {
            'citizen_id': 'CIT_DISABLED_001',
            'name': 'Lakshmi',
            'age': 42,
            'gender': 'female',
            'marital_status': 'single',
            'phone_number': '+919876543213',
            'aadhar_number': '123456789015',
            'monthly_income': 1500,
            'occupation': 'not_specified',
            'state_code': 'KA',
            'district': 'Bengaluru Urban',
            'disability_status': True,
            'disability_percentage': 60
        }
    ]
    
    conn = get_connection()
    cursor = conn.cursor()
    
    for citizen in citizens:
        profile_data = {k: v for k, v in citizen.items() 
                       if k not in ['citizen_id', 'name']}
        
        cursor.execute("""
            INSERT INTO citizens (
                citizen_id, name, profile_data, created_at
            )
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (citizen_id) DO UPDATE SET
                name = EXCLUDED.name,
                profile_data = EXCLUDED.profile_data,
                updated_at = NOW()
        """, (
            citizen['citizen_id'],
            citizen['name'],
            Json(profile_data)
        ))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"✓ Seeded {len(citizens)} citizens")

def seed_pinecone_metadata():
    """Create Pinecone metadata file for scheme documents"""
    
    pinecone_docs = [
        {
            'id': 'widow_pension_ka_doc',
            'scheme_id': 'ka-widow-pension',
            'scheme_name': 'Karnataka Widow Pension Scheme',
            'document_title': 'Karnataka Widow Pension - Complete Information',
            'storage_path': 'scheme-info/widow_pension_ka.pdf',
            'description': 'Monthly pension of ₹1,000 for widows aged 18-60 with family income below ₹50,000 annually. Provides financial support to widowed women.',
            'benefits': '₹1,000 per month direct bank transfer',
            'eligibility_summary': 'Widow, Age 18-60, Income <₹50,000/year, Karnataka resident',
            'required_documents': 'Death certificate of spouse, Income certificate, Bank passbook, Aadhar card, Age proof'
        },
        {
            'id': 'old_age_pension_ka_doc',
            'scheme_id': 'ka-old-age-pension',
            'scheme_name': 'Karnataka Old Age Pension',
            'document_title': 'Senior Citizen Pension Scheme Karnataka',
            'storage_path': 'scheme-info/old_age_pension_ka.pdf',
            'description': 'Monthly pension for senior citizens above 60 years. Provides ₹1,000 per month for those with income below ₹25,000 annually.',
            'benefits': '₹1,000 per month',
            'eligibility_summary': 'Age 60+, Income <₹25,000/year',
            'required_documents': 'Age proof certificate, Income certificate, Bank account details, Aadhar card, Residence proof'
        },
        {
            'id': 'disability_pension_ka_doc',
            'scheme_id': 'ka-disability-pension',
            'scheme_name': 'Karnataka Disability Pension',
            'document_title': 'Disability Pension Scheme Information',
            'storage_path': 'scheme-info/disability_pension_ka.pdf',
            'description': 'Monthly pension for persons with 40% or more disability. Provides financial assistance of ₹1,000 per month.',
            'benefits': '₹1,000 per month',
            'eligibility_summary': '40%+ disability, Karnataka resident',
            'required_documents': 'Disability certificate from medical board, Income proof, Aadhar, Bank details'
        },
        {
            'id': 'pmjay_doc',
            'scheme_id': 'pmjay',
            'scheme_name': 'PM-JAY Ayushman Bharat',
            'document_title': 'PM-JAY Health Insurance Information',
            'storage_path': 'scheme-info/pmjay.pdf',
            'description': 'Health insurance coverage up to ₹5 lakh per family per year. Covers secondary and tertiary hospitalization.',
            'benefits': '₹5 lakh health coverage per family annually',
            'eligibility_summary': 'Family income <₹1 lakh/year',
            'required_documents': 'Ration card, Income certificate, Family member list, Aadhar cards'
        },
        {
            'id': 'pm_kisan_doc',
            'scheme_id': 'pm-kisan',
            'scheme_name': 'PM-Kisan Samman Nidhi',
            'document_title': 'PM-Kisan Farmer Income Support',
            'storage_path': 'scheme-info/pm_kisan.pdf',
            'description': 'Income support of ₹6,000 per year to farmer families. Paid in three equal installments.',
            'benefits': '₹6,000 per year (₹2,000 per installment)',
            'eligibility_summary': 'Farmer with land ownership',
            'required_documents': 'Land ownership documents, Bank account, Aadhar card'
        }
    ]
    
    with open('/tmp/pinecone_scheme_docs.json', 'w') as f:
        json.dump(pinecone_docs, f, indent=2)
    
    print(f"✓ Created Pinecone metadata file with {len(pinecone_docs)} documents")
    print("  File: /tmp/pinecone_scheme_docs.json")

def main():
    print("=" * 70)
    print("ZELIA Database Seed Script")
    print("=" * 70)
    print()
    
    try:
        # Create tables first
        create_tables()

        # Check connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        print(f"✓ Connected to PostgreSQL: {cursor.fetchone()[0][:50]}...\n")
        cursor.close()
        conn.close()
        
        # Seed data
        print("Seeding data...")
        print()
        
        seed_schemes()
        seed_citizens()
        seed_pinecone_metadata()
        
        print()
        print("=" * 70)
        print("SUCCESS: Database seeded successfully!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("1. Run populate_pinecone.py to upload scheme documents")
        print("2. Import workflow: zelia-complete-production-v9.json")
        print("3. Run integration tests: python test_integration.py")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()