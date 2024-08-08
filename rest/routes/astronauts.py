import requests_cache

from flask import Blueprint, jsonify
from ..services.astronauts import astronauts

astronauts()
requests_cache.install_cache(cache_name='local_cache', expire_after=3600)
bp = Blueprint('astronauts', __name__, url_prefix='/astronauts')

@bp.route('/', methods=['GET'])
def get_astronauts():
    data = astronauts()
    return jsonify(data)