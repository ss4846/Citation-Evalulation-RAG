from dotenv import load_dotenv
import os
load_dotenv()

import faiss
import sentence_transformers
import mistralai
import run_faithfulness
import langchain
import pandas
import scipy
import sklearn
import matplotlib

print('faiss:', faiss.__version__)
print('sentence-transformers:', sentence_transformers.__version__)
print('ragas:', run_faithfulness.__version__)
print('langchain:', langchain.__version__)
print('pandas:', pandas.__version__)
print('MISTRAL_API_KEY loaded:', bool(os.getenv("MISTRAL_API_KEY")))
print('All good - ready to build.')