import os
import logging

from dotenv import load_dotenv
from flask import Flask, jsonify
from .routes import tracking, mailer
from .services.sat_data import last_updated

load_dotenv()

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = os.getenv('MAIL_PORT')
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_SENDER'] = os.getenv('MAIL_SENDER')
app.config['MAIL_RECIPIENTS'] = os.getenv('MAIL_RECIPIENTS')
app.config['REDIS_URL'] = os.getenv('REDIS_URL')

app.register_blueprint(tracking.bp)
app.register_blueprint(mailer.bp)

@app.route('/health')
def health():
    return jsonify(health="healthy", sat_data_updated_at=last_updated())
