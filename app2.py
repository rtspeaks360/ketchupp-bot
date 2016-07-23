import os
import sys
import json
import ast

import requests
from flask import Flask, request

page_recpient_id = 1162876460421056
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
          if recipient_id != page_recpient_id:
            if messaging_event["message"].__contains__("text"):
              message_text = messaging_event["message"]["text"]  # the message's text

              if messaging_event["message"].__contains__("quick_reply"):
                pass
              else:
                # send_text(recipient_id, get_name(recipient_id))
                # start_conversation(sender_id)
                process_message(sender_id, message_text)
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
            i_am_hungry(sender_id)
          if messaging_event["postback"]["payload"] == "DailyRecommendations" : 
            get_daily_recomendations(sender_id)
          if messaging_event["postback"]["payload"] == "FoodNews":
            pass
          if messaging_event["postback"]["payload"] == "Search":
            start_search_process(sender_id)
          if messaging_event["postback"]["payload"].startswith("ItemDetails"):
            get_item_details(sender_id, messaging_event["postback"]["payload"])
          if messaging_event["postback"]["payload"] == 'Ohk':
            send_text(sender_id, "Ohk!")


  return "ok", 200

def process_message(recipient_id, message_text):
  """This function processes the recieved text message and makes a call to the specific function according to the reply from the user and intent from the database."""
  try:
    intent = get_intent(recipient_id)
    if intent == "search_query":
      search_dish(recipient_id, message_text)
      return 0
    if intent == "del_location":
      update_botinfo(recipient_id, "del_location", message_text)
      start_search_process(recipient_id)
      return 0
    else :
      start_conversation(recipient_id)
      return 0
  except AttributeError:
    start_conversation(recipient_id)

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
    
    elements.append(get_element_for_card(product_cards[0]['cards'][0]))
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

def get_data_for_search_results(recipient_id, dish_name):
  """This function sends the data for search result message to the user."""

  user_data = get_user_data_db(recipient_id)

  url = API_URL + "dish_search_clicked"

  data_dsc_api = {
    "meal_time" : 'all',
    "veg_nonveg_ind" : "undefined",
    "city_name" : 'gurgaon',
    'del_loc_sf_name' : "sushant-lok-1",
    'sort_buy' : '0',
    'quick_buy' : '0',
    'restaurants' : '',
    'lower_price_limit' : '0',
    'upper_price_limit' : '500',
    'dish_name' : dish_name,
    'cuisine_name' : '',
    'is_available_now' : '0'
  }

  search_result_request = requests.post(url, data = data)

  product_cards = json.loads(search_result_request.content)['data']['cards']
  elements = []
  cards_with_quick_buy = []
  
  for card in product_cards:
    if card['is_available_now'] == 1 and card['is_quick_buy_enabled'] == 1:
      cards_with_quick_buy.append(card)

  for card in cards_with_quick_buy:
    elements.append(get_element_for_card(card))    

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

  return data

def search_dish(recipient_id, query):
  """This function sends user the resulting dishes from his her search."""

  url = API_URL + "search_bar"
  user_data = get_user_data_db(recipient_id)
  data = {
    'q' : query,
    'city_name' : "gurgaon",
    'type' : 'dishcuisine',
    'del_loc_sf_name' : user_data['del_location']
  }
  r = requests.post(url, data = data)
  r = json.loads(r.content)['data']
  print r
  if len(r) == 0:
    send_text(recipient_id, "Sorry, I couldn't find any thing with that name. Why don't you try something else!")
    set_intent(recipient_id, "")
  else:
    for t in r:
      if t['type'] == 'tag' or t['type'] == 'dish':
        data = get_data_for_search_results(recipient_id, t['name'])
        break
    send_message_gen(recipient_id, data)

