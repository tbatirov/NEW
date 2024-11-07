"""Main Streamlit application file with enhanced dashboard functionality"""
import streamlit as st
import json
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from database import (
    init_db, save_trial_balance, save_statements,
    get_historical_statements, get_statements_by_period,
    get_company, get_all_companies
)
from processor import process_trial_balance
from file_handlers import read_financial_file
from ratios import calculate_ratios
from comparison import calculate_variances, generate_comparison_charts
from export_utils import create_financial_statement_pdf, create_excel_export
from indexer import setup_knowledge_base
from update_checker import check_update_status

# Initialize session state
if 'selected_company_id' not in st.session_state:
    st.session_state.selected_company_id = None

def get_selected_date(label="Select Date", key=None, help_text=None):
    """Get selected date and format it for different uses"""
    date_obj = st.date_input(
        label,
        key=key,
        help=help_text
    )
    period = date_obj.strftime("%Y-%m")
    display_date = date_obj.strftime("%B %Y")
    return date_obj, period, display_date

def display_financial_section(data, level=0):
    """Display financial data in a hierarchical structure"""
    for key, value in data.items():
        if isinstance(value, dict):
            st.markdown("&nbsp;" * (level * 4) + f"**{key.replace('_', ' ').title()}**")
            display_financial_section(value, level + 1)
        else:
            st.markdown("&nbsp;" * (level * 4) + f"{key.replace('_', ' ').title()}: {value:,.2f}")

def display_historical_statement(statement):
    """Display a historical statement with proper formatting"""
    st.markdown(f"### Statement for {statement[5]}")
    st.markdown(f"Generated on: {statement[4]}")
    st.markdown(f"Company: {statement[6]}")
    
    with st.expander("View Details"):
        tabs = st.tabs(["Balance Sheet", "Income Statement", "Cash Flow"])
        
        with tabs[0]:
            balance_sheet = json.loads(statement[1])
            display_financial_section(balance_sheet)
            
        with tabs[1]:
            income_statement = json.loads(statement[2])
            display_financial_section(income_statement)
            
        with tabs[2]:
            cash_flow = json.loads(statement[3])
            display_financial_section(cash_flow)

def plot_ratio_radar_chart(ratios, category):
    """Create a radar chart for financial ratios"""
    try:
        category_ratios = ratios[category]
        values = []
        labels = []
        
        for name, value in category_ratios.items():
            if value is not None and not isinstance(value, str):
                labels.append(name.replace('_', ' ').title())
                values.append(value)
        
        if not values:
            return None
            
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=labels,
            fill='toself',
            name=category.replace('_', ' ').title()
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(values) * 1.2]
                )),
            showlegend=False
        )
        return fig
    except Exception:
        return None

