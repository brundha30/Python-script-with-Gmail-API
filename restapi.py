# -*- coding: utf-8 -*-
"""
Created on Tue May 16 12:14:51 2023

@author: LENOVO
"""


import os
import base64
import email
import re
import json
import datetime
import sys
import mysql.connector
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from http.server import BaseHTTPRequestHandler, HTTPServer


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

def process_emails():
    with open('rules.json') as f:
        rules = json.load(f)
        return
    
    
    query = 'is:unread'
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])
    
   
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        headers = msg['payload']['headers']
        body = msg['payload']['body'].get('data', '')
        date_received = datetime.fromtimestamp(int(msg['internalDate'])/1000.0)
        
        
        for rule in rules:
            if rule['predicate'] == 'All':
                match = all(check_condition(headers, body, date_received, condition) for condition in rule['conditions'])
            else:
                match = any(check_condition(headers, body, date_received, condition) for condition in rule['conditions'])
            
            
            if match:
                for action in rule['actions']:
                    if action == 'Mark as read':
                        mark_as_read(service, message['id'])
                    elif action == 'Mark as unread':
                        mark_as_unread(service, message['id'])
                    elif action.startswith('Move to'):
                        label_name = action.split(' ')[-1]
                        move_to_label(service, message['id'], label_name)

def check_condition(headers, body, date_received, condition):
    field_name = condition['field']
    predicate = condition['predicate']
    value = condition['value']
    
    if field_name == 'From':
        field_value = get_header_value(headers, 'From')
    elif field_name == 'To':
        field_value = get_header_value(headers, 'To')
    elif field_name == 'Subject':
        field_value = get_header_value(headers, 'Subject')
    elif field_name == 'Message':
        field_value = base64.urlsafe_b64decode(body).decode('utf-8')
    elif field_name == 'Received Date/Time':
        if predicate in ['Less than', 'Greater than']:
            if predicate == 'Less than':
                match = date_received < (datetime.today() - timedelta(days=value))
            else:
                match = date_received > (datetime.today() - timedelta(days=value))
            return match
        else:
         field_value = date_received.strftime('%Y-%m-%d %H:%M:%S')
    else:
        return False
    
    if predicate == 'Contains':
        return value in field_value
    elif predicate == 'Does not contain':
        return value not in field_value
    elif predicate == 'Equals':
        return value == field_value
    elif predicate == 'Does not equal':
        return value != field_value
    else:
        return False

def get_header_value(headers, name):
    for header in headers:
        if header['name'] == name:
            return header['value']
    return ''

def mark_as_read(service, message_id):
    message_labels = {'removeLabelIds': ['UNREAD'], 'addLabelIds': []}
    try:
        service.users().messages().modify(userId='me', id=message_id, body=message_labels).execute()
        print(f'Marked message with id {message_id} as read.')
    except HttpError as error:
        print(f'An error occurred: {error}')

def mark_as_unread(service, message_id):
    message_labels = {'addLabelIds': ['UNREAD'], 'removeLabelIds': []}
    try:
        service.users().messages().modify(userId='me', id=message_id, body=message_labels).execute()
        print(f'Marked message with id {message_id} as unread.')
    except HttpError as error:
        print(f'An error occurred: {error}')

def move_to_label(service, message_id, label_name):
    label_id = get_label_id(service, label_name)
    if label_id is None:
        print(f'Label {label_name} not found.')
        return
    
    message_labels = {'addLabelIds': [label_id], 'removeLabelIds': []}
    try:
        service.users().messages().modify(userId='me', id=message_id, body=message_labels).execute()
        print(f'Moved message with id {message_id} to label {label_name}.')
    except HttpError as error:
        print(f'An error occurred: {error}')

def get_label_id(service, label_name):
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    for label in labels:
        if label['name'] == label_name:
            return label['id']
    return None


print("Finished processing mails.")


class APIServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/emails':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            emails = ["email1@example.com", "email2@example.com"]
            response = {"emails": emails}
            response_json = json.dumps(response)

            self.wfile.write(response_json.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/emails':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, APIServer)
    print('Starting the server on port 8000...')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('Stopping the server...')
        httpd.server_close()
        sys.exit(0)
           
if __name__ == '__main__':
    process_emails()
    run_server()