import unittest
from restaurants import *
import sqlite3 as sqlite
DBNAME = 'restaurants.sqlite'

class TestDataAccess(unittest.TestCase):
    def test_yelp_api(self):
        global yelpurl
        result1 = make_yelp_request_using_cache(yelpurl, "Ann Arbor, MI 48104")
        result2 = make_yelp_request_using_cache(yelpurl, "Chicago, IL 60601")
        self.assertEqual(result1['businesses'][0]['name'], 'eat')
        self.assertEqual(result1['businesses'][-1]['coordinates']['latitude'], 42.298577940426)
        self.assertTrue(result2['businesses'][0]['display_phone'] == '(312) 464-1744')
        self.assertEqual(len(result1['businesses']), 50)
        self.assertEqual(len(result2['businesses']), 50)

    def test_review_api(self):
        #should access reviews for the Purple Pig in Chicago, IL
        reviews1 = make_reviews_request_using_cache('boE4Ahsssqic7o5wQLI04w')
        self.assertIn("The Purple Pig", reviews1['reviews'][1]['text'])
        self.assertEqual(reviews1['reviews'][0]['id'], "CFNIT8Ei7I0Savuf2lYWkw")

    def test_twitter_api(self):
        tweets1 = get_twitter_data(twitterurl, 'Zingermans Delicatessen Ann Arbor')
        self.assertTrue(len(tweets1['statuses']) <= 10)

class TestDatabase(unittest.TestCase):
    def test_db_tables(self):
        conn = sqlite.connect(DBNAME)
        cur = conn.cursor()
        create_yelp_db()
        fill_yelp_db("Chicago, IL 60601")

        sql = 'SELECT City FROM Restaurants'
        results = cur.execute(sql)
        result_list = results.fetchall()
        self.assertIn(('Chicago',), result_list)
        self.assertEqual(len(result_list), 50)

        sql = ' SELECT Rating From Reviews'
        results = cur.execute(sql)
        review_list = results.fetchall()
        self.assertTrue(type(review_list[0][0])==float)
        self.assertTrue(len(review_list)<=150)
        conn.close()

class TestClasses(unittest.TestCase):
    def test_restaurant_class(self):
        restaurant_insts = get_restaurants("Chicago, IL 60601")
        self.assertEqual(restaurant_insts[0].business_id, 'boE4Ahsssqic7o5wQLI04w')
        self.assertEqual(restaurant_insts[49].rating, 4.0)

    def test_review_class(self):
        restaurant_insts = get_restaurants("Chicago, IL 60601")
        review_insts = get_reviews(restaurant_insts, 1)
        self.assertEqual(review_insts[0].rating, 5.0)
        self.assertEqual(len(review_insts), 3)

    def test_tweet_class(self):
        global twitterurl
        restaurant_insts = get_restaurants("Chicago, IL 60601")
        tweet_insts = get_tweets(twitterurl, restaurant_insts, 1)
        self.assertTrue(tweet_insts[0].popularity_score >= tweet_insts[1].popularity_score)
        self.assertTrue(len(tweet_insts)<=10)
unittest.main()
