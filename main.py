"""Main Streamlit application file with enhanced export functionality"""
import streamlit as st
import pandas as pd
from indexer import setup_knowledge_base
from processor import process_trial_balance
from ratios import calculate_ratios
from comparison import calculate_variances, generate_comparison_charts
import io
import json
from database import (
    save_trial_balance, save_statements, get_historical_statements,
    get_statements_by_period, init_db, save_company, get_all_companies,
    get_company
)
from datetime import datetime, date
import plotly.graph_objects as go
from openai import OpenAI
from scraper import schedule_updates
from update_checker import check_update_status
from file_handlers import read_financial_file
from export_utils import create_financial_statement_pdf, create_excel_export
import base64

# Initialize OpenAI client
openai_client = OpenAI()

# Page configuration
st.set_page_config(
    page_title="Uzbekistan Financial Statement Generator",
    layout="wide"
)

# Initialize database and start the automatic updates scheduler
init_db()
schedule_updates()

# Initialize session state for company selection
if 'selected_company_id' not in st.session_state:
    st.session_state.selected_company_id = None

# Add status checker to sidebar
with st.sidebar:
    st.title("System Status")
    
    # Add company selection to sidebar
    st.subheader("Company Selection")
    companies = get_all_companies()
    if companies:
        company_options = {f"{company[1]} ({company[2]})": company[0] for company in companies}
        selected_company = st.selectbox(
            "Select Company",
            options=list(company_options.keys()),
            index=None,
            placeholder="Choose a company..."
        )
        if selected_company:
            st.session_state.selected_company_id = company_options[selected_company]
    
    if st.button("Check Updates Status"):
        status = check_update_status()
        if status:
            st.write("Knowledge Base Status:")
            st.write(f"Total Standards: {status['total_standards']}")
            if status['latest_update']:
                st.write(f"Last Update: {status['latest_update']}")

            st.write("Recent Activity:")
            for log in status['latest_logs']:
                timestamp, source, status_type, message = log
                st.write(f"- {timestamp}: {source} ({status_type})")
        else:
            st.error("Could not fetch update status")

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

def generate_ratio_analysis(ratios: dict) -> str:
    """Generate AI analysis of financial ratios"""
    prompt = f'''
    Analyze the following financial ratios and provide insights:
    {json.dumps(ratios, indent=2)}
    
    Please provide:
    1. Overall financial health assessment
    2. Key strengths and concerns
    3. Specific recommendations for improvement
    4. Industry comparison insights where possible
    
    Format the analysis in clear sections with bullet points.
    '''
    
    response = openai_client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content

def format_date(d: date) -> str:
    """Helper function to safely format dates"""
    if isinstance(d, date):
        return d.strftime('%B %Y')
    return ""

def format_period(d: date) -> str:
    """Helper function to format period for database"""
    if isinstance(d, date):
        return d.strftime('%Y-%m')
    return ""

def get_selected_date(label: str, key: str | None = None, help_text: str | None = None) -> tuple[date | None, str | None, str | None]:
    """Helper function to handle date selection"""
    try:
        selected_date = st.date_input(
            label,
            value=date.today(),
            min_value=date(2020, 1, 1),
            max_value=date.today(),
            key=key,
            help=help_text
        )
        
        if isinstance(selected_date, date):
            period = selected_date.strftime('%Y-%m')
            display_date = selected_date.strftime('%B %Y')
            return selected_date, period, display_date
        
    except Exception as e:
        st.error(f"Error with date selection: {str(e)}")
    
    return None, None, None

