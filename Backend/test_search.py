import os, sys
sys.path.insert(0, os.path.dirname(__file__))

# Load env
with open(os.path.join(os.path.dirname(__file__), '..', '.env')) as f:
    for line in f:
        if '=' in line:
            k, v = line.strip().split('=', 1)
            os.environ[k] = v

from app.config import settings
from app.services.indexing_pipeline import embed_text
from fastembed import TextEmbedding

# Test embedder
print("Loading embedder...")
try:
    embedder = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    print("Embedder loaded successfully")
    vec = embed_text(embedder, "bmw")
    print(f"Vector length: {len(vec)}")
except Exception as e:
    print(f"Embedder error: {e}")
    import traceback
    traceback.print_exc()

# Test Qdrant search
print("\nTesting Qdrant search...")
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

qdrant = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
try:
    if 'embedder' in dir():
        vector = embed_text(embedder, "bmw")
        must_conditions = [qmodels.FieldCondition(
            key="is_active", match=qmodels.MatchValue(value=True)
        )]
        search_result = qdrant.search(
            collection_name=settings.qdrant_collection,
            query_vector=vector,
            query_filter=qmodels.Filter(must=must_conditions),
            limit=10,
            with_payload=True,
        )
        print(f"Qdrant search returned {len(search_result)} results")
        for r in search_result:
            print(f"  Score: {r.score:.4f}, Brand: {r.payload.get('brand')}, Model: {r.payload.get('model')}")
    else:
        print("Skipping search - no embedder")
except Exception as e:
    print(f"Search error: {e}")
    import traceback
    traceback.print_exc()
