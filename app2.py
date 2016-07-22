import os
import sys
import json
import ast

import requests
from flask import Flask, request

ACCESS_TOKEN = "EAAELIKjsjMMBAGccJE5hLlpRisgwy0d2ZCwS3FljHnDpLzhXdcf5JSfQpktdOsLjWfi3ZBCdVWThg4ZC5L4CZAQ0b5VBvK9wVARyxlqi3morSWre4Ri8VVuCKL542Uu5qLHwaNaE018zJvONHIbM0zKmBD6STI40OoX5YeKm5QZDZD"
VERIFY_TOKEN = "secret_key"
API_URL = "http://52.220.0.228/production/v1.1/"

app = Flask(__name__)

@app.route('/', methods = ['GET'])
def verify():
  # when the endpoint is registered as a webhook, it must
  # return the 'hub.challenge' value in the query arguments
  if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
    if not request.args.get("hub.verify_token") == VERIFY_TOKEN:
      return "Verification token mismatch", 403
    print "verified"
    return request.args["hub.challenge"], 200

  return "Hello world", 200

@app.route("/", methods = ['POST'])
def webhook():

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

          if messaging_event["message"].__contains__("quick_reply"):
            pass
          else:
            start_conversation(sender_id)
          # start_settings()
          # send_text("1030094417086995", " too!")

        if messaging_event.get("delivery"):  # delivery confirmation
          pass

        if messaging_event.get("echoes"):
          pass


        if messaging_event.get("optin"):  # optin confirmation
          pass


          
        if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
          sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
          recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
          
          if messaging_event["postback"]["payload"] == "IAmHungry" : 
            pass
          if messaging_event["postback"]["payload"] == "DailyRecommendations" : 
            get_daily_recomendations(sender_id)
          if messaging_event["postback"]["payload"] == "FoodNews":
            pass
          if messaging_event["postback"]["payload"].startswith("ItemDetails"):
            get_item_details(sender_id, messaging_event["postback"]["payload"])
          if messaging_event["postback"]["payload"] == 'Ohk':
            send_text(sender_id, "Ohk!")

  return "ok", 200



def get_data_from_payload_itemdetails(payload):
  """This function extracts the parameters for Item details request from the payload and returns a dictionary with required data to make a request to Ketchupp deals api."""

  entry = {}
  payload = payload.split('_')
  # entry['purpose'] = payload[0]
  entry['city_name'] = payload[1]
  entry['location_name'] = payload[2]
  entry['rest_name'] = payload[3]
  entry['dish_name'] = payload[4]

  return entry

def send_confirmation_message_item_detail_qb(recipient_id, dish_id, final_total):
  """This function sends a confirmation message to the user asking to continue to order a quickbuy enabled dish."""

  data = json.dumps({
    "recipient" : {
      "id" : recipient_id
    },
    "message" : {
      "text" : "This item would cost you " + u"\u20B9" + str(final_total) + ", would you like to place an order?",
      "quick_replies" : [
        {
          "content_type" : "text",
          "title" : "Yes! Let's do it.",
          "payload" : "OrderItem_" + str(dish_id)
        },
        {
          "content_type" : "text",
          "title" : "No",
          "payload" : "Ohk"
        }
      ]
    }
  })

  send_message_gen(recipient_id, data)

def send_pre_reciept(recipient_id, dish_id, avl_price, discounted_price):
  """This function generates the prereciept with tax details and discounted price and sends it to the user. It also returns the final total for the dish."""

  url = API_URL + "get_tax"
  params = {
    'dish_id' : dish_id 
  }
  response = requests.post(url, data = params)
  total_tax = json.loads(response.content)['total_tax']
  final_total = float(discounted_price) + float(("%.2f" % total_tax))  
  string = "--KETCHUPP PRE-RECIEPT--\nItem price : " + avl_price + "\nItem quantity : 1\nTotal price : " + str(avl_price) + "\nPrice after discount : " + str(discounted_price) + "\nTax(VAT + Service Tax) : " + str(("%.2f" % total_tax)) + "\nTotal : " + u"\u20B9" + str(final_total)

  data = json.dumps({
    "recipient" : {
      "id" : recipient_id
    },
    "message" : { 
      "text" : string
    }
  })

  send_message_gen(recipient_id, data)
  return final_total

