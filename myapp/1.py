from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib import colors
from io import BytesIO
import datetime

def generate_sample_invoice():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    
    # Update styles without adding if they already exist
    styles['Title'].fontSize = 24
    styles['Title'].leading = 30
    styles['Title'].spaceAfter = 20
    styles['Title'].textColor = colors.HexColor('#04436C')
    styles['Title'].alignment = 1
    
    styles['BodyText'].fontSize = 12
    styles['BodyText'].leading = 14
    styles['BodyText'].spaceAfter = 10
    
    if 'InvoiceDetails' not in styles:
        styles.add(ParagraphStyle(name='InvoiceDetails', fontSize=12, leading=14, spaceAfter=10))
    else:
        styles['InvoiceDetails'].fontSize = 12
        styles['InvoiceDetails'].leading = 14
        styles['InvoiceDetails'].spaceAfter = 10
    
    if 'SectionTitle' not in styles:
        styles.add(ParagraphStyle(name='SectionTitle', fontSize=14, leading=18, spaceAfter=10, textColor=colors.HexColor('#04436C')))
    else:
        styles['SectionTitle'].fontSize = 14
        styles['SectionTitle'].leading = 18
        styles['SectionTitle'].spaceAfter = 10
        styles['SectionTitle'].textColor = colors.HexColor('#04436C')

    # Sample data
    context = {
        'invoice_id': '123456',
        'invoice_date': datetime.datetime.now(),
        'package': type('Package', (object,), {'name': 'Gold Package'})(),
        'amount': 99.99,
        'user': type('User', (object,), {'first_name': 'John', 'last_name': 'Doe', 'email': 'john.doe@example.com', 'address': '123 Main St, City, Country'})(),
        'site_title': 'My Company',
        'site_logo_url': 'https://via.placeholder.com/150',  # Placeholder image URL
        'site_phone': '+1-234-567-890',
        'site_email': 'contact@mycompany.com',
    }

    # Add company logo and date
    if context['site_logo_url']:
        logo = Image(context['site_logo_url'], width=150, height=50)
        logo.hAlign = 'LEFT'
        elements.append(logo)
    
    elements.append(Spacer(1, 20))
    
    elements.append(Paragraph('INVOICE', styles['Title']))

    elements.append(Spacer(1, 20))
    
    elements.append(Paragraph(context['invoice_date'].strftime('%B %d, %Y'), styles['InvoiceDetails']))

    elements.append(Spacer(1, 20))

    # Horizontal line
    elements.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.HexColor('#04436C'), spaceBefore=1, spaceAfter=1))

    elements.append(Spacer(1, 20))

    # Invoice details
    elements.append(Paragraph(f"Invoice #: {context['invoice_id']}", styles['InvoiceDetails']))

    elements.append(Spacer(1, 12))

    # Customer details
    elements.append(Paragraph('Customer Details', styles['SectionTitle']))
    elements.append(Paragraph(f"Name: {context['user'].first_name} {context['user'].last_name}", styles['BodyText']))
    elements.append(Paragraph(f"Email: {context['user'].email}", styles['BodyText']))
    elements.append(Paragraph(f"Address: {context['user'].address}", styles['BodyText']))

    elements.append(Spacer(1, 12))

    # Table of items
    data = [
        ['Description', 'Amount'],
        [context['package'].name, f"${context['amount']:.2f}"]
    ]

    table = Table(data, colWidths=[400, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#04436C')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F3F3F3')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)

    elements.append(Spacer(1, 12))

    # Total
    elements.append(Paragraph(f"Total: ${context['amount']:.2f}", styles['SectionTitle']))

    elements.append(Spacer(1, 20))

    # Horizontal line
    elements.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.HexColor('#04436C'), spaceBefore=1, spaceAfter=1))

    elements.append(Spacer(1, 20))

    # Footer
    elements.append(Paragraph('Thank you for your business!', styles['BodyText']))
    elements.append(Paragraph(f"Regards, {context['site_title']}", styles['BodyText']))
    if context['site_phone']:
        elements.append(Paragraph(f"Phone: {context['site_phone']}", styles['BodyText']))
    if context['site_email']:
        elements.append(Paragraph(f"Email: {context['site_email']}", styles['BodyText']))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    # Save the PDF to a file
    with open("sample_invoice.pdf", "wb") as f:
        f.write(pdf)

    return pdf

# Generate the sample invoice
generate_sample_invoice()
