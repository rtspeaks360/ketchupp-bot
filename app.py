import os
import sys
import json

import requests
from flask import Flask, request

ACCESS_TOKEN = "EAAELIKjsjMMBAGccJE5hLlpRisgwy0d2ZCwS3FljHnDpLzhXdcf5JSfQpktdOsLjWfi3ZBCdVWThg4ZC5L4CZAQ0b5VBvK9wVARyxlqi3morSWre4Ri8VVuCKL542Uu5qLHwaNaE018zJvONHIbM0zKmBD6STI40OoX5YeKm5QZDZD"
VERIFY_TOKEN = "secret_key"

app = Flask(__name__)

@app.route('/', methods=['GET'])
def verify():
  # when the endpoint is registered as a webhook, it must
  # return the 'hub.challenge' value in the query arguments
  if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
    if not request.args.get("hub.verify_token") == VERIFY_TOKEN:
      return "Verification token mismatch", 403
    print "verified"
    return request.args["hub.challenge"], 200

  return "Hello world", 200

@app.route('/', methods=['POST'])
def webook():

  # endpoint for processing incoming messaging events

  data = request.get_json()
  print json.dumps(data, indent = 2, sort_keys = True)
  if data["object"] == "page":

    for entry in data["entry"]:
      for messaging_event in entry["messaging"]:

        if messaging_event.get("message"):  # someone sent us a message
          print "message recieved"
          sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
          recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
          if messaging_event["message"].__contains__("text"):
            message_text = messaging_event["message"]["text"]  # the message's text


          # if messaging_event["message"].__contains__('quick_reply'):
          #   if messaging_event["message"]["quick_reply"]['payload'] == 'start_conversation':
          #     print "start_conversation"
          #     start_conversation(sender_id)

          #   if messaging_event["message"]["quick_reply"]['payload'] == 'end_conversation':
          #     print "ending_conversation"
          #     end_conversation(sender_id) 
          # else:
          #   send_message(sender_id)

            # pass
          start_conversation(sender_id)
          # send_message(sender_id)
          # get_user_query(sender_id)

        if messaging_event.get("delivery"):  # delivery confirmation
          pass

        if messaging_event.get("optin"):  # optin confirmation
          pass


          
        if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
          sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
          recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID

          if messaging_event.get("postback")['payload'] == 'fetch_daily_recomendations':
            print "\nfetching daily recomendations!\n"
            get_daily_recomendations(sender_id)

          if messaging_event.get("postback")['payload'] == 'dish_cuisine_search':
            print "\nfetching daily recomendations!\n"

          if messaging_event.get("postback")['payload'] == 'get_item_details':
            pass

          if messaging_event.get("postback")['payload'] == 'order_item':
            pass  

  return "ok", 200

def get_daily_recomendations(recipient_id):
  params = {
    "access_token": ACCESS_TOKEN
  }
  headers = {
    "Content-Type": "application/json"
  }
  data = json.dumps({
    "recipient" : {
      "id": recipient_id
    },
    "message": {
      "attachment": {
        "type": "template",
        "payload": {
          "template_type": "generic",
          "elements": [
            {
              "title": "Paneer Kathi Roll with Lacha Parantha : Rs 95",
              "image_url": "http://d33oocx83zywzt.cloudfront.net/img400/10100406126.jpg",
              "subtitle": "paneer kathi roll served with lachha parantha",
              "buttons": [
                {
                  "type" : "postback",
                  "title" : "View Item",
                  "payload": "get_item_details"
                },
                {
                  "type" : "postback",
                  "title": "Order Now",
                  "payload": "order_item"
                },
                {
                  "type": "web_url",
                  "title": "View On ketchupp.",
                  "url": "http://www.ketchupp.in/gurgaon/DLF-Phase-1/dck-dana-chogas-kitchen-dlf-phase-1/Paneer-Kathi-Roll-with-Lacha-Parantha"
                } 
              ]
            }
          ]
        }
      }
    }
  })    

  r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
  print r
  if r.status_code != 200:
    print r.status_code
    print r.text

