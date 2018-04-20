import requests
import secrets
import json
import sqlite3 as sqlite
from requests_oauthlib import OAuth1
import plotly.plotly as py
import plotly.graph_objs as go
import sys
import codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
import webbrowser

yelpurl = "https://api.yelp.com/v3/businesses/search"
twitterurl = 'https://api.twitter.com/1.1/search/tweets.json'
TWITTER_CACHE_FNAME = "twitter_cache.json"
class Restaurant:
    def __init__(self, restaurant_dict_from_json):
        self.business_id = restaurant_dict_from_json['id']
        self.name = restaurant_dict_from_json['name']
        self.rating = restaurant_dict_from_json['rating']
        self.latitude = restaurant_dict_from_json['coordinates']['latitude']
        self.longitude = restaurant_dict_from_json['coordinates']['longitude']
        try:
            self.price = restaurant_dict_from_json['price']
        except:
            self.price = "NA"
        self.street_address = restaurant_dict_from_json['location']['address1']
        self.city = restaurant_dict_from_json['location']['city']
        self.state = restaurant_dict_from_json['location']['state']
        self.zip = restaurant_dict_from_json['location']['zip_code']
        self.phone = restaurant_dict_from_json['display_phone']

    def __str__(self):
        name_rating = "{}: {} stars \nPrice: {}".format(self.name, self.rating, self.price)
        address = "\n{}\n{}, {} {}".format(self.street_address, self.city, self.state, self.zip)
        phone = "\n{}".format(self.phone)
        return name_rating + address + phone

class Review:
    def __init__(self, row_from_reviews_db):
        self.rating = row_from_reviews_db[2]
        self.text_samp = row_from_reviews_db[3]
        self.url = row_from_reviews_db[4]
    def __str__(self):
        return ("Rating: {}\n\n{}\n\nSee full review at: {}\n--------------------".format(self.rating, self.text_samp, self.url))

class Tweet:
    def __init__(self, tweet_dict_from_json):
        self.text = tweet_dict_from_json['text']
        self.username = tweet_dict_from_json['user']['screen_name']
        self.id = tweet_dict_from_json['id_str']
        self.num_favorites = tweet_dict_from_json['favorite_count']
        self.num_retweets = tweet_dict_from_json['retweet_count']
        self.popularity_score = (int(self.num_favorites))+(int(self.num_retweets))
        self.date = tweet_dict_from_json['created_at']
        self.is_retweet = self.text[0:2] == "RT"

    def __str__(self):
        username_text = "@{}: {}\n".format(self.username, self.text)
        retweeted = "[retweeted {} times]\n".format(self.num_retweets)
        favorited = "[favorited {} times]\n".format(self.num_favorites)
        date = "[tweeted on {}]\n".format(self.date)
        sep = "-"*10 +"\n"
        return username_text + retweeted + favorited + date + sep

def get_address_from_user():
    user_address = input("Enter your current location (Format: City, State, ZipCode): ")
    return user_address

########### Gets Restaurant Information from API/Cache #################
try:
    cache_file = open('yelp_cache.json', 'r')
    cache_contents = cache_file.read()
    YELP_CACHE_DICTION = json.loads(cache_contents)
    cache_file.close()
except:
    YELP_CACHE_DICTION = {}

def make_yelp_request_using_cache(yelpurl, address):
    compact_address = address.replace(',', '').replace(' ', '')
    if compact_address in YELP_CACHE_DICTION:
        return YELP_CACHE_DICTION[compact_address]
    else:
        params_diction = {'term':'restaurants',
                        'location': address,
                        'radius': 16093,
                        'limit': 50}
        headers = {"Authorization":"Bearer {}".format(secrets.YELP_API_KEY)}
        response = requests.get(yelpurl, params_diction, headers=headers)
        YELP_CACHE_DICTION[compact_address] = json.loads(response.text)
        dumped_json_cache = json.dumps(YELP_CACHE_DICTION)

        fw = open('yelp_cache.json',"w")
        fw.write(dumped_json_cache)
        fw.close() # Close the open file
        return YELP_CACHE_DICTION[compact_address]

############# Gets Reviews Information from API/Cache ################
try:
    cache_file = open('review_cache.json', 'r')
    cache_contents = cache_file.read()
    REVIEWS_CACHE_DICTION = json.loads(cache_contents)
    cache_file.close()
except:
    REVIEWS_CACHE_DICTION = {}

