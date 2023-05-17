# -*- coding: utf-8 -*-
"""
Created on Tue May 16 14:22:08 2023

@author: LENOVO
"""


from tkinter import *
from tkinter import messagebox
import base64
import email
import os
import re
import json
import datetime
import mysql.connector
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow


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


MYSQL_HOST = 'localhost'
MYSQL_USER = 'Brundha'
MYSQL_PASSWORD = 'bru30'
MYSQL_DATABASE = 'email_db'


db = mysql.connector.connect(
    host=MYSQL_HOST,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DATABASE
)
cursor = db.cursor()
    
def fetch_emails():
    try:
        results = service.users().messages().list(userId='me', labelIds=['INBOX']).execute()
        messages = results.get('messages', [])

        if not messages:
            print('No new messages.')
        else:
            print('Fetching emails...')
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                process_email(msg)
            print('Email processing completed.')

    except HttpError as error:
        print(f'An error occurred: {error}')


def process_email(msg):
    try:
        payload = msg['payload']
        headers = payload['headers']

        
        sender = get_header_value(headers, 'From')
        recipient = get_header_value(headers, 'To')
        subject = get_header_value(headers, 'Subject')
        received_date = datetime.datetime.fromtimestamp(int(msg['internalDate'])/1000)

        
        rules = load_rules_from_json()
        for rule in rules:
            if rule['predicate'] == 'All':
                match_all_conditions = True
                for condition in rule['conditions']:
                    if not check_condition(condition, sender, recipient, subject, received_date):
                        match_all_conditions = False
                        break

                if match_all_conditions:
                    perform_actions(rule['actions'], msg['id'])
                    break

            elif rule['predicate'] == 'Any':
                match_any_condition = False
                for condition in rule['conditions']:
                    if check_condition(condition, sender, recipient, subject, received_date):
                        match_any_condition = True
                        break

                if match_any_condition:
                    perform_actions(rule['actions'], msg['id'])
                    break

    except Exception as e:
        print(f'Error processing email: {e}')


def get_header_value(headers, field_name):
    for header in headers:
        if header['name'] == field_name:
            return header['value']
    return ''


def check_condition(condition, sender, recipient, subject, received_date):
    field_name = condition['field_name']
    predicate = condition['predicate']
    value = condition['value']

    if field_name == 'From':
        return evaluate_predicate(sender, predicate, value)
    elif field_name == 'To':
        return evaluate_predicate(recipient, predicate, value)
    elif field_name == 'Subject':
        return evaluate_predicate(subject, predicate, value)
    elif field_name == 'Date received':
        if predicate == 'less than':
            return received_date < datetime.datetime.now() - datetime.timedelta(days=value)
        elif predicate == 'greater than':
            return received_date > datetime.datetime.now() - datetime.timedelta(days=value)
    return False


def evaluate_predicate(value, predicate, expected_value):
    if predicate == 'contains':
        return expected_value.lower() in value.lower()
    elif predicate == 'not equals':
        return value.lower() != expected_value.lower()
    elif predicate == 'does not contain':
        return expected_value.lower() not in value.lower()
    elif predicate == 'equals':
        return value.lower() == expected_value.lower()
    return False

def perform_actions(actions, email_id):
    for action in actions:
        if action == 'Mark as read':
            mark_as_read(email_id)
        elif action == 'Mark as unread':
            mark_as_unread(email_id)
        elif action == 'Move message':
           move_message(email_id, 'Inbox')
           
def mark_as_read(email_id):
    service.users().messages().modify(userId='me', id=email_id, body={'removeLabelIds': ['UNREAD']}).execute()

def mark_as_unread(email_id):
    service.users().messages().modify(userId='me', id=email_id, body={'addLabelIds': ['UNREAD']}).execute()

def move_message(email_id, mailbox):
    service.users().messages().modify(userId='me', id=email_id, body={'addLabelIds': [mailbox]}).execute()
    
def start_processing():
    fetch_emails()
    
def save_values():
    data = {}

    data['description'] = entry_0.get()
    data['condition'] = variable1.get()
    data['condition_options'] = variable2.get()
    data['subject'] = variable3.get()
    data['date_received'] = variable4.get()
    data['option1'] = variable5.get()
    data['option2'] = variable6.get()
    data['option3'] = variable7.get()
    data['entry_1'] = entry_1.get()
    data['entry_2'] = entry_2.get()
    data['entry_3'] = entry_3.get()
    data['action1'] = variable8.get()
    data['action2'] = variable9.get()
    data['mailbox'] = variable10.get()

    with open('rules.json', 'w') as file:
        json.dump(data, file)

def cancel():
    # Clear the entered values
    entry_0.delete(0, 'end')
    entry_1.delete(0, 'end')
    entry_2.delete(0, 'end')
    entry_3.delete(0, 'end')
   
top=Tk()
top.geometry('850x500')
top.title("Rules")


frame = Frame(top, width=1000, height=1000)
frame.pack()
frame.place(anchor='center', relx=0.5, rely=0.5)

