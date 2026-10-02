import sqlite3
import tempfile
import unittest
from pathlib import Path
from app import create_app


class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / 'test.sqlite3')
        self.app = create_app({'TESTING': True, 'DATABASE': self.path, 'SEED_DEMO': False})
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, payload, client=None):
        return (client or self.client).post('/api' + path, json=payload, headers={'X-Requested-With': 'AYM'})

    def signup(self, login='testperson', client=None):
        response = self.write('/auth/signup', {'login': login, 'password': 'a long test password'}, client)
        self.assertEqual(response.status_code, 200)
        return response.json['user']['alias']

    def post(self):
        response = self.write('/posts', {'title': 'A meeting about meetings', 'body': 'This is a long enough story about an unnecessary meeting.', 'category': 'Meeting purgatory'})
        self.assertEqual(response.status_code, 201)
        return response.json['id']

    def test_health_reports_active_database(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'ok': True, 'database': 'sqlite'})

    def test_public_read_authenticated_write_and_private_identity(self):
        with self.client.get('/') as home:
            self.assertEqual(home.status_code, 200)
        self.assertEqual(self.client.get('/api/posts').status_code, 200)
        self.assertEqual(self.write('/posts', {}).status_code, 401)
        alias = self.signup()
        pid = self.post()
        reader = self.app.test_client()
        response = reader.get(f'/api/posts/{pid}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['post']['alias'], alias)
        for private in ('testperson', 'password_hash', 'user_id', 'token_hash'):
            self.assertNotIn(private, response.text)
        for action in ('comments', 'vote', 'report'):
            self.assertEqual(self.write(f'/posts/{pid}/{action}', {}, reader).status_code, 401)

    def test_login_persistence_and_logout_revocation(self):
        alias = self.signup()
        cookie = self.client.get_cookie('aym_session').value
        self.write('/logout', {})
        thief = self.app.test_client()
        thief.set_cookie('aym_session', cookie)
        self.assertIsNone(thief.get('/api/me').json['user'])
        self.assertEqual(self.write('/auth/login', {'login':'testperson', 'password':'wrong password long'}).status_code, 401)
        response = self.write('/auth/login', {'login':'TESTPERSON', 'password':'a long test password'})
        self.assertEqual(response.json['user']['alias'], alias)
        app2 = create_app({'TESTING': True, 'DATABASE': self.path, 'SEED_DEMO': False})
        browser = app2.test_client()
        browser.set_cookie('aym_session', self.client.get_cookie('aym_session').value)
        self.assertEqual(browser.get('/api/me').json['user']['alias'], alias)

    def test_csrf_and_validation(self):
        self.assertEqual(self.client.post('/api/auth/signup', json={}).status_code, 403)
        self.assertEqual(self.client.post('/api/auth/signup', json={}, headers={'X-Requested-With':'AYM','Origin':'https://evil.example'}).status_code, 403)
        self.signup()
        self.assertEqual(self.write('/posts', {'title': 'short'}).status_code, 400)
        response = self.write('/posts', {'title':'Do not post contact details', 'body':'Please contact person@example.com about the incident', 'category':'Manager mayhem'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.write('/posts', []).status_code, 400)
        self.assertEqual(self.client.get('/api/posts?offset=nope').status_code, 400)

    def test_votes_comments_reports_and_moderation(self):
        self.signup()
        pid = self.post()
        for _ in range(2):
            self.assertEqual(self.write(f'/posts/{pid}/vote', {'voted':True}).status_code, 200)
        self.assertEqual(self.client.get(f'/api/posts/{pid}').json['post']['votes'], 1)
        self.write(f'/posts/{pid}/vote', {'voted':False})
        self.assertEqual(self.client.get(f'/api/posts/{pid}').json['post']['votes'], 0)
        self.assertEqual(self.write(f'/posts/{pid}/comments', {'body':'That sounds exhausting.'}).status_code, 201)
        self.assertEqual(self.client.get(f'/api/posts/{pid}').json['post']['comments'], 1)
        self.write(f'/posts/{pid}/report', {'reason':'Private information'})
        self.write(f'/posts/{pid}/report', {'reason':'Private information'})
        with sqlite3.connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM reports').fetchone()[0], 1)
            conn.execute('UPDATE posts SET hidden=1 WHERE id=?', (pid,))
        conn.close()
        self.assertEqual(self.client.get(f'/api/posts/{pid}').status_code, 404)
        self.assertEqual(self.client.get('/api/posts').json['posts'], [])
        self.assertEqual(self.write(f'/posts/{pid}/comments', {'body':'another reply'}).status_code, 404)

    def test_search_filters_and_parameterized_sql(self):
        self.signup(); self.post()
        self.assertEqual(len(self.client.get('/api/posts?q=meetings').json['posts']), 1)
        self.assertEqual(len(self.client.get('/api/posts?q=MEET').json['posts']), 1)
        self.assertEqual(len(self.client.get('/api/posts?q=eeting%20ab').json['posts']), 1)
        self.assertEqual(self.client.get('/api/posts?q=unnecessary').json['posts'], [])
        self.assertEqual(len(self.client.get('/api/posts?category=Office%20politics').json['posts']), 0)
        self.assertEqual(self.client.get('/api/posts?q=%27%20OR%201=1--').json['posts'], [])
        self.assertEqual(self.client.get('/api/posts?q=%25').json['posts'], [])

    def test_post_does_not_require_a_category(self):
        self.signup()
        response = self.write('/posts', {'title':'No category needed here', 'body':'A story that can be published without choosing a topic.'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client.get('/api/posts').json['posts'][0]['title'], 'No category needed here')

    def test_rate_limit(self):
        self.signup()
        for _ in range(5):
            self.post()
        self.assertEqual(self.write('/posts', {'title':'Another meeting tomorrow', 'body':'This is yet another long story about a meeting.', 'category':'Meeting purgatory'}).status_code, 429)

    def test_seed_is_labeled_and_has_no_fake_engagement(self):
        seed_path = str(Path(self.tmp.name) / 'seed.sqlite3')
        seeded = create_app({'TESTING':True, 'DATABASE':seed_path, 'SEED_DEMO':True})
        posts = seeded.test_client().get('/api/posts').json['posts']
        self.assertEqual(len(posts), 5)
        self.assertTrue(all(p['demo'] and p['votes'] == 0 and p['comments'] == 0 for p in posts))


if __name__ == '__main__':
    unittest.main()
