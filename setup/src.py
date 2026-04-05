import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from docling.document_converter import DocumentConverter
from docling_core.types import DoclingDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document as LCDocument
import chromadb
from tqdm import tqdm


# ============================================================
# Step 1: Setup the repo and Define folder where all files are kept
# ============================================================
class RAGSetup:
    """Setup and configuration for the RAG system."""
    
    def __init__(self, data_folder: str = None, output_folder: str = None):
        """
        Initialize RAG setup.
        
        Args:
            data_folder (str): Folder containing documents to parse
            output_folder (str): Folder for storing outputs
        """
        # Use environment variables if not provided
        self.data_folder = Path(data_folder or os.getenv("DATA_FOLDER", "data"))
        self.output_folder = Path(output_folder or os.getenv("OUTPUT_FOLDER", "output"))
        self.extracted_data_folder = self.output_folder / os.getenv("EXTRACTED_DATA_FOLDER", "extracted_data")
        self.extracted_images_folder = self.output_folder / os.getenv("EXTRACTED_IMAGES_FOLDER", "images")
        self.embeddings_folder = self.output_folder / os.getenv("EMBEDDINGS_FOLDER", "embeddings")
        
        # Create output directories if they don't exist
        self.extracted_data_folder.mkdir(parents=True, exist_ok=True)
        self.extracted_images_folder.mkdir(parents=True, exist_ok=True)
        self.embeddings_folder.mkdir(parents=True, exist_ok=True)
        
    def get_supported_files(self) -> List[str]:
        """Get list of supported document files."""
        supported_extensions = ('.pdf', '.docx', '.pptx', '.xlsx', '.html', '.xml', '.txt', '.md')
        if not self.data_folder.exists():
            print(f"Warning: Data folder {self.data_folder} does not exist")
            return []
        return [f.name for f in self.data_folder.iterdir() 
                if f.suffix.lower() in supported_extensions]


