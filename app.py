# app.py - Complete Invoice Generator Application
import warnings
warnings.filterwarnings('ignore')

from flask import Flask, render_template_string, redirect, url_for, flash, request, send_file, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import secrets
import re
import io
import logging
import uuid

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not available, using default configuration")

# Flask Configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///invoices.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = 3600
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Windows-friendly cookie settings
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)

# Rate limiting setup (with better error handling)
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["1000 per day", "200 per hour"],
        headers_enabled=True
    )
    print("✅ Rate limiting enabled")
except ImportError:
    # Mock limiter when flask-limiter is not available
    class MockLimiter:
        def limit(self, limit_string):
            def decorator(f):
                return f
            return decorator
    limiter = MockLimiter()
    print("⚠️  Rate limiting disabled (Flask-Limiter not available)")
except Exception as e:
    # Mock limiter for any other rate limiting errors
    class MockLimiter:
        def limit(self, limit_string):
            def decorator(f):
                return f
            return decorator
    limiter = MockLimiter()
    print(f"⚠️  Rate limiting disabled due to error: {e}")

# Logging configuration
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Check for PDF libraries
PDF_AVAILABLE = False
PDF_METHOD = None

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocumentTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    PDF_AVAILABLE = True
    PDF_METHOD = "reportlab"
    print("✅ ReportLab available - PDF generation enabled")
except ImportError:
    print("⚠️  ReportLab not available - PDF generation disabled")

# Input validation helpers
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def sanitize_input(text, max_length=None):
    if text is None:
        return ""
    text = str(text).strip()
    if max_length:
        text = text[:max_length]
    text = re.sub(r'[<>"\']', '', text)
    return text

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    company_name = db.Column(db.String(200))
    default_currency = db.Column(db.String(3), default='USD')
    is_premium = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    failed_login_attempts = db.Column(db.Integer, default=0)
    last_login_attempt = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    invoices = db.relationship('Invoice', backref='user', lazy=True)

    def set_password(self, password):
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Invoice(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    invoice_number = db.Column(db.String(50), nullable=False)
    client_name = db.Column(db.String(200), nullable=False)
    client_email = db.Column(db.String(120))
    client_address = db.Column(db.Text)
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    subtotal = db.Column(db.Float, default=0.0)
    tax_rate = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade='all, delete-orphan')

    def get_currency_symbol(self):
        currency_symbols = {
            'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 'CAD': 'C$',
            'AUD': 'A$', 'CHF': 'CHF', 'CNY': '¥', 'INR': '₹', 'BRL': 'R$'
        }
        return currency_symbols.get(self.currency, self.currency)

    def format_amount(self, amount):
        symbol = self.get_currency_symbol()
        if self.currency in ['JPY', 'KRW']:
            return f"{symbol}{int(amount):,}"
        return f"{symbol}{amount:,.2f}"

