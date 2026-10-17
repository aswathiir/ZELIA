# -*- coding: utf-8 -*-
"""
ZELIA RAG Search Test with Web Scraping Fallback
Tests retrieval service and demonstrates fallback to web APIs
"""
import requests
import json
import sys

RETRIEVAL_URL = "http://localhost:8007"
CONFIDENCE_THRESHOLD = 0.5  # If top result score < this, use fallback

# Government scheme web APIs for fallback
WEB_APIS = {
    "myscheme": "https://www.myscheme.gov.in/search/schemes",
    "india_gov": "https://www.india.gov.in/api/schemes",
    "digital_india": "https://digitalindia.gov.in/api/search"
}

def test_rag_search():
    """Test RAG search with real queries"""
    print("=" * 80)
    print(" ZELIA RAG SEARCH TEST")
    print("=" * 80)
    print()
    
    # Test queries
    queries = [
        "What are the eligibility criteria for widow pension?",
        "How to apply for old age pension scheme?",
        "What documents are required for disability pension?",
        "MGNREGA employment guarantee scheme details",
        "Girl child scholarship eligibility and benefits"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"[Query {i}] {query}")
        print("-" * 80)
        
        try:
            # Search in vector index
            response = requests.post(
                f"{RETRIEVAL_URL}/search",
                json={"query": query, "k": 3, "threshold": 0.3},
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                
                if results and len(results) > 0:
                    print(f"✓ Found {len(results)} results from vector index")
                    
                    for j, result in enumerate(results, 1):
                        print(f"\n  Result {j}:")
                        print(f"  Score: {result['score']:.4f}")
                        print(f"  Source: {result['metadata'].get('source', 'unknown')}")
                        print(f"  State: {result['metadata'].get('state', 'unknown')}")
                        print(f"  Content: {result['content'][:200]}...")
                    
                    # Check if we need fallback
                    top_score = results[0]['score']
                    if top_score < CONFIDENCE_THRESHOLD:
                        print(f"\n  ⚠ Low confidence ({top_score:.4f} < {CONFIDENCE_THRESHOLD})")
                        print(f"  → Fallback to web scraping recommended")
                        demonstrate_fallback(query)
                else:
                    print("  ✗ No results found in vector index")
                    print("  → Using web scraping fallback")
                    demonstrate_fallback(query)
            else:
                print(f"  ✗ Search failed: {response.status_code}")
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        print()
    
    return True

def demonstrate_fallback(query):
    """Demonstrate web scraping fallback (mock implementation)"""
    print("\n  [FALLBACK] Web Scraping Strategy:")
    print(f"    1. MyScheme.gov.in API: Search for '{query[:50]}...'")
    print(f"    2. India.gov.in Portal: Scrape scheme listings")
    print(f"    3. State Government Sites: Targeted scraping")
    print(f"    4. Cache results for future queries")

def test_hybrid_search():
    """Test hybrid search: Vector + Web Scraping"""
    print("=" * 80)
    print(" HYBRID SEARCH TEST (Vector + Web)")
    print("=" * 80)
    print()
    
    query = "pradhan mantri awas yojana housing scheme"
    print(f"Query: {query}")
    print("-" * 80)
    
    # Step 1: Vector search
    print("\n[Step 1] Vector Search...")
    try:
        response = requests.post(
            f"{RETRIEVAL_URL}/search",
            json={"query": query, "k": 2},
            timeout=10
        )
        
        vector_results = response.json() if response.status_code == 200 else []
        print(f"  Found {len(vector_results)} results from local index")
        
    except Exception as e:
        print(f"  Error: {e}")
        vector_results = []
    
    # Step 2: Web scraping (mock)
    print("\n[Step 2] Web Scraping Fallback (Mock)...")
    web_results = mock_web_scraping(query)
    print(f"  Found {len(web_results)} results from web APIs")
    
    # Step 3: Merge and rank
    print("\n[Step 3] Merging Results...")
    all_results = merge_results(vector_results, web_results)
    print(f"  Total unique results: {len(all_results)}")
    
    for i, result in enumerate(all_results[:3], 1):
        print(f"\n  Result {i}:")
        print(f"  Source: {result['source']}")
        print(f"  Score: {result['score']:.4f}")
        print(f"  Content: {result['content'][:150]}...")
    
    print()

def mock_web_scraping(query):
    """Mock web scraping results"""
    return [
        {
            "source": "web_myscheme",
            "score": 0.85,
            "content": "Pradhan Mantri Awas Yojana (PMAY) provides financial assistance for construction of pucca houses to eligible beneficiaries. EWS and LIG categories can apply.",
            "url": "https://www.myscheme.gov.in/schemes/pmay"
        },
        {
            "source": "web_india_gov",
            "score": 0.78,
            "content": "PMAY scheme offers subsidy on home loans. Beneficiaries can get up to Rs. 2.67 lakh subsidy. Apply online through official portal.",
            "url": "https://www.india.gov.in/pmay"
        }
    ]

def merge_results(vector_results, web_results):
    """Merge and deduplicate results from vector and web"""
    merged = []
    
    # Add vector results
    for r in vector_results:
        merged.append({
            "source": f"vector_{r['metadata'].get('state', 'local')}",
            "score": r['score'],
            "content": r['content']
        })
    
    # Add web results
    for r in web_results:
        merged.append(r)
    
    # Sort by score
    merged.sort(key=lambda x: x['score'], reverse=True)
    
    return merged

def test_index_stats():
    """Check index statistics"""
    print("=" * 80)
    print(" INDEX STATISTICS")
    print("=" * 80)
    print()
    
    try:
        response = requests.get(f"{RETRIEVAL_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"  Status: {data['status']}")
            print(f"  Index Size: {data['index_size']} documents")
            print(f"  Embedding Service: {data['embedding_service']}")
            print()
            
            if data['index_size'] < 50:
                print("  ⚠ Warning: Low document count")
                print("  → Consider ingesting more data or using web fallback")
            else:
                print("  ✓ Index well-populated")
        else:
            print(f"  ✗ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print()

if __name__ == "__main__":
    print("\n")
    
    # Test 1: Index stats
    test_index_stats()
    
    # Test 2: RAG search
    success = test_rag_search()
    
    # Test 3: Hybrid search
    test_hybrid_search()
    
    print("=" * 80)
    print(" TEST COMPLETE")
    print("=" * 80)
    print()
    
    sys.exit(0 if success else 1)