def display_historical_statement(statement_data):
    """Display a single historical statement"""
    if not statement_data or len(statement_data) < 6:
        return
        
    file_name, balance_sheet, income_statement, cash_flow, generation_date, period = statement_data[:6]
    with st.expander(f"Statement from {generation_date} - {file_name} ({period})"):
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

    # Add sidebar navigation with Companies page
    st.sidebar.title("Navigation")
    selected_page = st.sidebar.radio(
        "Go to",
        ["Companies", "Generate Statements", "Financial Ratios", "Compare Periods", "History"],
        label_visibility="collapsed"
    )

    # Companies Page
    if selected_page == "Companies":
        st.header("Company Management")
        
        # Company Registration Form
        with st.expander("Register New Company"):
            with st.form("company_registration"):
                company_name = st.text_input("Company Name*", key="company_name")
                tax_id = st.text_input("Tax ID*", key="tax_id")
                address = st.text_input("Address", key="address")
                contact_email = st.text_input("Contact Email", key="email")
                contact_phone = st.text_input("Contact Phone", key="phone")
                
                submitted = st.form_submit_button("Register Company")
                if submitted:
                    if not company_name or not tax_id:
                        st.error("Company Name and Tax ID are required!")
                    else:
                        try:
                            company_id = save_company(
                                company_name, tax_id, address, contact_email, contact_phone
                            )
                            st.success(f"Company {company_name} registered successfully!")
                            st.session_state.selected_company_id = company_id
                        except ValueError as e:
                            st.error(str(e))
        
        # Display registered companies
        st.subheader("Registered Companies")
        companies = get_all_companies()
        if companies:
            company_df = pd.DataFrame(
                companies,
                columns=["ID", "Name", "Tax ID"]
            )
            st.dataframe(company_df)
        else:
            st.info("No companies registered yet.")

    # Generate Statements Page
    elif selected_page == "Generate Statements":
        if not st.session_state.selected_company_id:
            st.warning("Please select a company from the sidebar first!")
            return
            
        st.header("Generate Statements")
        
        # Get current company details
        company = get_company(st.session_state.selected_company_id)
        st.subheader(f"Generating statements for: {company[1]}")
        
        # File upload with expanded format support
        uploaded_file = st.file_uploader(
            "Upload Trial Balance File",
            type=['csv', 'xlsx', 'xls', 'json', 'xml', 'txt'],
            help="Supported formats: CSV, Excel, JSON, XML, Fixed-width text"
        )
        
        # Period selection with calendar
        st.markdown("### Select Period")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            date_obj, period, display_date = get_selected_date(
                "Select Statement Period",
                help_text="Select the month and year for the financial statements"
            )
            
            if date_obj and period:
                with col2:
                    st.markdown(f"**Selected Period:** {display_date}")
        
        # Process uploaded file
        if uploaded_file is not None and period:
            try:
                file_contents = uploaded_file.read()
                file_obj = io.BytesIO(file_contents)
                df = read_financial_file(file_obj, uploaded_file.name)
                
                # Save trial balance to database with company_id
                trial_balance_id = save_trial_balance(
                    uploaded_file.name,
                    df.to_json(orient='records'),
                    period,
                    st.session_state.selected_company_id
                )
                
                # Display the uploaded data
                st.subheader("Uploaded Trial Balance")
                st.dataframe(df)
                
                # Initialize knowledge base if not already done
                if 'knowledge_base' not in st.session_state:
                    with st.spinner('Setting up knowledge base...'):
                        try:
                            st.session_state.knowledge_base = setup_knowledge_base()
                            st.success("Knowledge base initialized successfully!")
                        except Exception as e:
                            st.error(f"Error initializing knowledge base: {str(e)}")
                            st.info("Continuing with limited functionality...")
                            st.session_state.knowledge_base = None

                # Process button
                if st.button("Generate Financial Statements"):
                    with st.spinner('Processing...'):
                        statements, citations = process_trial_balance(
                            df,
                            st.session_state.knowledge_base
                        )
                        
                        # Save statements to database with company_id
                        save_statements(
                            trial_balance_id,
                            statements,
                            st.session_state.selected_company_id
                        )
                        
                        # Store statements and citations in session state
                        st.session_state.current_statements = statements
                        st.session_state.current_citations = citations
                        
                        # Display results
                        st.subheader("Generated Financial Statements")
                        
                        # Balance Sheet
                        st.markdown("## Balance Sheet")
                        display_financial_section(statements['balance_sheet'])
                        
                        st.markdown("---")
                        
                        # Income Statement
                        st.markdown("## Income Statement")
                        display_financial_section(statements['income_statement'])
                        
                        st.markdown("---")
                        
                        # Cash Flow Statement
                        st.markdown("## Cash Flow Statement")
                        display_financial_section(statements['cash_flow'])
                        
                        # Citations section
                        if citations:
                            st.markdown("## Citations")
                            for idx, citation in enumerate(citations, 1):
                                st.markdown(f"**[{idx}]** {citation['text']}")
                                st.markdown(f"*Source: {citation['source']}*")
                        
                        # Export options
                        st.markdown("## Export Options")
                        export_col1, export_col2 = st.columns(2)
                        
                        with export_col1:
                            # PDF Export
                            pdf_bytes = create_financial_statement_pdf(
                                statements, citations, display_date
                            )
                            st.download_button(
                                label="Download PDF",
                                data=pdf_bytes,
                                file_name=f"financial_statements_{period}.pdf",
                                mime="application/pdf"
                            )
                        
                        with export_col2:
                            # Excel Export
                            excel_bytes = create_excel_export(
                                statements, citations, display_date
                            )
                            st.download_button(
                                label="Download Excel",
                                data=excel_bytes,
                                file_name=f"financial_statements_{period}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                            
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")

    # Financial Ratios Page
    elif selected_page == "Financial Ratios":
        if not st.session_state.selected_company_id:
            st.warning("Please select a company from the sidebar first!")
            return
            
        st.header("Financial Ratios Analysis")
        
        # Add tabs for different views
        ratio_view, analysis_view = st.tabs(["Ratio Details", "AI Analysis"])
        
        if 'current_statements' in st.session_state:
            try:
                ratios_data = calculate_ratios(
                    st.session_state.current_statements.get('balance_sheet', {}),
                    st.session_state.current_statements.get('income_statement', {})
                )
                ratios = ratios_data['ratios']
                explanations = ratios_data['explanations']
                
                with ratio_view:
                    # Visualization options
                    show_radar = st.checkbox("Show Radar Charts", value=True)
                    
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
                                    rcol1, rcol2 = st.columns([2, 1])
                                    with rcol1:
                                        st.write(ratio_name.replace('_', ' ').title())
                                    with rcol2:
                                        st.write(f"{ratio_value:.2f}")
                                    if ratio_name in explanations:
                                        st.info(explanations[ratio_name])
                        
                        st.markdown("---")
                
                with analysis_view:
                    try:
                        with st.spinner("Generating analysis..."):
                            analysis = generate_ratio_analysis(ratios)
                            st.markdown(analysis)
                    except Exception as e:
                        st.error(f"Error generating analysis: {str(e)}")
                
            except Exception as e:
                st.error(f"Error calculating ratios: {str(e)}")
        else:
            st.info("Generate financial statements first to view ratios")

    # Compare Periods Page
    elif selected_page == "Compare Periods":
        if not st.session_state.selected_company_id:
            st.warning("Please select a company from the sidebar first!")
            return
            
        st.header("Compare Periods")
        
        # Get all periods from historical statements for the selected company
        all_periods = [stmt[5] for stmt in get_historical_statements(st.session_state.selected_company_id) 
                      if stmt[5] is not None]
        
        if not all_periods:
            st.info("No historical data available for comparison")
            return
        
        # Period selection
        st.markdown("### Select Periods to Compare")
        col1, col2 = st.columns(2)
        
        # First Period
        with col1:
            st.markdown("**First Period**")
            date_obj1, period1, display_date1 = get_selected_date(
                "Select First Period",
                key="period1_date"
            )
            if date_obj1:
                st.markdown(f"**Selected:** {display_date1}")
        
        # Second Period
        with col2:
            st.markdown("**Second Period**")
            date_obj2, period2, display_date2 = get_selected_date(
                "Select Second Period",
                key="period2_date"
            )
            if date_obj2:
                st.markdown(f"**Selected:** {display_date2}")
        
        if period1 and period2:
            # Get statements for selected periods
            stmt1 = get_statements_by_period(period1, st.session_state.selected_company_id)
            stmt2 = get_statements_by_period(period2, st.session_state.selected_company_id)
            
            if stmt1 and stmt2:
                # Parse statements
                statements1 = {
                    'balance_sheet': json.loads(stmt1[1]),
                    'income_statement': json.loads(stmt1[2]),
                    'cash_flow': json.loads(stmt1[3])
                }
                statements2 = {
                    'balance_sheet': json.loads(stmt2[1]),
                    'income_statement': json.loads(stmt2[2]),
                    'cash_flow': json.loads(stmt2[3])
                }
                
                # Calculate variances
                variances = calculate_variances(statements1, statements2)
                
                # Display comparison
                st.subheader("Statement Comparison")
                
                # Balance Sheet
                st.markdown("### Balance Sheet")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"#### {period1}")
                    display_financial_section(statements1['balance_sheet'])
                with col2:
                    st.markdown(f"#### {period2}")
                    display_financial_section(statements2['balance_sheet'])
                with col3:
                    st.markdown("#### Variances")
                    display_financial_section(variances['balance_sheet'])
                
                st.markdown("---")
                
                # Income Statement
                st.markdown("### Income Statement")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"#### {period1}")
                    display_financial_section(statements1['income_statement'])
                with col2:
                    st.markdown(f"#### {period2}")
                    display_financial_section(statements2['income_statement'])
                with col3:
                    st.markdown("#### Variances")
                    display_financial_section(variances['income_statement'])
                
            else:
                st.warning("Could not find statements for one or both selected periods")

    # History Page
    elif selected_page == "History":
        if not st.session_state.selected_company_id:
            st.warning("Please select a company from the sidebar first!")
            return
            
        st.header("Statement History")
        
        # Get historical statements for the selected company
        historical_statements = get_historical_statements(st.session_state.selected_company_id)
        
        if not historical_statements:
            st.info("No historical statements found for this company.")
        else:
            for statement in historical_statements:
                display_historical_statement(statement)

if __name__ == "__main__":
    main()
