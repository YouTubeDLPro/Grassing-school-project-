# flask_app.py
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def health_check():
    return jsonify(status="healthy")