class InvoiceItem(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = db.Column(db.String(36), db.ForeignKey('invoice.id'), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Float, default=1.0)
    rate = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# Currency Helper Functions
def get_supported_currencies():
    return {
        'USD': {'name': 'US Dollar', 'symbol': '$', 'code': 'USD'},
        'EUR': {'name': 'Euro', 'symbol': '€', 'code': 'EUR'},
        'GBP': {'name': 'British Pound', 'symbol': '£', 'code': 'GBP'},
        'JPY': {'name': 'Japanese Yen', 'symbol': '¥', 'code': 'JPY'},
        'CAD': {'name': 'Canadian Dollar', 'symbol': 'C$', 'code': 'CAD'},
        'AUD': {'name': 'Australian Dollar', 'symbol': 'A$', 'code': 'AUD'},
        'CHF': {'name': 'Swiss Franc', 'symbol': 'CHF', 'code': 'CHF'},
        'CNY': {'name': 'Chinese Yuan', 'symbol': '¥', 'code': 'CNY'},
        'INR': {'name': 'Indian Rupee', 'symbol': '₹', 'code': 'INR'},
        'BRL': {'name': 'Brazilian Real', 'symbol': 'R$', 'code': 'BRL'}
    }

# PDF Generation
def generate_pdf(invoice):
    if not PDF_AVAILABLE:
        raise Exception("PDF generation not available - ReportLab not installed")
    
    try:
        buffer = io.BytesIO()
        doc = SimpleDocumentTemplate(buffer, pagesize=A4)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30
        )
        
        story = []
        
        # Header
        story.append(Paragraph("INVOICE", title_style))
        story.append(Spacer(1, 20))
        
        # Invoice details
        story.append(Paragraph(f"<b>Invoice #:</b> {invoice.invoice_number}", styles['Normal']))
        story.append(Paragraph(f"<b>Date:</b> {invoice.issue_date.strftime('%B %d, %Y')}", styles['Normal']))
        story.append(Paragraph(f"<b>Due Date:</b> {invoice.due_date.strftime('%B %d, %Y')}", styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Client info
        story.append(Paragraph(f"<b>Bill To:</b>", styles['Heading2']))
        story.append(Paragraph(sanitize_input(invoice.client_name, 200), styles['Normal']))
        if invoice.client_email:
            story.append(Paragraph(sanitize_input(invoice.client_email, 120), styles['Normal']))
        if invoice.client_address:
            story.append(Paragraph(sanitize_input(invoice.client_address, 500), styles['Normal']))
        
        story.append(Spacer(1, 30))
        
        # Items table
        item_data = [['Description', 'Qty', 'Rate', 'Amount']]
        for item in invoice.items:
            item_data.append([
                sanitize_input(item.description, 500),
                str(item.quantity),
                f"${item.rate:.2f}",
                f"${item.amount:.2f}"
            ])
        
        items_table = Table(item_data)
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(items_table)
        story.append(Spacer(1, 20))
        
        # Totals
        story.append(Paragraph(f"<b>Subtotal:</b> ${invoice.subtotal:.2f}", styles['Normal']))
        story.append(Paragraph(f"<b>Tax ({invoice.tax_rate}%):</b> ${invoice.tax_amount:.2f}", styles['Normal']))
        story.append(Paragraph(f"<b>Total:</b> ${invoice.total:.2f}", styles['Heading2']))
        
        if invoice.notes:
            story.append(Spacer(1, 30))
            story.append(Paragraph("<b>Notes:</b>", styles['Heading3']))
            story.append(Paragraph(sanitize_input(invoice.notes, 1000), styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        app.logger.error(f"PDF generation error: {str(e)}")
        raise

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template_string(INDEX_TEMPLATE)

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    if request.method == 'POST':
        try:
            email = sanitize_input(request.form.get('email', ''), 120).lower()
            password = request.form.get('password', '')
            company_name = sanitize_input(request.form.get('company_name', ''), 200)
            
            if not validate_email(email):
                flash('Invalid email address.', 'error')
                return render_template_string(REGISTER_TEMPLATE, currencies=get_supported_currencies())
            
            if len(password) < 8:
                flash('Password must be at least 8 characters long.', 'error')
                return render_template_string(REGISTER_TEMPLATE, currencies=get_supported_currencies())
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered.', 'error')
                return render_template_string(REGISTER_TEMPLATE, currencies=get_supported_currencies())
            
            user = User(
                email=email,
                company_name=company_name,
                default_currency='USD'
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            login_user(user)
            session.permanent = True
            app.logger.info(f'New user registered: {email}')
            flash('Registration successful!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Registration error: {str(e)}')
            flash('Registration failed. Please try again.', 'error')
    
    return render_template_string(REGISTER_TEMPLATE, currencies=get_supported_currencies())

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        try:
            email = sanitize_input(request.form.get('email', ''), 120).lower()
            password = request.form.get('password', '')
            
            if not email or not password:
                flash('Email and password are required.', 'error')
                return render_template_string(LOGIN_TEMPLATE)
            
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password) and user.is_active:
                login_user(user, remember=True)
                session.permanent = True
                app.logger.info(f'User logged in: {email}')
                
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            else:
                app.logger.warning(f'Failed login attempt for: {email}')
                flash('Invalid email or password.', 'error')
                
        except Exception as e:
            app.logger.error(f'Login error: {str(e)}')
            flash('Login failed. Please try again.', 'error')
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
@login_required
def logout():
    app.logger.info(f'User logged out: {current_user.email}')
    logout_user()
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        invoices = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.created_at.desc()).all()
        return render_template_string(DASHBOARD_TEMPLATE, invoices=invoices, current_user=current_user)
    except Exception as e:
        app.logger.error(f'Dashboard error: {str(e)}')
        flash('Error loading dashboard.', 'error')
        return redirect(url_for('index'))

@app.route('/create-invoice', methods=['GET', 'POST'])
@login_required
@limiter.limit("20 per hour")
def create_invoice():
    try:
        if request.method == 'POST':
            # Validate and sanitize inputs
            invoice_number = sanitize_input(request.form.get('invoice_number', ''), 50)
            client_name = sanitize_input(request.form.get('client_name', ''), 200)
            client_email = sanitize_input(request.form.get('client_email', ''), 120)
            client_address = sanitize_input(request.form.get('client_address', ''), 500)
            notes = sanitize_input(request.form.get('notes', ''), 1000)
            
            if not invoice_number or not client_name:
                flash('Invoice number and client name are required.', 'error')
                return redirect(url_for('create_invoice'))
            
            try:
                issue_date = datetime.strptime(request.form['issue_date'], '%Y-%m-%d').date()
                due_date = datetime.strptime(request.form['due_date'], '%Y-%m-%d').date()
                tax_rate = float(request.form.get('tax_rate', 0))
            except (ValueError, TypeError):
                flash('Invalid date or tax rate format.', 'error')
                return redirect(url_for('create_invoice'))
            
            # Create invoice
            invoice = Invoice(
                user_id=current_user.id,
                invoice_number=invoice_number,
                client_name=client_name,
                client_email=client_email,
                client_address=client_address,
                issue_date=issue_date,
                due_date=due_date,
                currency='USD',
                tax_rate=tax_rate,
                notes=notes
            )
            
            db.session.add(invoice)
            db.session.flush()
            
            # Add items
            descriptions = request.form.getlist('description[]')
            quantities = request.form.getlist('quantity[]')
            rates = request.form.getlist('rate[]')
            
            subtotal = 0
            for i in range(len(descriptions)):
                if descriptions[i].strip():
                    try:
                        description = sanitize_input(descriptions[i], 500)
                        quantity = float(quantities[i])
                        rate = float(rates[i])
                        amount = quantity * rate
                        
                        item = InvoiceItem(
                            invoice_id=invoice.id,
                            description=description,
                            quantity=quantity,
                            rate=rate,
                            amount=amount
                        )
                        db.session.add(item)
                        subtotal += amount
                        
                    except (ValueError, TypeError):
                        flash('Invalid quantity or rate values.', 'error')
                        db.session.rollback()
                        return redirect(url_for('create_invoice'))
            
            # Calculate totals
            invoice.subtotal = subtotal
            invoice.tax_amount = subtotal * (tax_rate / 100)
            invoice.total = subtotal + invoice.tax_amount
            
            db.session.commit()
            app.logger.info(f'Invoice created: {invoice_number} by {current_user.email}')
            flash('Invoice created successfully!', 'success')
            return redirect(url_for('view_invoice', invoice_id=invoice.id))
        
        # Generate next invoice number
        invoice_count = Invoice.query.filter_by(user_id=current_user.id).count()
        next_number = f"INV-{invoice_count + 1:04d}"
        
        return render_template_string(CREATE_INVOICE_TEMPLATE, next_number=next_number)
                             
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Create invoice error: {str(e)}')
        flash('Error creating invoice.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/invoice/<invoice_id>')
@login_required
def view_invoice(invoice_id):
    try:
        invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first()
        if not invoice:
            flash('Invoice not found.', 'error')
            return redirect(url_for('dashboard'))
        return render_template_string(VIEW_INVOICE_TEMPLATE, invoice=invoice)
    except Exception as e:
        app.logger.error(f'View invoice error: {str(e)}')
        flash('Invoice not found.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/invoice/<invoice_id>/pdf')
@login_required
@limiter.limit("30 per hour")
def download_pdf(invoice_id):
    try:
        if not PDF_AVAILABLE:
            flash('PDF generation not available. Please install ReportLab.', 'error')
            return redirect(url_for('view_invoice', invoice_id=invoice_id))
            
        invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first()
        if not invoice:
            flash('Invoice not found.', 'error')
            return redirect(url_for('dashboard'))
            
        pdf_buffer = generate_pdf(invoice)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'invoice_{invoice.invoice_number}.pdf'
        )
    except Exception as e:
        app.logger.error(f'PDF download error: {str(e)}')
        flash('Error generating PDF.', 'error')
        return redirect(url_for('view_invoice', invoice_id=invoice_id))

# Database initialization
def init_db():
    """Initialize database and create admin user"""
    try:
        with app.app_context():
            db.create_all()
            
            # Create admin user if not exists
            admin = User.query.filter_by(email='admin@invoicegen.com').first()
            if not admin:
                admin = User(
                    email='admin@invoicegen.com',
                    company_name='Admin Company',
                    default_currency='USD'
                )
                admin.set_password('SecureAdmin123!')
                admin.is_premium = True
                db.session.add(admin)
                db.session.commit()
                print("✅ Admin user created: admin@invoicegen.com / SecureAdmin123!")
            else:
                print("✅ Admin user already exists")
                
            # Create test user if not exists
            test_user = User.query.filter_by(email='test@example.com').first()
            if not test_user:
                test_user = User(
                    email='test@example.com',
                    company_name='Test Company',
                    default_currency='USD'
                )
                test_user.set_password('test1234')
                db.session.add(test_user)
                db.session.commit()
                print("✅ Test user created: test@example.com / test1234")
            
            return True
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return False

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template_string(ERROR_404_TEMPLATE), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template_string(ERROR_500_TEMPLATE), 500

# Embedded Templates (so we don't need external template files)
BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Invoice Generator{% endblock %}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: #f8fafc; color: #1a202c; line-height: 1.6; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .card { background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); 
                border: 1px solid #e2e8f0; overflow: hidden; }
        .card-header { padding: 20px; border-bottom: 1px solid #e2e8f0; background: #f7fafc; }
        .card-body { padding: 20px; }
        .btn { display: inline-block; padding: 12px 24px; border-radius: 6px; text-decoration: none; 
               font-weight: 500; border: none; cursor: pointer; transition: all 0.2s; }
        .btn-primary { background: #3182ce; color: white; }
        .btn-primary:hover { background: #2c5aa0; }
        .btn-secondary { background: #718096; color: white; }
        .btn-success { background: #38a169; color: white; }
        .btn-danger { background: #e53e3e; color: white; }
        .form-group { margin-bottom: 20px; }
        .form-label { display: block; margin-bottom: 8px; font-weight: 500; color: #2d3748; }
        .form-input { width: 100%; padding: 12px; border: 1px solid #cbd5e0; border-radius: 6px; 
                      font-size: 16px; transition: border-color 0.2s; }
        .form-input:focus { outline: none; border-color: #3182ce; box-shadow: 0 0 0 3px rgba(49,130,206,0.1); }
        .alert { padding: 16px; border-radius: 6px; margin-bottom: 20px; }
        .alert-success { background: #c6f6d5; color: #22543d; border: 1px solid #9ae6b4; }
        .alert-error { background: #fed7d7; color: #742a2a; border: 1px solid #fc8181; }
        .alert-warning { background: #faf5ff; color: #553c9a; border: 1px solid #d6bcfa; }
        .navbar { background: white; border-bottom: 1px solid #e2e8f0; padding: 16px 0; margin-bottom: 32px; }
        .navbar .container { display: flex; justify-content: space-between; align-items: center; }
        .navbar-brand { font-size: 24px; font-weight: bold; color: #3182ce; text-decoration: none; }
        .navbar-nav { display: flex; gap: 16px; align-items: center; }
        .table { width: 100%; border-collapse: collapse; }
        .table th, .table td { padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }
        .table th { background: #f7fafc; font-weight: 600; }
        .status-badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 500; }
        .status-draft { background: #e2e8f0; color: #4a5568; }
        .status-sent { background: #bee3f8; color: #2c5aa0; }
        .status-paid { background: #c6f6d5; color: #22543d; }
        .grid { display: grid; gap: 20px; }
        .grid-2 { grid-template-columns: 1fr 1fr; }
        .text-center { text-align: center; }
        .text-right { text-align: right; }
        .mb-4 { margin-bottom: 16px; }
        .mt-4 { margin-top: 16px; }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="container">
            <a href="{{ url_for('index') }}" class="navbar-brand">🧾 InvoiceGen</a>
            <div class="navbar-nav">
                {% if current_user.is_authenticated %}
                    <a href="{{ url_for('dashboard') }}" class="btn btn-secondary">Dashboard</a>
                    <a href="{{ url_for('create_invoice') }}" class="btn btn-primary">New Invoice</a>
                    <a href="{{ url_for('logout') }}" class="btn btn-secondary">Logout</a>
                {% else %}
                    <a href="{{ url_for('login') }}" class="btn btn-secondary">Login</a>
                    <a href="{{ url_for('register') }}" class="btn btn-primary">Sign Up</a>
                {% endif %}
            </div>
        </div>
    </nav>

    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

INDEX_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div class="text-center">
    <h1 style="font-size: 48px; margin-bottom: 24px; color: #2d3748;">
        Professional Invoice Generation
        <span style="color: #3182ce;">Made Simple</span>
    </h1>
    <p style="font-size: 20px; color: #718096; margin-bottom: 48px; max-width: 600px; margin-left: auto; margin-right: auto;">
        Create beautiful, professional invoices in minutes. Track your billing, manage clients, and get paid faster.
    </p>
    
    <div style="margin-bottom: 64px;">
        <a href="{{ url_for('register') }}" class="btn btn-primary" style="font-size: 18px; padding: 16px 32px; margin-right: 16px;">
            Get Started Free
        </a>
        <a href="{{ url_for('login') }}" class="btn btn-secondary" style="font-size: 18px; padding: 16px 32px;">
            Sign In
        </a>
    </div>

    <div class="grid grid-2" style="max-width: 800px; margin: 0 auto;">
        <div class="card">
            <div class="card-body text-center">
                <div style="font-size: 48px; margin-bottom: 16px;">📄</div>
                <h3 style="margin-bottom: 16px;">Professional Templates</h3>
                <p style="color: #718096;">Choose from beautifully designed templates that make your business look professional.</p>
            </div>
        </div>
        
        <div class="card">
            <div class="card-body text-center">
                <div style="font-size: 48px; margin-bottom: 16px;">💰</div>
                <h3 style="margin-bottom: 16px;">Easy Management</h3>
                <p style="color: #718096;">Track invoices, manage clients, and monitor payments all in one place.</p>
            </div>
        </div>
    </div>
</div>
{% endblock %}
''')

LOGIN_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div style="max-width: 400px; margin: 0 auto;">
    <div class="card">
        <div class="card-header text-center">
            <h2>Welcome Back</h2>
            <p style="color: #718096; margin-top: 8px;">Sign in to your account</p>
        </div>
        <div class="card-body">
            <form method="POST">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                
                <div class="form-group">
                    <label class="form-label">Email Address</label>
                    <input type="email" name="email" class="form-input" placeholder="your@email.com" required>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Password</label>
                    <input type="password" name="password" class="form-input" placeholder="Enter your password" required>
                </div>
                
                <button type="submit" class="btn btn-primary" style="width: 100%;">Sign In</button>
            </form>
            
            <div class="text-center mt-4">
                <p style="color: #718096;">Don't have an account? 
                    <a href="{{ url_for('register') }}" style="color: #3182ce;">Create one</a>
                </p>
            </div>
        </div>
    </div>
</div>
{% endblock %}
''')
# LOGIN_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
# {% block content %}
# <div style="max-width: 400px; margin: 0 auto;">
#     <div class="card">
#         <div class="card-header text-center">
#             <h2>Welcome Back</h2>
#             <p style="color: #718096; margin-top: 8px;">Sign in to your account</p>
#         </div>
#         <div class="card-body">
#             <form method="POST">
#                 <div class="form-group">
#                     <label class="form-label">Email Address</label>
#                     <input type="email" name="email" class="form-input" placeholder="your@email.com" required>
#                 </div>
                
#                 <div class="form-group">
#                     <label class="form-label">Password</label>
#                     <input type="password" name="password" class="form-input" placeholder="Enter your password" required>
#                 </div>
                
#                 <button type="submit" class="btn btn-primary" style="width: 100%;">Sign In</button>
#             </form>
            
#             <div class="text-center mt-4">
#                 <p style="color: #718096;">Don't have an account? 
#                     <a href="{{ url_for('register') }}" style="color: #3182ce;">Create one</a>
#                 </p>
#             </div>
#         </div>
#     </div>
# </div>
# {% endblock %}
# ''')

REGISTER_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div style="max-width: 400px; margin: 0 auto;">
    <div class="card">
        <div class="card-header text-center">
            <h2>Create Account</h2>
            <p style="color: #718096; margin-top: 8px;">Start generating professional invoices today</p>
        </div>
        <div class="card-body">
            <form method="POST">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                
                <div class="form-group">
                    <label class="form-label">Email Address</label>
                    <input type="email" name="email" class="form-input" placeholder="your@email.com" required>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Company Name (Optional)</label>
                    <input type="text" name="company_name" class="form-input" placeholder="Your Company Name">
                </div>
                
                <div class="form-group">
                    <label class="form-label">Password</label>
                    <input type="password" name="password" class="form-input" placeholder="Choose a strong password" required>
                </div>
                
                <button type="submit" class="btn btn-primary" style="width: 100%;">Create Account</button>
            </form>
            
            <div class="text-center mt-4">
                <p style="color: #718096;">Already have an account? 
                    <a href="{{ url_for('login') }}" style="color: #3182ce;">Sign in</a>
                </p>
            </div>
        </div>
    </div>
</div>
{% endblock %}
''')
# REGISTER_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
# {% block content %}
# <div style="max-width: 400px; margin: 0 auto;">
#     <div class="card">
#         <div class="card-header text-center">
#             <h2>Create Account</h2>
#             <p style="color: #718096; margin-top: 8px;">Start generating professional invoices today</p>
#         </div>
#         <div class="card-body">
#             <form method="POST">
#                 <div class="form-group">
#                     <label class="form-label">Email Address</label>
#                     <input type="email" name="email" class="form-input" placeholder="your@email.com" required>
#                 </div>
                
#                 <div class="form-group">
#                     <label class="form-label">Company Name (Optional)</label>
#                     <input type="text" name="company_name" class="form-input" placeholder="Your Company Name">
#                 </div>
                
#                 <div class="form-group">
#                     <label class="form-label">Password</label>
#                     <input type="password" name="password" class="form-input" placeholder="Choose a strong password" required>
#                 </div>
                
#                 <button type="submit" class="btn btn-primary" style="width: 100%;">Create Account</button>
#             </form>
            
#             <div class="text-center mt-4">
#                 <p style="color: #718096;">Already have an account? 
#                     <a href="{{ url_for('login') }}" style="color: #3182ce;">Sign in</a>
#                 </p>
#             </div>
#         </div>
#     </div>
# </div>
# {% endblock %}
# ''')

DASHBOARD_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px;">
    <div>
        <h1>Dashboard</h1>
        <p style="color: #718096; margin-top: 8px;">{{ invoices|length }} invoices created</p>
    </div>
    <a href="{{ url_for('create_invoice') }}" class="btn btn-primary">+ New Invoice</a>
</div>

<div class="card">
    <div class="card-header">
        <h2>Recent Invoices</h2>
    </div>
    <div class="card-body">
        {% if invoices %}
            <table class="table">
                <thead>
                    <tr>
                        <th>Invoice #</th>
                        <th>Client</th>
                        <th>Date</th>
                        <th>Amount</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for invoice in invoices %}
                    <tr>
                        <td>{{ invoice.invoice_number }}</td>
                        <td>{{ invoice.client_name }}</td>
                        <td>{{ invoice.issue_date.strftime('%b %d, %Y') }}</td>
                        <td>${{ "%.2f"|format(invoice.total) }}</td>
                        <td><span class="status-badge status-{{ invoice.status }}">{{ invoice.status.title() }}</span></td>
                        <td>
                            <a href="{{ url_for('view_invoice', invoice_id=invoice.id) }}" class="btn btn-secondary" style="padding: 6px 12px; font-size: 14px;">View</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% else %}
            <div class="text-center" style="padding: 64px 0;">
                <div style="font-size: 64px; margin-bottom: 24px; opacity: 0.5;">📄</div>
                <h3 style="margin-bottom: 16px;">No invoices yet</h3>
                <p style="color: #718096; margin-bottom: 24px;">Get started by creating your first invoice</p>
                <a href="{{ url_for('create_invoice') }}" class="btn btn-primary">Create Invoice</a>
            </div>
        {% endif %}
    </div>
</div>
{% endblock %}
''')

CREATE_INVOICE_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px;">
    <h1>Create New Invoice</h1>
    <a href="{{ url_for('dashboard') }}" class="btn btn-secondary">← Back to Dashboard</a>
</div>

<form method="POST">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
    
    <div class="grid grid-2">
        <!-- Rest of the form stays the same -->
        <div class="card">
            <div class="card-header">
                <h3>Invoice Details</h3>
            </div>
            <div class="card-body">
                <div class="form-group">
                    <label class="form-label">Invoice Number</label>
                    <input type="text" name="invoice_number" class="form-input" value="{{ next_number }}" required>
                </div>
                
                <div class="grid grid-2">
                    <div class="form-group">
                        <label class="form-label">Issue Date</label>
                        <input type="date" name="issue_date" class="form-input" required>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Due Date</label>
                        <input type="date" name="due_date" class="form-input" required>
                    </div>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Tax Rate (%)</label>
                    <input type="number" name="tax_rate" class="form-input" value="0" step="0.01" min="0" max="100">
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <h3>Client Information</h3>
            </div>
            <div class="card-body">
                <div class="form-group">
                    <label class="form-label">Client Name</label>
                    <input type="text" name="client_name" class="form-input" placeholder="Enter client or company name" required>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Client Email</label>
                    <input type="email" name="client_email" class="form-input" placeholder="client@example.com">
                </div>
                
                <div class="form-group">
                    <label class="form-label">Client Address</label>
                    <textarea name="client_address" class="form-input" rows="4" placeholder="Street Address, City, State ZIP, Country"></textarea>
                </div>
            </div>
        </div>
    </div>

    <div class="card mt-4">
        <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
            <h3>Invoice Items</h3>
            <button type="button" class="btn btn-success" onclick="addItem()">+ Add Item</button>
        </div>
        <div class="card-body">
            <div id="items-container">
                <div class="item-row" style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr auto; gap: 12px; align-items: end; margin-bottom: 16px;">
                    <div class="form-group">
                        <label class="form-label">Description</label>
                        <input type="text" name="description[]" class="form-input" placeholder="What did you provide?" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Quantity</label>
                        <input type="number" name="quantity[]" class="form-input" value="1" step="0.01" min="0" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Rate ($)</label>
                        <input type="number" name="rate[]" class="form-input" step="0.01" min="0" placeholder="0.00" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Amount</label>
                        <input type="text" class="form-input" readonly style="background: #f7fafc;">
                    </div>
                    <div style="padding-top: 32px;">
                        <button type="button" class="btn btn-danger" onclick="removeItem(this)" style="padding: 12px;">×</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="card mt-4">
        <div class="card-header">
            <h3>Additional Notes</h3>
        </div>
        <div class="card-body">
            <div class="form-group">
                <label class="form-label">Notes (Optional)</label>
                <textarea name="notes" class="form-input" rows="4" placeholder="Payment terms, thank you message, or any other details..."></textarea>
            </div>
        </div>
    </div>

    <div style="display: flex; gap: 16px; justify-content: flex-end; margin-top: 32px;">
        <a href="{{ url_for('dashboard') }}" class="btn btn-secondary">Cancel</a>
        <button type="submit" class="btn btn-primary">Create Invoice</button>
    </div>
</form>

<script>
// Set default dates
document.addEventListener('DOMContentLoaded', function() {
    const today = new Date();
    const dueDate = new Date(today);
    dueDate.setDate(dueDate.getDate() + 30);
    
    document.querySelector('input[name="issue_date"]').value = today.toISOString().split('T')[0];
    document.querySelector('input[name="due_date"]').value = dueDate.toISOString().split('T')[0];
});

function addItem() {
    const container = document.getElementById('items-container');
    const firstItem = container.querySelector('.item-row');
    const newItem = firstItem.cloneNode(true);
    
    // Clear values
    newItem.querySelectorAll('input').forEach(input => {
        if (input.name === 'quantity[]') {
            input.value = '1';
        } else if (input.type !== 'button') {
            input.value = '';
        }
    });
    
    container.appendChild(newItem);
}

function removeItem(button) {
    const container = document.getElementById('items-container');
    if (container.children.length > 1) {
        button.closest('.item-row').remove();
    }
}
</script>
{% endblock %}
''')

# CREATE_INVOICE_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
# {% block content %}
# <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px;">
#     <h1>Create New Invoice</h1>
#     <a href="{{ url_for('dashboard') }}" class="btn btn-secondary">← Back to Dashboard</a>
# </div>

# <form method="POST">
#     <div class="grid grid-2">
#         <div class="card">
#             <div class="card-header">
#                 <h3>Invoice Details</h3>
#             </div>
#             <div class="card-body">
#                 <div class="form-group">
#                     <label class="form-label">Invoice Number</label>
#                     <input type="text" name="invoice_number" class="form-input" value="{{ next_number }}" required>
#                 </div>
                
#                 <div class="grid grid-2">
#                     <div class="form-group">
#                         <label class="form-label">Issue Date</label>
#                         <input type="date" name="issue_date" class="form-input" required>
#                     </div>
                    
#                     <div class="form-group">
#                         <label class="form-label">Due Date</label>
#                         <input type="date" name="due_date" class="form-input" required>
#                     </div>
#                 </div>
                
#                 <div class="form-group">
#                     <label class="form-label">Tax Rate (%)</label>
#                     <input type="number" name="tax_rate" class="form-input" value="0" step="0.01" min="0" max="100">
#                 </div>
#             </div>
#         </div>

#         <div class="card">
#             <div class="card-header">
#                 <h3>Client Information</h3>
#             </div>
#             <div class="card-body">
#                 <div class="form-group">
#                     <label class="form-label">Client Name</label>
#                     <input type="text" name="client_name" class="form-input" placeholder="Enter client or company name" required>
#                 </div>
                
#                 <div class="form-group">
#                     <label class="form-label">Client Email</label>
#                     <input type="email" name="client_email" class="form-input" placeholder="client@example.com">
#                 </div>
                
#                 <div class="form-group">
#                     <label class="form-label">Client Address</label>
#                     <textarea name="client_address" class="form-input" rows="4" placeholder="Street Address, City, State ZIP, Country"></textarea>
#                 </div>
#             </div>
#         </div>
#     </div>

#     <div class="card mt-4">
#         <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
#             <h3>Invoice Items</h3>
#             <button type="button" class="btn btn-success" onclick="addItem()">+ Add Item</button>
#         </div>
#         <div class="card-body">
#             <div id="items-container">
#                 <div class="item-row" style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr auto; gap: 12px; align-items: end; margin-bottom: 16px;">
#                     <div class="form-group">
#                         <label class="form-label">Description</label>
#                         <input type="text" name="description[]" class="form-input" placeholder="What did you provide?" required>
#                     </div>
#                     <div class="form-group">
#                         <label class="form-label">Quantity</label>
#                         <input type="number" name="quantity[]" class="form-input" value="1" step="0.01" min="0" required>
#                     </div>
#                     <div class="form-group">
#                         <label class="form-label">Rate ($)</label>
#                         <input type="number" name="rate[]" class="form-input" step="0.01" min="0" placeholder="0.00" required>
#                     </div>
#                     <div class="form-group">
#                         <label class="form-label">Amount</label>
#                         <input type="text" class="form-input" readonly style="background: #f7fafc;">
#                     </div>
#                     <div style="padding-top: 32px;">
#                         <button type="button" class="btn btn-danger" onclick="removeItem(this)" style="padding: 12px;">×</button>
#                     </div>
#                 </div>
#             </div>
#         </div>
#     </div>

#     <div class="card mt-4">
#         <div class="card-header">
#             <h3>Additional Notes</h3>
#         </div>
#         <div class="card-body">
#             <div class="form-group">
#                 <label class="form-label">Notes (Optional)</label>
#                 <textarea name="notes" class="form-input" rows="4" placeholder="Payment terms, thank you message, or any other details..."></textarea>
#             </div>
#         </div>
#     </div>

#     <div style="display: flex; gap: 16px; justify-content: flex-end; margin-top: 32px;">
#         <a href="{{ url_for('dashboard') }}" class="btn btn-secondary">Cancel</a>
#         <button type="submit" class="btn btn-primary">Create Invoice</button>
#     </div>
# </form>

# <script>
# // Set default dates
# document.addEventListener('DOMContentLoaded', function() {
#     const today = new Date();
#     const dueDate = new Date(today);
#     dueDate.setDate(dueDate.getDate() + 30);
    
#     document.querySelector('input[name="issue_date"]').value = today.toISOString().split('T')[0];
#     document.querySelector('input[name="due_date"]').value = dueDate.toISOString().split('T')[0];
# });

# function addItem() {
#     const container = document.getElementById('items-container');
#     const firstItem = container.querySelector('.item-row');
#     const newItem = firstItem.cloneNode(true);
    
#     // Clear values
#     newItem.querySelectorAll('input').forEach(input => {
#         if (input.name === 'quantity[]') {
#             input.value = '1';
#         } else if (input.type !== 'button') {
#             input.value = '';
#         }
#     });
    
#     container.appendChild(newItem);
# }

# function removeItem(button) {
#     const container = document.getElementById('items-container');
#     if (container.children.length > 1) {
#         button.closest('.item-row').remove();
#     }
# }
# </script>
# {% endblock %}
# ''')

VIEW_INVOICE_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px;">
    <div>
        <h1>Invoice {{ invoice.invoice_number }}</h1>
        <p style="color: #718096; margin-top: 8px;">Created {{ invoice.created_at.strftime('%B %d, %Y') }}</p>
    </div>
    <div style="display: flex; gap: 12px;">
        <a href="{{ url_for('dashboard') }}" class="btn btn-secondary">← Back to Dashboard</a>
        {% if PDF_AVAILABLE %}
        <a href="{{ url_for('download_pdf', invoice_id=invoice.id) }}" class="btn btn-primary">📄 Download PDF</a>
        {% endif %}
    </div>
</div>

<div class="card">
    <div class="card-body">
        <div style="text-align: center; margin-bottom: 48px;">
            <h2 style="color: #3182ce; font-size: 36px; margin-bottom: 16px;">INVOICE</h2>
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div style="text-align: left;">
                    <p><strong>Invoice #:</strong> {{ invoice.invoice_number }}</p>
                    <p><strong>Date:</strong> {{ invoice.issue_date.strftime('%B %d, %Y') }}</p>
                    <p><strong>Due Date:</strong> {{ invoice.due_date.strftime('%B %d, %Y') }}</p>
                </div>
                <div>
                    <span class="status-badge status-{{ invoice.status }}" style="font-size: 16px; padding: 8px 16px;">
                        {{ invoice.status.upper() }}
                    </span>
                </div>
            </div>
        </div>

        <div style="margin-bottom: 48px;">
            <h3 style="margin-bottom: 16px;">Bill To:</h3>
            <div style="background: #f7fafc; padding: 20px; border-radius: 8px;">
                <p style="font-weight: 600; margin-bottom: 8px;">{{ invoice.client_name }}</p>
                {% if invoice.client_email %}
                    <p style="color: #718096;">{{ invoice.client_email }}</p>
                {% endif %}
                {% if invoice.client_address %}
                    <p style="color: #718096; white-space: pre-line;">{{ invoice.client_address }}</p>
                {% endif %}
            </div>
        </div>

        <table class="table" style="margin-bottom: 48px;">
            <thead>
                <tr>
                    <th>Description</th>
                    <th class="text-right" style="width: 80px;">Qty</th>
                    <th class="text-right" style="width: 100px;">Rate</th>
                    <th class="text-right" style="width: 100px;">Amount</th>
                </tr>
            </thead>
            <tbody>
                {% for item in invoice.items %}
                <tr>
                    <td>{{ item.description }}</td>
                    <td class="text-right">{{ item.quantity }}</td>
                    <td class="text-right">${{ "%.2f"|format(item.rate) }}</td>
                    <td class="text-right">${{ "%.2f"|format(item.amount) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <div style="display: flex; justify-content: flex-end;">
            <div style="width: 300px;">
                <div style="display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #e2e8f0;">
                    <span>Subtotal:</span>
                    <span>${{ "%.2f"|format(invoice.subtotal) }}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #e2e8f0;">
                    <span>Tax ({{ invoice.tax_rate }}%):</span>
                    <span>${{ "%.2f"|format(invoice.tax_amount) }}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 16px 0; border-top: 2px solid #2d3748; font-weight: bold; font-size: 20px;">
                    <span>Total:</span>
                    <span style="color: #3182ce;">${{ "%.2f"|format(invoice.total) }}</span>
                </div>
            </div>
        </div>

        {% if invoice.notes %}
        <div style="border-top: 1px solid #e2e8f0; padding-top: 32px; margin-top: 48px;">
            <h3 style="margin-bottom: 16px;">Notes:</h3>
            <p style="color: #718096; white-space: pre-line;">{{ invoice.notes }}</p>
        </div>
        {% endif %}
    </div>
</div>
{% endblock %}
''')

ERROR_404_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div class="text-center" style="padding: 64px 0;">
    <div style="font-size: 96px; margin-bottom: 32px; opacity: 0.5;">❓</div>
    <h1 style="font-size: 48px; margin-bottom: 16px;">Page Not Found</h1>
    <p style="color: #718096; margin-bottom: 32px;">The page you're looking for doesn't exist or has been moved.</p>
    <a href="{{ url_for('index') }}" class="btn btn-primary">Go Home</a>
</div>
{% endblock %}
''')

ERROR_500_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div class="text-center" style="padding: 64px 0;">
    <div style="font-size: 96px; margin-bottom: 32px; opacity: 0.5;">⚠️</div>
    <h1 style="font-size: 48px; margin-bottom: 16px;">Server Error</h1>
    <p style="color: #718096; margin-bottom: 32px;">Something went wrong on our end. Please try again later.</p>
    <a href="{{ url_for('index') }}" class="btn btn-primary">Go Home</a>
</div>
{% endblock %}
''')

# Main execution
if __name__ == '__main__':
    print('='*60)
    print('🧾 INVOICE GENERATOR STARTING')
    print('='*60)
    
    # Initialize database
    if not init_db():
        print("❌ Failed to initialize database. Exiting.")
        exit(1)
    
    print(f'📱 Application: http://localhost:5000')
    print(f'🔑 Admin Login: admin@invoicegen.com / SecureAdmin123!')
    print(f'🔑 Test Login: test@example.com / test1234')
    print(f'📄 PDF Generation: {"✅ Enabled" if PDF_AVAILABLE else "❌ Disabled (install ReportLab)"}')
    print(f'🛡️  Rate Limiting: {"✅ Enabled" if hasattr(limiter, "limit") and not isinstance(limiter, type) else "❌ Disabled"}')
    print('🛑 Stop server: Press Ctrl+C')
    print('='*60)
    
    try:
        app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)
    except OSError as e:
        if "Address already in use" in str(e):
            print("❌ Port 5000 is in use. Trying port 5001...")
            app.run(debug=True, host='127.0.0.1', port=5001, use_reloader=False)
        else:
            raise e
    except KeyboardInterrupt:
        print("\n✅ Invoice Generator stopped gracefully")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")