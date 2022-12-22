from flask import Flask
from .routes import tracking

app = Flask(__name__)

app.register_blueprint(tracking.bp)