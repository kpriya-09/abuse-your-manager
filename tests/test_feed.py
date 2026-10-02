import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from app import create_app
from feed import rank_candidates, POLICY_VERSION


class RankingTests(unittest.TestCase):
    def test_support_can_outrank_newer_posts_but_old_posts_decay(self):
        now = 1_000_000
        posts = [
            {'id':1, 'created_at':now, 'votes':0},
            {'id':2, 'created_at':now - 3600, 'votes':10},
            {'id':3, 'created_at':now - 3600 * 24 * 365, 'votes':1_000_000},
        ]
        self.assertEqual([p['id'] for p in rank_candidates(posts, now)], [2,1,3])

    def test_ties_are_deterministic(self):
        posts = [{'id':i, 'created_at':10, 'votes':0} for i in [1,3,2]]
        self.assertEqual([p['id'] for p in rank_candidates(posts, 20)], [3,2,1])


class FeedApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / 'feed.sqlite3')
        self.app = create_app({'TESTING':True, 'DATABASE':self.path, 'SEED_DEMO':False})
        self.client = self.app.test_client()
        conn = sqlite3.connect(self.path)
        now = int(time.time())
        with conn:
            conn.execute('INSERT INTO users VALUES (1,?,?,?,?)', ('synthetic', 'unusable', 'TestAlias', now))
            conn.executemany('INSERT INTO posts(id,user_id,title,body,category,created_at) VALUES (?,1,?,?,?,?)',
                             [(i, f'Synthetic story {i}', 'Test body for feed verification.', 'General', now-i) for i in range(1,26)])
        conn.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_snapshot_stays_stable_and_hidden_content_is_removed(self):
        first = self.client.get('/api/feed').json
        self.assertEqual(first['policy_version'], POLICY_VERSION)
        self.assertEqual(len(first['posts']), 20)
        first_ids = {post['id'] for post in first['posts']}
        conn = sqlite3.connect(self.path)
        with conn:
            conn.execute('UPDATE posts SET created_at=? WHERE id=25', (int(time.time())+100,))
            conn.execute('UPDATE posts SET hidden=1 WHERE id=21')
        conn.close()
        second = self.client.get('/api/feed', query_string={'cursor':first['next_cursor']}).json
        second_ids = [post['id'] for post in second['posts']]
        self.assertEqual(second_ids, [22,23,24,25])
        self.assertFalse(first_ids.intersection(second_ids))
        self.assertFalse(second['has_more'])
        fresh = self.client.get('/api/feed').json
        self.assertEqual(fresh['posts'][0]['id'], 25)

    def test_invalid_and_expired_cursors(self):
        self.assertEqual(self.client.get('/api/feed?cursor=invalid').status_code, 400)
        first = self.client.get('/api/feed').json
        conn = sqlite3.connect(self.path)
        with conn:
            conn.execute('UPDATE feed_snapshots SET expires=0')
        conn.close()
        self.assertEqual(self.client.get('/api/feed', query_string={'cursor':first['next_cursor']}).status_code, 410)

    def test_popular_uses_real_activity_and_distinct_repliers(self):
        initial = self.client.get('/api/popular').json
        self.assertEqual(initial['mode'], 'opening')
        self.assertEqual(len(initial['posts']), 5)
        conn = sqlite3.connect(self.path)
        with conn:
            conn.execute('INSERT INTO votes VALUES (1,1)')
            conn.executemany('INSERT INTO comments(post_id,user_id,body,created_at) VALUES (2,1,?,?)',
                             [('Repeated synthetic reply', int(time.time()))] * 5)
        popular = self.client.get('/api/popular').json
        self.assertEqual(popular['mode'], 'popular')
        self.assertEqual([p['id'] for p in popular['posts']], [1,2])
        self.assertEqual(popular['posts'][1]['comments'], 5)
        with conn:
            conn.execute('UPDATE posts SET hidden=1 WHERE id=1')
        conn.close()
        self.assertEqual([p['id'] for p in self.client.get('/api/popular').json['posts']], [2])

    def test_feed_ignores_client_sort_and_search_and_keeps_identity_private(self):
        result = self.client.get('/api/feed?q=nomatch&sort=top')
        self.assertEqual(len(result.json['posts']), 20)
        self.assertNotIn('password_hash', result.text)
        self.assertNotIn('user_id', result.text)
        self.assertNotIn('synthetic', result.text)
        search = self.client.get('/api/posts?q=nomatch')
        self.assertEqual(search.json['posts'], [])


if __name__ == '__main__':
    unittest.main()
