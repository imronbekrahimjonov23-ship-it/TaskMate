import os
import logging
import requests
import psycopg
from flask import Flask, request

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
TOKEN = os.environ.get('BOT_TOKEN', '')
DATABASE_URL = os.environ.get('DATABASE_URL', '')
API = f'https://api.telegram.org/bot{TOKEN}'


def db():
    return psycopg.connect(DATABASE_URL, connect_timeout=10)


def init_db():
    with db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                user_id BIGINT NOT NULL,
                name TEXT NOT NULL,
                done BOOLEAN NOT NULL DEFAULT FALSE
            )
        ''')


def send(chat_id, text):
    r = requests.post(
        API + '/sendMessage',
        json={'chat_id': chat_id, 'text': text},
        timeout=15,
    )
    r.raise_for_status()


def handle(user_id, text):
    text = text.strip()
    if text in ('/start', '/help'):
        return (
            '✅ TaskMate botiga xush kelibsiz!\n\n'
            '/add Kitob o‘qish — vazifa qo‘shish\n'
            '/list — vazifalarni ko‘rish\n'
            '/edit 1 Yangi nom — tahrirlash\n'
            '/done 1 — bajarildi\n'
            '/delete 1 — o‘chirish'
        )

    if text.startswith('/add '):
        name = text[5:].strip()
        if not name:
            return 'Vazifa nomini yozing.'
        with db() as conn:
            task_id = conn.execute(
                'INSERT INTO tasks (user_id, name) VALUES (%s, %s) RETURNING id',
                (user_id, name),
            ).fetchone()[0]
        return f'✅ Vazifa qo‘shildi! ID: {task_id}\n{name}'

    if text == '/list':
        with db() as conn:
            rows = conn.execute(
                'SELECT id, name, done FROM tasks WHERE user_id = %s ORDER BY id',
                (user_id,),
            ).fetchall()
        if not rows:
            return 'Hozircha vazifalar yo‘q.'
        lines = ['📋 Vazifalaringiz:']
        for task_id, name, done in rows:
            lines.append(f'{task_id}. {"✅" if done else "⬜"} {name}')
        return '\n'.join(lines)[:4000]

    parts = text.split(maxsplit=2)
    if len(parts) >= 2 and parts[0] in ('/done', '/delete', '/edit'):
        if not parts[1].isdigit():
            return 'Vazifa ID raqamini kiriting.'
        task_id = int(parts[1])
        if parts[0] == '/edit':
            if len(parts) < 3 or not parts[2].strip():
                return 'Yangi nomni yozing: /edit 1 Yangi nom'
            sql = 'UPDATE tasks SET name = %s WHERE id = %s AND user_id = %s RETURNING id'
            params = (parts[2].strip(), task_id, user_id)
            success = '✏️ Vazifa yangilandi!'
        elif parts[0] == '/done':
            sql = 'UPDATE tasks SET done = TRUE WHERE id = %s AND user_id = %s RETURNING id'
            params = (task_id, user_id)
            success = '✅ Vazifa bajarildi!'
        else:
            sql = 'DELETE FROM tasks WHERE id = %s AND user_id = %s RETURNING id'
            params = (task_id, user_id)
            success = '🗑 Vazifa o‘chirildi!'
        with db() as conn:
            updated = conn.execute(sql, params).fetchone()
        return success if updated else 'Bunday vazifa topilmadi.'

    return 'Buyruq tushunilmadi. /help deb yozing.'


@app.get('/')
def home():
    return 'TaskMate is running!', 200


@app.post('/webhook')
def webhook():
    update = request.get_json(silent=True) or {}
    msg = update.get('message') or {}
    chat = msg.get('chat') or {}
    user = msg.get('from') or {}
    text = msg.get('text')
    if chat.get('type') == 'private' and user.get('id') and isinstance(text, str):
        try:
            reply = handle(user['id'], text)
            send(chat['id'], reply)
        except Exception:
            app.logger.exception('TaskMate request failed')
            return 'Temporary error', 500
    return 'OK', 200


if __name__ == '__main__':
    if not TOKEN or not DATABASE_URL:
        raise RuntimeError('BOT_TOKEN va DATABASE_URL sozlanishi kerak')
    init_db()
    url = os.environ.get('RENDER_EXTERNAL_URL', '')
    if url:
        r = requests.post(
            API + '/setWebhook',
            json={'url': url.rstrip('/') + '/webhook'},
            timeout=15,
        )
        r.raise_for_status()
        if not r.json().get('ok'):
            raise RuntimeError('Telegram webhook sozlanmadi')
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '10000')))


