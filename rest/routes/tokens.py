from flask import current_app, jsonify, Blueprint

bp = Blueprint('tokens', __name__, url_prefix='/tokens')

@bp.route('', methods=['GET'])
def get_tokens():
    return jsonify({
        'MAPBOX_API_TOKEN': current_app.config['MAPBOX_API_TOKEN'],
        'GOOGLE_API_TOKEN': current_app.config['GOOGLE_API_TOKEN'],
        'TIMEZONEDB_API_KEY': current_app.config['TIMEZONEDB_API_KEY']
    })