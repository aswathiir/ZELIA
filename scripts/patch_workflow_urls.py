import json
import re

ALLOWED_FIELDS = ['name', 'nodes', 'connections', 'settings', 'staticData', 'meta']

def patch_workflow(file_path, output_path):
    with open(file_path, 'r') as f:
        workflow = json.load(f)

    # Filter fields for API compliance (strip id, createdAt, etc.)
    filtered_workflow = {k: v for k, v in workflow.items() if k in ALLOWED_FIELDS}

    workflow_str = json.dumps(filtered_workflow)
    mappings = {
        '127.0.0.1:8007': 'retrieval-service:8007',
        'localhost:8007': 'retrieval-service:8007',
        '127.0.0.1:8011': 'rules-engine:8000',
        'localhost:8011': 'rules-engine:8000',
        '127.0.0.1:8009': 'submission-service:8009',
        'localhost:8009': 'submission-service:8009',
        '127.0.0.1:8010': 'document-processor:8010',
        'localhost:8010': 'document-processor:8010',
        '127.0.0.1:9000': 'minio:9000',
        'localhost:9000': 'minio:9000',
        '127.0.0.1:8019': 'form-filler-service:8013', # I moved this to 8019 on host
        'localhost:8019': 'form-filler-service:8013',
        '127.0.0.1:8013': 'ultravox-handler:8000',
        'localhost:8013': 'ultravox-handler:8000'
    }

    workflow_str = json.dumps(workflow)
    
    for old, new in mappings.items():
        workflow_str = workflow_str.replace(old, new)
        print(f"Patched {old} -> {new}")

    patched_workflow = json.loads(workflow_str)
    
    with open(output_path, 'w') as f:
        json.dump(patched_workflow, f, indent=2)

if __name__ == "__main__":
    patch_workflow('/tmp/workflow_ijp.json', '/tmp/workflow_patched.json')
