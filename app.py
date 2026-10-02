"""Abuse Your Manager: public stories, private credentials, persistent pseudonyms."""
from functools import wraps
from hashlib import sha256
from pathlib import Path
import argparse
import json
import os
import re
import secrets
import time

from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from feed import rank_candidates, POLICY_VERSION, CANDIDATE_LIMIT, PAGE_SIZE, SNAPSHOT_TTL
from database import Database

ROOT = Path(__file__).resolve().parent
CATEGORIES = ('General', 'Manager mayhem', 'Meeting purgatory', 'Office politics', 'HR said what?', 'Small victories')


def create_app(test_config=None):
    app = Flask(__name__, static_folder='static')
    production_without_database = bool(os.getenv('VERCEL') and not os.getenv('DATABASE_URL'))
    app.config.update(DATABASE=None if production_without_database else
                      os.getenv('DATABASE_URL', str(ROOT / 'instance' / 'aym.sqlite3')),
                      MAX_CONTENT_LENGTH=20_000, SECURE_COOKIES=os.getenv('AYM_HTTPS') == '1',
                      SEED_DEMO=os.getenv('AYM_SEED_DEMO', '1') == '1',
                      GOOGLE_CLIENT_ID=os.getenv('GOOGLE_CLIENT_ID', ''))
    if test_config:
        app.config.update(test_config)
    if app.config['DATABASE'] and not app.config['DATABASE'].startswith(('postgres://', 'postgresql://')):
        Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)

    def db():
        if not app.config['DATABASE']:
            raise RuntimeError('DATABASE_URL is not configured for this deployment.')
        if 'db' not in g:
            g.db = Database(app.config['DATABASE'])
        return g.db

    @app.teardown_appcontext
    def close_db(error=None):
        if 'db' in g:
            g.db.close()

    def fail(message, status=400):
        return jsonify(error=message), status

    def actor():
        token = request.cookies.get('aym_session', '')
        return db().execute('SELECT u.id,u.alias FROM sessions s JOIN users u ON u.id=s.user_id '
                            'WHERE s.token_hash=? AND s.expires>?',
                            (sha256(token.encode()).hexdigest(), int(time.time()))).fetchone() if token else None

    def authenticated(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            g.user = actor()
            if g.user is None:
                return fail('Sign in to join the conversation.', 401)
            return fn(*args, **kwargs)
        return wrapped

    def limited(bucket, limit, seconds):
        now = int(time.time())
        key = sha256(bucket.encode()).hexdigest()
        db().execute('DELETE FROM rate_limits WHERE expires<?', (now,))
        counter = 'rate_limits.count+1' if db().is_postgres else 'count+1'
        db().execute('INSERT INTO rate_limits VALUES (?,1,?) ON CONFLICT(bucket) '
                     f'DO UPDATE SET count={counter}', (key, now + seconds))
        db().commit()
        row = db().execute('SELECT count FROM rate_limits WHERE bucket=?', (key,)).fetchone()
        return (row['count'] if db().is_postgres else row[0]) > limit

    @app.before_request
    def protect_writes():
        if not app.config['DATABASE'] and request.path.startswith('/api/') and request.path != '/api/health':
            return fail('The production database is not configured.', 503)
        if request.method in ('POST', 'DELETE', 'PATCH', 'PUT'):
            if request.headers.get('X-Requested-With') != 'AYM' or not request.is_json:
                return fail('This action must come from the app.', 403)
            origin = request.headers.get('Origin')
            if origin and origin != request.host_url.rstrip('/'):
                return fail('Cross-site requests are not accepted.', 403)
            if request.headers.get('Sec-Fetch-Site') == 'cross-site':
                return fail('Cross-site requests are not accepted.', 403)

    @app.after_request
    def headers(response):
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' https://accounts.google.com/gsi/client; style-src 'self' https://accounts.google.com/gsi/style; font-src 'self'; img-src 'self' data:; connect-src 'self' https://accounts.google.com/gsi/; frame-src https://accounts.google.com/gsi/; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        if app.config['SECURE_COOKIES']:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        return fail(error.description, error.code)

    def data():
        payload = request.get_json(silent=True)
        return payload if isinstance(payload, dict) else {}

    def field(payload, name, low, high):
        value = payload.get(name)
        if not isinstance(value, str) or not low <= len(value.strip()) <= high:
            raise ValueError(f'{name.capitalize()} must be {low}–{high} characters.')
        return value.strip()

    @app.errorhandler(ValueError)
    def invalid(error):
        return fail(str(error))

    def content_check(text):
        # Deliberately limited: catches obvious contact details, not all personal data.
        if re.search(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}|(?:\+?\d[\s().-]*){10,}', text):
            raise ValueError('Leave out email addresses and phone numbers. Keep people unidentifiable.')

    def new_session(uid, alias):
        raw = secrets.token_urlsafe(32)
        db().execute('DELETE FROM sessions WHERE expires<?', (int(time.time()),))
        db().execute('INSERT INTO sessions VALUES (?,?,?)',
                     (sha256(raw.encode()).hexdigest(), uid, int(time.time()) + 604800))
        db().commit()
        response = jsonify(user={'alias': alias})
        response.set_cookie('aym_session', raw, httponly=True, secure=app.config['SECURE_COOKIES'],
                            samesite='Lax', max_age=604800)
        return response

    @app.get('/')
    @app.get('/post/<int:post_id>')
    def index(post_id=None):
        return send_from_directory(app.static_folder, 'index.html')

    @app.get('/api/me')
    def me():
        user = actor()
        return jsonify(user={'alias': user['alias']} if user else None)

    @app.get('/api/health')
    def health():
        if not app.config['DATABASE']:
            return jsonify(ok=False, error='DATABASE_URL is not configured.'), 503
        try:
            db().execute('SELECT 1').fetchone()
        except Exception:
            app.logger.exception('Database health check failed')
            return jsonify(ok=False, error='Database connection failed.'), 503
        return jsonify(ok=True, database='postgresql' if db().is_postgres else 'sqlite')

    @app.post('/api/auth/<mode>')
    def auth(mode):
        if mode not in ('signup', 'login'):
            return fail('Not found.', 404)
        if limited('auth:' + (request.remote_addr or ''), 20, 900):
            return fail('Too many attempts. Try again in 15 minutes.', 429)
        payload = data()
        login = field(payload, 'login', 3, 40).lower()
        password = field(payload, 'password', 12, 128)
        if not re.fullmatch(r'[a-z0-9_.-]+', login):
            return fail('Use letters, numbers, dots, dashes or underscores for your private login.')
        if mode == 'signup':
            alias = secrets.choice(['Feral', 'Overcaffeinated', 'Quiet', 'Corporate', 'Unmuted', 'OutOfOffice']) + secrets.choice(['Stapler', 'Pigeon', 'Potato', 'Raccoon', 'Paperclip', 'Toast']) + '_' + secrets.token_hex(3)
            try:
                uid = db().insert_id('INSERT INTO users(login,password_hash,alias,created_at) VALUES (?,?,?,?)',
                                     (login, generate_password_hash(password), alias, int(time.time())))
                db().commit()
            except Exception as error:
                db().rollback()
                if 'unique' not in str(error).lower() and 'duplicate' not in str(error).lower():
                    raise
                return fail('That private login is unavailable. Try another.', 409)
            return new_session(uid, alias)
        user = db().execute('SELECT * FROM users WHERE login=?', (login,)).fetchone()
        # Do the expensive check even if the account does not exist.
        matched = check_password_hash(user['password_hash'] if user else app.config['DUMMY_HASH'], password)
        if not user or not matched:
            return fail('Login or password is incorrect.', 401)
        return new_session(user['id'], user['alias'])

    @app.get('/api/auth/providers')
    def auth_providers():
        client_id = app.config['GOOGLE_CLIENT_ID']
        return jsonify(google={'enabled': bool(client_id), 'client_id': client_id or None})

    @app.post('/api/auth/google')
    def google_auth():
        client_id = app.config['GOOGLE_CLIENT_ID']
        if not client_id:
            return fail('Google sign-in is not configured.', 503)
        if limited('google-auth:' + (request.remote_addr or ''), 20, 900):
            return fail('Too many attempts. Try again in 15 minutes.', 429)
        credential = data().get('credential')
        if not isinstance(credential, str) or not 100 <= len(credential) <= 10_000:
            return fail('Google sign-in could not be verified.')
        try:
            claims = google_id_token.verify_oauth2_token(
                credential, google_requests.Request(), client_id)
        except (ValueError, TypeError):
            return fail('Google sign-in could not be verified.', 401)
        subject = claims.get('sub')
        if not isinstance(subject, str) or not subject:
            return fail('Google sign-in could not be verified.', 401)
        # Google profile fields are deliberately not stored. Only the stable subject
        # becomes a one-way internal key; the public continues to see a random alias.
        login = 'google-' + sha256(subject.encode()).hexdigest()[:32]
        user = db().execute('SELECT id,alias FROM users WHERE login=?', (login,)).fetchone()
        if not user:
            alias = secrets.choice(['Feral', 'Overcaffeinated', 'Quiet', 'Corporate', 'Unmuted', 'OutOfOffice']) + secrets.choice(['Stapler', 'Pigeon', 'Potato', 'Raccoon', 'Paperclip', 'Toast']) + '_' + secrets.token_hex(3)
            try:
                uid = db().insert_id('INSERT INTO users(login,password_hash,alias,created_at) VALUES (?,?,?,?)',
                                     (login, generate_password_hash(secrets.token_urlsafe(48)), alias, int(time.time())))
                db().commit()
            except Exception as error:
                db().rollback()
                if 'unique' not in str(error).lower() and 'duplicate' not in str(error).lower():
                    raise
                user = db().execute('SELECT id,alias FROM users WHERE login=?', (login,)).fetchone()
                if not user:
                    raise
                uid, alias = user['id'], user['alias']
        else:
            uid, alias = user['id'], user['alias']
        return new_session(uid, alias)

    @app.post('/api/logout')
    def logout():
        db().execute('DELETE FROM sessions WHERE token_hash=?',
                     (sha256(request.cookies.get('aym_session', '').encode()).hexdigest(),))
        db().commit()
        response = jsonify(ok=True)
        response.delete_cookie('aym_session')
        return response

    POST_SELECT = '''SELECT p.id,p.title,p.body,p.category,p.created_at,p.demo,u.alias,
        (SELECT count(*) FROM votes WHERE post_id=p.id) AS votes,
        (SELECT count(*) FROM comments WHERE post_id=p.id) AS comments
        FROM posts p JOIN users u ON u.id=p.user_id WHERE p.hidden=0'''

    def serialize_post(row, uid=None):
        result = dict(row)
        result['voted'] = bool(uid and db().execute('SELECT 1 FROM votes WHERE post_id=? AND user_id=?', (row['id'], uid)).fetchone())
        return result

    @app.get('/api/feed')
    def feed():
        now = int(time.time())
        cursor = request.args.get('cursor', '')
        if cursor:
            match = re.fullmatch(r'([a-f0-9]{32}):(\d{1,3})', cursor)
            if not match:
                return fail('Invalid feed cursor.', 400)
            token, position = match[1], int(match[2])
            snapshot = db().execute('SELECT * FROM feed_snapshots WHERE token=? AND expires>?',
                                     (token, now)).fetchone()
            if not snapshot:
                return fail('This feed has expired. Refresh to get a new feed.', 410)
            ids = json.loads(snapshot['post_ids'])
            if position > len(ids):
                return fail('Invalid feed position.', 400)
            policy = snapshot['policy_version']
        else:
            if limited('feed:' + (request.remote_addr or ''), 60, 60):
                return fail('Please wait a moment before refreshing again.', 429)
            candidates = db().execute(POST_SELECT + ' ORDER BY p.created_at DESC,p.id DESC LIMIT ?',
                                      (CANDIDATE_LIMIT,)).fetchall()
            ids = [row['id'] for row in rank_candidates(candidates, now)]
            token, position, policy = secrets.token_hex(16), 0, POLICY_VERSION
            db().execute('DELETE FROM feed_snapshots WHERE expires<=?', (now,))
            # Hard bound for this local implementation; a shared TTL store can replace it.
            db().execute('DELETE FROM feed_snapshots WHERE token IN '
                         '(SELECT token FROM feed_snapshots ORDER BY created_at DESC,token DESC LIMIT 1000000 OFFSET 999)')
            db().execute('INSERT INTO feed_snapshots VALUES (?,?,?,?,?)',
                         (token, json.dumps(ids), policy, now, now + SNAPSHOT_TTL))
            db().commit()
        # Preserve snapshot order while enforcing current moderation state on every page.
        remaining = ids[position:]
        visible = {}
        if remaining:
            placeholders = ','.join('?' for _ in remaining)
            visible = {row['id']: row for row in db().execute(POST_SELECT + f' AND p.id IN ({placeholders})', remaining)}
        page = []
        while position < len(ids) and len(page) < PAGE_SIZE:
            row = visible.get(ids[position])
            position += 1
            if row is not None:
                page.append(row)
        has_more = any(pid in visible for pid in ids[position:])
        user = actor()
        return jsonify(posts=[serialize_post(row, user['id'] if user else None) for row in page],
                       has_more=has_more, next_cursor=f'{token}:{position}' if has_more else None,
                       policy_version=policy)

    @app.get('/api/popular')
    def popular():
        # One reply author counts once, so repeated comments do not inflate popularity.
        query = POST_SELECT.replace('FROM posts p JOIN',
            ', (SELECT count(DISTINCT user_id) FROM comments WHERE post_id=p.id) AS repliers FROM posts p JOIN')
        rows = db().execute('SELECT * FROM (' + query + ') WHERE votes+repliers>0 '
                            'ORDER BY votes+repliers DESC,created_at DESC,id DESC LIMIT 5').fetchall()
        mode = 'popular'
        if not rows:
            mode = 'opening'
            rows = db().execute(POST_SELECT + ' ORDER BY p.created_at DESC,p.id DESC LIMIT 5').fetchall()
        return jsonify(mode=mode, posts=[{key: row[key] for key in
                       ('id', 'title', 'votes', 'comments', 'demo')} for row in rows])

    @app.get('/api/posts')
    def posts():
        query, params = POST_SELECT, []
        category, search = request.args.get('category', ''), request.args.get('q', '')[:120]
        if category:
            query += ' AND p.category=?'
            params.append(category)
        if search:
            query += (" AND p.title ILIKE ? ESCAPE '\\'" if db().is_postgres else
                      " AND p.title LIKE ? ESCAPE '\\'")
            search = search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            params.append('%' + search + '%')
        order = 'votes DESC,p.created_at DESC' if request.args.get('sort') == 'top' else 'p.created_at DESC'
        try:
            offset = max(0, int(request.args.get('offset', '0')))
        except ValueError:
            return fail('Invalid page.')
        rows = db().execute(query + ' ORDER BY ' + order + ' LIMIT 21 OFFSET ?', params + [offset]).fetchall()
        user = actor()
        return jsonify(posts=[serialize_post(row, user['id'] if user else None) for row in rows[:20]],
                       has_more=len(rows) > 20)

    def visible_post(pid):
        return db().execute(POST_SELECT + ' AND p.id=?', (pid,)).fetchone()

    @app.get('/api/posts/<int:pid>')
    def post(pid):
        row = visible_post(pid)
        if not row:
            return fail('This story is unavailable.', 404)
        user = actor()
        comments = db().execute('SELECT c.id,c.body,c.created_at,u.alias FROM comments c '
                                'JOIN users u ON u.id=c.user_id WHERE post_id=? ORDER BY c.created_at,c.id LIMIT 200', (pid,)).fetchall()
        return jsonify(post=serialize_post(row, user['id'] if user else None), comments=[dict(c) for c in comments])

    @app.post('/api/posts')
    @authenticated
    def create_post():
        payload = data()
        title, body = field(payload, 'title', 8, 160), field(payload, 'body', 20, 5000)
        category = payload.get('category', 'General')
        if category not in CATEGORIES:
            return fail('Choose a valid category.')
        content_check(title + ' ' + body)
        if limited('post:' + str(g.user['id']), 5, 3600):
            return fail('Five stories an hour is the limit. Take a breather.', 429)
        post_id = db().insert_id('INSERT INTO posts(user_id,title,body,category,created_at) VALUES (?,?,?,?,?)',
                                 (g.user['id'], title, body, category, int(time.time())))
        db().commit()
        return jsonify(id=post_id), 201

    @app.post('/api/posts/<int:pid>/comments')
    @authenticated
    def comment(pid):
        if not visible_post(pid):
            return fail('This story is unavailable.', 404)
        body = field(data(), 'body', 2, 2000)
        content_check(body)
        if limited('comment:' + str(g.user['id']), 30, 3600):
            return fail('Take a breather and try again in an hour.', 429)
        created_at = int(time.time())
        comment_id = db().insert_id('INSERT INTO comments(post_id,user_id,body,created_at) VALUES (?,?,?,?)',
                                    (pid, g.user['id'], body, created_at))
        db().commit()
        return jsonify(comment={'id': comment_id, 'body': body, 'created_at': created_at,
                                'alias': g.user['alias']}), 201

    @app.post('/api/posts/<int:pid>/vote')
    @authenticated
    def vote(pid):
        if not visible_post(pid):
            return fail('This story is unavailable.', 404)
        desired = data().get('voted')
        if not isinstance(desired, bool):
            return fail('Voted must be true or false.')
        if desired:
            db().execute('INSERT INTO votes VALUES (?,?) ON CONFLICT DO NOTHING', (pid, g.user['id']))
        else:
            db().execute('DELETE FROM votes WHERE post_id=? AND user_id=?', (pid, g.user['id']))
        db().commit()
        return jsonify(voted=desired)

    @app.post('/api/posts/<int:pid>/report')
    @authenticated
    def report(pid):
        if not visible_post(pid):
            return fail('This story is unavailable.', 404)
        reason = field(data(), 'reason', 5, 500)
        if limited('report:' + str(g.user['id']), 20, 3600):
            return fail('Report limit reached. Try again later.', 429)
        db().execute('INSERT INTO reports(post_id,user_id,reason,created_at) VALUES (?,?,?,?) ON CONFLICT DO NOTHING',
                     (pid, g.user['id'], reason, int(time.time())))
        db().commit()
        return jsonify(ok=True)

    app.config['DUMMY_HASH'] = generate_password_hash(secrets.token_urlsafe(32))
    if app.config['DATABASE'] and not app.config['DATABASE'].startswith(('postgres://', 'postgresql://')):
        with app.app_context():
            db().executescript((ROOT / 'schema.sql').read_text())
            db().execute('PRAGMA journal_mode=WAL')
            if app.config['SEED_DEMO'] and not db().execute('SELECT 1 FROM posts LIMIT 1').fetchone():
                from seed import seed
                seed(db())
    return app


app = create_app()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5050)
    args = parser.parse_args()
    from waitress import serve
    print(f'Abuse Your Manager: http://localhost:{args.port}', flush=True)
    serve(app, host='127.0.0.1', port=args.port, threads=4)
