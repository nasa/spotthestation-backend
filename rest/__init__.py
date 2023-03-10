from flask import Flask, jsonify
from .routes import tracking

health_status = True

app = Flask(__name__)
app.register_blueprint(tracking.bp)

@app.route('/health')
def health():
    if health_status:
        resp = jsonify(health="healthy")
        resp.status_code = 200
    else:
        resp = jsonify(health="unhealthy")
        resp.status_code = 500

    return resp
