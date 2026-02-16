import json
from rank_bm25 import BM25Okapi
from pathlib import Path
 
class BM25Pipeline:
    def __init__(self, corpus_dir="data/processed"):
        self.corpus, self.metadata = [], []
        for fp in Path(corpus_dir).glob("entities_*.json"):
            for e in json.load(open(fp)):
                text = " ".join(filter(None,[e.get("title",""),e.get("body",""),
                    e.get("content",""),e.get("name",""),e.get("text_payload","")])).strip()
                if len(text) > 20:
                    for i in range(0, len(text), 1848):
                        chunk = text[i:i+2048]
                        self.corpus.append(chunk)
                        self.metadata.append({"entity_id":e.get("id",""),"entity_type":e.get("type","")})
        print(f"BM25 corpus: {len(self.corpus)} chunks")
        self.bm25 = BM25Okapi([d.lower().split() for d in self.corpus], k1=1.2, b=0.75)
 
    def retrieve(self, query, top_k=10):
        scores = self.bm25.get_scores(query.lower().split())
        top_idx = scores.argsort()[-top_k:][::-1]
        return [{"text":self.corpus[i],"score":float(scores[i]),"metadata":self.metadata[i]} for i in top_idx]