def plot_trend_chart(data, title):
    """Create a line chart for trend analysis"""
    fig = go.Figure()
    
    for key, values in data.items():
        fig.add_trace(go.Scatter(
            x=list(values.keys()),
            y=list(values.values()),
            name=key.replace('_', ' ').title(),
            mode='lines+markers'
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Period",
        yaxis_title="Value",
        hovermode='x unified'
    )
    return fig

def generate_ratio_analysis(ratios):
    """Generate narrative analysis of financial ratios"""
    analysis = []
    
    # Analyze liquidity
    current_ratio = ratios['liquidity_ratios']['current_ratio']
    if current_ratio:
        if current_ratio < 1:
            analysis.append("⚠️ The company's current ratio is below 1, indicating potential liquidity issues.")
        elif current_ratio < 1.5:
            analysis.append("⚠️ The company's current ratio is adequate but could be improved.")
        else:
            analysis.append("✅ The company maintains a healthy liquidity position.")
    
    # Analyze profitability
    roi = ratios['profitability_ratios']['return_on_assets']
    if roi:
        if roi < 0:
            analysis.append("❌ The company is currently operating at a loss.")
        elif roi < 5:
            analysis.append("⚠️ The company's profitability is below industry average.")
        else:
            analysis.append("✅ The company shows strong profitability.")
    
    # Analyze efficiency
    asset_turnover = ratios['efficiency_ratios']['asset_turnover']
    if asset_turnover:
        if asset_turnover < 0.5:
            analysis.append("⚠️ Asset utilization could be improved.")
        else:
            analysis.append("✅ The company is efficiently utilizing its assets.")
    
    return "\n\n".join(analysis)

def main():
    st.set_page_config(
        page_title="Financial Statement Generator",
        page_icon="📊",
        layout="wide"
    )
    
    # Initialize database
    init_db()
    
    # Sidebar for company selection and navigation
    with st.sidebar:
        st.title("Financial Statement Generator")
        
        # Company selection
        companies = get_all_companies()
        if companies:
            company_options = {f"{company[1]} (Tax ID: {company[2]})": company[0] 
                             for company in companies}
            selected_company = st.selectbox(
                "Select Company",
                options=list(company_options.keys())
            )
            st.session_state.selected_company_id = company_options[selected_company]
        
        # Navigation
        selected_page = st.radio(
            "Navigation",
            ["Dashboard", "Generate Statements", "View Ratios", "Compare Periods", "History"]
        )
        
        # Knowledge base status
        update_status = check_update_status()
        if update_status:
            with st.expander("Knowledge Base Status"):
                st.write(f"Total Standards: {update_status['total_standards']}")
                st.write(f"Last Update: {update_status['latest_update']}")
    
    # Main content area based on selected page
    if selected_page == "Generate Statements":
        if not st.session_state.selected_company_id:
            st.warning("Please select a company from the sidebar first!")
            return
            
        st.header("Generate Financial Statements")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Upload Trial Balance",
            type=['csv', 'xlsx', 'json', 'xml']
        )
        
        # Period selection
        date_obj, period, display_date = get_selected_date(
            "Select Statement Period",
            help_text="Select the period for which the trial balance applies"
        )
        
        if uploaded_file and period:
            try:
                # Process trial balance
                df = read_financial_file(uploaded_file, uploaded_file.name)
                
                # Initialize knowledge base
                knowledge_base = setup_knowledge_base()
                
                # Save trial balance
                trial_balance_id = save_trial_balance(
                    uploaded_file.name,
                    df.to_json(),
                    period,
                    st.session_state.selected_company_id
                )
                
                # Generate statements
                statements, citations = process_trial_balance(df, knowledge_base)
                
                # Save statements
                save_statements(
                    trial_balance_id,
                    statements,
                    st.session_state.selected_company_id
                )
                
                # Display statements
                st.success("Financial statements generated successfully!")
                
                # Export options
                st.subheader("Export Statements")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # PDF Export
                    pdf_bytes = create_financial_statement_pdf(
                        statements,
                        citations,
                        display_date
                    )
                    st.download_button(
                        label="Download PDF",
                        data=pdf_bytes,
                        file_name=f"financial_statements_{period}.pdf",
                        mime="application/pdf"
                    )
                
                with col2:
                    # Excel Export
                    excel_bytes = create_excel_export(
                        statements,
                        citations,
                        display_date
                    )
                    st.download_button(
                        label="Download Excel",
                        data=excel_bytes,
                        file_name=f"financial_statements_{period}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                # Display preview
                tabs = st.tabs(["Balance Sheet", "Income Statement", "Cash Flow", "Citations"])
                
                with tabs[0]:
                    display_financial_section(statements['balance_sheet'])
                    
                with tabs[1]:
                    display_financial_section(statements['income_statement'])
                    
                with tabs[2]:
                    display_financial_section(statements['cash_flow'])
                    
                with tabs[3]:
                    for citation in citations:
                        st.markdown(f"- {citation['text']}")
                        st.markdown(f"  Source: {citation['source']}")
                
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
    
    # View Ratios Page
    elif selected_page == "View Ratios":
        if not st.session_state.selected_company_id:
            st.warning("Please select a company from the sidebar first!")
            return
            
        st.header("Financial Ratios")
        
        # Period selection
        date_obj, period, display_date = get_selected_date(
            "Select Period",
            key="ratio_period",
            help_text="Select the period to calculate ratios for"
        )
        
        if period:
            statements_data = get_statements_by_period(period, st.session_state.selected_company_id)
            
            if statements_data:
                statements = {
                    'balance_sheet': json.loads(statements_data[1]),
                    'income_statement': json.loads(statements_data[2])
                }
                
                try:
                    # Calculate ratios
                    ratios_data = calculate_ratios(statements['balance_sheet'], statements['income_statement'])
                    ratios = ratios_data['ratios']
                    explanations = ratios_data['explanations']
                    
                    # Display options
                    show_radar = st.checkbox("Show Radar Charts", value=True)
                    
                    # Create tabs for different views
                    ratio_view, analysis_view = st.tabs(["Ratios", "Analysis"])
                    
                    with ratio_view:
                        # Display ratios by category
                        for category in ratios:
                            st.markdown(f"### {category.replace('_', ' ').title()}")
                            
                            # Create columns for ratios and radar chart
                            ratio_col, chart_col = st.columns([3, 2])
                            
                            with ratio_col:
                                for ratio_name, value in ratios[category].items():
                                    if value is not None:
                                        st.write(f"**{ratio_name.replace('_', ' ').title()}:** {value:.2f}")
                                        st.write(f"*{explanations.get(ratio_name, '')}*")
                                        st.write("---")
                            
                            with chart_col:
                                if show_radar:
                                    chart = plot_ratio_radar_chart(ratios, category)
                                    if chart:
                                        st.plotly_chart(chart, use_container_width=True)
                    
                    with analysis_view:
                        analysis = generate_ratio_analysis(ratios)
                        st.markdown(analysis)
                        
                except Exception as e:
                    st.error(f"Error calculating ratios: {str(e)}")
            else:
                st.info("Please generate financial statements first to view ratios.")
    
    # Compare Periods Page
    elif selected_page == "Compare Periods":
        if not st.session_state.selected_company_id:
            st.warning("Please select a company from the sidebar first!")
            return
            
        st.header("Period Comparison")
        
        # Period selection
        col1, col2 = st.columns(2)
        
        with col1:
            date_obj1, period1, display_date1 = get_selected_date(
                "Select First Period",
                key="period1"
            )
            
        with col2:
            date_obj2, period2, display_date2 = get_selected_date(
                "Select Second Period",
                key="period2"
            )
            
        if period1 and period2:
            # Get statements for both periods
            statements1 = get_statements_by_period(period1, st.session_state.selected_company_id)
            statements2 = get_statements_by_period(period2, st.session_state.selected_company_id)
            
            if statements1 and statements2:
                # Parse JSON strings to dictionaries
                period1_data = {
                    'balance_sheet': json.loads(statements1[1]),
                    'income_statement': json.loads(statements1[2]),
                    'cash_flow': json.loads(statements1[3])
                }
                
                period2_data = {
                    'balance_sheet': json.loads(statements2[1]),
                    'income_statement': json.loads(statements2[2]),
                    'cash_flow': json.loads(statements2[3])
                }
                
                # Calculate variances
                variances = calculate_variances(period1_data, period2_data)
                
                # Generate comparison charts
                comparison_charts = generate_comparison_charts([
                    {'period': display_date1, 'statements': period1_data},
                    {'period': display_date2, 'statements': period2_data}
                ])
                
                # Display results
                st.plotly_chart(comparison_charts['trend_chart'])
                
                # Display variances
                st.subheader("Detailed Comparison")
                
                for statement_type, variance_data in variances.items():
                    with st.expander(f"{statement_type.replace('_', ' ').title()} Comparison"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.markdown(f"#### {display_date1}")
                            display_financial_section(period1_data[statement_type])
                            
                        with col2:
                            st.markdown(f"#### {display_date2}")
                            display_financial_section(period2_data[statement_type])
                            
                        with col3:
                            st.markdown("#### Variances")
                            display_financial_section(variance_data)
                
            else:
                st.warning("Financial statements not found for one or both periods.")
    
    # History Page
    elif selected_page == "History":
        if not st.session_state.selected_company_id:
            st.warning("Please select a company from the sidebar first!")
            return
            
        st.header("Statement History")
        
        # Get historical statements for the selected company
        historical_statements = get_historical_statements(st.session_state.selected_company_id)
        
        if historical_statements:
            for statement in historical_statements:
                display_historical_statement(statement)
        else:
            st.info("No historical statements found for this company.")
    
    # Dashboard Page
    elif selected_page == "Dashboard":
        if not st.session_state.selected_company_id:
            st.warning("Please select a company from the sidebar first!")
            return
            
        st.header("Company Dashboard")
        
        # Get company details
        company = get_company(st.session_state.selected_company_id)
        st.subheader(f"Dashboard for: {company[1]}")
        
        # Period Selection
        date_obj, period, display_date = get_selected_date(
            "Select Period for Dashboard",
            key="dashboard_period",
            help_text="Select the period to view dashboard metrics"
        )
        
        if period:
            statements_data = get_statements_by_period(period, st.session_state.selected_company_id)
            
            if statements_data:
                statements = {
                    'balance_sheet': json.loads(statements_data[1]),
                    'income_statement': json.loads(statements_data[2]),
                    'cash_flow': json.loads(statements_data[3])
                }
                
                # Calculate financial ratios
                try:
                    ratios_data = calculate_ratios(statements['balance_sheet'], statements['income_statement'])
                    ratios = ratios_data['ratios']
                    
                    # Dashboard Layout
                    # Key Financial Metrics
                    st.markdown("## Key Financial Metrics")
                    metrics_cols = st.columns(4)
                    
                    # Current Ratio
                    with metrics_cols[0]:
                        current_ratio = ratios['liquidity_ratios']['current_ratio']
                        delta_color = "normal" if current_ratio >= 1.5 else "off" if current_ratio >= 1 else "inverse"
                        st.metric(
                            "Current Ratio",
                            f"{current_ratio:.2f}" if current_ratio else "N/A",
                            delta_color=delta_color
                        )
                    
                    # Return on Assets
                    with metrics_cols[1]:
                        roa = ratios['profitability_ratios']['return_on_assets']
                        delta_color = "normal" if roa >= 5 else "off" if roa >= 0 else "inverse"
                        st.metric(
                            "Return on Assets",
                            f"{roa:.2f}%" if roa else "N/A",
                            delta_color=delta_color
                        )
                    
                    # Debt Ratio
                    with metrics_cols[2]:
                        debt_ratio = ratios['leverage_ratios']['debt_ratio']
                        delta_color = "normal" if debt_ratio <= 40 else "off" if debt_ratio <= 60 else "inverse"
                        st.metric(
                            "Debt Ratio",
                            f"{debt_ratio:.2f}%" if debt_ratio else "N/A",
                            delta_color=delta_color
                        )
                    
                    # Asset Turnover
                    with metrics_cols[3]:
                        asset_turnover = ratios['efficiency_ratios']['asset_turnover']
                        delta_color = "normal" if asset_turnover >= 1 else "off" if asset_turnover >= 0.5 else "inverse"
                        st.metric(
                            "Asset Turnover",
                            f"{asset_turnover:.2f}" if asset_turnover else "N/A",
                            delta_color=delta_color
                        )
                    
                    # Financial Health Overview
                    st.markdown("## Financial Health Overview")
                    health_cols = st.columns(2)
                    
                    with health_cols[0]:
                        st.markdown("### Liquidity & Solvency Analysis")
                        liquidity_chart = plot_ratio_radar_chart(ratios, 'liquidity_ratios')
                        if liquidity_chart:
                            st.plotly_chart(liquidity_chart, use_container_width=True)
                    
                    with health_cols[1]:
                        st.markdown("### Profitability Analysis")
                        profitability_chart = plot_ratio_radar_chart(ratios, 'profitability_ratios')
                        if profitability_chart:
                            st.plotly_chart(profitability_chart, use_container_width=True)
                    
                    # Historical Trend Analysis
                    st.markdown("## Historical Performance")
                    historical_statements = get_historical_statements(st.session_state.selected_company_id)
                    
                    if historical_statements:
                        # Prepare trend data
                        trend_data = {
                            'revenue': {},
                            'net_income': {},
                            'total_assets': {},
                            'total_liabilities': {}
                        }
                        
                        for stmt in historical_statements:
                            if len(stmt) >= 6:
                                period_date = stmt[5]
                                bs = json.loads(stmt[1])
                                is_stmt = json.loads(stmt[2])
                                
                                # Extract key metrics
                                trend_data['total_assets'][period_date] = sum(
                                    float(val) for val in bs.get('assets', {}).values() 
                                    if isinstance(val, (int, float))
                                )
                                trend_data['total_liabilities'][period_date] = sum(
                                    float(val) for val in bs.get('liabilities', {}).values() 
                                    if isinstance(val, (int, float))
                                )
                                trend_data['revenue'][period_date] = sum(
                                    float(val) for val in is_stmt.get('revenue', {}).values() 
                                    if isinstance(val, (int, float))
                                )
                                trend_data['net_income'][period_date] = sum(
                                    float(val) for val in is_stmt.get('net_income', {}).values() 
                                    if isinstance(val, (int, float))
                                )
                        
                        # Create trend charts
                        trend_cols = st.columns(2)
                        
                        with trend_cols[0]:
                            st.markdown("### Balance Sheet Trends")
                            bs_trend_chart = plot_trend_chart(
                                {k: trend_data[k] for k in ['total_assets', 'total_liabilities']},
                                "Assets vs Liabilities"
                            )
                            st.plotly_chart(bs_trend_chart, use_container_width=True)
                        
                        with trend_cols[1]:
                            st.markdown("### Income Statement Trends")
                            is_trend_chart = plot_trend_chart(
                                {k: trend_data[k] for k in ['revenue', 'net_income']},
                                "Revenue vs Net Income"
                            )
                            st.plotly_chart(is_trend_chart, use_container_width=True)
                        
                        # Financial Analysis Summary
                        st.markdown("## Financial Analysis Summary")
                        summary_text = generate_ratio_analysis(ratios)
                        st.markdown(summary_text)
                        
                        # Export Options
                        st.markdown("## Export Dashboard")
                        export_cols = st.columns(2)
                        
                        with export_cols[0]:
                            pdf_bytes = create_financial_statement_pdf(
                                statements,
                                [],  # No citations needed for dashboard
                                display_date
                            )
                            st.download_button(
                                label="Download Dashboard PDF",
                                data=pdf_bytes,
                                file_name=f"dashboard_{period}.pdf",
                                mime="application/pdf"
                            )
                        
                        with export_cols[1]:
                            excel_bytes = create_excel_export(
                                statements,
                                [],  # No citations needed for dashboard
                                display_date
                            )
                            st.download_button(
                                label="Download Dashboard Excel",
                                data=excel_bytes,
                                file_name=f"dashboard_{period}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    else:
                        st.info("No historical data available for trend analysis.")
                        
                except Exception as e:
                    st.error(f"Error generating dashboard: {str(e)}")
            else:
                st.warning("No financial statements found for the selected period.")

if __name__ == "__main__":
    main()
