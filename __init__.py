"""
Flask Documentation:     http://flask.pocoo.org/docs/
Jinja2 Documentation:    http://jinja.pocoo.org/2/documentation/
Werkzeug Documentation:  http://werkzeug.pocoo.org/documentation/
"""

import os
import sys
import json
from flask import Flask, render_template, request, redirect, url_for, session, Markup, flash
import bcrypt
import requests
from models import *
import config

reload(sys)
sys.setdefaultencoding('utf-8')
app = Flask(__name__)
g_api_key = config.G_API_KEY
fs_client_id = config.FS_CLIENT_ID
fs_secret = config.FS_CLIENT_SECRET


@app.route('/')
def home():
    """
    Retuns homepage template with Jumbotron and search fields to enable finding
    happy hours.
    """
    return render_template('homepage.html')


@app.route('/convert_address', methods=['GET'])
def convert_address():
    """
    Takes the address from user's search and uses the Geocoding API to convert
    it to a lat and lng value, storing those in session. Returns the map
    template with results & pins.
    """
    session['address_bool'] = 0
    if request.args.get('is_active', 'anytime') == 'now':
        session['active_only'] = True
    else:
        session['active_only'] = False
    session['radius'] = request.args.get('radius', '20')
    address_input = ''
    address_input = request.args.get('address')
    if address_input:
        session['address_bool'] = 1
        coords_tuple = Place.address_to_coords(request.args.get('address', \
                                                                ''))
        session['lat'] = coords_tuple[0]
        session['lng'] = coords_tuple[1]
        return redirect(url_for('display'))
    else:
        return render_template('location.html', apikey=g_api_key)


@app.route('/display', methods=["GET", "POST"])
def display():
    """
    Gets a list of places based on a passed in mile radius from user's location
    Returns render of the map template / display homepage
    """
    if not session.get('address_bool'):
        session['lat'] = request.form.get('lat', '')
        session['lng'] = request.form.get('lng', '')
    lat = session.get('lat', 29.7604)
    lng = session.get('lng', -95.3698)
    is_active = session.get('active_only', False)
    radius = session.get('radius', '50')
    place_list = Place.get_places(lat, lng, radius, is_active)
    # for place in place_list:
    #     print"*********"
    #     print place.is_happy_hour
    return render_template(
        "display.html", place_list=place_list, apikey=g_api_key, latitude=
        lat, longitude=lng, address_input=session.get('address_bool'))


@app.route('/details/<int:location_id>')
def show_location(location_id):
    """
    Shows the Foursquare and happyhour details for a given id from id_venue_id
    """
    lat = session.get('lat', 29.7604)
    lng = session.get('lng', -95.3698)
    location_object = Place(location_id)
    return render_template("details.html", latitude=lat, longitude=lng, venue=location_object, apikey=g_api_key)


@app.route('/account/create', methods=["GET", "POST"])
def create_account():
    """
    Displays form to user that allows signups
    """
    return render_template('create_account.html')


@app.route('/account/submit', methods=["POST"])
def submit_new_account():
    """
    Takes user input and creates a new account for them
    """
    username = request.form.get('username', '').lower()
    password = request.form.get('password', '')
    valid_userinfo = User.validate_userinfo(username, password)
    if valid_userinfo:
        new_user = User()
        new_user.username = username
        new_user.email = request.form.get('email', '')
        new_user.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        new_user.save()
        flash("Account created for %s!" % new_user.username)
        session['username'] = new_user.username
        return render_template('homepage.html')
    flash("Sorry, that username already exists.")
    return render_template('create_account.html')


@app.route('/account/login')
def login():
    """
    Shows user form to allow them to log in
    """
    return render_template('login.html')


@app.route('/account/login_submit', methods=["POST"])
def submit_login():
    """
    Tests user's form input against stored credentials. Logs user in and Shows
    homepage or flashes authentication failure message and reloads itself.
    Stores logged-in state in session
    """
    username_test = request.form.get('username', '').lower()
    password_test = request.form.get('password', '')
    user_to_login = User(username=username_test)
    if user_to_login.authenticate(username_test, password_test):
        session['username'] = user_to_login.username
        return redirect(url_for('home'))
    flash("Incorrect username or password")
    return redirect(url_for('login'))


@app.route('/account/logout')
def logout():
    """
    Logs user out by deleting their username from session
    """
    del session['username']
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.secret_key = config.SECRET_KEY
    # app.config['APPLICATION_ROOT'] = config.APPLICATION_ROOT
    app.config['DEBUG'] = config.DEBUG
    app.run()