def get_user_query(recipient_id):
  params = {
    "access_token": ACCESS_TOKEN
  }
  headers = {
    "Content-Type": "application/json"
  }
  data = json.dumps({
    "recipient" : {
      "id": recipient_id
    },
    "message" : {
      "text" : "What is query today?"
    },
    "postback": {
      "payload" : "fetch_daily_recomendations"
    }
  })
  print "Starting conversation and sending message to {recipient}".format(recipient=recipient_id)
  r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
  print r
  if r.status_code != 200:
    print r.status_code
    print r.text

# def process_message():
#   pass

def start_conversation(recipient_id):

  # print "sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text)
  # name = get_name(recipient_id)
  params = {
    "access_token": ACCESS_TOKEN
  }
  headers = {
    "Content-Type": "application/json"
  }
  data = json.dumps({
    "recipient" : {
      "id": recipient_id
    },
    "message": {
      "attachment" : {
        "type" : "template",
        "payload":{
          "template_type": "button",
          "text": "What would you like to see right now?",
          "buttons":[
            {
              "type": "postback",
              "title": "Daily Recomendations",
              "payload": "fetch_daily_recomendations"
            },
            {
              "type": "postback",
              "title": "Dish/Cuisine Search",
              "payload": "dish_cuisine_search"              
            },
            {
              "type": "web_url",
              "title": "Visit more at ketchupp.in",
              "url" : "www.ketchupp.in"
            }
          ]
        }
      }
    }
  })
    

  print "Starting conversation and sending message to {recipient}".format(recipient=recipient_id)
  r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
  print r
  if r.status_code != 200:
    print r.status_code
    print r.text


def end_conversation(recipient_id):
  params = {
    "access_token": ACCESS_TOKEN
  }
  headers = {
    "Content-Type": "application/json"
  }
  data = json.dumps({
      "recipient" : {
        "id" : recipient_id
      },
      "message" : {
        "text" : "Sorry, I couldn't help you this time! You can come back later. We are soon coming to your city."
      }
    })
  
  print "Ending conversation and sending message to {recipient}".format(recipient=recipient_id)
  r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
  if r.status_code != 200:
    print r.status_code
    print r.text

def get_name(recipient_id):
  url = "https://graph.facebook.com/v2.6/" + recipient_id + "?fields=first_name&access_token=" + ACCESS_TOKEN
  user_info = requests.get(url)
  print user_info.content
  print json.loads(user_info.content)['first_name']
  name = json.loads(user_info.content)['first_name']
  print name
  return name

def send_message(recipient_id):
  # name = get_name(recipient_id)
  
  params = {
    "access_token": ACCESS_TOKEN
  }
  headers = {
    "Content-Type": "application/json"
  }
  
  data = json.dumps({
    "recipient" : {
      "id": recipient_id
    },
    "message" : {
      "text" : "Hi, I'm KetchuppBot. I can get you anything you would like to get, but currently only in Gurgoan. Would you like to continue?", #% (get_name(recipient_id)),
      "quick_replies" : [
        {
          "content_type" : "text",
          "title" : "Yes, I'm in!",
          "payload" : "start_conversation"
        },
        {
          "content_type" : "text",
          "title" : "No",
          "payload" : "end_conversation"
        },
      ]
    }
  })

  print "sending message to {recipient}".format(recipient=recipient_id)
  r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
  if r.status_code != 200:
    print r.status_code
    print r.text


if __name__ == '__main__':
  app.debug = True
  app.run(host = '0.0.0.0', port = 5000)

  # else:
  #   data = json.dumps({
  #     "recipient": {
  #       "id": recipient_id
  #     },
  #     "message": {
  #       "text": "Sorry, Couldn't get you!"
  #     }
  #   })