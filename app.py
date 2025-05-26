from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

user_sessions = {}
chat_history = {}
online_users = set()  # Для отслеживания онлайн-пользователей

def get_history_key(user1, user2):
    return tuple(sorted([user1, user2]))

@app.route("/")
def index():
    return render_template("index2.html")  # Главная страница

@app.route("/login", methods=["GET", "POST"])
def login():
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
        return redirect(url_for("login"))
    return render_template("chat.html", user_id=session["user_id"])

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@socketio.on("connect")
def handle_connect():
    user_id = session.get("user_id")
    if user_id:
        user_sessions[user_id] = request.sid
        online_users.add(user_id)
        print(f"{user_id} подключился (session {request.sid})")
        emit("online_users", list(online_users), broadcast=True)

@socketio.on("send_message")
def handle_send_message(data):
    from_user = session.get("user_id")
    to_user = data.get("to_user")
    msg = data.get("message")

    if from_user and to_user and msg:
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

@socketio.on("get_online_users")
def handle_get_online_users():
    emit("online_users", list(online_users))

# --- WebRTC аудиозвонок (сигналинг) ---
@socketio.on("call_offer")
def handle_call_offer(data):
    from_user = session.get("user_id")
    to_user = data.get("to")
    offer = data.get("offer")
    to_session = user_sessions.get(to_user)
    if to_session:
        emit("call_offer", {"from": from_user, "offer": offer}, room=to_session)

@socketio.on("call_answer")
def handle_call_answer(data):
    from_user = session.get("user_id")
    to_user = data.get("to")
    answer = data.get("answer")
    to_session = user_sessions.get(to_user)
    if to_session:
        emit("call_answer", {"from": from_user, "answer": answer}, room=to_session)

@socketio.on("call_ice")
def handle_call_ice(data):
    from_user = session.get("user_id")
    to_user = data.get("to")
    candidate = data.get("candidate")
    to_session = user_sessions.get(to_user)
    if to_session:
        emit("call_ice", {"from": from_user, "candidate": candidate}, room=to_session)

@socketio.on("call_hangup")
def handle_call_hangup(data):
    from_user = session.get("user_id")
    to_user = data.get("from")
    to_session = user_sessions.get(to_user)
    if to_session:
        emit("call_hangup", {}, room=to_session)

@socketio.on("call_reject")
def handle_call_reject(data):
    from_user = session.get("user_id")
    to_user = data.get("from")
    to_session = user_sessions.get(to_user)
    if to_session:
        emit("call_reject", {}, room=to_session)

@socketio.on("call_busy")
def handle_call_busy(data):
    from_user = session.get("user_id")
    to_user = data.get("to")
    to_session = user_sessions.get(to_user)
    if to_session:
        emit("call_busy", {}, room=to_session)

@socketio.on("disconnect")
def handle_disconnect():
    for uid, sid in list(user_sessions.items()):
        if sid == request.sid:
            print(f"{uid} отключился")
            del user_sessions[uid]
            if uid in online_users:
                online_users.remove(uid)
                emit("online_users", list(online_users), broadcast=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)