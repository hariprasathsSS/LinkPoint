from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.model.chunk_model import ChunkModel


class ChunkingService:

    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 50
    ):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=[
                "\n\n",   # paragraph
                "\n",     # line
                ". ",     # sentence
                " ",      # word
                ""        # character fallback
            ]
        )

    def chunk_text(self, text: str):

        split_chunks = self.text_splitter.split_text(text)

        chunks = []

        for i, chunk_text in enumerate(split_chunks):

            chunk = ChunkModel(
                text=chunk_text,
                metadata={
                    "chunk_index": i
                }
            )

            chunks.append(chunk)

        return chunks
