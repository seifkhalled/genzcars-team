from fastembed import TextEmbedding


class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        full_name = f"sentence-transformers/{model_name}"
        self.model = TextEmbedding(model_name=full_name)

    def encode(self, text: str) -> list[float]:
        return list(self.model.embed([text]))[0].tolist()