def start_search_process(recipient_id):
  """This function is called whenever a user clicks on search dish cuisine button. This function starts the search process."""
  # data = get_user_data_db(recipient_id)
  # if data["del_location"] == None:
    # get_data_from_user(recipient_id, "Before we begin, I need to know your exact location so that i can show you more refined results", "del_location")

  get_data_from_user(recipient_id, "So, what is it it that you would like to have today.", "search_query")

def i_am_hungry(recipient_id):
  """This function is used to continue conversation when user chooses i am hungry option in the starting of conversion."""
  data = json.dumps({
    "recipient" : {
      "id" : recipient_id
    },
    "message" : {
      "attachment" : {
        "type" : "template",
        "payload" : {
          "template_type" : "button",
          "text" : "Ohk! Well, I'm always here to serve your hunger!",
          "buttons" : [
            {
              "type" : "postback",
              "title" : "Search dish/cuisine",
              "payload" : "Search"
            },
            {
              "type" : "postback",
              "title" : "No, not hungry!",
              "payload" : "StartFacts"
            },
            {
              "type" : "postback",
              "title" : "What others are having!",
              "payload" : "DailyRecommendations"
            }
          ]
        }
      }
    }
  })

  send_message_gen(recipient_id, data)

def start_conversation(recipient_id):
  """This is the function which begins the conservation with user from scratch."""

  user = get_user_data_db(recipient_id)

  if user == "User Not Found!":
    add_user_db(recipient_id)  
    user = get_user_data_db(recipient_id)
  print user

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

def get_data_from_user(recipient_id, question, intent):
  """This function sends user a quesrtion and updates the intent field according to the question."""
  set_intent(recipient_id ,intent)
  print get_intent(recipient_id)
  send_text(recipient_id, question)

def send_text(recipient_id, text):
  "This function takes user's recipient id and text as arguments and sends a text to the user."

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

def get_intent(recipient_id):
  """This function sends the set intent fetched from the database and returns string 'empty' if it is empty."""
  
  r = get_user_data_db(recipient_id)
  if r != 'User Not Found!':
    print r
    user_data = r
    if user_data['intent'] == None:
      return user_data['intent']
    else:
      return "empty"

def set_intent(recipient_id, intent):
  """This function takes intent as parameter and updates the intent field in db to facilitiate user communication."""
  
  update_user_data_db(recipient_id, "intent", intent)

def get_user_data_db(recipient_id):
  """This function gets current user data from the database."""

  url = API_URL + "get_botinfo"
  data = {
    "recp_id" : recipient_id
  }
  r = requests.post(url, data=data)
  if r.status_code == 200:
    user_data = json.loads(r.content)["data"]
    return user_data
  else :
    return "User Not Found!"

def update_user_data_db(recipient_id, key, value):
  """This function takes in user recipient id, key and value and updates the value of specific key given to the function in parameters."""

  entry = {}
  entry[key] = value
  entry["recp_id"] = recipient_id

  url = API_URL + "update_botinfo"
  
  r = requests.post(url, data = entry)

def get_name(recipient_id):
  """This function takes recipientr_id as argument and returns the name of the user."""
  if recipient_id != page_recpient_id:
    url = "https://graph.facebook.com/v2.6/" + recipient_id + "?fields=first_name&access_token=" + ACCESS_TOKEN
    user_info = requests.get(url)
    print recipient_id
    print user_info.content
    # print user_info.content
    # print json.loads(user_info.content)['first_name']
    name = json.loads(user_info.content)['first_name']
    print name
    return name
  else:
    return "page"

def add_user_db(recipient_id):
  """This function takes in user recipient id and adds the user in  database"""

  entry = {}
  entry["recp_id"] = recipient_id
  # entry["name"] = get_name(recipient_id)

  url = API_URL + "insert_botinfo"
  r = requests.post(url, data = entry)
  print r.content
  print "new user added"
  # update_user_data_db(recipient_id, 'city', 'Gurgaon')

def start_settings():
  """This function was used once to set the get started button and the greeting text."""

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