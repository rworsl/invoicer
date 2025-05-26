# app.py - Fixed Invoice Generator for Windows
from flask import Flask, render_template, redirect, url_for, flash, request, send_file, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import secrets
import re
from dotenv import load_dotenv
import io
import logging
import uuid

# Try to import optional dependencies
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    LIMITER_AVAILABLE = True
except ImportError:
    LIMITER_AVAILABLE = False
    print("Flask-Limiter not available - rate limiting disabled")

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("ReportLab not available - PDF generation disabled")

load_dotenv()

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

# Security Headers (Windows-friendly)
@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    if app.config.get('SESSION_COOKIE_SECURE'):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# Initialize extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)

# Initialize rate limiter only if available
if LIMITER_AVAILABLE:
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )
else:
    # Mock limiter for when it's not available
    class MockLimiter:
        def limit(self, limit_string):
            def decorator(f):
                return f
            return decorator
    limiter = MockLimiter()

# Logging configuration
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Input validation helpers
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_currency(currency_code):
    supported_currencies = get_supported_currencies()
    return currency_code in supported_currencies

def sanitize_input(text, max_length=None):
    if text is None:
        return ""
    text = str(text).strip()
    if max_length:
        text = text[:max_length]
    # Remove potentially dangerous characters
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
    
    def is_account_locked(self):
        if self.failed_login_attempts >= 5:
            if self.last_login_attempt and datetime.utcnow() - self.last_login_attempt < timedelta(minutes=15):
                return True
        return False
    
    def reset_failed_attempts(self):
        self.failed_login_attempts = 0
        self.last_login_attempt = None

class Invoice(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    invoice_number = db.Column(db.String(50), nullable=False)
    client_name = db.Column(db.String(200), nullable=False)
    client_email = db.Column(db.String(120))
    client_address = db.Column(db.Text)
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    template_type = db.Column(db.String(50), default='modern')
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
            'AUD': 'A$', 'CHF': 'CHF', 'CNY': '¥', 'INR': '₹', 'BRL': 'R$',
            'KRW': '₩', 'SEK': 'kr', 'NOK': 'kr', 'DKK': 'kr', 'PLN': 'zł',
            'CZK': 'Kč', 'HUF': 'Ft', 'RUB': '₽', 'TRY': '₺', 'ZAR': 'R',
            'MXN': '$', 'SGD': 'S$', 'HKD': 'HK$', 'NZD': 'NZ$', 'THB': '฿'
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
        'BRL': {'name': 'Brazilian Real', 'symbol': 'R$', 'code': 'BRL'},
        'KRW': {'name': 'South Korean Won', 'symbol': '₩', 'code': 'KRW'},
        'SEK': {'name': 'Swedish Krona', 'symbol': 'kr', 'code': 'SEK'},
        'NOK': {'name': 'Norwegian Krone', 'symbol': 'kr', 'code': 'NOK'},
        'DKK': {'name': 'Danish Krone', 'symbol': 'kr', 'code': 'DKK'},
        'PLN': {'name': 'Polish Zloty', 'symbol': 'zł', 'code': 'PLN'},
        'MXN': {'name': 'Mexican Peso', 'symbol': '$', 'code': 'MXN'},
        'SGD': {'name': 'Singapore Dollar', 'symbol': 'S$', 'code': 'SGD'},
        'HKD': {'name': 'Hong Kong Dollar', 'symbol': 'HK$', 'code': 'HKD'},
        'NZD': {'name': 'New Zealand Dollar', 'symbol': 'NZ$', 'code': 'NZD'},
        'THB': {'name': 'Thai Baht', 'symbol': '฿', 'code': 'THB'}
    }

@app.template_filter('currency')
def currency_filter(amount, currency_code='USD'):
    currencies = get_supported_currencies()
    if currency_code in currencies:
        symbol = currencies[currency_code]['symbol']
        if currency_code in ['JPY', 'KRW']:
            return f"{symbol}{int(amount):,}"
        return f"{symbol}{amount:,.2f}"
    return f"{amount:.2f}"

