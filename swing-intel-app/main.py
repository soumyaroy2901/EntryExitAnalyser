from flask import Flask, render_template, request, jsonify
from logic.scanner_logic import run_scan
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scan', methods=['POST'])
def api_scan():
    data = request.json
    tickers = data.get('tickers', [])
    if not tickers:
        return jsonify({"error": "No tickers provided"}), 400
    
    # Process comma separated if single string
    if isinstance(tickers, str):
        tickers = [t.strip() for t in tickers.split(',')]
    
    results = run_scan(tickers)
    return jsonify(results)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
