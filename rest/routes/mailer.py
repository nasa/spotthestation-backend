from flask import Blueprint, current_app, request
from flask_mail import Mail, Message

bp = Blueprint('mailer', __name__, url_prefix='/mailer')

@bp.route('/send-mail', methods=['POST'])
def send_mail():
  data = request.get_json()
  mail = Mail(current_app)
  recipients = current_app.config['MAIL_RECIPIENTS'].replace(' ','').split(',')
  msg = Message(data['subject'], sender=current_app.config['MAIL_SENDER'], recipients=recipients)
  msg.body = data['body']
  mail.send(msg)
  return 'Mail sent!'
