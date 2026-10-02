"""Explicitly fictional starter content. No manufactured users or engagement."""
import time
import secrets
from werkzeug.security import generate_password_hash


def seed(db):
    stories = [
        ('OvercaffeinatedPigeon', 'Manager mayhem', 'My manager scheduled a meeting to ask why we spend so much time in meetings.',
         'Forty-five minutes. Twelve people. A slide titled “Protecting our focus time”.\n\nThe action item? A weekly check-in to track how many meetings we’ve cut. I wish I was making this up. Anyway, see you all at the meeting about the meeting.'),
        ('UnmutedStapler', 'Office politics', 'Apparently “we’re a family” means I’m the unpaid therapist.',
         'I came here to make spreadsheets. Somehow I’m now mediating a cold war over who changed the shared playlist.\n\nPlease just let me do my extremely medium job and go home at a reasonable hour.'),
        ('QuietRaccoon', 'Small victories', 'I closed my laptop at 6. Nothing caught fire.',
         'No dramatic exit. No announcement. Just closed it, went for a walk, and ate dinner without refreshing my inbox.\n\nThe next morning, the company was still there. Wild concept. Trying it again tomorrow.'),
        ('CorporatePotato', 'Meeting purgatory', '“Quick sync” is the biggest lie in the English language.',
         'A quick sync became a deep dive, which became a parking lot, which somehow became a sprint.\n\nI’ve been sitting in the same chair for ninety minutes. How is there this much movement and no progress?'),
        ('FeralPaperclip', 'HR said what?', 'The burnout workshop has mandatory homework.',
         'We have to complete a wellbeing worksheet, log our relaxation goals, and present our personal resilience plan on Friday.\n\nI asked if having less work could be on the plan. Apparently that’s outside the scope of the workshop.'),
    ]
    for i, (alias, category, title, body) in enumerate(stories):
        user = db.execute('INSERT INTO users(login,password_hash,alias,created_at) VALUES (?,?,?,?)',
                          ('demo-' + secrets.token_hex(16), generate_password_hash(secrets.token_urlsafe(48)), alias, int(time.time())))
        db.execute('INSERT INTO posts(user_id,title,body,category,created_at,demo) VALUES (?,?,?,?,?,1)',
                   (user.lastrowid, title, body, category, int(time.time()) - (i + 1) * 3600))
    db.commit()
