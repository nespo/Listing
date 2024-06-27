from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from io import BytesIO
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from .models import SiteSettings

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
    styles.add(ParagraphStyle(name='InvoiceTitle', fontSize=18, leading=22, spaceAfter=20))
    styles.add(ParagraphStyle(name='InvoiceDetails', fontSize=12, leading=14, spaceAfter=10))

    # Invoice title
    elements.append(Paragraph('Invoice', styles['InvoiceTitle']))

    # Invoice details
    elements.append(Paragraph(f"Invoice #: {context['invoice_id']}", styles['InvoiceDetails']))
    elements.append(Paragraph(f"Created: {context['invoice_date']}", styles['InvoiceDetails']))

    elements.append(Spacer(1, 12))

    # Customer details
    elements.append(Paragraph(f"Customer: {context['user'].first_name} {context['user'].last_name}", styles['InvoiceDetails']))
    elements.append(Paragraph(f"Email: {context['user'].email}", styles['InvoiceDetails']))

    elements.append(Spacer(1, 12))

    # Company details
    elements.append(Paragraph(f"Company: {context['site_title']}", styles['InvoiceDetails']))
    elements.append(Paragraph(f"Address: {context['site_address']}", styles['InvoiceDetails']))

    elements.append(Spacer(1, 12))

    # Table of items
    data = [
        ['Package', 'Price'],
        [context['package'].name, f"${context['amount']}"]
    ]

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)

    elements.append(Spacer(1, 12))

    # Total
    elements.append(Paragraph(f"Total: ${context['amount']}", styles['InvoiceDetails']))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    return {
        'filename': f"invoice_{context['invoice_id']}.pdf",
        'content': pdf,
        'mimetype': 'application/pdf'
    }

def get_site_settings():
    try:
        return SiteSettings.objects.first()
    except SiteSettings.DoesNotExist:
        return None
