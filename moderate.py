"""Operator CLI: inspect reports and hide/restore stories. No public admin API."""
import argparse
import json
import os
from pathlib import Path
from database import Database

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=['reports', 'hide', 'restore'])
parser.add_argument('post_id', type=int, nargs='?')
parser.add_argument('--database', default=os.getenv('DATABASE_URL', str(Path(__file__).parent / 'instance' / 'aym.sqlite3')))
args = parser.parse_args()
if not args.database.startswith(('postgres://', 'postgresql://')) and not Path(args.database).is_file():
    parser.error('Database does not exist. Run the app first.')
db = Database(args.database)
if args.action == 'reports':
    for row in db.execute('SELECT r.id,r.post_id,r.reason,r.created_at,p.title,p.hidden FROM reports r '
                          'JOIN posts p ON p.id=r.post_id ORDER BY r.created_at DESC'):
        print(json.dumps(dict(row), ensure_ascii=True))
else:
    if args.post_id is None:
        parser.error('A post ID is required for hide/restore.')
    cursor = db.execute('UPDATE posts SET hidden=? WHERE id=?', (args.action == 'hide', args.post_id))
    db.commit()
    if not cursor.rowcount:
        parser.error('No story found with that ID.')
    print(dict(db.execute('SELECT id,title,hidden FROM posts WHERE id=?', (args.post_id,)).fetchone()))
db.close()
