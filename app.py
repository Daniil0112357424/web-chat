from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Храним user_id -> session_id
user_sessions = {}

# Храним историю: (user1, user2) -> [ {from, to, type, content}, ... ]
chat_history = {}

def get_history_key(user1, user2):
    return tuple(sorted([user1, user2]))

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        if not user_id:
            return render_template("index.html", error="Введите UserID")
        session["user_id"] = user_id
        return redirect(url_for("chat"))
    return render_template("index.html")

@app.route("/chat")
def chat():
    if "user_id" not in session:
        return redirect(url_for("index"))
    return render_template("chat.html", user_id=session["user_id"])

@socketio.on("connect")
def handle_connect():
    user_id = session.get("user_id")
    if user_id:
        user_sessions[user_id] = request.sid
        print(f"{user_id} подключился (session {request.sid})")

@socketio.on("send_message")
def handle_send_message(data):
    from_user = session.get("user_id")
    to_user = data.get("to_user")
    msg = data.get("message")

    if from_user and to_user and msg:
        # Сохраняем в историю
        key = get_history_key(from_user, to_user)
        chat_history.setdefault(key, []).append({
            "from": from_user,
            "to": to_user,
            "type": "text",
            "content": msg
        })
        to_session = user_sessions.get(to_user)
        if to_session:
            emit("receive_message", {"from": from_user, "message": msg}, room=to_session)
            emit("receive_message", {"from": from_user, "message": msg}, room=request.sid)
        else:
            emit("receive_message", {"from": "System", "message": f"Пользователь '{to_user}' не найден или не в сети."}, room=request.sid)

@socketio.on("send_image")
def handle_send_image(data):
    from_user = session.get("user_id")
    to_user = data.get("to_user")
    image = data.get("image")
    if from_user and to_user and image:
        # Сохраняем в историю
        key = get_history_key(from_user, to_user)
        chat_history.setdefault(key, []).append({
            "from": from_user,
            "to": to_user,
            "type": "image",
            "content": image
        })
        to_session = user_sessions.get(to_user)
        if to_session:
            emit("receive_image", {"from": from_user, "image": image}, room=to_session)
            emit("receive_image", {"from": from_user, "image": image}, room=request.sid)
        else:
            emit("receive_message", {"from": "System", "message": f"Пользователь '{to_user}' не найден или не в сети."}, room=request.sid)

@socketio.on("get_history")
def handle_get_history(data):
    from_user = session.get("user_id")
    to_user = data.get("to_user")
    if from_user and to_user:
        key = get_history_key(from_user, to_user)
        history = chat_history.get(key, [])
        emit("chat_history", {"history": history})

@socketio.on("disconnect")
def handle_disconnect():
    for uid, sid in list(user_sessions.items()):
        if sid == request.sid:
            print(f"{uid} отключился")
            del user_sessions[uid]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)