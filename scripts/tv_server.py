"""
Dean Family Grades — TV Server
Author: Harold A. Dean, Jr. | Claude Sonnet 4.6 (2026-03-01)

Serves the TV dashboard HTML + grades JSON API.
Deploy to Railway:  Procfile -> web: gunicorn scripts.tv_server:app
Access on TV:       https://your-railway-url.up.railway.app/tv

NIST 800-53: SC-28 (no PII stored), AU-2 (access logged by gunicorn)
"""
import json
import os
from pathlib import Path
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__)

BASE_DIR    = Path(__file__).parent.parent
GRADES_FILE = BASE_DIR / 'data' / 'grades.json'
TV_DIR      = BASE_DIR / 'tv'


@app.route('/tv')
def tv_dashboard():
    return send_from_directory(str(TV_DIR), 'grades-tv.html')


@app.route('/api/grades')
def api_grades():
    try:
        with open(GRADES_FILE) as f:
            grades = json.load(f)
        return jsonify({'grades': grades, 'source': 'lcps_email'})
    except FileNotFoundError:
        return jsonify({'error': 'grades.json not found', 'grades': []}), 404
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid JSON: {e}', 'grades': []}), 500


@app.route('/health')
def health():
    exists = GRADES_FILE.exists()
    return jsonify({
        'status': 'ok',
        'grades_file': str(GRADES_FILE),
        'grades_exists': exists
    }), 200


@app.route('/')
def index():
    return '<meta http-equiv="refresh" content="0;url=/tv">', 302


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    print(f'[GradesTV] Serving on http://0.0.0.0:{port}/tv')
    print(f'[GradesTV] Grades file: {GRADES_FILE}')
    app.run(host='0.0.0.0', port=port, debug=False)