def send_pd_details(recipient_id, avl_price, discounted_price, del_charge, del_time):
  """This function sends the available price, discounted price, Delivery fee and minimum delivery time to the user."""

  string = "Actual Price : " + u"\u20B9" + str(avl_price) + "\nDiscounted Price : " + u"\u20B9" + str(discounted_price) + "\n" 
  if del_charge != None:
    string = string + "Delivery Fee : " + u"\u20B9" + str(del_charge) + "\n" 
  print del_charge
  if del_time != None:
    string = string + "Delivery Time : " + str(del_time) + " mins"


  data = json.dumps({
    "recipient" : {
      "id" : recipient_id
    },
    "message" : {
      "text" : string
    }
  })

  send_message_gen(recipient_id, data)

def send_product_desc(recipient_id, description):
  """This function sends the description of the product to the user."""
  send_text(recipient_id, description)

def send_product_intro(recipient_id, dish_name, rest_name, price):
  """This funtion sends the product intro to the user when view item is clicked. Intro contains rest_name, dish_name, discounted_price from the deals api."""

  data = json.dumps({
    "recipient" : {
      "id" : recipient_id
    },
    "message" : {
      "text" : dish_name + " by " + rest_name + " | " + u"\u20B9" + str(price)
    }
  })

  send_message_gen(recipient_id, data)

def send_product_image(recipient_id, image_url):
  """This funtion sends the 650px product image to the user when view item is clicked."""

  data = json.dumps({
    "recipient" : {
      "id" : recipient_id
    },
    "message" : {
      "attachment" : {
        "type" : "image",
        "payload" : {
          "url" : "http://d33oocx83zywzt.cloudfront.net/img650/" + image_url + ".jpg"
        }
      }
    }
  })

  send_message_gen(recipient_id, data)

def get_dish_info_json(payload):
  """This function sends request to ketchupp deals api to get in order to get the details of a product according to payload.
  Payload format is  ItemDetails_city-sf-name_location-sf-name_restaurant-sf-name_dish-sf-name."""

  url = API_URL + "deals"
  data_for_dish = get_data_from_payload_itemdetails(payload)
  response = requests.post(url, data = data_for_dish)
  dish_details = json.loads(response.content)['data']
  # print json.dumps(dish_details, indent = 2, sort_keys = True)
  return dish_details

def get_item_details(recipient_id, payload):
  """This function sends the details of a product when ever user clicks on a View Item button."""
  item_details = get_dish_info_json(payload)
  send_product_image(recipient_id, item_details['image_url'])
  send_product_intro(recipient_id, item_details['dish_name'], item_details['rest_name'], item_details['discounted_price'])
  send_product_desc(recipient_id, item_details['description'])
  if item_details['is_quick_buy_enabled'] == 1:
    send_pd_details(recipient_id, item_details['price'], item_details['discounted_price'], item_details['available_store'][0]['del_fee'], item_details['available_store'][0]['del_time']) 
    final_total = send_pre_reciept(recipient_id, item_details['dish_id'], item_details['price'], item_details['discounted_price'])
    send_confirmation_message_item_detail_qb(recipient_id, item_details['dish_id'], final_total)

def get_element_for_card(card):
  """This functions sends the data for each card of daily recommendation dshes."""

  entry = {}

  if len(str(card['dish_name'])) <= 67:
    entry['title'] = card['dish_name'] + " | " + u"\u20B9" + card['price']
  elif len(str(card['dish_name'])) > 67:
    entry['title'] = card['dish_name'][0:63] + "... | " + u"\u20B9" + card['price']  
  entry["image_url"] = "http://d33oocx83zywzt.cloudfront.net/img400/" + card['image_url'] + ".jpg"
  entry["item_url"] = "http://www.ketchupp.in/" + card["city_sf_name"] + "/" + card["location_sf_name"] + "/" + card["restaurant_sf_name"] + "/" + card["dish_sf_name"]
  entry["subtitle"] = card["description"]
  entry["buttons"] = []
  entry["buttons"].append({
    "type" : "postback",
    "title" : "View Item",
    "payload" : "ItemDetails" + '_' + card['city_sf_name'] + '_' + card['location_sf_name'] + '_' + card['restaurant_sf_name'] + '_' + card['dish_sf_name']
  })
  if card['is_quick_buy_enabled'] == 1:
    entry["buttons"].append({
      "type" : "postback",
      "title" : "Quick Buy",
      "payload" : "order_item"
    })
  else:
    entry["buttons"].append({
      "type" : "web_url",
      "title" : "Order Now",
      "url" : entry['item_url']
    })

  entry['buttons'].append({
    "type" : "web_url",
    "title" : "View on ketchupp",
    "url" : entry['item_url']
  })
                

  return entry

