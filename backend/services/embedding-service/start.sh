#!/bin/bash
# Startup wrapper for embedding service

echo "=== ZELIA Embedding Service Startup ==="

# Check if label_index.json exists
if [ ! -f "label_index.json" ]; then
    echo "⚠️  label_index.json not found. Building index..."
    # Use timeout to prevent infinite hangs; allow 120s for model download + encoding
    timeout 120 python build_label_index.py
    BUILD_EXIT=$?
    if [ $BUILD_EXIT -ne 0 ]; then
        echo "⚠️  Index build failed (exit $BUILD_EXIT), creating minimal fallback..."
        # Create a minimal label_index.json so the service can still start
        python -c "
import json
with open('canonical_labels.json', 'r') as f:
    labels = json.load(f)
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
with open('label_index.json', 'w') as f:
    json.dump(label_list, f, indent=2)
print(f'Created minimal label_index.json with {len(label_list)} entries')
"
        echo "✅ Minimal fallback index created"
    else
        echo "✅ Index built successfully"
    fi
else
    echo "✅ Index files found"
fi

# Start the service
echo "Starting embedding service..."
python embedding_service.py