# PDF Generation (only if ReportLab is available)
def generate_pdf(invoice):
    if not REPORTLAB_AVAILABLE:
        raise Exception("PDF generation not available - ReportLab not installed")
    
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2563eb')
        )
        
        story = []
        
        # Header
        story.append(Paragraph("INVOICE", title_style))
        story.append(Spacer(1, 20))
        
        # Invoice details
        invoice_data = [
            ['Invoice #:', invoice.invoice_number, 'Date:', invoice.issue_date.strftime('%B %d, %Y')],
            ['Due Date:', invoice.due_date.strftime('%B %d, %Y'), 'Status:', invoice.status.title()],
            ['Currency:', f"{invoice.currency} ({invoice.get_currency_symbol()})", '', '']
        ]
        
        invoice_table = Table(invoice_data, colWidths=[1*inch, 2*inch, 1*inch, 2*inch])
        invoice_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        story.append(invoice_table)
        story.append(Spacer(1, 30))
        
        # Client info
        story.append(Paragraph(f"<b>Bill To:</b>", styles['Heading2']))
        story.append(Paragraph(sanitize_input(invoice.client_name, 200), styles['Normal']))
        if invoice.client_email:
            story.append(Paragraph(sanitize_input(invoice.client_email, 120), styles['Normal']))
        if invoice.client_address:
            clean_address = sanitize_input(invoice.client_address, 500).replace('\n', '<br/>')
            story.append(Paragraph(clean_address, styles['Normal']))
        
        story.append(Spacer(1, 30))
        
        # Items table
        item_data = [['Description', 'Qty', 'Rate', 'Amount']]
        for item in invoice.items:
            item_data.append([
                sanitize_input(item.description, 500),
                str(item.quantity),
                invoice.format_amount(item.rate),
                invoice.format_amount(item.amount)
            ])
        
        items_table = Table(item_data, colWidths=[3*inch, 0.75*inch, 1*inch, 1*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(items_table)
        story.append(Spacer(1, 20))
        
        # Totals
        totals_data = [
            ['Subtotal:', invoice.format_amount(invoice.subtotal)],
            [f'Tax ({invoice.tax_rate}%):', invoice.format_amount(invoice.tax_amount)],
            ['Total:', invoice.format_amount(invoice.total)]
        ]
        
        totals_table = Table(totals_data, colWidths=[1.5*inch, 1*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
        ]))
        
        story.append(totals_table)
        
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
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    if request.method == 'POST':
        try:
            email = sanitize_input(request.form.get('email', ''), 120).lower()
            password = request.form.get('password', '')
            company_name = sanitize_input(request.form.get('company_name', ''), 200)
            default_currency = request.form.get('default_currency', 'USD')
            
            # Validation
            if not validate_email(email):
                flash('Invalid email address.', 'error')
                return render_template('register.html', currencies=get_supported_currencies())
            
            if len(password) < 8:
                flash('Password must be at least 8 characters long.', 'error')
                return render_template('register.html', currencies=get_supported_currencies())
            
            if not validate_currency(default_currency):
                flash('Invalid currency selected.', 'error')
                return render_template('register.html', currencies=get_supported_currencies())
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered.', 'error')
                return render_template('register.html', currencies=get_supported_currencies())
            
            user = User(
                email=email,
                company_name=company_name,
                default_currency=default_currency
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
    
    return render_template('register.html', currencies=get_supported_currencies())

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        try:
            email = sanitize_input(request.form.get('email', ''), 120).lower()
            password = request.form.get('password', '')
            
            if not email or not password:
                flash('Email and password are required.', 'error')
                return render_template('login.html')
            
            user = User.query.filter_by(email=email).first()
            
            if user and user.is_account_locked():
                flash('Account temporarily locked due to multiple failed login attempts. Try again in 15 minutes.', 'error')
                return render_template('login.html')
            
            if user and user.check_password(password) and user.is_active:
                user.reset_failed_attempts()
                db.session.commit()
                
                login_user(user, remember=True)
                session.permanent = True
                app.logger.info(f'User logged in: {email}')
                
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            else:
                if user:
                    user.failed_login_attempts += 1
                    user.last_login_attempt = datetime.utcnow()
                    db.session.commit()
                
                app.logger.warning(f'Failed login attempt for: {email}')
                flash('Invalid email or password.', 'error')
                
        except Exception as e:
            app.logger.error(f'Login error: {str(e)}')
            flash('Login failed. Please try again.', 'error')
    
    return render_template('login.html')

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
        return render_template('dashboard.html', invoices=invoices)
    except Exception as e:
        app.logger.error(f'Dashboard error: {str(e)}')
        flash('Error loading dashboard.', 'error')
        return redirect(url_for('index'))

@app.route('/create-invoice', methods=['GET', 'POST'])
@login_required
@limiter.limit("20 per hour")
def create_invoice():
    try:
        # Free tier limit check
        if not current_user.is_premium:
            invoice_count = Invoice.query.filter_by(user_id=current_user.id).count()
            if invoice_count >= 5:
                flash('Free tier limited to 5 invoices. Upgrade to Premium for unlimited invoices.', 'warning')
                return redirect(url_for('upgrade'))
        
        if request.method == 'POST':
            # Validate and sanitize inputs
            invoice_number = sanitize_input(request.form.get('invoice_number', ''), 50)
            client_name = sanitize_input(request.form.get('client_name', ''), 200)
            client_email = sanitize_input(request.form.get('client_email', ''), 120)
            client_address = sanitize_input(request.form.get('client_address', ''), 500)
            currency = request.form.get('currency', current_user.default_currency)
            notes = sanitize_input(request.form.get('notes', ''), 1000)
            
            # Validation
            if not invoice_number or not client_name:
                flash('Invoice number and client name are required.', 'error')
                return redirect(url_for('create_invoice'))
            
            if client_email and not validate_email(client_email):
                flash('Invalid client email address.', 'error')
                return redirect(url_for('create_invoice'))
            
            if not validate_currency(currency):
                flash('Invalid currency selected.', 'error')
                return redirect(url_for('create_invoice'))
            
            try:
                issue_date = datetime.strptime(request.form['issue_date'], '%Y-%m-%d').date()
                due_date = datetime.strptime(request.form['due_date'], '%Y-%m-%d').date()
                tax_rate = float(request.form.get('tax_rate', 0))
                
                if tax_rate < 0 or tax_rate > 100:
                    flash('Tax rate must be between 0 and 100.', 'error')
                    return redirect(url_for('create_invoice'))
                    
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
                template_type=request.form.get('template_type', 'modern'),
                currency=currency,
                tax_rate=tax_rate,
                notes=notes
            )
            
            db.session.add(invoice)
            db.session.flush()
            
            # Add items with validation
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
                        
                        if quantity <= 0 or rate < 0:
                            flash('Quantity must be positive and rate cannot be negative.', 'error')
                            db.session.rollback()
                            return redirect(url_for('create_invoice'))
                        
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
            return redirect(url_for('view_invoice', id=invoice.id))
        
        # Generate next invoice number
        last_invoice = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.created_at.desc()).first()
        next_number = f"INV-{(Invoice.query.count() + 1):04d}"
        
        return render_template('create_invoice.html',
                             next_number=next_number,
                             currencies=get_supported_currencies(),
                             user_currency=current_user.default_currency)
                             
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Create invoice error: {str(e)}')
        flash('Error creating invoice.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/invoice/<invoice_id>')
