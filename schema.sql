PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY, login TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
 alias TEXT UNIQUE NOT NULL, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), expires INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS posts (
 id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), title TEXT NOT NULL,
 body TEXT NOT NULL, category TEXT NOT NULL, created_at INTEGER NOT NULL,
 demo INTEGER NOT NULL DEFAULT 0, hidden INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS comments (
 id INTEGER PRIMARY KEY, post_id INTEGER NOT NULL REFERENCES posts(id),
 user_id INTEGER NOT NULL REFERENCES users(id), body TEXT NOT NULL, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS votes (
 post_id INTEGER NOT NULL REFERENCES posts(id), user_id INTEGER NOT NULL REFERENCES users(id),
 PRIMARY KEY(post_id,user_id)
);
CREATE TABLE IF NOT EXISTS reports (
 id INTEGER PRIMARY KEY, post_id INTEGER NOT NULL REFERENCES posts(id),
 user_id INTEGER NOT NULL REFERENCES users(id), reason TEXT NOT NULL, created_at INTEGER NOT NULL,
 UNIQUE(post_id,user_id)
);
CREATE TABLE IF NOT EXISTS rate_limits (
 bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, expires INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS posts_feed ON posts(hidden,created_at DESC);
CREATE INDEX IF NOT EXISTS comments_post ON comments(post_id,created_at);
CREATE TABLE IF NOT EXISTS feed_snapshots (
 token TEXT PRIMARY KEY, post_ids TEXT NOT NULL, policy_version TEXT NOT NULL,
 created_at INTEGER NOT NULL, expires INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS feed_snapshots_expiry ON feed_snapshots(expires);
