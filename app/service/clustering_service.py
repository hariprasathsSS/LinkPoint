from sklearn.cluster import KMeans
import joblib

class ClusteringService:

    def __init__(self, n_clusters: int = 5, model_path: str = "kmeans.pkl"):
        self.n_clusters = n_clusters
        self.model_path = model_path
        self.model = None

    def train(self, embeddings):
        self.model = KMeans(n_clusters=self.n_clusters, random_state=42)
        self.model.fit(embeddings)

        # Save model
        joblib.dump(self.model, self.model_path)

        return self.model.labels_

    def load(self):
        if self.model is None:
            self.model = joblib.load(self.model_path)

    def predict(self, embedding):
        self.load()
        return int(self.model.predict([embedding])[0])
