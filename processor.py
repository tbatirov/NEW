from typing import Dict, Any
import pandas as pd
from llama_index.core import VectorStoreIndex
from indexer import query_knowledge_base
import os
from openai import OpenAI
import json
from templates import BALANCE_SHEET_TEMPLATE, INCOME_STATEMENT_TEMPLATE, CASH_FLOW_TEMPLATE

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI()

def process_trial_balance(
    df: pd.DataFrame,
    knowledge_base: VectorStoreIndex
) -> Dict[str, Any]:
    """Process trial balance and generate financial statements"""
    
    # Get relevant accounting standards
    relevant_standards = query_knowledge_base(
        knowledge_base,
        "financial statement preparation requirements and classification rules"
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
    Based on the following trial balance and Uzbekistan accounting standards:
    {context}
    
    Generate a complete set of financial statements following the exact structure below:

    Balance Sheet Structure:
    {json.dumps(BALANCE_SHEET_TEMPLATE, indent=2)}

    Income Statement Structure:
    {json.dumps(INCOME_STATEMENT_TEMPLATE, indent=2)}

    Cash Flow Statement Structure:
    {json.dumps(CASH_FLOW_TEMPLATE, indent=2)}

    Requirements:
    1. Follow Uzbekistan NAS standards strictly
    2. Classify all accounts according to the provided templates
    3. Ensure all amounts are properly calculated and balanced
    4. Use proper account names as per Uzbekistan standards
    5. Return a single JSON object with three main keys: 'balance_sheet', 'income_statement', and 'cash_flow'
    6. Each statement should follow the exact structure shown above
    """
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        statements = json.loads(response.choices[0].message.content)
        return statements
    except Exception as e:
        print(f"Error generating statements: {e}")
        raise
