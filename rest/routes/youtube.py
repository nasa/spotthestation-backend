import requests_cache

from flask import Blueprint, jsonify
from ..services.youtube import youtube_livestream_id

youtube_livestream_id()
requests_cache.install_cache(cache_name='local_cache', expire_after=3600)
bp = Blueprint('youtube', __name__, url_prefix='/youtube')

@bp.route('/livestream-id', methods=['GET'])
def get_youtube_livestream_id():
    data = youtube_livestream_id()
    return jsonify({ "id": data })
