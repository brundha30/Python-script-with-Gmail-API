# -*- coding: utf-8 -*-
"""
Created on Sun May 14 13:54:58 2023

@author: LENOVO
"""

import os
import base64
import email
import re
import datetime
import mysql.connector
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow


MYSQL_HOST = 'localhost'
MYSQL_USER = 'Brundha'
MYSQL_PASSWORD = 'bru30'
MYSQL_DATABASE = 'email_db'


creds = None
if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/gmail.readonly'])
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', ['https://www.googleapis.com/auth/gmail.readonly'])
        creds = flow.run_local_server(port=0)
    with open('token.json', 'w') as token:
        token.write(creds.to_json())


service = build('gmail', 'v1', credentials=creds)


results = service.users().messages().list(userId='me', q='in:inbox').execute()
messages = results.get('messages', [])


db = mysql.connector.connect(
    host=MYSQL_HOST,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DATABASE
)
cursor = db.cursor()

for message in messages:
    msg = service.users().messages().get(userId='me', id=message['id']).execute()
    payload = msg['payload']
    headers = payload['headers']
    
    
    sender = None
    for header in headers:
        if header['name'] == 'From':
            sender = header['value']
            break
    if sender is None:
        continue
    
    
    subject = None
    for header in headers:
        if header['name'] == 'Subject':
            subject = header['value']
            break
    
    
    date = None
    for header in headers:
        if header['name'] == 'Date':
            date = header['value']
            break
    if date is None:
        continue

    
    body = ''
    parts = payload.get('parts')
    if parts:
        for part in parts:
            data = part.get('body')
            if data.get('data') is not None:
                body = base64.urlsafe_b64decode(data.get('data')).decode()
            else:
                body = ""

   
    sql = "INSERT INTO email (sender, subject, body, date) VALUES (%s, %s, %s, %s)"
    date_str = "Mon, 15 May 2023 18:09:46 +0000"
    date_obj = datetime.datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
    date_mysql = date_obj.strftime('%Y-%m-%d %H:%M:%S')
    values = (sender, subject, body, date_mysql)
    cursor.execute(sql, values)



db.commit()
cursor.close()
db.close()

print("Finished storing emails in the database.")

