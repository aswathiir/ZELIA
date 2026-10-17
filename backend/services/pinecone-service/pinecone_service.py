from flask import Flask, request, jsonify
from pinecone import Pinecone
import os
import json

app = Flask(__name__)

# Initialize Pinecone
api_key = os.getenv('PINECONE_API_KEY')
index_name = os.getenv('PINECONE_INDEX_NAME', 'zelia-documents')

if not api_key:
    print("WARNING: PINECONE_API_KEY not set")

try:
    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)
except Exception as e:
    print(f"Error initializing Pinecone: {e}")
    index = None

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'pinecone-service',
        'index_name': index_name,
        'pinecone_initialized': index is not None
    })

@app.route('/query', methods=['POST'])
def query_documents():
    """
    Query Pinecone for matching documents
    """
    if not index:
        return jsonify({'error': 'Pinecone index not initialized'}), 500

    try:
        data = request.json
        
        vector = data.get('vector')
        if not vector:
             return jsonify({'error': 'Vector is required'}), 400

        top_k = data.get('top_k', 3)
        namespace = data.get('namespace', 'document_templates')
        include_metadata = data.get('include_metadata', True)
        filters = data.get('filter', {})
        
        # Query Pinecone
        results = index.query(
            vector=vector,
            top_k=top_k,
            namespace=namespace,
            include_metadata=include_metadata,
            filter=filters
        )
        
        # Parse form_fields JSON in metadata
        matches = []
        for match in results.get('matches', []):
            match_data = match.to_dict() # Convert to dict if not already
            if 'form_fields' in match_data.get('metadata', {}):
                try:
                    match_data['metadata']['form_fields'] = json.loads(
                        match_data['metadata']['form_fields']
                    )
                except:
                    pass
            matches.append(match_data)
        
        return jsonify({
            'matches': matches,
            'namespace': namespace
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8014)
