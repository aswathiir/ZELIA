"""
RAG Engine for ZELIA - Hybrid Search with Embeddings
Combines semantic vector search (Pinecone) with keyword-based text search (PostgreSQL)
"""
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
import numpy as np
import json
import os
import time
from typing import List, Dict, Tuple

class RAGEngine:
    def __init__(self, 
                 model_name='sentence-transformers/all-MiniLM-L6-v2',
                 dim=384):
        """
        Initialize RAG engine with Pinecone support
        
        Args:
            model_name: Sentence transformer model for embeddings
            dim: Embedding dimension (384 for all-MiniLM-L6-v2)
        """
        self.model_name = model_name
        self.dim = dim
        
        # Load model
        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        
        # Initialize Pinecone
        api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "zelia-documents")
        
        if not api_key:
            print("WARNING: PINECONE_API_KEY not set. Vector search will result in errors.")
            self.pc = None
            self.index = None
        else:
            try:
                print(f"Initializing Pinecone with index: {self.index_name}")
                self.pc = Pinecone(api_key=api_key)
                self.index = self.pc.Index(self.index_name)
                print("Pinecone initialized successfully")
            except Exception as e:
                print(f"Error initializing Pinecone: {e}")
                self.pc = None
                self.index = None
    
    def encode(self, text: str) -> List[float]:
        """Generate embedding for text"""
        embedding = self.model.encode(text)
        return embedding.tolist()
    
    def search_vector(self, query: str, k: int = 10) -> List[Dict]:
        """
        Semantic vector search using Pinecone
        
        Args:
            query: Search query text
            k: Number of results
            
        Returns:
            List of scheme dictionaries with similarity scores
        """
        if self.index is None:
            print("Pinecone index not available")
            return []
        
        try:
            # Generate query embedding
            query_vec = self.encode(query)
            
            # Search Pinecone
            response = self.index.query(
                vector=query_vec,
                top_k=k,
                include_metadata=True
            )
            
            results = []
            for match in response['matches']:
                metadata = match.get('metadata', {})
                scheme = {
                    'scheme_id': metadata.get('scheme_id', str(match['id'])),
                    'title': metadata.get('scheme_name', metadata.get('title', 'Unknown Scheme')),
                    'description': metadata.get('description', ''),
                    'category': metadata.get('category', 'General'),
                    'score': float(match['score']),
                    'source': 'vector',
                    # Parse JSON strings back to objects if needed
                    'eligibility_criteria': json.loads(metadata.get('eligibility_criteria', '{}')) if isinstance(metadata.get('eligibility_criteria'), str) else metadata.get('eligibility_criteria', {}),
                    'required_documents': json.loads(metadata.get('required_documents', '[]')) if isinstance(metadata.get('required_documents'), str) else metadata.get('required_documents', [])
                }
                results.append(scheme)
            
            return results
            
        except Exception as e:
            print(f"Error executing vector search: {e}")
            return []
    
    def search_text(self, query: str, conn, k: int = 10) -> List[Dict]:
        """
        PostgreSQL full-text search (unchanged)
        """
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT scheme_id, scheme_name, description, category, 
                   eligibility_summary, required_documents, impact_weight
            FROM schemes
            WHERE to_tsvector('english', scheme_name || ' ' || COALESCE(description, '')) 
                  @@ plainto_tsquery('english', %s)
            ORDER BY impact_weight DESC
            LIMIT %s
        """, (query, k))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'scheme_id': str(row[0]),
                'title': row[1],
                'description': row[2] or '',
                'category': row[3] or 'General',
                'eligibility_criteria': row[4] or {},
                'required_documents': row[5] or [],
                'score': row[6] or 0.5,
                'source': 'text'
            })
        
        cursor.close()
        return results
    
    def hybrid_search(self, query: str, conn, k: int = 10, 
                     alpha: float = 0.5) -> List[Dict]:
        """
        Hybrid search combining vector and text search
        """
        # Get results from both methods
        vector_results = self.search_vector(query, k=k*2)
        text_results = self.search_text(query, conn, k=k*2)
        
        # Merge results by scheme_id
        merged = {}
        
        for result in vector_results:
            sid = result['scheme_id']
            merged[sid] = result.copy()
            merged[sid]['vector_score'] = result['score']
            merged[sid]['text_score'] = 0.0
        
        for result in text_results:
            sid = result['scheme_id']
            if sid in merged:
                merged[sid]['text_score'] = result['score']
            else:
                merged[sid] = result.copy()
                merged[sid]['vector_score'] = 0.0
                merged[sid]['text_score'] = result['score']
        
        # Calculate hybrid score
        for sid in merged:
            v_score = merged[sid].get('vector_score', 0)
            t_score = merged[sid].get('text_score', 0)
            merged[sid]['score'] = alpha * v_score + (1 - alpha) * t_score
            merged[sid]['source'] = 'hybrid'
        
        # Sort by hybrid score
        sorted_results = sorted(
            merged.values(), 
            key=lambda x: x['score'], 
            reverse=True
        )
        
        return sorted_results[:k]
