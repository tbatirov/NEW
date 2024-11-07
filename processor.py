"""Financial statement processor with citation tracking"""
from typing import Dict, Any, List, Tuple
import pandas as pd
from llama_index.core import VectorStoreIndex
from indexer import query_knowledge_base
import os
from openai import OpenAI
import json
from templates import BALANCE_SHEET_TEMPLATE, INCOME_STATEMENT_TEMPLATE, CASH_FLOW_TEMPLATE

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI()

def process_trial_balance(df: pd.DataFrame, knowledge_base: VectorStoreIndex = None) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """Process trial balance and generate financial statements with citations"""
    try:
        # Get relevant accounting standards if knowledge base is available
        relevant_standards = []
        citations = []
        if knowledge_base is not None:
            try:
                relevant_standards = query_knowledge_base(
                    knowledge_base,
                    "financial statement preparation requirements and classification rules"
                )
                # Track citations
                for idx, standard in enumerate(relevant_standards):
                    citations.append({
                        'text': standard,
                        'source': f"NAS Uzbekistan Standards"
                    })
            except Exception as e:
                print(f"Error querying knowledge base: {e}")
                # Continue with empty standards list
        
        # Prepare context for OpenAI
        context = "\n".join([
            "Trial Balance Data:",
            df.to_string(),
            "\nRelevant Accounting Standards:",
            "\n".join(relevant_standards) if relevant_standards else "Using default accounting principles"
        ])
        
        # Generate statements using OpenAI
        prompt = f"""
        Based on the following trial balance and {'Uzbekistan accounting standards' if relevant_standards else 'general accounting principles'}:
        {context}
        
        Generate a complete set of financial statements following the exact structure below:

        Balance Sheet Structure:
        {json.dumps(BALANCE_SHEET_TEMPLATE, indent=2)}

        Income Statement Structure:
        {json.dumps(INCOME_STATEMENT_TEMPLATE, indent=2)}

        Cash Flow Statement Structure:
        {json.dumps(CASH_FLOW_TEMPLATE, indent=2)}

        Requirements:
        1. Follow {'Uzbekistan NAS standards' if relevant_standards else 'general accounting principles'} strictly
        2. Classify all accounts according to the provided templates
        3. Ensure all amounts are properly calculated and balanced
        4. Use proper account names
        5. Return a single JSON object with three main keys: 'balance_sheet', 'income_statement', and 'cash_flow'
        6. Each statement should follow the exact structure shown above
        """
        
        response = openai_client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        statements = json.loads(response.choices[0].message.content)
        
        # Validate required keys exist
        required_keys = ['balance_sheet', 'income_statement', 'cash_flow']
        for key in required_keys:
            if key not in statements:
                statements[key] = {}  # Initialize empty if missing
        
        return statements, citations
    except Exception as e:
        print(f"Error generating statements: {e}")
        # Return empty structure if error occurs
        return {
            'balance_sheet': {},
            'income_statement': {},
            'cash_flow': {}
        }, []
