from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib import colors
from io import BytesIO
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from .models import SiteSettings
import datetime

def send_custom_email(subject, template_name, context, recipient_list, attachment=None):
    message = render_to_string(template_name, context)
    email = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list)
    email.content_subtype = "html"  # Main content is now text/html
    if attachment:
        email.attach(attachment['filename'], attachment['content'], attachment['mimetype'])
    email.send()

def generate_invoice_pdf(context):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()

    # Define or redefine styles only if they don't exist
    if 'InvoiceTitle' not in styles:
        styles.add(ParagraphStyle(name='InvoiceTitle', fontSize=24, leading=30, spaceAfter=20, textColor=colors.HexColor('#04436C'), alignment=1))
    if 'InvoiceDetails' not in styles:
        styles.add(ParagraphStyle(name='InvoiceDetails', fontSize=12, leading=14, spaceAfter=10))
    if 'SectionTitle' not in styles:
        styles.add(ParagraphStyle(name='SectionTitle', fontSize=14, leading=18, spaceAfter=10, textColor=colors.HexColor('#04436C')))
    if 'BodyText' not in styles:
        styles.add(ParagraphStyle(name='BodyText', fontSize=12, leading=14, spaceAfter=10))
    else:
        # Redefine BodyText style without adding it again
        styles['BodyText'].fontSize = 12
        styles['BodyText'].leading = 14
        styles['BodyText'].spaceAfter = 10

    # Add company logo and date
    if context.get('site_logo_url'):
        logo = Image(context['site_logo_url'], width=150, height=50)
        logo.hAlign = 'LEFT'
        elements.append(logo)
    
    elements.append(Spacer(1, 20))
    
    elements.append(Paragraph('INVOICE', styles['InvoiceTitle']))

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
    elements.append(Paragraph(f"Name: {context['first_name']} {context['last_name']}", styles['BodyText']))
    elements.append(Paragraph(f"Email: {context['user'].email}", styles['BodyText']))
    elements.append(Paragraph(f"Address: {context['address']}", styles['BodyText']))

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
    if context.get('site_phone'):
        elements.append(Paragraph(f"Phone: {context['site_phone']}", styles['BodyText']))
    if context.get('site_email'):
        elements.append(Paragraph(f"Email: {context['site_email']}", styles['BodyText']))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    return {
        'filename': f"invoice_{context['invoice_id']}.pdf",
        'content': pdf,
        'mimetype': 'application/pdf'
    }