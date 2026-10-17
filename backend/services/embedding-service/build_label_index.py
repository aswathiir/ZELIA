import json
import sys
import os
import numpy as np

print('Building label index for ZELIA...')
print('=' * 60)

try:
    print('Loading canonical labels...')
    with open('canonical_labels.json', 'r', encoding='utf-8') as f:
        labels = json.load(f)
    print(f'Loaded {len(labels)} field definitions')

    # Flatten all aliases
    label_list = []
    for field_id, field_data in labels.items():
        label_list.append({
            'field_id': field_id,
            'canonical': field_data['canonical'],
            'text': field_data['canonical'],
            'field_type': field_data['field_type'],
            'required': field_data['required']
        })
        for alias in field_data['aliases']:
            label_list.append({
                'field_id': field_id,
                'canonical': field_data['canonical'],
                'text': alias,
                'field_type': field_data['field_type'],
                'required': field_data['required']
            })

    print(f'Total label variants: {len(label_list)}')

    # ── Strategy 1: Try sentence-transformers + Annoy (full quality) ──
    use_annoy = False
    try:
        print('Loading sentence transformer model...')
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(
            'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
        )
        print('Model loaded')

        print('Encoding labels...')
        texts = [item['text'] for item in label_list]
        # Encode with batch_size=8 to reduce memory pressure and avoid segfaults
        embeddings = model.encode(texts, show_progress_bar=True, batch_size=8)
        print('Encoding complete')

        embedding_dim = embeddings.shape[1]
        print(f'Building Annoy index (dimension={embedding_dim})...')

        from annoy import AnnoyIndex
        index = AnnoyIndex(embedding_dim, 'angular')
        for i, embedding in enumerate(embeddings):
            index.add_item(i, embedding.tolist())

        index.build(50)
        index.save('annoy_index.ann')

        # Save annoy metadata
        with open('annoy_metadata.json', 'w', encoding='utf-8') as f:
            json.dump({
                'embedding_dim': embedding_dim,
                'n_items': len(label_list),
                'n_trees': 50,
                'model': 'paraphrase-multilingual-MiniLM-L12-v2'
            }, f, indent=2)

        use_annoy = True
        print('✅ Annoy index built successfully')

    except Exception as e:
        print(f'⚠️  Annoy/SentenceTransformer failed ({type(e).__name__}: {e})')
        print('   Falling back to TF-IDF lookup...')

    # ── Strategy 2: Fallback TF-IDF cosine similarity (lightweight) ──
    if not use_annoy:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            print('Building TF-IDF fallback index...')
            texts = [item['text'] for item in label_list]
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform(texts)

            # Save the vectorizer vocabulary for runtime reconstruction
            with open('tfidf_vocab.json', 'w', encoding='utf-8') as f:
                json.dump(vectorizer.vocabulary_, f, ensure_ascii=False)
            with open('tfidf_idf.json', 'w', encoding='utf-8') as f:
                json.dump(vectorizer.idf_.tolist(), f)

            print('✅ TF-IDF fallback index built')
        except ImportError:
            # If scikit-learn is not available, use pure string matching
            print('⚠️  scikit-learn not available, using pure string matching fallback')
            with open('tfidf_vocab.json', 'w', encoding='utf-8') as f:
                json.dump({}, f)

    # ── Always save label_index.json (required by embedding_service.py) ──
    with open('label_index.json', 'w', encoding='utf-8') as f:
        json.dump(label_list, f, ensure_ascii=False, indent=2)

    print('Files saved')
    print('=' * 60)
    print('SUCCESS!')
    print(f'   - Total items indexed: {len(label_list)}')
    print(f'   - Strategy: {"Annoy (full)" if use_annoy else "TF-IDF fallback"}')
    print(f'   - Output files:')
    print(f'     * label_index.json')
    if use_annoy:
        print(f'     * annoy_index.ann')
        print(f'     * annoy_metadata.json')
    else:
        print(f'     * tfidf_vocab.json')
    print('=' * 60)

except Exception as e:
    print(f'ERROR: {str(e)}', file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)