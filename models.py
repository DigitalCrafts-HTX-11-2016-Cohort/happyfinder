"""
Module holds the object models, API calls, and db connections for the Happy
Hour app
"""
import json
import StringIO
import urllib
import pycurl
import config
import pg

# API Keys
# apikey = config.G_API_KEY
client_id = config.FS_CLIENT_ID
secret = config.FS_CLIENT_SECRET

class User(object):
    """
    User superclass. Stores basic lat / lon data for each user as a
    comma-separated string value
    """
    def __init__(self, lat='', lng=''):
        self.lat = lat
        self.lng = lng

class Place(object):
    """
    Place superclass. Gets various detail attributes from the Foursquare api
    using Curl. Generates based on internal ID for each venue.
    """
    location_id = 0
    venue_id = ''
    happy_hour = []
    name = ''
    lat = 0
    lng = 0
    website = ''
    price_level = 0
    rating = 0.0
    formatted_phone_number = ''
    formatted_address = []
    def __init__(self, location_id=0):
        self.location_id = location_id
        # Get local info from our db
        sql = "SELECT venue_id FROM happyhour.public.id_venue_id WHERE id = $1 LIMIT 1"
        self.venue_id = DbConnect.get_named_results(sql, True, self.location_id).venue_id
        sql = ("SELECT day_of_week, start_time, end_time FROM"
               " happyhour.public.id_times WHERE location_id = $1")
        self.happy_hour = DbConnect.get_named_results(sql, False, \
        self.location_id)

        # Curl to get Foursquare venue details
        url = ("https://api.foursquare.com/v2/venues/%s?client_id=%s&"
               "client_secret=%s&v=20170109" % \
               (self.venue_id, \
                client_id, \
                secret)
              )
        venue_details = ApiConnect.get_load(url).get('response', {}).get\
                        ('venue')
        self.name = venue_details.get('name', '')
        self.lat = venue_details.get('location', {}).get('lat', 0)
        self.lng = venue_details.get('location', {}).get('lng', 0)
        self.website = venue_details.get('url', '')
        self.price_level = venue_details.get('price', {}).get('tier', 0)
        self.rating = venue_details.get('rating', 0.0)
        self.formatted_phone_number = venue_details.get('contact', {}).get\
        ('formattedPhone', '')
        self.formatted_address = venue_details.get('location', {}).get\
        ('formattedAddress', [])
        # Log to console to check returns of API calls
        print ''
        print '***************************************************************'
        print 'name: %s' % self.name
        print 'venue_id: %s' % self.venue_id
        print 'lat: %d' % self.lat
        print 'lng: %d' % self.lng
        print 'website: %s' % self.website
        print 'price level: %d' % self.price_level
        print 'rating: %d' % self.rating
        print 'phone: %s' % self.formatted_phone_number
        print 'address: %s' % self.formatted_address
        print 'Happy Hour Times: %s' % self.happy_hour
        print '***************************************************************'

    def insert(self):
        """
        Inserts new venue records into our database.
        Is called by the save() method
        """
        # Insert into venues & coords tables
        sql = ("WITH venues AS (INSERT INTO happyhour.public.id_venue_id"
               " (venue_id) VALUES ($1) RETURNING id) INSERT INTO"
               " happyhour.pulic.coordinates (location_id, lat, lng) SELECT id,"
               " $2, $3 FROM venues RETURNING id"
              )
        query_result = DbConnect.get_named_results(sql, True, self.venue_id, \
                       self.lat, self.lng)
        self.location_id = query_result.id
        # Insert into happy hours time table
        # for day in self.happy_hour:
        #     day_num = day.day_of_week
        #     start = day.start_time
        #     end = day.end_time
        #     sql = ("INSERT INTO happyhour.public.id_times (location_id,"
        #            " day_of_week, start_time, end_time) VALUES"
        #            " ($1, $2, $3, $4)")
        #     query_result = DbConnect.get_named_results(sql, True, \
        #                    self.location_id, day_num, start, end)
        return self.location_id

    def update(self):
        """
        Updates an existing Place record. Is called by the save() method.
        """
        pass

    def save(self):
        """
        Saves to database, using either insert() or update() methods depending
        on whether or not result already exists in our database
        Args: self - uses self.location_id to determine whether to call insert()
                     or update()
        Returns: self.location_id
        """
        if self.location_id > 0:
            self.update()
        else:
            self.insert()
        return self.location_id

    def delete(self):
        """
        Sets deleted property in id_venue_id table to 1
        """
        pass

    @staticmethod
    def get_places(lat, lng, radius='1'):
        """
        Gets all places within a certain mile radius of a geo from DB
        Args: lat - comma-separated string of a float lat, e.g. '-29.67'
              lng - comma-separated string of a float lng, e.g. '95.43'
              radius(opt) - string of miles, min '1', default '1'
        Returns: list of Place object instances
        """
        # For more info on the below query, see:
        # http://www.movable-type.co.uk/scripts/latlong.html
        sql = ("SELECT location_id FROM happyhour.public.coordinates WHERE"
               " (acos(sin(lat * 0.0175) * sin($1 * 0.0175) + cos(lat *"
               " 0.0175) * cos($2 * 0.0175) * cos(($3 * 0.0175) - (lng *"
               " 0.0175))) * 3959 <= $4);"
              )
        venue_id_objects = DbConnect.get_named_results(sql, False, lat, lat, lng, radius)
        place_object_list = []
        for venue_row in venue_id_objects:
            place_instance = Place(venue_row[0])
            place_object_list.append(place_instance)
        return place_object_list

