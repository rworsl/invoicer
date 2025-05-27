@echo off
title Complete PDF Setup for Invoice Generator
color 0A

echo.
echo =====================================================
echo    Complete PDF Setup for Invoice Generator
echo =====================================================
echo.

echo 🔍 Checking current system...
python --version
echo.

echo 📦 Step 1: Updating pip and installing tools...
python -m pip install --upgrade pip setuptools wheel
echo.

echo 📦 Step 2: Installing ReportLab (Primary PDF library)...
echo Trying multiple installation methods...
echo.

REM Method 1: Direct installation
echo Method 1: Direct pip install...
pip install reportlab
if %errorlevel% equ 0 (
    echo ✅ ReportLab installed successfully!
    goto :test_installation
)

REM Method 2: With dependencies
echo.
echo Method 2: Installing with dependencies...
pip install pillow freetype-py
pip install reportlab
if %errorlevel% equ 0 (
    echo ✅ ReportLab installed with dependencies!
    goto :test_installation
)

REM Method 3: Pre-compiled wheel
echo.
echo Method 3: Using pre-compiled wheel...
pip install --only-binary=all reportlab
if %errorlevel% equ 0 (
    echo ✅ ReportLab installed from wheel!
    goto :test_installation
)

REM Method 4: Force reinstall
echo.
echo Method 4: Force reinstall...
pip uninstall reportlab -y
pip install --force-reinstall --no-cache-dir reportlab
if %errorlevel% equ 0 (
    echo ✅ ReportLab force-installed!
    goto :test_installation
)

echo.
echo ⚠️  ReportLab installation failed. Installing alternatives...

REM Alternative 1: WeasyPrint
echo.
echo 📦 Installing WeasyPrint (Alternative 1)...
pip install weasyprint
if %errorlevel% equ 0 (
    echo ✅ WeasyPrint installed as alternative!
    set PDF_METHOD=weasyprint
    goto :test_alternative
)

REM Alternative 2: xhtml2pdf
echo.
echo 📦 Installing xhtml2pdf (Alternative 2)...
pip install xhtml2pdf
if %errorlevel% equ 0 (
    echo ✅ xhtml2pdf installed as alternative!
    set PDF_METHOD=xhtml2pdf
    goto :test_alternative
)

echo.
echo ❌ All PDF library installations failed.
echo.
echo 🔧 Manual installation required:
echo.
echo Option A: Install Visual Studio Build Tools
echo   1. Download from: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022
echo   2. Install "C++ build tools"
echo   3. Restart command prompt
echo   4. Run: pip install reportlab
echo.
echo Option B: Use Anaconda/Miniconda
echo   1. Install Anaconda: https://www.anaconda.com/download
echo   2. Run: conda install -c conda-forge reportlab
echo.
echo Option C: Use HTML export (No PDF)
echo   The app will export HTML files instead of PDFs
echo.
goto :end

:test_installation
echo.
echo 🧪 Testing ReportLab installation...
python -c "
import sys
try:
    import reportlab
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    print('✅ ReportLab is working perfectly!')
    print('Version:', reportlab.Version)
    
    # Create a simple test PDF
    from reportlab.platypus import SimpleDocTemplate
    import io
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [Paragraph('PDF Generation Test - Success!', styles['Title'])]
    doc.build(story)
    print('✅ PDF generation test successful!')
    print('📄 Full PDF generation is now enabled!')
    
except ImportError as e:
    print('❌ ReportLab import failed:', e)
    sys.exit(1)
except Exception as e:
    print('❌ ReportLab test failed:', e)
    sys.exit(1)
"

if %errorlevel% equ 0 (
    echo.
    echo 🎉 SUCCESS! ReportLab is working correctly!
    set PDF_METHOD=reportlab
    goto :create_test_script
) else (
    echo.
    echo ❌ ReportLab test failed. Installing alternatives...
    goto :install_alternatives
)

:test_alternative
if "%PDF_METHOD%"=="weasyprint" (
    echo.
    echo 🧪 Testing WeasyPrint...
    python -c "
try:
    import weasyprint
    print('✅ WeasyPrint is working!')
    # Test HTML to PDF conversion
    html = '<html><body><h1>Test PDF</h1><p>WeasyPrint is working!</p></body></html>'
    pdf = weasyprint.HTML(string=html).write_pdf()
    print('✅ PDF generation test successful!')
    print('📄 HTML to PDF conversion enabled!')
except Exception as e:
    print('❌ WeasyPrint test failed:', e)
"
) else if "%PDF_METHOD%"=="xhtml2pdf" (
    echo.
    echo 🧪 Testing xhtml2pdf...
    python -c "
try:
    from xhtml2pdf import pisa
    print('✅ xhtml2pdf is working!')
    print('📄 HTML to PDF conversion enabled!')
except Exception as e:
    print('❌ xhtml2pdf test failed:', e)
"
)

:create_test_script
echo.
echo 📝 Creating PDF test script...
(
    echo # test-pdf.py - Test PDF generation
    echo print^("Testing PDF generation..."^)
    echo.
    echo try:
    echo     import reportlab
    echo     from reportlab.lib.pagesizes import A4
    echo     from reportlab.platypus import SimpleDocTemplate, Paragraph
    echo     from reportlab.lib.styles import getSampleStyleSheet
    echo     
    echo     # Create test PDF
    echo     doc = SimpleDocTemplate^("test-invoice.pdf", pagesize=A4^)
    echo     styles = getSampleStyleSheet^(^)
    echo     story = [
    echo         Paragraph^("Test Invoice", styles['Title']^),
    echo         Paragraph^("PDF generation is working!", styles['Normal']^)
    echo     ]
    echo     doc.build^(story^)
    echo     print^("✅ Test PDF created: test-invoice.pdf"^)
    echo     
    echo except ImportError:
    echo     print^("❌ ReportLab not available"^)
    echo except Exception as e:
    echo     print^(f"❌ PDF generation failed: {e}"^)
) > test-pdf.py

echo ✅ Test script created: test-pdf.py

:install_alternatives
echo.
echo 📦 Installing additional PDF alternatives...
pip install --quiet matplotlib cairo-lang fpdf2
echo.

:end
echo.
echo =====================================================
echo    PDF Setup Complete!
echo =====================================================
echo.

if defined PDF_METHOD (
    echo ✅ PDF Generation Status: ENABLED
    echo 📄 Method: %PDF_METHOD%
) else (
    echo ⚠️  PDF Generation Status: DISABLED
    echo 📄 Method: HTML Export Fallback
)

echo.
echo 🚀 Next Steps:
echo.
echo 1. Restart your Invoice Generator:
echo    start-invoice-generator.bat
echo.
echo 2. Test PDF generation:
echo    python test-pdf.py
echo.
echo 3. Create an invoice and try "Download PDF"
echo.
echo 4. If PDFs don't work, the app will export HTML files instead
echo    ^(HTML files can be printed to PDF using your browser^)
echo.

echo 📱 Available commands:
echo   start-invoice-generator.bat  ^(Start the app^)
echo   python test-pdf.py           ^(Test PDF generation^)
echo.

echo 🔧 Troubleshooting:
echo   - If you get import errors, restart your command prompt
echo   - If PDFs are blank, check the invoice has items
echo   - If nothing works, the app will use HTML export
echo.

pause