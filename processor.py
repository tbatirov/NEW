from typing import Dict, Any
import pandas as pd
from llama_index.core import VectorStoreIndex
from indexer import query_knowledge_base
import os
from openai import OpenAI
import json

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def process_trial_balance(
    df: pd.DataFrame,
    knowledge_base: VectorStoreIndex
) -> Dict[str, Any]:
    """Process trial balance and generate financial statements"""
    
    # Get relevant accounting standards
    relevant_standards = query_knowledge_base(
        knowledge_base,
        "financial statement preparation requirements"
    )
    
    # Prepare context for OpenAI
    context = "\n".join([
        "Trial Balance Data:",
        df.to_string(),
        "\nRelevant Accounting Standards:",
        "\n".join(relevant_standards)
    ])
    
    # Generate statements using OpenAI
    prompt = f"""
    Based on the following trial balance and accounting standards:
    {context}
    
    Generate a complete set of financial statements including:
    1. Balance Sheet
    2. Income Statement
    3. Cash Flow Statement
    
    Follow Uzbekistan NAS standards strictly.
    Provide the output in JSON format with separate sections for each statement.
    """
    
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    statements = json.loads(response.choices[0].message.content)
    return statements
