from flask import Flask
app = Flask(__name__)
@app.route('/')
def home():
    return "^<h1^>Flask is working!^</h1^>^<p^>^<a href='/test'^>Test page^</a^>^</p^>"
@app.route('/test')
def test():
    return "^<h1^>Test page works!^</h1^>^<p^>^<a href='/'^>Home^</a^>^</p^>"
if __name__ == '__main__':
    print('Simple Flask test starting...')
    print('Open: http://localhost:5000')
    app.run(debug=True, port=5000)
