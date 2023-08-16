import json
import pickle
import random
from datetime import datetime
import csv

from yahooquery import Ticker
import sqlite3
import nltk
import numpy as np
from nltk.stem import WordNetLemmatizer
from tensorflow.keras.models import load_model
from newscatcher import Newscatcher, describe_url

con = sqlite3.connect('fred.db')
cur = con.cursor()


def tooManyAttempts():
    print("Lets do something else")
    listening()

def resetAgenda():
    cur.execute("DROP TABLE IF EXISTS AGENDA")
    cur.execute("CREATE TABLE agenda (title TEXT, week INT, day TEXT, time TEXT, reminder TEXT)")

def resetNews():
    cur.execute("DROP TABLE IF EXISTS news")
    cur.execute("CREATE TABLE news (name TEXT, url TEXT, follow TEXT) ")
    url_list = ['cnn.com', 'bbc.com', 'aljazeera.com', 'nu.nl', 'nos.nl', 'theguardian.com', 'independent.com',
            'telegraaf.nl', 'scmp.com']
    name_list = ['cnn', 'bbc', 'aljazeera', 'nu', 'nos', 'the guardian', 'independent', 'telegraaf',
             'south china morning post']
    for item1, item2 in zip(url_list, name_list):
        params = (item2, item1, 'no')
        cur.execute("INSERT INTO news VALUES(?,?,?)", params)
        con.commit()

def resetStocks():
    cur.execute("DROP TABLE IF EXISTS stocks")
    cur.execute("CREATE TABLE stocks (ticker TEXT, name TEXT, selected TEXT)")
    with open('nasdaq_100_stocks.csv') as nasdaq:
        csv_reader = csv.reader(nasdaq, delimiter=',')
        counter = 0
        for row in csv_reader:
            if counter == 0:
                print("Entering nasdaq info into db")
                counter += 1
            else:
                params = (row[0], row[1], "no")
                cur.execute("INSERT INTO stocks VALUES(?, ?, ?)", params)
                con.commit()
                counter += 1
        print("Succes")
    con.commit()

def agendaInsert():
    for attempt in range(5):
        try:
            print("Which date is your new appointment? Please use the following date format: 31/12/2023")
            dateInput = input("").lower()
            dateObject = datetime.strptime(dateInput, '%d/%m/%Y')
            date = dateObject.strftime('%d/%m/%Y')
            week = datetime.date(dateObject).isocalendar().week
        except ValueError:
            print("Please enter the correct date format")
        else:
            break
    else:
        tooManyAttempts()
    for attempt in range(5):
        try:
            print("What time is your appointment? Please use the following time format: 17:00")
            timeInput = input("").lower()
            timeObject =datetime.strptime(timeInput, '%H:%M').time()
            time = timeObject.strftime('%H:%M')
        except ValueError:
            print("Please enter the correct time format")
        else:
            break
    else:
        tooManyAttempts()
    print("What would you like to name this appointment?")
    title = input("").lower()
    print("Do you need an extra reminder in the same week?")
    reminder = input("").lower()
    params = (title, week, date, time, reminder)
    cur.execute("INSERT INTO agenda VALUES(?, ?, ?, ?, ?)", params)
    con.commit()
    print("Agenda updated succesfully")
    listening()

def stopFollowingStocks():
    for attempt in range(5):
        try:
            print("Which company would you like to stop following?")
            choice = input("").lower()
            option = cur.execute("SELECT name FROM stocks WHERE name LIKE ? ", ('%'+choice+'%', ))
            for row in option:
                company = row[0]
            print("Do you want to stop recieving stock updates from " + company + "?")
        except UnboundLocalError:
            print("You are not following this company's stocks")
        else:
            break
    else:
        tooManyAttempts()
    response = input("").lower()
    if (response == "yes"):
        cur.execute("UPDATE stocks SET selected = 'no' WHERE name = ?", (company,))
        con.commit()
        print("stock list updated")
        checkStocksUserFollows()
    else:
        print("Would you like to try again?")
        tryAgain = input("").lower()
        if(tryAgain == "yes"):
            stopFollowingStocks()
        else:
            listening()


def checkUserStocks():
    print("Sure thing, here is a list of the company's stocks you follow:")
    stocks = cur.execute("SELECT * FROM stocks WHERE selected = 'yes'")
    tickerList = []
    for row in stocks:
        tickerList.append(row[0])
    for ticker in tickerList:
        stock = Ticker(ticker)
        print(stock.calendar_events)

def checkStocksUserFollows():
    stocklist = cur.execute("SELECT name FROM stocks WHERE selected = 'yes'")
    if stocklist:
        print("You are following the stocks for the following companies:")
        for row in stocklist:
            print(row)
    else:
        print("You are not following any stocks")
        print("Would you like to add a company to follow?")
        response = input("").lower()
        if response == "yes":
            updateStockChoice()
        else:
            listening()