class Day(object):
    """
    Defines an individual day on which a Place has a Happy Hour
    """
    def __init__(self, day_time_id=0):
        self.day_time_id = id
        sql = ("SELECT location_id, day_of_week, start_time, end_time FROM"
               " happyhour.public.id_times WHERE id = $1")
        day_info = DbConnect.get_named_results(sql, True, self.day_time_id)
        if day_info:
            self.location_id = day_info.location_id
            self.day_of_week = day_info.day_of_week
            self.start_time = day_info.start_time
            self.end_time = day_info.end_time
        else:
            self.location_id = day_info.location_id
            self.day_of_week = day_info.day_of_week
            self.start_time = '00:00:00'
            self.end_time = 'OO:00:00'

    def insert(self):
        pass

    def update(self):
        pass

    def save(self):
        pass

    @staticmethod
    def get_days(location_id):
        """
        Gets a list of day objects based for each location_id
        """
        sql = "SELECT id FROM happyhour.public.id_times WHERE location_id = $1"
        day_id_list = DbConnect.get_named_results(sql, False, location_id)
        day_objects_list = []
        for day in day_id_list:
            day_object = Day(day[0])
            day_objects_list.append(day_object)
        return day_objects_list

class ApiConnect(object):
    """
    Holds Curl code to get info from our API partners
    """
    @staticmethod
    def get_load(api_call):
        """
        Performs Curl with PyCurl using the GET method. Opens/closes each conn.
        Args: Full URL for the API call
        Returns: getvalue of JSON load from API
        """
        response = StringIO.StringIO()
        c = pycurl.Curl()
        c.setopt(c.URL, api_call)
        c.setopt(c.WRITEFUNCTION, response.write)
        c.setopt(c.HTTPHEADER, ['Content-Type: application/json', \
        'Accept-Charset: UTF-8'])
        c.perform()
        c.close()
        json_values = json.loads(response.getvalue())
        response.close()
        return json_values

class DbConnect(object):
    """
    Collection of static methods that set up our DB connection and create
    generalized methods for running queries / establish and release
    connections in pSQL
    """
    @staticmethod
    def get_connection():
        """
        Sets up the postgreSQL connection by loading in params from config
        """
        return pg.DB(
            host=config.DBHOST,
            user=config.DBUSER,
            passwd=config.DBPASS,
            dbname=config.DBNAME
            )

    @staticmethod
    def escape(value):
        """
        Escapes apostrophes in SQL
        """
        return value.replace("'", "''")

    @staticmethod
    def get_named_results(sql, get_one, *args):
        """
        Opens a connection to the db, executes a query, gets results using
        pSQL's named_results, and then closes the connection.
        Args: query   - pSQL query as string
              get_one - Bool that determines whether list or first
                        result of list are returned (default = False)
              *args   - pass in as many parameters for the query as needed
        Returns: the fetchOne or fetchAll of the query
        """
        conx = DbConnect.get_connection()
        query = conx.query(sql, *args)
        results = query.namedresult()
        if get_one:
            results = results[0]
        conx.close()
        return results

"""
*****
* Code We Still Need For Other Stuff
*****
# Curl to get Foursquare Happy String
        url = ("https://api.foursquare.com/v2/venues/%s/menu?client_id=%s&client_secret=%s&v=20170109 % (self.venue_id, client_id, secret)
        happy_strings = ApiConnect.get_load(url)
        self.happy_string = ''
        self.has_happy_hour = False
        for menu in happy_strings.get('response').get('menu').get('menus')\
        .get('items', [{'name': '', 'description': ''}]):
            if 'happy hour' in str(menu.get('name', '')).lower() or \
            'happy hour' in str(menu.get('description', '')).lower():
                self.happy_string = menu.get('description').lower()
                self.has_happy_hour = True
                break
# Curl to get Foursquare venue details if venue has Happy Hour
*****
"""