label_0 = Label(top,text="Description:",width=15,font=("bold",12))
label_0.place(x=1,y=10)

entry_0=Entry(top,textvar=id,width=110)
entry_0.place(x=130,y=12)

label_1 = Label(top,text="If",width=7,font=("bold",12))
label_1.place(x=0,y=60)

options1 = ["All", "Any"]
variable1 = StringVar(top)
variable1.set("All")

w1 = OptionMenu(top, variable1, *options1)
w1.config(width=10, font=("bold", 9))
w1.place(x=80, y=55)

label_2 = Label(top,text="of the following conditions are met:",width=30,font=("bold",12))
label_2.place(x=200,y=60)

frame = Frame(top, bd=0, relief="solid" ,bg="white")
frame.place(x=80, y=120, width=700, height=150)

options2 = ["From", "To"]
variable2 = StringVar(top)
variable2.set("From")

w2 = OptionMenu(top, variable2, *options2)
w2.config(width=18, font=("bold", 9))
w2.place(x=100, y=130)

options3 = ["Subject"]
variable3 = StringVar(top)
variable3.set("Subject")

w3 = OptionMenu(top, variable3, *options3)
w3.config(width=18, font=("bold", 9))
w3.place(x=100, y=175)

options4 = ["Date received"]
variable4 = StringVar(top)
variable4.set("Date received")

w4 = OptionMenu(top, variable4, *options4)
w4.config(width=18, font=("bold", 9))
w4.place(x=100, y=220)

options5 = ["contains","not equals","does not contain","equals"]
variable5 = StringVar(top)
variable5.set("contains")

w5 = OptionMenu(top, variable5, *options5)
w5.config(width=18, font=("bold", 9))
w5.place(x=300, y=130)

options6 = ["contains","not equals","does not contain","equals"]
variable6 = StringVar(top)
variable6.set("not equals")

w6 = OptionMenu(top, variable6, *options6)
w6.config(width=18, font=("bold", 9))
w6.place(x=300, y=175)

options7 = ["greater than","is less than"]
variable7 = StringVar(top)
variable7.set("is less than")

w7 = OptionMenu(top, variable7, *options7)
w7.config(width=18, font=("bold", 9))
w7.place(x=300, y=220)

entry_1=Entry(top,textvar=StringVar(),width=15,bd= 4)
entry_1.place(x=500,y=135)

entry_2=Entry(top,textvar=StringVar(),width=15,bd=4)
entry_2.place(x=500,y=180)

entry_3=Entry(top,textvar=IntVar(),width=5,bd=4)
entry_3.place(x=500,y=225)

label_3 = Label(top,text="days old",width=10,font=("bold",10))
label_3.place(x=550,y=225)

def increment():
    value = int(entry_3.get())
    value += 1
    entry_3.delete(0, END)
    entry_3.insert(0, str(value))


def decrement():
    value = int(entry_3.get())
    value -= 1
    entry_3.delete(0, END)
    entry_3.insert(0, str(value))


minus_button = Button(top, text="-", font=("Arial", 12),height=1,width=2, command=decrement)
minus_button.place(x=720,y=215)

plus_button = Button(top, text="+", font=("Arial", 12),height=1,width=2, command=increment)
plus_button.place(x=750,y=215)


label_4 = Label(top,text="Perform the following actions:",width=30,font=("bold",12))
label_4.place(x=0,y=290)

frame = Frame(top, bd=0, relief="solid" ,bg="white")
frame.place(x=80, y=320, width=700, height=100)


options8 = ["Move message"]
variable8 = StringVar(top)
variable8.set("Move Message")

w8 = OptionMenu(top, variable8, *options8)
w8.config(width=18, font=("bold", 9))
w8.place(x=95, y=330)

options9 = ["Mark as read","Mark as unread"]
variable9 = StringVar(top)
variable9.set("Mark as read")

w9 = OptionMenu(top, variable9, *options9)
w9.config(width=18, font=("bold", 9))
w9.place(x=95, y=370)

label_5 = Label(top,text="to mailbox:",width=10,font=("bold",12))
label_5.place(x=300,y=333)

options10 = ["Inbox"]
variable10 = StringVar(top)
variable10.set("Inbox")

w10 = OptionMenu(top, variable10, *options10)
w10.config(width=15, font=("bold", 9))
w10.place(x=420, y=330)

button1=Button(top,text="Cancel",width=10,bd=5,command=cancel).place(x=580,y=430)

button2=Button(top,text="Ok",width=10,bd=5,command=save_values).place(x=690,y=430)


canvas = Canvas(top, width=50, height=50)
canvas.place(x=20,y=430)

canvas.create_oval(3, 3, 33, 33, fill="white")

canvas.create_text(18, 18, text="?", font=("Arial", 15), fill="black")

def on_button_click(event):
    top.geometry("200x200")
    messagebox.askyesno(" ","Help")

canvas.bind("<Button-1>", on_button_click)


top.mainloop()