def make_reviews_request_using_cache(business_id):
    review_url = 'https://api.yelp.com/v3/businesses/{}/reviews'.format(business_id)
    if review_url in REVIEWS_CACHE_DICTION.keys():
        return REVIEWS_CACHE_DICTION[review_url]
    else:
        params_diction = {'locale': 'en_US'}
        headers = {"Authorization":"Bearer {}".format(secrets.YELP_API_KEY)}
        response = requests.get(review_url, params_diction, headers=headers)
        REVIEWS_CACHE_DICTION[review_url] = json.loads(response.text)
        dumped_json_cache = json.dumps(REVIEWS_CACHE_DICTION)

        fw = open('review_cache.json',"w")
        fw.write(dumped_json_cache)
        fw.close() # Close the open file
        return REVIEWS_CACHE_DICTION[review_url]

############# Creates the DB ###############
def create_yelp_db():
    conn = sqlite.connect('restaurants.sqlite')
    cur = conn.cursor()
    statement = '''
        DROP TABLE IF EXISTS 'Restaurants';
    '''
    cur.execute(statement)
    conn.commit()
    statement = '''
        DROP TABLE IF EXISTS 'Reviews';
    '''
    cur.execute(statement)
    conn.commit()

    #try:
        # Your code goes here
    statement = '''
        CREATE TABLE 'Restaurants' (
            'BusinessId' TEXT PRIMARY KEY,
            'Name' TEXT NOT NULL,
            'Rating' REAL NOT NULL,
            'Latitude' REAL NOT NULL,
            'Longitude' REAL NOT NULL,
            'Price' TEXT,
            'StreetAddress' TEXT NOT NULL,
            'City' TEXT NOT NULL,
            'State' TEXT NOT NULL,
            'ZipCode' INTEGER,
            'Phone' TEXT,
            'SearchedAddress' TEXT
        );
    '''
    cur.execute(statement)
    #except:
    #    print("Could not initialize Restaurants table")
    try:
        statement = '''
            CREATE TABLE 'Reviews' (
                'ReviewId' TEXT PRIMARY KEY,
                'BusinessId' TEXT,
                'Rating' REAL NOT NULL,
                'TextSample' TEXT,
                'ReviewURL' TEXT NOT NULL
            );
        '''
        cur.execute(statement)
    except:
        print('Could not initialize Reviews table')
    conn.commit()
    conn.close()

######## Inserts current restaurant information into the DB #################
def fill_yelp_db(address):
    compact_address = address.replace(',', '').replace(' ', '')
    conn = sqlite.connect('restaurants.sqlite')
    cur = conn.cursor()

    cache_file = open('yelp_cache.json', 'r')
    cache_contents = cache_file.read()
    YELP_CACHE_DICTION = json.loads(cache_contents)
    cache_file.close()

    business_info = YELP_CACHE_DICTION[compact_address]['businesses']
    for row in business_info:
        if 'price' in row.keys():
            insertion = (row['id'], row['name'], row['rating'], row['coordinates']['latitude'], row['coordinates']['longitude'],
            row['price'], row['location']['address1'], row['location']['city'], row['location']['state'],
            row['location']['zip_code'], row['display_phone'], compact_address)
            statement = 'INSERT INTO "Restaurants" '
            statement += 'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)'
            cur.execute(statement, insertion)
        else:
            insertion = (row['id'], row['name'], row['rating'], row['coordinates']['latitude'], row['coordinates']['longitude'],
            None, row['location']['address1'], row['location']['city'], row['location']['state'],
            row['location']['zip_code'], row['display_phone'], compact_address)
            statement = 'INSERT INTO "Restaurants" '
            statement += 'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)'
            cur.execute(statement, insertion)
        conn.commit()

    statement = "SELECT BusinessId FROM Restaurants"
    cur.execute(statement)
    restaurants = cur.fetchall()
    statement= "SELECT ReviewId FROM Reviews"
    cur.execute(statement)
    review_ids = []
    for review in cur:
        review_ids.append(review[0])

    for row in restaurants:
        review_results = make_reviews_request_using_cache(row[0])
        for review in review_results['reviews']:
            # if review['id'] in review_ids:
            #     continue
            # else:
            insertion = (review['id'], row[0], review["rating"], review['text'], review['url'])
            statement = 'INSERT INTO "Reviews"'
            statement += 'VALUES (?, ?, ?, ?, ?)'
            cur.execute(statement, insertion)
    conn.commit()
    conn.close()

