# app.py - Enhanced Invoice Generator with Tiered Memberships & Currencies
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
from decimal import Decimal

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

# Membership Tiers Configuration
MEMBERSHIP_TIERS = {
    'free': {
        'name': 'Free',
        'price': 0,
        'invoice_limit': 5,
        'features': [
            'Up to 5 invoices per month',
            'Basic templates',
            'PDF export',
            'Basic currency support'
        ],
        'color': 'gray',
        'popular': False
    },
    'starter': {
        'name': 'Starter',
        'price': 9,
        'invoice_limit': 25,
        'features': [
            'Up to 25 invoices per month',
            'All templates',
            'Advanced PDF export',
            'Multi-currency support',
            'Email integration',
            'Basic analytics'
        ],
        'color': 'blue',
        'popular': False
    },
    'professional': {
        'name': 'Professional',
        'price': 19,
        'invoice_limit': 100,
        'features': [
            'Up to 100 invoices per month',
            'Premium templates',
            'Advanced customization',
            'Full currency conversion',
            'Advanced analytics',
            'Priority support',
            'Custom branding'
        ],
        'color': 'purple',
        'popular': True
    },
    'business': {
        'name': 'Business',
        'price': 39,
        'invoice_limit': -1,  # Unlimited
        'features': [
            'Unlimited invoices',
            'All premium features',
            'API access',
            'Team collaboration',
            'Advanced integrations',
            'Custom workflows',
            'White-label solution',
            'Dedicated support'
        ],
        'color': 'green',
        'popular': False
    }
}

# Enhanced Currency Configuration
CURRENCIES = {
    # Major Currencies
    'USD': {'name': 'US Dollar', 'symbol': '$', 'code': 'USD', 'decimal_places': 2},
    'EUR': {'name': 'Euro', 'symbol': '€', 'code': 'EUR', 'decimal_places': 2},
    'GBP': {'name': 'British Pound', 'symbol': '£', 'code': 'GBP', 'decimal_places': 2},
    'JPY': {'name': 'Japanese Yen', 'symbol': '¥', 'code': 'JPY', 'decimal_places': 0},
    'CHF': {'name': 'Swiss Franc', 'symbol': 'CHF', 'code': 'CHF', 'decimal_places': 2},
    
    # Americas
    'CAD': {'name': 'Canadian Dollar', 'symbol': 'C$', 'code': 'CAD', 'decimal_places': 2},
    'BRL': {'name': 'Brazilian Real', 'symbol': 'R$', 'code': 'BRL', 'decimal_places': 2},
    'MXN': {'name': 'Mexican Peso', 'symbol': '$', 'code': 'MXN', 'decimal_places': 2},
    'ARS': {'name': 'Argentine Peso', 'symbol': '$', 'code': 'ARS', 'decimal_places': 2},
    
    # Asia Pacific
    'CNY': {'name': 'Chinese Yuan', 'symbol': '¥', 'code': 'CNY', 'decimal_places': 2},
    'INR': {'name': 'Indian Rupee', 'symbol': '₹', 'code': 'INR', 'decimal_places': 2},
    'KRW': {'name': 'South Korean Won', 'symbol': '₩', 'code': 'KRW', 'decimal_places': 0},
    'AUD': {'name': 'Australian Dollar', 'symbol': 'A$', 'code': 'AUD', 'decimal_places': 2},
    'NZD': {'name': 'New Zealand Dollar', 'symbol': 'NZ$', 'code': 'NZD', 'decimal_places': 2},
    'SGD': {'name': 'Singapore Dollar', 'symbol': 'S$', 'code': 'SGD', 'decimal_places': 2},
    'HKD': {'name': 'Hong Kong Dollar', 'symbol': 'HK$', 'code': 'HKD', 'decimal_places': 2},
    'THB': {'name': 'Thai Baht', 'symbol': '฿', 'code': 'THB', 'decimal_places': 2},
    'MYR': {'name': 'Malaysian Ringgit', 'symbol': 'RM', 'code': 'MYR', 'decimal_places': 2},
    'PHP': {'name': 'Philippine Peso', 'symbol': '₱', 'code': 'PHP', 'decimal_places': 2},
    'IDR': {'name': 'Indonesian Rupiah', 'symbol': 'Rp', 'code': 'IDR', 'decimal_places': 0},
    'VND': {'name': 'Vietnamese Dong', 'symbol': '₫', 'code': 'VND', 'decimal_places': 0},
    
    # Europe
    'NOK': {'name': 'Norwegian Krone', 'symbol': 'kr', 'code': 'NOK', 'decimal_places': 2},
    'SEK': {'name': 'Swedish Krona', 'symbol': 'kr', 'code': 'SEK', 'decimal_places': 2},
    'DKK': {'name': 'Danish Krone', 'symbol': 'kr', 'code': 'DKK', 'decimal_places': 2},
    'PLN': {'name': 'Polish Zloty', 'symbol': 'zł', 'code': 'PLN', 'decimal_places': 2},
    'CZK': {'name': 'Czech Koruna', 'symbol': 'Kč', 'code': 'CZK', 'decimal_places': 2},
    'HUF': {'name': 'Hungarian Forint', 'symbol': 'Ft', 'code': 'HUF', 'decimal_places': 0},
    'RON': {'name': 'Romanian Leu', 'symbol': 'lei', 'code': 'RON', 'decimal_places': 2},
    'BGN': {'name': 'Bulgarian Lev', 'symbol': 'лв', 'code': 'BGN', 'decimal_places': 2},
    'HRK': {'name': 'Croatian Kuna', 'symbol': 'kn', 'code': 'HRK', 'decimal_places': 2},
    'RUB': {'name': 'Russian Ruble', 'symbol': '₽', 'code': 'RUB', 'decimal_places': 2},
    'UAH': {'name': 'Ukrainian Hryvnia', 'symbol': '₴', 'code': 'UAH', 'decimal_places': 2},
    'TRY': {'name': 'Turkish Lira', 'symbol': '₺', 'code': 'TRY', 'decimal_places': 2},
    
    # Middle East & Africa
    'AED': {'name': 'UAE Dirham', 'symbol': 'د.إ', 'code': 'AED', 'decimal_places': 2},
    'SAR': {'name': 'Saudi Riyal', 'symbol': '﷼', 'code': 'SAR', 'decimal_places': 2},
    'QAR': {'name': 'Qatari Riyal', 'symbol': '﷼', 'code': 'QAR', 'decimal_places': 2},
    'ILS': {'name': 'Israeli Shekel', 'symbol': '₪', 'code': 'ILS', 'decimal_places': 2},
    'EGP': {'name': 'Egyptian Pound', 'symbol': '£', 'code': 'EGP', 'decimal_places': 2},
    'ZAR': {'name': 'South African Rand', 'symbol': 'R', 'code': 'ZAR', 'decimal_places': 2},
    'NGN': {'name': 'Nigerian Naira', 'symbol': '₦', 'code': 'NGN', 'decimal_places': 2},
    'KES': {'name': 'Kenyan Shilling', 'symbol': 'KSh', 'code': 'KES', 'decimal_places': 2},
    
    # Cryptocurrencies (for progressive businesses)
    'BTC': {'name': 'Bitcoin', 'symbol': '₿', 'code': 'BTC', 'decimal_places': 8},
    'ETH': {'name': 'Ethereum', 'symbol': 'Ξ', 'code': 'ETH', 'decimal_places': 6},
}

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

