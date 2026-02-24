import json, numpy as np, faiss
from sentence_transformers import SentenceTransformer
from pathlib import Path
 
class VectorRAGPipeline:
    def __init__(self, corpus_dir="data/processed", model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.corpus, self.metadata = [], []
        for fp in Path(corpus_dir).glob("entities_*.json"):
            for e in json.load(open(fp)):
                text = " ".join(filter(None,[e.get("title",""),e.get("body",""),
                    e.get("content",""),e.get("name",""),e.get("text_payload","")])).strip()
                if len(text) > 20:
                    for i in range(0, len(text), 1848):
                        self.corpus.append(text[i:i+2048])
                        self.metadata.append({"entity_id":e.get("id",""),"entity_type":e.get("type","")})
        print(f"Vector RAG: Embedding {len(self.corpus)} chunks...")
        embs = self.model.encode(self.corpus, show_progress_bar=True, batch_size=64, normalize_embeddings=True)
        embs = np.array(embs, dtype="float32")
        self.index = faiss.IndexFlatIP(embs.shape[1])
        self.index.add(embs)
        print(f"FAISS index: {self.index.ntotal} vectors")
 
    def retrieve(self, query, top_k=10):
        qe = self.model.encode([query], normalize_embeddings=True).astype("float32")
        scores, indices = self.index.search(qe, top_k)
        return [{"text":self.corpus[i],"score":float(s),"metadata":self.metadata[i]}
                for s, i in zip(scores[0], indices[0]) if i >= 0]
