from llama_index.core import VectorStoreIndex, ServiceContext
from llama_index.core.schema import Document
from llama_index.core.node_parser import SimpleNodeParser
from scraper import scrape_standards
from typing import List
import os

def setup_knowledge_base() -> VectorStoreIndex:
    """Setup and return LlamaIndex knowledge base"""
    
    # Scrape standards
    standards = scrape_standards()
    
    # Create documents
    documents: List[Document] = []
    for standard in standards:
        doc = Document(
            text=standard['content'],
            metadata={'url': standard['url']}
        )
        documents.append(doc)
    
    # Create parser and parse nodes
    parser = SimpleNodeParser.from_defaults()
    nodes = parser.get_nodes_from_documents(documents)
    
    # Create and return index
    service_context = ServiceContext.from_defaults()
    index = VectorStoreIndex(nodes, service_context=service_context)
    
    return index

def query_knowledge_base(
    index: VectorStoreIndex,
    query: str,
    num_results: int = 3
) -> List[str]:
    """Query the knowledge base and return relevant passages"""
    
    query_engine = index.as_query_engine(
        similarity_top_k=num_results
    )
    response = query_engine.query(query)
    
    # Extract and return relevant text passages
    results = []
    for node in response.source_nodes:
        results.append(node.text)
    
    return results
