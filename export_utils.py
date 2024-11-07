"""Utilities for exporting financial statements with citations"""
import io
from typing import Dict, Any, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch

def format_amount(amount) -> str:
    """Format numerical values for display"""
    try:
        return f"{float(amount):,.2f}"
    except:
        return str(amount)

def create_financial_statement_pdf(
    statements: Dict[str, Any],
    citations: List[Dict[str, str]],
    period: str
) -> bytes:
    """Create a PDF document containing financial statements with citations"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    # Styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Custom style for citations
    citation_style = ParagraphStyle(
        'Citation',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.gray
    )

    # Build the document
    elements = []
    
    # Title
    elements.append(Paragraph(f"Financial Statements - {period}", title_style))
    elements.append(Spacer(1, 12))
    
    # Process each statement type
    for statement_type in ['balance_sheet', 'income_statement', 'cash_flow']:
        title = statement_type.replace('_', ' ').title()
        elements.append(Paragraph(title, subtitle_style))
        elements.append(Spacer(1, 12))
        
        # Convert statement data to table format
        table_data = []
        statement = statements.get(statement_type, {})
        
        def process_section(data, indent=0):
            rows = []
            for key, value in data.items():
                if isinstance(value, dict):
                    rows.append([('    ' * indent) + key.replace('_', ' ').title(), ''])
                    rows.extend(process_section(value, indent + 1))
                else:
                    rows.append([
                        ('    ' * indent) + key.replace('_', ' ').title(),
                        format_amount(value)
                    ])
            return rows
        
        table_data.extend(process_section(statement))
        
        # Create and style the table
        if table_data:
            table = Table(table_data, colWidths=[4*inch, 2*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 12))
    
    # Add citations section
    if citations:
        elements.append(Paragraph("Citations", subtitle_style))
        elements.append(Spacer(1, 12))
        
        for idx, citation in enumerate(citations, 1):
            citation_text = f"[{idx}] {citation['text']} - Source: {citation['source']}"
            elements.append(Paragraph(citation_text, citation_style))
            elements.append(Spacer(1, 6))
    
    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes

def create_excel_export(
    statements: Dict[str, Any],
    citations: List[Dict[str, str]],
    period: str
) -> bytes:
    """Create an Excel workbook containing financial statements with citations"""
    import pandas as pd
    
    buffer = io.BytesIO()
    
    # Create Excel writer
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Process each statement
        for statement_type in ['balance_sheet', 'income_statement', 'cash_flow']:
            rows = []
            statement = statements.get(statement_type, {})
            
            def process_section(data, indent=0):
                section_rows = []
                for key, value in data.items():
                    if isinstance(value, dict):
                        section_rows.append({
                            'Account': ('    ' * indent) + key.replace('_', ' ').title(),
                            'Amount': ''
                        })
                        section_rows.extend(process_section(value, indent + 1))
                    else:
                        section_rows.append({
                            'Account': ('    ' * indent) + key.replace('_', ' ').title(),
                            'Amount': format_amount(value)
                        })
                return section_rows
            
            rows.extend(process_section(statement))
            
            # Create DataFrame and write to Excel
            df = pd.DataFrame(rows)
            sheet_name = statement_type.replace('_', ' ').title()[:31]  # Excel sheet name length limit
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Adjust column widths
            worksheet = writer.sheets[sheet_name]
            worksheet.set_column('A:A', 40)
            worksheet.set_column('B:B', 15)
        
        # Add citations sheet
        if citations:
            citations_df = pd.DataFrame(citations)
            citations_df.to_excel(writer, sheet_name='Citations', index=False)
            
            # Adjust column widths
            worksheet = writer.sheets['Citations']
            worksheet.set_column('A:A', 60)
            worksheet.set_column('B:B', 20)
    
    return buffer.getvalue()
