import os
from flask import Blueprint, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import app.secret.apikey as apikey

line_bot_api = LineBotApi(apikey.get_line_channel_access_token())
handler = WebhookHandler(apikey.get_line_channel_secret())

bp = Blueprint("linebot", __name__)

@bp.route("/line/webhook", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# Text received
@handler.add(MessageEvent, message=TextMessage)
def on_message(event: MessageEvent):
    user_text = event.message.text
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"Received: {user_text}")
    )