@login_required
def view_invoice(invoice_id):
    try:
        invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
        return render_template('view_invoice.html', invoice=invoice)
    except Exception as e:
        app.logger.error(f'View invoice error: {str(e)}')
        flash('Invoice not found.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/invoice/<invoice_id>/pdf')
@login_required
@limiter.limit("30 per hour")
def download_pdf(invoice_id):
    try:
        if not REPORTLAB_AVAILABLE:
            flash('PDF generation not available. Please install ReportLab.', 'error')
            return redirect(url_for('view_invoice', invoice_id=invoice_id))
            
        invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
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

@app.route('/upgrade')
@login_required
def upgrade():
    return render_template('upgrade.html')

@app.route('/upgrade/process', methods=['POST'])
@login_required
def process_upgrade():
    try:
        current_user.is_premium = True
        current_user.updated_at = datetime.utcnow()
        db.session.commit()
        app.logger.info(f'User upgraded to premium: {current_user.email}')
        flash('Upgraded to Premium successfully!', 'success')
        return redirect(url_for('dashboard'))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Upgrade error: {str(e)}')
        flash('Upgrade failed. Please try again.', 'error')
        return redirect(url_for('upgrade'))

# Simple template rendering for missing templates
@app.errorhandler(404)
def not_found_error(error):
    return '<h1>Page Not Found</h1><p>The page you are looking for does not exist.</p><a href="/">Go Home'