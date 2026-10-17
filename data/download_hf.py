import os
from transformers import LayoutLMv2Processor, LayoutLMv2ForTokenClassification

save_dir = r'C:\Users\lazya\OneDrive\Documents\sem 6\software eng\project\data\layoutlm-model'
model_name = 'microsoft/layoutlmv2-base-uncased'

if not os.path.exists(os.path.join(save_dir, 'config.json')):
    print(f'Downloading {model_name} to {save_dir}...')
    try:
        processor = LayoutLMv2Processor.from_pretrained(model_name)
        model = LayoutLMv2ForTokenClassification.from_pretrained(model_name)
        processor.save_pretrained(save_dir)
        model.save_pretrained(save_dir)
        print('Download complete.')
    except Exception as e:
        print(f'Error downloading model: {e}')
else:
    print('LayoutLMv2 model already exists locally.')