def create_twitter_search_term(business_id):
    conn = sqlite.connect('restaurants.sqlite')
    cur = conn.cursor()
    statement = "SELECT Name, City FROM RESTAURANTS WHERE BusinessId='{}'".format(business_id)
    cur.execute(statement)
    result = cur.fetchone()
    search_term = result[0]+" " +result[1]
    return search_term

try:
    cache_file = open(TWITTER_CACHE_FNAME, 'r')
    cache_contents = cache_file.read()
    TWITTER_CACHE_DICTION = json.loads(cache_contents)
    cache_file.close()

# if there was no file, no worries. There will be soon!
except:
    TWITTER_CACHE_DICTION = {}

def get_twitter_data(baseurl, search_term):
    consumer_key = secrets.CONSUMER_KEY
    consumer_secret = secrets.CONSUMER_SECRET
    access_token = secrets.ACCESS_KEY
    access_secret = secrets.ACCESS_SECRET
    unique_ident = search_term.replace(' ', '')

    global TWITTER_CACHE_FNAME
    if unique_ident in TWITTER_CACHE_DICTION:
        return TWITTER_CACHE_DICTION[unique_ident]

    ## if not, fetch the data afresh, add it to the cache,
    ## then write the cache to file
    else:
        # Make the request and cache the new data
        auth = OAuth1(consumer_key,consumer_secret, access_token, access_secret)
        params = {'q': search_term, 'count': 10, 'lang':'en'}
        resp = requests.get(baseurl, params, auth=auth)
        TWITTER_CACHE_DICTION[unique_ident] = json.loads(resp.text)
        dumped_json_cache = json.dumps(TWITTER_CACHE_DICTION)

        fw = open(TWITTER_CACHE_FNAME,"w")
        fw.write(dumped_json_cache)
        fw.close() # Close the open file
        return TWITTER_CACHE_DICTION[unique_ident]

def load_help_text():
    with open('help.txt') as f:
        return f.read()
############ Accesses Yelp API or cache to get restaurants, fill DB and print #################
#            results as formatted by Restaurants class and returns a list
#             of Restaurant instances
def get_restaurants(address):
    global yelpurl
    create_yelp_db()
    result = make_yelp_request_using_cache(yelpurl, address)
    restaurant_insts = []
    for restaurant in result['businesses']:
        restaurant_insts.append(Restaurant(restaurant))
    if __name__=="__main__":
        count = 1
        for restaurant in restaurant_insts:
            print('\n'+ str(count) + ". ")
            print(restaurant)
            count +=1
    fill_yelp_db(address)
    return restaurant_insts

############ Accesses Reviews table in DB to get reviews, converts to Reviews ##################
#              class object and prints results as formatted by Review class
#                   and returns a list of Review instances
def get_reviews(restaurants, idx):
    conn = sqlite.connect('restaurants.sqlite')
    cur = conn.cursor()

    restaurant = restaurants[idx-1]
    rest_id = restaurant.business_id
    statement = "SELECT * FROM Reviews WHERE BusinessId = '{}'".format(rest_id)
    cur.execute(statement)
    reviews = cur.fetchall()
    review_insts = []
    for review in reviews:
        review_insts.append(Review(review))
    if __name__=="__main__":
        for review in review_insts:
            print(review)
    conn.close()
    return review_insts

############ Accesses Twitter API or cache to get Tweets, converts to Tweet ##################
#              class object, prints results as formatted by Tweet class
#                   and returns a list of Tweet instances
def get_tweets(url, restaurants, idx):
    restaurant = restaurants[idx-1]
    search_term = create_twitter_search_term(restaurant.business_id)
    tweets = get_twitter_data(url, search_term)
    if tweets['statuses'] == []:
        print('Sorry, there are no tweets about this restaurant.')
        return None
    else:
        tweet_insts = []
        for tweet in tweets['statuses']:
            tweet_insts.append(Tweet(tweet))
        tweet_insts = sorted(tweet_insts, key = lambda x: x.popularity_score, reverse = True)
        if __name__=="__main__":
            for tweet in tweet_insts:
                print(tweet)
        return tweet_insts

#Creates pie chart in Plotly that shows the distribution of price in the active results set
def create_price_pie_chart():
    conn = sqlite.connect('restaurants.sqlite')
    cur = conn.cursor()

    statement = "SELECT Price, Count(*) FROM Restaurants GROUP BY Price"
    cur.execute(statement)
    counts = cur.fetchall()

    labels = []
    values = []
    for x in counts:
        if x[0] == None:
            continue
        labels.append(x[0])
        values.append(x[1])

    fig = {
    'data': [{'labels': labels,
              'values': values,
              'type': 'pie'}],
    'layout': {'title': 'Price Distribution in Area',
                'height': 500,
                'width': 1000}}
    py.plot(fig)
    conn.close()