# ============================================================
# Step 2 & 3: Load files and Extract text, images, and tables
# ============================================================
class DocumentExtractor:
    """Extract text, images, and tables from documents using Docling."""
    
    def __init__(self, output_folder: Path):
        """Initialize document extractor."""
        self.converter = DocumentConverter()
        self.output_folder = output_folder
        self.extracted_images_folder = output_folder / "images"
        self.extracted_images_folder.mkdir(parents=True, exist_ok=True)
    
    def extract_from_document(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text, images, and tables from a document.
        
        Args:
            file_path (str): Path to the document file
            
        Returns:
            dict: Dictionary containing extracted text, images, and tables
        """
        try:
            result = self.converter.convert(file_path)
            document = result.document
            
            extracted_data = {
                'filename': Path(file_path).name,
                'text': document.export_to_markdown(),
                'images': self._extract_images(document),
                'tables': self._extract_tables(document),
                'raw_content': document.export_to_dict()
            }
            return extracted_data
        except Exception as e:
            print(f"Error extracting from {file_path}: {e}")
            return None
    
    def _extract_images(self, document: DoclingDocument) -> List[Dict[str, str]]:
        """Extract images from document."""
        images = []
        try:
            # Extract image information from document
            # This is a basic implementation - enhance based on document structure
            images_data = document.export_to_dict().get('images', [])
            for idx, img in enumerate(images_data):
                images.append({
                    'index': idx,
                    'description': f'Image {idx} from document'
                })
        except Exception as e:
            print(f"Error extracting images: {e}")
        return images
    
    def _extract_tables(self, document: DoclingDocument) -> List[str]:
        """Extract tables from document and convert to markdown."""
        tables = []
        try:
            # Extract table information from document
            doc_dict = document.export_to_dict()
            tables_data = doc_dict.get('tables', [])
            for table in tables_data:
                tables.append(table)
        except Exception as e:
            print(f"Error extracting tables: {e}")
        return tables


# ============================================================
# Step 4: Chunk the files into smaller pieces
# ============================================================
class DocumentChunker:
    """Chunk documents into smaller pieces for embedding."""
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        """
        Initialize document chunker.
        
        Args:
            chunk_size (int): Size of each chunk
            chunk_overlap (int): Overlap between chunks
        """
        chunk_size = chunk_size or int(os.getenv("CHUNK_SIZE", "1000"))
        chunk_overlap = chunk_overlap or int(os.getenv("CHUNK_OVERLAP", "200"))
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[LCDocument]:
        """
        Chunk text into smaller pieces.
        
        Args:
            text (str): Text to chunk
            metadata (dict): Metadata for the chunks
            
        Returns:
            list: List of LangChain Document objects
        """
        chunks = self.text_splitter.split_text(text)
        documents = []
        for idx, chunk in enumerate(chunks):
            meta = metadata or {}
            meta['chunk_id'] = idx
            documents.append(LCDocument(page_content=chunk, metadata=meta))
        return documents


# ============================================================
# Step 5: Create embeddings and store in vector database
# ============================================================
class EmbeddingsManager:
    """Manage embeddings creation and storage."""
    
    def __init__(self, model_name: str = None):
        """
        Initialize embeddings manager.
        
        Args:
            model_name (str): Name of the embedding model to use
        """
        model_name = model_name or os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
        self.vector_db = None
    
    def create_vector_store(self, documents: List[LCDocument], collection_name: str = "multimodal_rag") -> Chroma:
        """
        Create vector store from documents.
        
        Args:
            documents (list): List of LangChain Document objects
            collection_name (str): Name of the collection
            
        Returns:
            Chroma: Vector store
        """
        if not documents:
            print("No documents to create vector store")
            return None
        
        self.vector_db = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            collection_name=collection_name,
            persist_directory=os.getenv("CHROMA_DB_PATH", "./chroma_db")
        )
        return self.vector_db
    
    def add_documents(self, documents: List[LCDocument]) -> None:
        """Add documents to existing vector store."""
        if self.vector_db:
            self.vector_db.add_documents(documents)


# ============================================================
# Step 6: Ingestion Pipeline
# ============================================================
class IngestionPipeline:
    """Automated ingestion pipeline."""
    
    def __init__(self, data_folder: str = "data", output_folder: str = "output"):
        """Initialize ingestion pipeline."""
        self.rag_setup = RAGSetup(data_folder, output_folder)
        self.extractor = DocumentExtractor(self.rag_setup.output_folder)
        self.chunker = DocumentChunker()
        self.embeddings_manager = EmbeddingsManager()
        self.all_chunks = []
    
    def run(self) -> Chroma:
        """
        Run the complete ingestion pipeline.
        
        Returns:
            Chroma: Vector store with all documents
        """
        print("Starting ingestion pipeline...")
        
        # Get files to process
        files = self.rag_setup.get_supported_files()
        print(f"Found {len(files)} files to process")
        
        # Process each file
        for filename in tqdm(files, desc="Processing documents"):
            file_path = self.rag_setup.data_folder / filename
            
            # Extract content
            extracted = self.extractor.extract_from_document(str(file_path))
            if not extracted:
                continue
            
            # Save extracted data
            self._save_extracted_data(extracted)
            
            # Chunk the text
            chunks = self.chunker.chunk_text(
                extracted['text'],
                metadata={'source': filename}
            )
            self.all_chunks.extend(chunks)
        
        # Create vector store
        print(f"Creating vector store with {len(self.all_chunks)} chunks...")
        vector_store = self.embeddings_manager.create_vector_store(self.all_chunks)
        
        print("Ingestion pipeline completed!")
        return vector_store
    
    def _save_extracted_data(self, extracted: Dict[str, Any]) -> None:
        """Save extracted data to file."""
        output_file = self.rag_setup.extracted_data_folder / \
                     f"{extracted['filename'].split('.')[0]}_extracted.json"
        with open(output_file, 'w') as f:
            json.dump({
                'filename': extracted['filename'],
                'text_preview': extracted['text'][:500],
                'num_images': len(extracted['images']),
                'num_tables': len(extracted['tables'])
            }, f, indent=2)


# ============================================================
# Step 7: Retrieval Pipeline
# ============================================================
class RetrievalPipeline:
    """Retrieval pipeline to query the vector database."""
    
    def __init__(self, vector_store: Chroma, k: int = None):
        """
        Initialize retrieval pipeline.
        
        Args:
            vector_store (Chroma): Vector store to retrieve from
            k (int): Number of documents to retrieve
        """
        self.vector_store = vector_store
        self.k = k or int(os.getenv("RETRIEVAL_K", "5"))
        self.retriever = vector_store.as_retriever(search_kwargs={"k": self.k})
    
    def retrieve(self, query: str) -> List[LCDocument]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query (str): User query
            
        Returns:
            list: Retrieved documents
        """
        results = self.retriever.invoke(query)
        return results


# ============================================================
# Step 8 & 10: Answer Generation
# ============================================================
class AnswerGenerator:
    """Generate answers using retrieved information."""
    
    def __init__(self, retrieval_pipeline: RetrievalPipeline):
        """Initialize answer generator."""
        self.retrieval_pipeline = retrieval_pipeline
    
    def generate_answer(self, query: str) -> Dict[str, Any]:
        """
        Generate answer for a user query.
        
        Args:
            query (str): User query
            
        Returns:
            dict: Generated answer and source documents
        """
        # Retrieve relevant documents
        retrieved_docs = self.retrieval_pipeline.retrieve(query)
        
        # Format retrieved context
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        
        # Create response
        response = {
            'query': query,
            'context': context,
            'num_sources': len(retrieved_docs),
            'sources': [
                {
                    'content': doc.page_content[:200],
                    'source': doc.metadata.get('source', 'Unknown')
                }
                for doc in retrieved_docs
            ]
        }
        return response


# ============================================================
# Main RAG System
# ============================================================
class MultimodalRAG:
    """Complete Multimodal RAG System."""
    
    def __init__(self, data_folder: str = "data"):
        """Initialize the complete RAG system."""
        self.data_folder = data_folder
        self.ingestion_pipeline = IngestionPipeline(data_folder)
        self.vector_store = None
        self.retrieval_pipeline = None
        self.answer_generator = None
    
    def initialize(self) -> None:
        """Initialize the RAG system by running the ingestion pipeline."""
        self.vector_store = self.ingestion_pipeline.run()
        self.retrieval_pipeline = RetrievalPipeline(self.vector_store)
        self.answer_generator = AnswerGenerator(self.retrieval_pipeline)
        print("RAG system initialized successfully!")
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        Query the RAG system.
        
        Args:
            question (str): User question
            
        Returns:
            dict: Answer and source information
        """
        if not self.answer_generator:
            print("RAG system not initialized. Call initialize() first.")
            return None
        
        return self.answer_generator.generate_answer(question)


# ============================================================
# Usage Example
# ============================================================
if __name__ == "__main__":
    # Initialize RAG system
    rag_system = MultimodalRAG(data_folder="data")
    
    # Run initialization (this processes all documents)
    # rag_system.initialize()
    
    # Example query
    # result = rag_system.query("What is the main topic discussed?")
    # print(json.dumps(result, indent=2))