# Currency Helper Functions
def get_supported_currencies():
    return CURRENCIES

def format_currency(amount, currency_code):
    """Format amount according to currency specifications"""
    if currency_code not in CURRENCIES:
        currency_code = 'USD'
    
    currency = CURRENCIES[currency_code]
    decimal_places = currency['decimal_places']
    symbol = currency['symbol']
    
    if decimal_places == 0:
        return f"{symbol}{int(amount):,}"
    else:
        return f"{symbol}{amount:,.{decimal_places}f}"

def get_exchange_rate(from_currency, to_currency):
    """Get exchange rate between currencies - mock implementation"""
    # In a real app, you'd use an API like exchangerate-api.com or fixer.io
    # For demo purposes, returning mock rates
    mock_rates = {
        ('USD', 'EUR'): 0.85,
        ('USD', 'GBP'): 0.73,
        ('USD', 'JPY'): 110.0,
        ('USD', 'CAD'): 1.25,
        ('USD', 'AUD'): 1.35,
        ('EUR', 'USD'): 1.18,
        ('GBP', 'USD'): 1.37,
    }
    
    if from_currency == to_currency:
        return 1.0
    
    rate_key = (from_currency, to_currency)
    if rate_key in mock_rates:
        return mock_rates[rate_key]
    
    # Try reverse rate
    reverse_key = (to_currency, from_currency)
    if reverse_key in mock_rates:
        return 1.0 / mock_rates[reverse_key]
    
    # Default fallback
    return 1.0

def convert_currency(amount, from_currency, to_currency):
    """Convert amount between currencies"""
    rate = get_exchange_rate(from_currency, to_currency)
    return Decimal(str(amount)) * Decimal(str(rate))

# Membership Helper Functions
def get_membership_tier(tier_name):
    """Get membership tier configuration"""
    return MEMBERSHIP_TIERS.get(tier_name, MEMBERSHIP_TIERS['free'])

def can_create_invoice(user):
    """Check if user can create another invoice based on their tier"""
    tier = get_membership_tier(user.membership_tier)
    if tier['invoice_limit'] == -1:  # Unlimited
        return True
    
    # Count invoices created this month
    now = datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    invoices_this_month = Invoice.query.filter(
        Invoice.user_id == user.id,
        Invoice.created_at >= start_of_month
    ).count()
    
    return invoices_this_month < tier['invoice_limit']