def get_data_for_dr(recipient_id):
  """This is the function which gets all the daily reccomendations from the home sections api."""
  cards_with_quick_buy = []

  url = API_URL + "home_sections"

  data_dr_api = {
    "sf_name" : "food-coupons-offers-deals"
  }

  response = requests.post(url, data = data_dr_api)
  print response
  data = json.loads(response.content)

  product_cards = data['data']
  if len(product_cards) != 0 :
    for card in product_cards[0]['cards']:
      if card['is_available_now'] == 1 and card['is_quick_buy_enabled'] == 1:
        cards_with_quick_buy.append(card)
    
    elements = []
    
    for card in cards_with_quick_buy:
      elements.append(get_element_for_card(card))  
    
    # elements.append(get_element_for_card(product_cards[0]['cards'][0]))
    if len(elements) != 0:
      data = json.dumps({
        "recipient" : {
          "id": recipient_id
        },
        "message": {
          "attachment": {
            "type": "template",
            "payload": {
              "template_type": "generic",
              "elements": elements[0:5]
            }
          }
        }
      })
    else :
      data = json.dumps({
        "recipient" : {
          "id" : recipient_id
        },
        "message" : {
          "text" : "Sorry, no recomended dishes are available for order right now! :("
        }
      })      

  else : 
    data = json.dumps({
      "recipient" : {
        "id" : recipient_id
      },
      "message" : {
        "text" : "Sorry, no recomended dishes are available right now! :("
      }
    })

  return data

def get_daily_recomendations(recipient_id):
  """This is the function which sends the daily recommendations to the user."""

  params = {
    "access_token": ACCESS_TOKEN
  }
  headers = {
    "Content-Type": "application/json"
  }
  data = get_data_for_dr(recipient_id)
  
  r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
  print r
  if r.status_code != 200:
    print r.status_code
    print r.text

# def i_am_hungry(recipient_id):


def start_conversation(recipient_id):
  """This is the function which begins the conservation with user ffrom scratch."""

  data = json.dumps({
    "recipient" : {
      "id" : recipient_id,
    },
    "message" : {
      "attachment" : {
        "type" : "template",
        "payload" : {
          "template_type" : "button",
          "text" : "Hi, How are you today?",
          "buttons" : [
            {
              "type" : "postback",
              "title" : "I am hungry!",
              "payload" : "IAmHungry"
            },
            {
              "type" : "postback",
              "title" : "Trending Dishes",
              "payload" : "DailyRecommendations"
            },
            {
              "type" : "postback",
              "title" : "Trends in Food World",
              "payload" : "FoodNews"
            }
          ]
        }
      }
    }
  })

  send_message_gen(recipient_id, data)

def send_text(recipient_id, text):
  data = json.dumps({
    "recipient" : {
      "id" : recipient_id
    },
    "message" : {
      "text" : text
    }
  })

  send_message_gen(recipient_id, data)

def send_message_gen(recipient_id, data):
  """This function takes recpient_id and gen_data as input and makes a post request to send message to the user."""

  params = {
    "access_token": ACCESS_TOKEN
  }
  headers = {
    "Content-Type": "application/json"
  }

  print "sending message to {recipient}".format(recipient=recipient_id)
  r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
  if r.status_code != 200:
    print r.status_code
    print r.text

def start_settings():
  params = {
    "access_token" : ACCESS_TOKEN
  }
  headers = {
    "Content-Type" : "application/json"
  }
  data1 = {
    "setting_type" : "greeting",
    "greeting" : {
      "text" : "Hi from ketchupp!"
    }
  }
  data2 = {
    "setting_type" : "call_to_actions",
    "thread_state" : "new_thread",
    "call_to_actions" : [
      {
        "payload" : "StartConversation"
      }
    ]
  }

  r1 = requests.post("https://graph.facebook.com/v2.6/me/thread_settings", params=params, headers=headers, data=data1)
  if r1.status_code != 200:
    print r1.status_code
    print r1.text
  r2 = requests.post("https://graph.facebook.com/v2.6/me/thread_settings", params=params, headers=headers, data=data2)
  if r2.status_code != 200:
    print r2.status_code
    print r2.text


if __name__ == "__main__":
  
  app.debug = True
  app.run(host = '0.0.0.0', port = 5000)