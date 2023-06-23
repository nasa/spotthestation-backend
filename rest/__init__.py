import os
import logging

from flask import Flask, jsonify
from .routes import tracking, mailer
from dotenv import load_dotenv

health_status = True
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
    if health_status:
        resp = jsonify(health="healthy")
        resp.status_code = 200
    else:
        resp = jsonify(health="unhealthy")
        resp.status_code = 500

    return resp