#Creates a bar chart in Plotly which shows the distribution of ratings in the active results set
def create_ratings_bar():
    conn = sqlite.connect('restaurants.sqlite')
    cur = conn.cursor()

    statement = "SELECT Rating, Count(*) FROM Restaurants GROUP BY Rating"
    cur.execute(statement)
    ratings = cur.fetchall()
    x=[]
    y=[]
    for r in ratings:
        x.append(r[0])
        y.append(r[1])

    fig = {
    'data': [{'x': x,
              'y': y,
              'type': 'bar'}],
    'layout': {'title': 'Ratings Distribution in Area',
                'height': 500,
                'width': 1000}}
    py.plot(fig)

#Creates bar chars in Plotly which show the distribution of ratings based on price
def create_ratings_box():
    conn = sqlite.connect('restaurants.sqlite')
    cur = conn.cursor()

    statement = "SELECT Rating, Price FROM Restaurants"
    cur.execute(statement)
    ratings = cur.fetchall()

    ratings_by_price = {}
    for r in ratings:
        if r[1] == None:
            continue
        elif r[1] in ratings_by_price:
            ratings_by_price[r[1]].append(r[0])
        else:
            ratings_by_price[r[1]] = [r[0]]
    traces = []
    for k in ratings_by_price.keys():
        trace = go.Box(
            y=ratings_by_price[k],
            name = k,
            boxpoints = 'suspectedoutliers'
        )
        traces.append(trace)
    data = traces
    layout = go.Layout(
    title = "Box Plots for Ratings Based on Price",
    height = 500,
    width = 1000
    )

    fig = go.Figure(data=data,layout=layout)
    py.plot(fig, filename = "Box Plot Ratings on Price")

#Creates a scattter map in Plotly of the locations of the restaurants in the active results set
def create_map():
    conn = sqlite.connect('restaurants.sqlite')
    cur = conn.cursor()

    statement = "SELECT Name, Latitude, Longitude FROM Restaurants"
    cur.execute(statement)
    locations = cur.fetchall()
    mapbox_token = secrets.mapbox_token
    lats = []
    longs = []
    names = []
    for loc in locations:
        lats.append(loc[1])
        longs.append(loc[2])
        names.append(loc[0])
    mean_lat = sum(lats) / float(len(lats))
    mean_long = sum(longs) / float(len(longs))

    data = go.Data([
        go.Scattermapbox(
            lat=lats,
            lon=longs,
            mode='markers',
            marker=go.Marker(
                size=12
            ),
            text=names,
             )])
    layout = go.Layout(
        autosize=True,
        hovermode='closest',
        mapbox=dict(
            accesstoken=mapbox_token,
            bearing=0,
            center=dict(
                lat=mean_lat,
                lon=mean_long
            ),
            pitch=0,
            zoom=12
        ), height= 500,
        width= 1000)

    fig = dict(data=data, layout=layout)
    py.plot(fig, filename='Mapbox')

if __name__=="__main__":
    print("Welcome to the Restaurant Search Tool!")
    while True:
        user_command = input("Please enter a command ('help' for available commands): ")
        if user_command == "get restaurants":
            address = get_address_from_user()
            rest_results = get_restaurants(address)

        elif "get reviews" in user_command:
            try:
                user_command_splt = user_command.split()
                reviews = get_reviews(rest_results, int(user_command_splt[2]))
            except:
                print("Please activate a set of restaurant results with 'get restaurants'\n")

        elif "see full review" in user_command:
            user_command_splt = user_command.split()
            idx = int(user_command_splt[3])
            webbrowser.open(reviews[idx-1].url)

        elif "get tweets" in user_command:
            try:
                user_command_splt = user_command.split()
                get_tweets(twitterurl, rest_results, int(user_command_splt[2]))
            except:
                print("Please activate a set of restaurant results with 'get restaurants'\n")

        elif user_command == "price pie chart":
            create_price_pie_chart()

        elif user_command == "rating bar chart":
            create_ratings_bar()

        elif user_command == "rating boxplot by price":
            create_ratings_box()

        elif user_command == "create map":
            create_map()

        elif user_command == 'help':
            helptxt = load_help_text()
            print(helptxt)

        elif user_command == 'exit':
            print("Goodbye!")
            break