def get_invoice_usage(user):
    """Get current invoice usage for the user"""
    tier = get_membership_tier(user.membership_tier)
    now = datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = Invoice.query.filter(
        Invoice.user_id == user.id,
        Invoice.created_at >= start_of_month
    ).count()
    
    return {
        'used': used,
        'limit': tier['invoice_limit'],
        'percentage': (used / tier['invoice_limit'] * 100) if tier['invoice_limit'] > 0 else 0
    }

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    company_name = db.Column(db.String(200))
    default_currency = db.Column(db.String(3), default='USD')
    membership_tier = db.Column(db.String(20), default='free')
    subscription_expires = db.Column(db.DateTime)
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
    
    @property
    def is_premium(self):
        """Backward compatibility property"""
        return self.membership_tier != 'free'
    
    def get_tier_info(self):
        """Get detailed tier information"""
        return get_membership_tier(self.membership_tier)
    
    def can_access_feature(self, feature):
        """Check if user can access a specific feature"""
        tier_features = {
            'advanced_templates': ['professional', 'business'],
            'currency_conversion': ['professional', 'business'],
            'analytics': ['starter', 'professional', 'business'],
            'api_access': ['business'],
            'custom_branding': ['professional', 'business'],
            'priority_support': ['professional', 'business']
        }
        
        return self.membership_tier in tier_features.get(feature, [])

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
    template_style = db.Column(db.String(20), default='modern')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade='all, delete-orphan')

    def get_currency_info(self):
        """Get currency information"""
        return CURRENCIES.get(self.currency, CURRENCIES['USD'])

    def format_amount(self, amount):
        """Format amount with proper currency symbol and decimal places"""
        return format_currency(amount, self.currency)

    def convert_to_currency(self, target_currency):
        """Convert invoice amounts to target currency"""
        if self.currency == target_currency:
            return self
        
        rate = get_exchange_rate(self.currency, target_currency)
        converted_invoice = {
            'subtotal': float(convert_currency(self.subtotal, self.currency, target_currency)),
            'tax_amount': float(convert_currency(self.tax_amount, self.currency, target_currency)),
            'total': float(convert_currency(self.total, self.currency, target_currency)),
            'currency': target_currency,
            'exchange_rate': rate,
            'original_currency': self.currency
        }
        return converted_invoice

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
        currency_info = invoice.get_currency_info()
        symbol = currency_info['symbol']
        
        item_data = [['Description', 'Qty', 'Rate', 'Amount']]
        for item in invoice.items:
            item_data.append([
                sanitize_input(item.description, 500),
                str(item.quantity),
                f"{symbol}{item.rate:.{currency_info['decimal_places']}f}",
                f"{symbol}{item.amount:.{currency_info['decimal_places']}f}"
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
        story.append(Paragraph(f"<b>Subtotal:</b> {invoice.format_amount(invoice.subtotal)}", styles['Normal']))
        story.append(Paragraph(f"<b>Tax ({invoice.tax_rate}%):</b> {invoice.format_amount(invoice.tax_amount)}", styles['Normal']))
        story.append(Paragraph(f"<b>Total:</b> {invoice.format_amount(invoice.total)}", styles['Heading2']))
        
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
    return render_template_string(INDEX_TEMPLATE, tiers=MEMBERSHIP_TIERS)

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    if request.method == 'POST':
        try:
            email = sanitize_input(request.form.get('email', ''), 120).lower()
            password = request.form.get('password', '')
            company_name = sanitize_input(request.form.get('company_name', ''), 200)
            currency = request.form.get('default_currency', 'USD')
            tier = request.form.get('membership_tier', 'free')
            
            if not validate_email(email):
                flash('Invalid email address.', 'error')
                return render_template_string(REGISTER_TEMPLATE, 
                                            currencies=get_supported_currencies(),
                                            tiers=MEMBERSHIP_TIERS)
            
            if len(password) < 8:
                flash('Password must be at least 8 characters long.', 'error')
                return render_template_string(REGISTER_TEMPLATE, 
                                            currencies=get_supported_currencies(),
                                            tiers=MEMBERSHIP_TIERS)
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered.', 'error')
                return render_template_string(REGISTER_TEMPLATE, 
                                            currencies=get_supported_currencies(),
                                            tiers=MEMBERSHIP_TIERS)
            
            # Validate tier
            if tier not in MEMBERSHIP_TIERS:
                tier = 'free'
            
            user = User(
                email=email,
                company_name=company_name,
                default_currency=currency if currency in CURRENCIES else 'USD',
                membership_tier=tier
            )
            
            # Set subscription expiration for paid tiers
            if tier != 'free':
                user.subscription_expires = datetime.utcnow() + timedelta(days=30)
            
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            login_user(user)
            session.permanent = True
            app.logger.info(f'New user registered: {email} ({tier} tier)')
            flash(f'Registration successful! Welcome to {MEMBERSHIP_TIERS[tier]["name"]} tier!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Registration error: {str(e)}')
            flash('Registration failed. Please try again.', 'error')
    
    return render_template_string(REGISTER_TEMPLATE, 
                                currencies=get_supported_currencies(),
                                tiers=MEMBERSHIP_TIERS)

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
        usage = get_invoice_usage(current_user)
        tier_info = current_user.get_tier_info()
        
        # Calculate some basic analytics
        analytics = {
            'total_invoices': len(invoices),
            'total_value': sum(inv.total for inv in invoices),
            'paid_invoices': len([inv for inv in invoices if inv.status == 'paid']),
            'pending_invoices': len([inv for inv in invoices if inv.status == 'pending']),
            'draft_invoices': len([inv for inv in invoices if inv.status == 'draft']),
        }
        
        return render_template_string(DASHBOARD_TEMPLATE, 
                                    invoices=invoices, 
                                    current_user=current_user,
                                    usage=usage,
                                    tier_info=tier_info,
                                    analytics=analytics,
                                    format_currency=format_currency)
    except Exception as e:
        app.logger.error(f'Dashboard error: {str(e)}')
        flash('Error loading dashboard.', 'error')
        return redirect(url_for('index'))

@app.route('/create-invoice', methods=['GET', 'POST'])
@login_required
@limiter.limit("20 per hour")
def create_invoice():
    try:
        # Check if user can create another invoice
        if not can_create_invoice(current_user):
            tier_info = current_user.get_tier_info()
            flash(f'You have reached your monthly limit of {tier_info["invoice_limit"]} invoices. Please upgrade your plan.', 'warning')
            return redirect(url_for('upgrade'))
        
        if request.method == 'POST':
            # Validate and sanitize inputs
            invoice_number = sanitize_input(request.form.get('invoice_number', ''), 50)
            client_name = sanitize_input(request.form.get('client_name', ''), 200)
            client_email = sanitize_input(request.form.get('client_email', ''), 120)
            client_address = sanitize_input(request.form.get('client_address', ''), 500)
            notes = sanitize_input(request.form.get('notes', ''), 1000)
            currency = request.form.get('currency', current_user.default_currency)
            template_style = request.form.get('template_style', 'modern')
            
            if not invoice_number or not client_name:
                flash('Invoice number and client name are required.', 'error')
                return redirect(url_for('create_invoice'))
            
            if currency not in CURRENCIES:
                currency = current_user.default_currency
            
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
                currency=currency,
                tax_rate=tax_rate,
                notes=notes,
                template_style=template_style
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
        
        # Get available templates based on user tier
        available_templates = ['modern']
        if current_user.can_access_feature('advanced_templates'):
            available_templates.extend(['professional', 'creative', 'minimal'])
        
        return render_template_string(CREATE_INVOICE_TEMPLATE, 
                                    next_number=next_number,
                                    currencies=get_supported_currencies(),
                                    available_templates=available_templates,
                                    current_user=current_user)
                             
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
        
        # Currency conversion option for premium users
        convert_to = request.args.get('convert_to')
        converted_invoice = None
        if convert_to and current_user.can_access_feature('currency_conversion'):
            if convert_to in CURRENCIES and convert_to != invoice.currency:
                converted_invoice = invoice.convert_to_currency(convert_to)
        
        return render_template_string(VIEW_INVOICE_TEMPLATE, 
                                    invoice=invoice, 
                                    converted_invoice=converted_invoice,
                                    currencies=get_supported_currencies(),
                                    format_currency=format_currency,
                                    current_user=current_user)
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

@app.route('/upgrade')
@login_required
def upgrade():
    return render_template_string(UPGRADE_TEMPLATE, 
                                tiers=MEMBERSHIP_TIERS,
                                current_tier=current_user.membership_tier,
                                usage=get_invoice_usage(current_user))

@app.route('/upgrade/<tier_name>', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def process_upgrade(tier_name):
    try:
        if tier_name not in MEMBERSHIP_TIERS:
            flash('Invalid membership tier.', 'error')
            return redirect(url_for('upgrade'))
        
        tier_info = MEMBERSHIP_TIERS[tier_name]
        
        # In a real app, you would integrate with a payment processor here
        # For demo purposes, we'll just update the tier
        
        current_user.membership_tier = tier_name
        if tier_name != 'free':
            current_user.subscription_expires = datetime.utcnow() + timedelta(days=30)
        else:
            current_user.subscription_expires = None
        
        db.session.commit()
        
        app.logger.info(f'User {current_user.email} upgraded to {tier_name}')
        flash(f'Successfully upgraded to {tier_info["name"]} tier!', 'success')
        
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Upgrade error: {str(e)}')
        flash('Error processing upgrade. Please try again.', 'error')
        return redirect(url_for('upgrade'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        try:
            # Update user settings
            current_user.company_name = sanitize_input(request.form.get('company_name', ''), 200)
            current_user.default_currency = request.form.get('default_currency', 'USD')
            
            # Password change
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            
            if current_password and new_password:
                if current_user.check_password(current_password):
                    if len(new_password) >= 8:
                        current_user.set_password(new_password)
                        flash('Password updated successfully!', 'success')
                    else:
                        flash('New password must be at least 8 characters long.', 'error')
                        return render_template_string(SETTINGS_TEMPLATE, 
                                                    currencies=get_supported_currencies(),
                                                    tiers=MEMBERSHIP_TIERS,
                                                    current_user=current_user)
                else:
                    flash('Current password is incorrect.', 'error')
                    return render_template_string(SETTINGS_TEMPLATE, 
                                                currencies=get_supported_currencies(),
                                                tiers=MEMBERSHIP_TIERS,
                                                current_user=current_user)
            
            db.session.commit()
            flash('Settings updated successfully!', 'success')
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Settings update error: {str(e)}')
            flash('Error updating settings.', 'error')
    
    return render_template_string(SETTINGS_TEMPLATE, 
                                currencies=get_supported_currencies(),
                                tiers=MEMBERSHIP_TIERS,
                                current_user=current_user,
                                usage=get_invoice_usage(current_user))

# API Routes for currency conversion (for premium users)
@app.route('/api/convert', methods=['POST'])
@login_required
@limiter.limit("100 per hour")
def api_convert_currency():
    try:
        if not current_user.can_access_feature('currency_conversion'):
            return jsonify({'error': 'Currency conversion requires Professional tier or higher'}), 403
        
        data = request.get_json()
        amount = float(data.get('amount', 0))
        from_currency = data.get('from', 'USD')
        to_currency = data.get('to', 'USD')
        
        if from_currency not in CURRENCIES or to_currency not in CURRENCIES:
            return jsonify({'error': 'Invalid currency code'}), 400
        
        converted_amount = convert_currency(amount, from_currency, to_currency)
        rate = get_exchange_rate(from_currency, to_currency)
        
        return jsonify({
            'amount': float(converted_amount),
            'rate': rate,
            'from': from_currency,
            'to': to_currency,
            'formatted': format_currency(float(converted_amount), to_currency)
        })
        
    except Exception as e:
        app.logger.error(f'Currency conversion API error: {str(e)}')
        return jsonify({'error': 'Conversion failed'}), 500

# Database initialization
def init_db():
    """Initialize database and create users"""
    try:
        with app.app_context():
            db.create_all()
            
            # Create admin user if not exists
            admin = User.query.filter_by(email='admin@invoicegen.com').first()
            if not admin:
                admin = User(
                    email='admin@invoicegen.com',
                    company_name='Admin Company',
                    default_currency='USD',
                    membership_tier='business'
                )
                admin.set_password('SecureAdmin123!')
                admin.subscription_expires = datetime.utcnow() + timedelta(days=365)
                db.session.add(admin)
                db.session.commit()
                print("✅ Admin user created: admin@invoicegen.com / SecureAdmin123! (Business tier)")
            else:
                print("✅ Admin user already exists")
                
            # Create test users for different tiers
            test_users = [
                ('test@example.com', 'test1234', 'Test Company', 'free'),
                ('starter@example.com', 'starter123', 'Starter Corp', 'starter'),
                ('pro@example.com', 'professional123', 'Professional LLC', 'professional'),
                ('business@example.com', 'business123', 'Business Enterprise', 'business')
            ]
            
            for email, password, company, tier in test_users:
                if not User.query.filter_by(email=email).first():
                    user = User(
                        email=email,
                        company_name=company,
                        default_currency='USD',
                        membership_tier=tier
                    )
                    user.set_password(password)
                    if tier != 'free':
                        user.subscription_expires = datetime.utcnow() + timedelta(days=30)
                    db.session.add(user)
                    db.session.commit()
                    print(f"✅ Test user created: {email} / {password} ({tier} tier)")
            
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

# Enhanced Templates with Tier and Currency Support

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
                border: 1px solid #e2e8f0; overflow: hidden; margin-bottom: 20px; }
        .card-header { padding: 20px; border-bottom: 1px solid #e2e8f0; background: #f7fafc; }
        .card-body { padding: 20px; }
        .btn { display: inline-block; padding: 12px 24px; border-radius: 6px; text-decoration: none; 
               font-weight: 500; border: none; cursor: pointer; transition: all 0.2s; text-align: center; }
        .btn-primary { background: #3182ce; color: white; }
        .btn-primary:hover { background: #2c5aa0; }
        .btn-secondary { background: #718096; color: white; }
        .btn-success { background: #38a169; color: white; }
        .btn-danger { background: #e53e3e; color: white; }
        .btn-purple { background: #9f7aea; color: white; }
        .btn-green { background: #48bb78; color: white; }
        .btn-outline { background: transparent; border: 2px solid #e2e8f0; color: #4a5568; }
        .btn-outline:hover { background: #f7fafc; }
        .form-group { margin-bottom: 20px; }
        .form-label { display: block; margin-bottom: 8px; font-weight: 500; color: #2d3748; }
        .form-input, .form-select { width: 100%; padding: 12px; border: 1px solid #cbd5e0; border-radius: 6px; 
                      font-size: 16px; transition: border-color 0.2s; }
        .form-input:focus, .form-select:focus { outline: none; border-color: #3182ce; box-shadow: 0 0 0 3px rgba(49,130,206,0.1); }
        .alert { padding: 16px; border-radius: 6px; margin-bottom: 20px; }
        .alert-success { background: #c6f6d5; color: #22543d; border: 1px solid #9ae6b4; }
        .alert-error { background: #fed7d7; color: #742a2a; border: 1px solid #fc8181; }
        .alert-warning { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
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
        .tier-badge { padding: 6px 12px; border-radius: 20px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
        .tier-free { background: #e2e8f0; color: #4a5568; }
        .tier-starter { background: #bee3f8; color: #2c5aa0; }
        .tier-professional { background: #d6bcfa; color: #553c9a; }
        .tier-business { background: #c6f6d5; color: #22543d; }
        .grid { display: grid; gap: 20px; }
        .grid-2 { grid-template-columns: 1fr 1fr; }
        .grid-3 { grid-template-columns: 1fr 1fr 1fr; }
        .text-center { text-align: center; }
        .text-right { text-align: right; }
        .mb-4 { margin-bottom: 16px; }
        .mt-4 { margin-top: 16px; }
        .popular-badge { position: absolute; top: -10px; right: 20px; background: #f56565; color: white; 
                         padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600; }
        .pricing-card { position: relative; border: 2px solid #e2e8f0; border-radius: 12px; padding: 24px; }
        .pricing-card.popular { border-color: #9f7aea; }
        .usage-bar { background: #e2e8f0; height: 8px; border-radius: 4px; overflow: hidden; }
        .usage-fill { background: #3182ce; height: 100%; transition: width 0.3s ease; }
        .feature-list { list-style: none; }
        .feature-list li { padding: 8px 0; display: flex; align-items: center; }
        .feature-list li:before { content: "✓"; color: #38a169; font-weight: bold; margin-right: 8px; }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="container">
            <a href="{{ url_for('index') }}" class="navbar-brand">🧾 InvoiceGen Pro</a>
            <div class="navbar-nav">
                {% if current_user.is_authenticated %}
                    <span class="tier-badge tier-{{ current_user.membership_tier }}">{{ current_user.get_tier_info()['name'] }}</span>
                    <a href="{{ url_for('dashboard') }}" class="btn btn-secondary">Dashboard</a>
                    <a href="{{ url_for('create_invoice') }}" class="btn btn-primary">New Invoice</a>
                    <a href="{{ url_for('settings') }}" class="btn btn-outline">Settings</a>
                    {% if current_user.membership_tier == 'free' %}
                        <a href="{{ url_for('upgrade') }}" class="btn btn-purple">Upgrade</a>
                    {% endif %}
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
        Create beautiful, professional invoices with multi-currency support. Choose from flexible pricing tiers to match your business needs.
    </p>
    
    <div style="margin-bottom: 64px;">
        <a href="{{ url_for('register') }}" class="btn btn-primary" style="font-size: 18px; padding: 16px 32px; margin-right: 16px;">
            Get Started Free
        </a>
        <a href="{{ url_for('login') }}" class="btn btn-secondary" style="font-size: 18px; padding: 16px 32px;">
            Sign In
        </a>
    </div>

    <!-- Pricing Overview -->
    <div class="grid grid-3" style="max-width: 1000px; margin: 0 auto;">
        {% for tier_id, tier in tiers.items() %}
            {% if tier_id in ['free', 'professional', 'business'] %}
            <div class="pricing-card {% if tier.popular %}popular{% endif %}">
                {% if tier.popular %}
                    <div class="popular-badge">Most Popular</div>
                {% endif %}
                <h3 style="font-size: 24px; margin-bottom: 16px;">{{ tier.name }}</h3>
                <div style="font-size: 36px; font-weight: bold; margin-bottom: 8px;">
                    {% if tier.price == 0 %}Free{% else %}<span style="font-size: 18px;">$</span>{{ tier.price }}{% endif %}
                    {% if tier.price > 0 %}<span style="font-size: 16px; color: #718096;">/month</span>{% endif %}
                </div>
                <p style="color: #718096; margin-bottom: 24px;">
                    {% if tier.invoice_limit == -1 %}Unlimited invoices{% else %}{{ tier.invoice_limit }} invoices/month{% endif %}
                </p>
                <ul class="feature-list" style="margin-bottom: 24px; text-align: left;">
                    {% for feature in tier.features[:3] %}
                        <li>{{ feature }}</li>
                    {% endfor %}
                </ul>
                <a href="{{ url_for('register') }}?tier={{ tier_id }}" class="btn btn-{{ tier.color }}" style="width: 100%;">
                    Get Started
                </a>
            </div>
            {% endif %}
        {% endfor %}
    </div>

    <div style="margin-top: 64px;">
        <h2 style="margin-bottom: 32px;">Supported Currencies</h2>
        <p style="color: #718096;">Over 40 currencies supported including:</p>
        <div style="margin-top: 16px; font-size: 18px;">
            USD • EUR • GBP • JPY • CAD • AUD • CNY • INR • BRL • and many more...
        </div>
    </div>
</div>
{% endblock %}
''')

REGISTER_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div style="max-width: 500px; margin: 0 auto;">
    <div class="card">
        <div class="card-header text-center">
            <h2>Create Your Account</h2>
            <p style="color: #718096; margin-top: 8px;">Start generating professional invoices today</p>
        </div>
        <div class="card-body">
            <form method="POST">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                
                <div class="form-group">
                    <label class="form-label">Email Address *</label>
                    <input type="email" name="email" class="form-input" placeholder="your@email.com" required>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Company Name (Optional)</label>
                    <input type="text" name="company_name" class="form-input" placeholder="Your Company Name">
                </div>
                
                <div class="form-group">
                    <label class="form-label">Default Currency</label>
                    <select name="default_currency" class="form-select">
                        {% for code, currency in currencies.items() %}
                            <option value="{{ code }}" {% if code == 'USD' %}selected{% endif %}>
                                {{ currency.symbol }} {{ currency.name }} ({{ code }})
                            </option>
                        {% endfor %}
                    </select>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Membership Tier</label>
                    <select name="membership_tier" class="form-select">
                        {% for tier_id, tier in tiers.items() %}
                            <option value="{{ tier_id }}" {% if tier_id == 'free' %}selected{% endif %}>
                                {{ tier.name }} - 
                                {% if tier.price == 0 %}Free{% else %}<span class="dollar-sign">$</span>{{ tier.price }}/month{% endif %}
                                ({% if tier.invoice_limit == -1 %}Unlimited{% else %}{{ tier.invoice_limit }}{% endif %} invoices)
                            </option>
                        {% endfor %}
                    </select>
                    <small style="color: #718096;">You can upgrade or downgrade anytime</small>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Password *</label>
                    <input type="password" name="password" class="form-input" placeholder="Choose a strong password (8+ characters)" required>
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
            
            <!-- Demo Credentials -->
            <div style="margin-top: 32px; padding: 16px; background: #f7fafc; border-radius: 8px; border-left: 4px solid #3182ce;">
                <h4 style="margin-bottom: 12px; color: #2d3748;">Demo Accounts:</h4>
                <div style="font-size: 14px; color: #4a5568;">
                    <p><strong>Admin:</strong> admin@invoicegen.com / SecureAdmin123!</p>
                    <p><strong>Free:</strong> test@example.com / test1234</p>
                    <p><strong>Professional:</strong> pro@example.com / professional123</p>
                    <p><strong>Business:</strong> business@example.com / business123</p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
''')

DASHBOARD_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<!-- Tier Status & Usage -->
<div class="card">
    <div class="card-body">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1>Dashboard</h1>
                <p style="color: #718096; margin-top: 8px;">
                    Welcome back! You're on the <strong>{{ tier_info.name }}</strong> tier.
                </p>
            </div>
            <div style="text-align: right;">
                {% if tier_info.invoice_limit != -1 %}
                    <div style="margin-bottom: 8px;">
                        <span style="font-size: 24px; font-weight: bold;">{{ usage.used }}</span>
                        <span style="color: #718096;">/ {{ usage.limit }} invoices this month</span>
                    </div>
                    <div class="usage-bar" style="width: 200px;">
                        <div class="usage-fill" style="width: {{ usage.percentage }}%;"></div>
                    </div>
                {% else %}
                    <div style="color: #38a169; font-weight: bold;">✨ Unlimited Invoices</div>
                {% endif %}
                
                {% if current_user.membership_tier == 'free' %}
                    <a href="{{ url_for('upgrade') }}" class="btn btn-purple" style="margin-top: 16px;">
                        Upgrade for More Features
                    </a>
                {% endif %}
            </div>
        </div>
    </div>
</div>

<!-- Quick Stats -->
<div class="grid grid-2" style="margin-bottom: 32px;">
    <div class="card">
        <div class="card-body">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3 style="color: #3182ce; font-size: 28px; margin-bottom: 8px;">{{ analytics.total_invoices }}</h3>
                    <p style="color: #718096;">Total Invoices</p>
                </div>
                <div style="font-size: 48px; opacity: 0.6;">📄</div>
            </div>
        </div>
    </div>
    
    <div class="card">
        <div class="card-body">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3 style="color: #38a169; font-size: 28px; margin-bottom: 8px;">{{ format_currency(analytics.total_value, current_user.default_currency) }}</h3>
                    <p style="color: #718096;">Total Value</p>
                </div>
                <div style="font-size: 48px; opacity: 0.6;">💰</div>
            </div>
        </div>
    </div>
</div>

<div class="grid grid-3" style="margin-bottom: 32px;">
    <div class="card">
        <div class="card-body text-center">
            <h4 style="color: #f56565; font-size: 24px;">{{ analytics.draft_invoices }}</h4>
            <p style="color: #718096;">Draft</p>
        </div>
    </div>
    <div class="card">
        <div class="card-body text-center">
            <h4 style="color: #ed8936; font-size: 24px;">{{ analytics.pending_invoices }}</h4>
            <p style="color: #718096;">Pending</p>
        </div>
    </div>
    <div class="card">
        <div class="card-body text-center">
            <h4 style="color: #38a169; font-size: 24px;">{{ analytics.paid_invoices }}</h4>
            <p style="color: #718096;">Paid</p>
        </div>
    </div>
</div>

<!-- Actions -->
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px;">
    <h2>Recent Invoices</h2>
    <div style="display: flex; gap: 12px;">
        {% if usage.used < usage.limit or usage.limit == -1 %}
            <a href="{{ url_for('create_invoice') }}" class="btn btn-primary">+ New Invoice</a>
        {% else %}
            <a href="{{ url_for('upgrade') }}" class="btn btn-purple">Upgrade to Create More</a>
        {% endif %}
    </div>
</div>

<!-- Invoices Table -->
<div class="card">
    <div class="card-body">
        {% if invoices %}
            <table class="table">
                <thead>
                    <tr>
                        <th>Invoice #</th>
                        <th>Client</th>
                        <th>Date</th>
                        <th>Amount</th>
                        <th>Currency</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for invoice in invoices %}
                    <tr>
                        <td style="font-weight: 500;">{{ invoice.invoice_number }}</td>
                        <td>{{ invoice.client_name }}</td>
                        <td>{{ invoice.issue_date.strftime('%b %d, %Y') }}</td>
                        <td style="font-weight: 500;">{{ invoice.format_amount(invoice.total) }}</td>
                        <td>
                            <span style="background: #e2e8f0; padding: 2px 8px; border-radius: 12px; font-size: 12px;">
                                {{ invoice.currency }}
                            </span>
                        </td>
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
                {% if usage.used < usage.limit or usage.limit == -1 %}
                    <a href="{{ url_for('create_invoice') }}" class="btn btn-primary">Create Invoice</a>
                {% else %}
                    <a href="{{ url_for('upgrade') }}" class="btn btn-purple">Upgrade to Create Invoices</a>
                {% endif %}
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
                    <label class="form-label">Currency</label>
                    <select name="currency" class="form-select">
                        {% for code, currency in currencies.items() %}
                            <option value="{{ code }}" {% if code == current_user.default_currency %}selected{% endif %}>
                                {{ currency.symbol }} {{ currency.name }} ({{ code }})
                            </option>
                        {% endfor %}
                    </select>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Tax Rate (%)</label>
                    <input type="number" name="tax_rate" class="form-input" value="0" step="0.01" min="0" max="100">
                </div>
                
                {% if current_user.can_access_feature('advanced_templates') %}
                <div class="form-group">
                    <label class="form-label">Template Style</label>
                    <select name="template_style" class="form-select">
                        {% for template in available_templates %}
                            <option value="{{ template }}">{{ template.title() }}</option>
                        {% endfor %}
                    </select>
                </div>
                {% endif %}
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <h3>Client Information</h3>
            </div>
            <div class="card-body">
                <div class="form-group">
                    <label class="form-label">Client Name *</label>
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
                        <label class="form-label">Rate</label>
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

VIEW_INVOICE_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px;">
    <div>
        <h1>Invoice {{ invoice.invoice_number }}</h1>
        <p style="color: #718096; margin-top: 8px;">Created {{ invoice.created_at.strftime('%B %d, %Y') }}</p>
    </div>
    <div style="display: flex; gap: 12px;">
        <a href="{{ url_for('dashboard') }}" class="btn btn-secondary">← Back</a>
        {% if PDF_AVAILABLE %}
        <a href="{{ url_for('download_pdf', invoice_id=invoice.id) }}" class="btn btn-primary">📄 Download PDF</a>
        {% endif %}
    </div>
</div>

<!-- Currency Conversion (Premium Feature) -->
{% if current_user.can_access_feature('currency_conversion') and currencies|length > 1 %}
<div class="card">
    <div class="card-body">
        <div style="display: flex; justify-content: between; align-items: center;">
            <h3>💱 Currency Conversion</h3>
            <div style="display: flex; gap: 12px; align-items: center;">
                <span>Convert to:</span>
                <select onchange="convertCurrency(this.value)" style="padding: 8px; border-radius: 4px; border: 1px solid #cbd5e0;">
                    <option value="">Select Currency</option>
                    {% for code, currency in currencies.items() %}
                        {% if code != invoice.currency %}
                        <option value="{{ code }}">{{ currency.symbol }} {{ currency.name }}</option>
                        {% endif %}
                    {% endfor %}
                </select>
            </div>
        </div>
        {% if converted_invoice %}
        <div style="margin-top: 16px; padding: 16px; background: #f7fafc; border-radius: 8px;">
            <p><strong>Converted Amount:</strong> {{ format_currency(converted_invoice.total, converted_invoice.currency) }}</p>
            <p style="color: #718096; font-size: 14px;">
                Exchange Rate: 1 {{ invoice.currency }} = {{ "%.4f"|format(converted_invoice.exchange_rate) }} {{ converted_invoice.currency }}
            </p>
        </div>
        {% endif %}
    </div>
</div>
{% endif %}

<div class="card">
    <div class="card-body">
        <div style="text-align: center; margin-bottom: 48px;">
            <h2 style="color: #3182ce; font-size: 36px; margin-bottom: 16px;">INVOICE</h2>
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div style="text-align: left;">
                    <p><strong>Invoice #:</strong> {{ invoice.invoice_number }}</p>
                    <p><strong>Date:</strong> {{ invoice.issue_date.strftime('%B %d, %Y') }}</p>
                    <p><strong>Due Date:</strong> {{ invoice.due_date.strftime('%B %d, %Y') }}</p>
                    <p><strong>Currency:</strong> {{ invoice.get_currency_info().name }} ({{ invoice.currency }})</p>
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
                    <td class="text-right">{{ invoice.format_amount(item.rate) }}</td>
                    <td class="text-right">{{ invoice.format_amount(item.amount) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <div style="display: flex; justify-content: flex-end;">
            <div style="width: 300px;">
                <div style="display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #e2e8f0;">
                    <span>Subtotal:</span>
                    <span>{{ invoice.format_amount(invoice.subtotal) }}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #e2e8f0;">
                    <span>Tax ({{ invoice.tax_rate }}%):</span>
                    <span>{{ invoice.format_amount(invoice.tax_amount) }}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 16px 0; border-top: 2px solid #2d3748; font-weight: bold; font-size: 20px;">
                    <span>Total:</span>
                    <span style="color: #3182ce;">{{ invoice.format_amount(invoice.total) }}</span>
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

<script>
function convertCurrency(targetCurrency) {
    if (targetCurrency) {
        window.location.href = '{{ url_for("view_invoice", invoice_id=invoice.id) }}?convert_to=' + targetCurrency;
    }
}
</script>
{% endblock %}
''')

UPGRADE_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div class="text-center" style="margin-bottom: 48px;">
    <h1 style="font-size: 48px; margin-bottom: 16px;">Upgrade Your Plan</h1>
    <p style="font-size: 20px; color: #718096;">Unlock more features and increase your invoice limits</p>
</div>

<!-- Current Usage -->
{% if current_tier != 'business' %}
<div class="card" style="margin-bottom: 32px;">
    <div class="card-body">
        <h3 style="margin-bottom: 16px;">Current Usage</h3>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <p>You're currently on the <strong>{{ tiers[current_tier].name }}</strong> tier</p>
                {% if usage.limit != -1 %}
                <p style="color: #718096;">{{ usage.used }}/{{ usage.limit }} invoices used this month</p>
                {% endif %}
            </div>
            {% if usage.limit != -1 %}
            <div style="width: 200px;">
                <div class="usage-bar">
                    <div class="usage-fill" style="width: {{ usage.percentage }}%;"></div>
                </div>
            </div>
            {% endif %}
        </div>
    </div>
</div>
{% endif %}

<!-- Pricing Tiers -->
<div class="grid grid-2" style="max-width: 900px; margin: 0 auto;">
    {% for tier_id, tier in tiers.items() %}
        {% if tier_id != 'free' %}
        <div class="pricing-card {% if tier.popular %}popular{% endif %}" style="{% if tier_id == current_tier %}opacity: 0.7;{% endif %}">
            {% if tier.popular %}
                <div class="popular-badge">Most Popular</div>
            {% endif %}
            
            <div class="text-center" style="margin-bottom: 24px;">
                <h3 style="font-size: 28px; margin-bottom: 8px;">{{ tier.name }}</h3>
                <div style="font-size: 48px; font-weight: bold; margin-bottom: 8px;">
                    <span style="font-size: 24px;">$</span>{{ tier.price }}
                    <span style="font-size: 18px; color: #718096;">/month</span>
                </div>
                <p style="color: #718096;">
                    {% if tier.invoice_limit == -1 %}
                        Unlimited invoices
                    {% else %}
                        {{ tier.invoice_limit }} invoices per month
                    {% endif %}
                </p>
            </div>
            
            <ul class="feature-list" style="margin-bottom: 32px;">
                {% for feature in tier.features %}
                    <li>{{ feature }}</li>
                {% endfor %}
            </ul>
            
            {% if tier_id == current_tier %}
                <div class="btn btn-outline" style="width: 100%; opacity: 0.6;">Current Plan</div>
            {% else %}
                <form method="POST" action="{{ url_for('process_upgrade', tier_name=tier_id) }}">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                    <button type="submit" class="btn btn-{{ tier.color }}" style="width: 100%;">
                        {% if tier.price > tiers[current_tier].price %}Upgrade{% else %}Downgrade{% endif %} Now
                    </button>
                </form>
            {% endif %}
        </div>
        {% endif %}
    {% endfor %}
</div>

<div style="text-center; margin-top: 48px; padding: 32px; background: #f7fafc; border-radius: 12px;">
    <h3 style="margin-bottom: 16px;">Need Help Choosing?</h3>
    <p style="color: #718096; margin-bottom: 24px;">Not sure which plan is right for you? Here's a quick guide:</p>
    
    <div class="grid grid-3" style="text-align: left;">
        <div>
            <h4 style="color: #3182ce; margin-bottom: 8px;">Starter</h4>
            <p style="font-size: 14px; color: #718096;">Perfect for freelancers and small businesses just getting started</p>
        </div>
        <div>
            <h4 style="color: #9f7aea; margin-bottom: 8px;">Professional</h4>
            <p style="font-size: 14px; color: #718096;">Ideal for growing businesses that need advanced features and currency support</p>
        </div>
        <div>
            <h4 style="color: #48bb78; margin-bottom: 8px;">Business</h4>
            <p style="font-size: 14px; color: #718096;">For established companies requiring unlimited invoices and premium features</p>
        </div>
    </div>
</div>

<div style="text-center; margin-top: 32px;">
    <p style="color: #718096;">All plans include a 30-day money-back guarantee</p>
</div>
{% endblock %}
''')

SETTINGS_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px;">
    <h1>Account Settings</h1>
    <a href="{{ url_for('dashboard') }}" class="btn btn-secondary">← Back to Dashboard</a>
</div>

<div class="grid grid-2">
    <!-- Account Information -->
    <div class="card">
        <div class="card-header">
            <h3>Account Information</h3>
        </div>
        <div class="card-body">
            <form method="POST">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                
                <div class="form-group">
                    <label class="form-label">Email Address</label>
                    <input type="email" class="form-input" value="{{ current_user.email }}" disabled style="background: #f7fafc;">
                    <small style="color: #718096;">Email cannot be changed for security reasons</small>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Company Name</label>
                    <input type="text" name="company_name" class="form-input" value="{{ current_user.company_name or '' }}" placeholder="Your Company Name">
                </div>
                
                <div class="form-group">
                    <label class="form-label">Default Currency</label>
                    <select name="default_currency" class="form-select">
                        {% for code, currency in currencies.items() %}
                            <option value="{{ code }}" {% if code == current_user.default_currency %}selected{% endif %}>
                                {{ currency.symbol }} {{ currency.name }} ({{ code }})
                            </option>
                        {% endfor %}
                    </select>
                    <small style="color: #718096;">This will be used for new invoices by default</small>
                </div>
                
                <h4 style="margin: 24px 0 16px 0;">Change Password</h4>
                
                <div class="form-group">
                    <label class="form-label">Current Password</label>
                    <input type="password" name="current_password" class="form-input" placeholder="Enter current password">
                </div>
                
                <div class="form-group">
                    <label class="form-label">New Password</label>
                    <input type="password" name="new_password" class="form-input" placeholder="Enter new password (8+ characters)">
                </div>
                
                <button type="submit" class="btn btn-primary">Save Changes</button>
            </form>
        </div>
    </div>
    
    <!-- Subscription Information -->
    <div class="card">
        <div class="card-header">
            <h3>Subscription Details</h3>
        </div>
        <div class="card-body">
            <div style="text-align: center; margin-bottom: 24px;">
                <div class="tier-badge tier-{{ current_user.membership_tier }}" style="font-size: 16px; padding: 12px 24px;">
                    {{ current_user.get_tier_info().name }} Plan
                </div>
            </div>
            
            <div style="margin-bottom: 24px;">
                <h4 style="margin-bottom: 12px;">Current Usage</h4>
                {% if usage.limit == -1 %}
                    <p style="color: #38a169; font-weight: bold;">✨ Unlimited Invoices</p>
                {% else %}
                    <div style="margin-bottom: 8px;">
                        <span style="font-size: 24px; font-weight: bold;">{{ usage.used }}</span>
                        <span style="color: #718096;">/ {{ usage.limit }} invoices this month</span>
                    </div>
                    <div class="usage-bar">
                        <div class="usage-fill" style="width: {{ usage.percentage }}%;"></div>
                    </div>
                {% endif %}
            </div>
            
            <div style="margin-bottom: 24px;">
                <h4 style="margin-bottom: 12px;">Plan Features</h4>
                <ul class="feature-list">
                    {% for feature in current_user.get_tier_info().features %}
                        <li>{{ feature }}</li>
                    {% endfor %}
                </ul>
            </div>
            
            {% if current_user.subscription_expires %}
            <div style="margin-bottom: 24px; padding: 16px; background: #f7fafc; border-radius: 8px;">
                <p><strong>Subscription expires:</strong> {{ current_user.subscription_expires.strftime('%B %d, %Y') }}</p>
            </div>
            {% endif %}
            
            {% if current_user.membership_tier != 'business' %}
                <a href="{{ url_for('upgrade') }}" class="btn btn-purple" style="width: 100%;">
                    Upgrade Plan
                </a>
            {% else %}
                <div style="text-align: center; color: #38a169; font-weight: bold;">
                    🎉 You're on our highest tier!
                </div>
            {% endif %}
        </div>
    </div>
</div>

<!-- Account Statistics -->
<div class="card" style="margin-top: 32px;">
    <div class="card-header">
        <h3>Account Statistics</h3>
    </div>
    <div class="card-body">
        <div class="grid grid-3">
            <div style="text-align: center;">
                <h4 style="color: #3182ce; font-size: 24px;">{{ current_user.invoices|length }}</h4>
                <p style="color: #718096;">Total Invoices Created</p>
            </div>
            <div style="text-align: center;">
                <h4 style="color: #38a169; font-size: 24px;">{{ (current_user.created_at.now() - current_user.created_at).days }}</h4>
                <p style="color: #718096;">Days Since Signup</p>
            </div>
            <div style="text-align: center;">
                <h4 style="color: #9f7aea; font-size: 24px;">{{ current_user.default_currency }}</h4>
                <p style="color: #718096;">Primary Currency</p>
            </div>
        </div>
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
    print('🧾 ENHANCED INVOICE GENERATOR STARTING')
    print('='*60)
    
    # Initialize database
    if not init_db():
        print("❌ Failed to initialize database. Exiting.")
        exit(1)
    
    print(f'📱 Application: http://localhost:5000')
    print('🔑 Demo Accounts:')
    print('   Admin (Business): admin@invoicegen.com / SecureAdmin123!')
    print('   Free: test@example.com / test1234')
    print('   Starter: starter@example.com / starter123')
    print('   Professional: pro@example.com / professional123')
    print('   Business: business@example.com / business123')
    print(f'📄 PDF Generation: {"✅ Enabled" if PDF_AVAILABLE else "❌ Disabled (install ReportLab)"}')
    print(f'🛡️  Rate Limiting: {"✅ Enabled" if hasattr(limiter, "limit") and not isinstance(limiter, type) else "❌ Disabled"}')
    print(f'💰 Membership Tiers: ✅ 4 tiers (Free, Starter, Professional, Business)')
    print(f'💱 Currencies: ✅ {len(CURRENCIES)} currencies supported')
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
        print("\n✅ Enhanced Invoice Generator stopped gracefully")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")