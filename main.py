import streamlit as st
import pandas as pd
from indexer import setup_knowledge_base
from processor import process_trial_balance
import io

# Page configuration
st.set_page_config(
    page_title="Uzbekistan Financial Statement Generator",
    layout="wide"
)

# Initialize session state
if 'knowledge_base' not in st.session_state:
    with st.spinner('Setting up knowledge base...'):
        st.session_state.knowledge_base = setup_knowledge_base()

def main():
    st.title("Uzbekistan Financial Statement Generator")
    st.write("Generate financial statements according to NAS Uzbekistan standards")

    # File upload
    uploaded_file = st.file_uploader(
        "Upload Trial Balance (CSV or Excel)",
        type=['csv', 'xlsx']
    )

    if uploaded_file is not None:
        try:
            # Read the file
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            # Display the uploaded data
            st.subheader("Uploaded Trial Balance")
            st.dataframe(df)

            # Process button
            if st.button("Generate Financial Statements"):
                with st.spinner('Processing...'):
                    statements = process_trial_balance(
                        df,
                        st.session_state.knowledge_base
                    )
                    
                    # Display results
                    st.subheader("Generated Financial Statements")
                    
                    # Balance Sheet
                    st.markdown("### Balance Sheet")
                    st.json(statements['balance_sheet'])
                    
                    # Income Statement
                    st.markdown("### Income Statement")
                    st.json(statements['income_statement'])
                    
                    # Cash Flow Statement
                    st.markdown("### Cash Flow Statement")
                    st.json(statements['cash_flow'])

                    # Download button
                    output = io.StringIO()
                    pd.DataFrame(statements).to_csv(output, index=False)
                    st.download_button(
                        label="Download Statements",
                        data=output.getvalue(),
                        file_name="financial_statements.csv",
                        mime="text/csv"
                    )

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    main()