def updateStockChoice():
    print("Which nasdaq100 company would you like to follow?")
    choice = input("").lower()
    option = cur.execute("SELECT name FROM stocks WHERE name LIKE ? ", ('%'+choice+'%', ))
    for row in option:
        company = row[0]
    print("Do you want to recieve stock updates from " +company+"?")
    response = input("").lower()
    if (response == "yes"):
        cur.execute("UPDATE stocks SET selected = 'yes' WHERE name = ?", (company, ))
        con.commit()
        print("stock list updated")
        checkStocksUserFollows()
    else:
        print("no thanks")


def updateNewsFollow():
   print("Which news outlet would you like to follow?")
   choice = input("").lower()
   result = cur.execute("SELECT url FROM news WHERE name = ? ", (choice, ))
   for row in result:
      newsOutlet = row[0]
   print("Would you like to follow the news from " +newsOutlet+ "?")
   response = input("").lower()
   if (response == "yes"):
      cur.execute("UPDATE news SET follow = 'yes' WHERE url = ?", (newsOutlet,))
      con.commit()
      print("News sites updated")


def showNews():
   newsSites = cur.execute("SELECT url FROM news WHERE follow = 'yes'")
   for row in newsSites:
      url = row[0]
      mm = Newscatcher(website = url)
      for headline in enumerate(mm.get_headlines()):
         print(headline)


def enterTestData():
    cur.execute("UPDATE news SET follow = 'yes' WHERE name = 'bbc' ")
    con.commit()
    cur.execute("UPDATE news SET follow = 'yes' WHERE name = 'cnn'")
    con.commit()
    cur.execute("UPDATE stocks SET selected = 'yes' WHERE name = 'Apple Inc'")
    con.commit()
    cur.execute("UPDATE stocks SET selected = 'yes' WHERE name = 'Adobe inc'")
    con.commit()
    agendaInsert()



# load lemmatizer and the json file
lemmatizer = WordNetLemmatizer()
intents = json.loads(open('intents.json').read())

#load the pickle files
words = pickle.load(open('words.pkl', 'rb'))
classes = pickle.load(open('classes.pkl', 'rb'))
model = load_model('chatbot_model.h5')



# lemmatize the sentence the user inputs
def clean_up_sentence(sentence):
    sentence_words = nltk.word_tokenize(sentence)
    sentence_words = [lemmatizer.lemmatize(word) for word in sentence_words]
    return sentence_words

#create a bag of words with the lemmatized words for prediction
def bag_of_words(sentence):
    sentence_words = clean_up_sentence(sentence)
    bag = [0] * len(words)
    for w in sentence_words:
        for i, word in enumerate(words):
            if word == w:
                bag[i] = 1
    return np.array(bag)

#predict what kind of sentence the user puts in
def predict_class(sentence):
    bow = bag_of_words(sentence)
    res = model.predict(np.array([bow]))[0]
    ERROR_TRESHOLD = 0.5
    results = [[i, r] for i, r in enumerate(res) if r > ERROR_TRESHOLD]

    results.sort(key=lambda x: x[1], reverse=True)
    return_list = []
    for r in results:
        return_list.append({'intent': classes[r[0]], 'probabilty': str(r[1])})
        print(r[1])
        if r[1] < 0.6:
            listening()
    return return_list

# select a response based on the predicted tag
def get_response(intents_list, intents_json):
    tag = intents_list[0]['intent']
    list_of_intents = intents_json['intents']
    for i in list_of_intents:
        if i['tag'] == tag:
            result_sentence = random.choice(i['responses'])
            result_tag = tag
            break
    return result_sentence, result_tag

def listening():
    while True:
        print("What can i do for you?")
        message = input("")
        ints = predict_class(message)
        response = get_response(ints, intents)
        print(response[0])
        print(response[1])
        if response[1] == "stockCheck":
            checkUserStocks()
        elif response[1] == "newsSiteFollow":
            showNews()
        elif response[1] == "agendaInsert":
            agendaInsert()
        else:
            listening()




def startFred():
    print("Would you like an update on your agenda?")
    userResponse = input("").lower()
    if(userResponse == "yes"):
        now = datetime.now()
        currentWeekObject = now.strftime("%W")
        currentWeek = int(currentWeekObject)
        nextWeek = currentWeek +1
        params = (currentWeek,)
        params2 = (nextWeek,)
        agenda = cur.execute("SELECT * FROM agenda WHERE week = ?", params)
        for row in agenda:
            print(row)
        agenda2 = cur.execute("SELECT * FROM agenda WHERE week = ?", params2)
        for rows in agenda2:
            print(rows)
    else:
        listening()

listening()