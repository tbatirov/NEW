from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.schema import Document
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.llms.openai import OpenAI
from scraper import scrape_standards
from typing import List
import os
from database import get_all_standards
import logging

logger = logging.getLogger(__name__)

def setup_knowledge_base() -> VectorStoreIndex:
    """Setup and return LlamaIndex knowledge base"""
    
    # Setup Settings
    Settings.llm = OpenAI()  # It will automatically use OPENAI_API_KEY from environment
    Settings.embed_model = "default"  # This will use OpenAI's ada-002 model
    
    try:
        # First try to get standards from database
        standards_data = get_all_standards()
        
        if not standards_data:
            # If no data in database, scrape new data
            logger.info("No standards found in database, initiating scraping")
            scrape_standards()
            standards_data = get_all_standards()
        
        # Create documents
        documents: List[Document] = []
        for url, content, source, last_updated in standards_data:
            doc = Document(
                text=content,
                metadata={
                    'url': url,
                    'source': source,
                    'last_updated': str(last_updated)
                }
            )
            documents.append(doc)
        
        # Create parser and parse nodes
        parser = SimpleNodeParser.from_defaults()
        nodes = parser.get_nodes_from_documents(documents)
        
        # Create and return index
        index = VectorStoreIndex(nodes)
        
        return index
    
    except Exception as e:
        logger.error(f"Error setting up knowledge base: {str(e)}")
        # Return a minimal index with fallback data if everything fails
        fallback_doc = Document(
            text="Basic Uzbekistan Accounting Standards guide",
            metadata={'source': 'fallback'}
        )
        return VectorStoreIndex([fallback_doc])

def query_knowledge_base(
    index: VectorStoreIndex,
    query: str,
    num_results: int = 3
) -> List[str]:
    """Query the knowledge base and return relevant passages"""
    
    query_engine = index.as_query_engine(
        similarity_top_k=num_results,
        llm=OpenAI(model="gpt-4", api_key=os.environ.get("OPENAI_API_KEY"))
    )
    response = query_engine.query(query)
    
    # Extract and return relevant text passages
    results = []
    for node in response.source_nodes:
        results.append(node.text)
    
    return results
