#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import sqlite3

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

conn = sqlite3.connect('pipeline.db')
c = conn.cursor()

print('='*70)
print('PIPELINE STATISTICS')
print('='*70)

# Places
c.execute('SELECT place_id, name FROM places')
places = c.fetchall()
print(f'\nPLACES: {len(places)} total')
for p in places:
    print(f'  - {p[1]}')

# Emails
c.execute('SELECT e.email, e.source, p.name FROM emails e JOIN places p ON e.place_id = p.place_id')
emails = c.fetchall()
print(f'\nEMAILS: {len(emails)} total')
for e in emails:
    print(f'  - {e[2]}: {e[0]} (source: {e[1]})')

# Success rate
places_with_email = len(set([e[2] for e in emails]))
total_places = len(places)
success_rate = (places_with_email / total_places * 100) if total_places > 0 else 0

print(f'\nSUCCESS RATE')
print(f'  Places with email: {places_with_email}/{total_places} ({success_rate:.1f}%)')

# By source
c.execute('SELECT source, COUNT(*) FROM emails GROUP BY source')
by_source = c.fetchall()
print(f'\nBY SOURCE')
for s in by_source:
    print(f'  - {s[0]}: {s[1]} emails')

conn.close()
print('='*70)
