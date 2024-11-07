import streamlit as st
import pandas as pd
from indexer import setup_knowledge_base
from processor import process_trial_balance
from ratios import calculate_ratios
import io
import json
from database import save_trial_balance, save_statements, get_historical_statements
from datetime import datetime
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="Uzbekistan Financial Statement Generator",
    layout="wide"
)

# Helper functions for financial statement display
def format_amount(amount):
    try:
        return f"{float(amount):,.2f}"
    except:
        return amount

def display_financial_section(data, indent_level=0):
    for key, value in data.items():
        # Format the key for display
        display_key = key.replace('_', ' ').title()
        
        # If value is a dict, create a section
        if isinstance(value, dict):
            st.markdown(f"{'#' * (indent_level + 4)} {display_key}")
            display_financial_section(value, indent_level + 1)
        else:
            # Display leaf nodes with proper number formatting
            st.write(f"{'    ' * indent_level}{display_key}: {format_amount(value)}")

def plot_ratio_radar_chart(ratios: dict, category: str):
    """Create a radar chart for a specific ratio category"""
    category_ratios = ratios[category]
    values = []
    labels = []
    
    for name, value in category_ratios.items():
        if value is not None:
            labels.append(name.replace('_', ' ').title())
            values.append(value)
    
    if values:  # Only create chart if there are valid values
        fig = go.Figure(data=go.Scatterpolar(
            r=values,
            theta=labels,
            fill='toself'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(values) * 1.2]
                )),
            showlegend=False,
            title=category.replace('_', ' ').title()
        )
        return fig
    return None

# Initialize session state
if 'knowledge_base' not in st.session_state:
    with st.spinner('Setting up knowledge base...'):
        st.session_state.knowledge_base = setup_knowledge_base()

def display_historical_statement(statement_data):
    file_name, balance_sheet, income_statement, cash_flow, generation_date = statement_data
    with st.expander(f"Statement from {generation_date} - {file_name}"):
        st.markdown("#### Balance Sheet")
        display_financial_section(json.loads(balance_sheet))
        
        st.markdown("---")
        
        st.markdown("#### Income Statement")
        display_financial_section(json.loads(income_statement))
        
        st.markdown("---")
        
        st.markdown("#### Cash Flow Statement")
        display_financial_section(json.loads(cash_flow))

def main():
    st.title("Uzbekistan Financial Statement Generator")
    st.write("Generate financial statements according to NAS Uzbekistan standards")

    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Generate Statements", "Financial Ratios", "History"])

    with tab1:
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

                # Save trial balance to database
                trial_balance_id = save_trial_balance(
                    uploaded_file.name,
                    df.to_json(orient='records')
                )

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
                        
                        # Store statements in session state
                        st.session_state.current_statements = statements
                        
                        # Save statements to database
                        save_statements(trial_balance_id, statements)
                        
                        # Display results with improved formatting
                        st.subheader("Generated Financial Statements")
                        
                        # Balance Sheet
                        st.markdown("## Balance Sheet")
                        display_financial_section(statements['balance_sheet'])

                        st.markdown("---")  # Add separator

                        # Income Statement
                        st.markdown("## Income Statement")
                        display_financial_section(statements['income_statement'])

                        st.markdown("---")  # Add separator

                        # Cash Flow Statement
                        st.markdown("## Cash Flow Statement")
                        display_financial_section(statements['cash_flow'])

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

    with tab2:
        st.header("Financial Ratios Analysis")
        if 'current_statements' in st.session_state:
            try:
                ratios_data = calculate_ratios(
                    st.session_state.current_statements.get('balance_sheet', {}),
                    st.session_state.current_statements.get('income_statement', {})
                )
                ratios = ratios_data['ratios']
                explanations = ratios_data['explanations']
                
                # Add visualization options
                st.sidebar.subheader("Visualization Options")
                show_radar = st.sidebar.checkbox("Show Radar Charts", value=True)
                
                # Display ratios by category
                for category, category_ratios in ratios.items():
                    st.subheader(category.replace('_', ' ').title())
                    
                    # Create two columns for the layout
                    if show_radar:
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            for ratio_name, ratio_value in category_ratios.items():
                                if ratio_value is not None:
                                    # Create columns for ratio name, value, and explanation
                                    rcol1, rcol2 = st.columns([2, 1])
                                    with rcol1:
                                        st.write(ratio_name.replace('_', ' ').title())
                                    with rcol2:
                                        st.write(f"{ratio_value:.2f}")
                                    # Add tooltip with explanation
                                    if ratio_name in explanations:
                                        st.info(explanations[ratio_name])
                        
                        # Show radar chart in the second column
                        with col2:
                            chart = plot_ratio_radar_chart(ratios, category)
                            if chart:
                                st.plotly_chart(chart, use_container_width=True)
                    else:
                        for ratio_name, ratio_value in category_ratios.items():
                            if ratio_value is not None:
                                # Create columns for ratio name, value, and explanation
                                rcol1, rcol2 = st.columns([2, 1])
                                with rcol1:
                                    st.write(ratio_name.replace('_', ' ').title())
                                with rcol2:
                                    st.write(f"{ratio_value:.2f}")
                                # Add tooltip with explanation
                                if ratio_name in explanations:
                                    st.info(explanations[ratio_name])
                
                    st.markdown("---")
            except Exception as e:
                st.error(f"Error calculating ratios: {str(e)}")
        else:
            st.info("Generate financial statements first to view ratios")

    with tab3:
        st.header("Historical Statements")
        historical_statements = get_historical_statements()
        if historical_statements:
            for statement in historical_statements:
                display_historical_statement(statement)
        else:
            st.info("No historical statements found. Generate some statements to see them here!")

if __name__ == "__main__":
    main()