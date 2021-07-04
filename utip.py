import requests
import mechanize
import json
import datetime
import http.cookiejar
import os
import time

from bs4 import BeautifulSoup

from config import load_config


DONATIONS_DB_FILENAME = "donations_db.json"
COOKIES_FILENAME = "utip-cookies.txt"

browser = None


class DonationsDb:
    instance = None

    def __init__(self):
        DonationsDb.instance = self
        self.last_update_date = -1
        self.db = {}
        self.phpsessid = None
        self.new_entries = []
        self._load_from_file()

    def _load_from_file(self):
        if os.path.exists(DONATIONS_DB_FILENAME):
            fp = open(DONATIONS_DB_FILENAME, "r")
            self.db = json.load(fp)
            fp.close()

            self.last_update_date = os.path.getmtime(DONATIONS_DB_FILENAME)
        else:
            self.last_update_date = -1

    def _save_to_file(self):
        fp = open(DONATIONS_DB_FILENAME, "w")
        json.dump(self.db, fp)
        fp.close()

    def update(self, phpsessid):
        new_data = retrieve_last_donations(phpsessid)
        if new_data is None:
            print("<!!> Something went wrong during the donations data retrieval")
            return False

        self.update_with_data(new_data)

        return True

    def update_with_data(self, data):
        def _get_transaction_unique_name(t):
            return "_".join([t["username"], str(t["amount"]), t["datetime"]["date"]])

        for t in data:
            t_uname = _get_transaction_unique_name(t)
            if t_uname not in self.db:
                self.new_entries.append(t)
                self.db[t_uname] = t

        self.last_update_date = time.time()
        self._save_to_file()

    def get_new_entries(self):
        new_entries = self.new_entries
        return new_entries

    def flush_new_entries(self):
        new_entries = self.new_entries
        self.new_entries = []
        return new_entries

    def get_db(self, force_update=False):
        if force_update or time.time() - self.last_update_date > 60:
            print("<i> Updating db")
            self.phpsessid = connect()
            #self.update(self.phpsessid)
        else:
            print("<i> Getting db from disk")

        return self.db

    @staticmethod
    def get():
        if DonationsDb.instance:
            return DonationsDb.instance
        else:
            return DonationsDb()


def get_phpsessid(cookiejar):
    c = get_phpsessid_cookie(cookiejar)
    return c.value if c else None


def get_phpsessid_cookie(cookiejar):
    for c in cookiejar:
        if c.domain == "utip.io":
            if c.name == "PHPSESSID":
                return c
    return None


def connect():
    global browser

    # Initing browser
    browser = mechanize.Browser()
    browser.addheaders = [(
        'User-Agent',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'
        )]

    # Creating cookie jar
    # print("<i> Creating cookie jar")
    cj = http.cookiejar.LWPCookieJar()
    browser.set_cookiejar(cj)

    is_updated = False

    # Load cookie
    if os.path.exists(COOKIES_FILENAME):
        cj.load(COOKIES_FILENAME, ignore_discard=True)
        php_sessid = get_phpsessid(cj)

        if not php_sessid:
            print("<!> Session id not found in cookies, trying to log in")
        else:
            print("<i> Session id is in cookies!")
            is_updated = DonationsDb.get().update(php_sessid)
    else:
        print("<!> Cookies are inexistant ! Login for the first time")

    if not is_updated:
        new_id = login()

        print("<i> Just logged in! Got new PHPSESSID: %s" % new_id)

        cj.save("utip-cookies.txt", ignore_discard=True)

        php_sessid = get_phpsessid(cj)
        is_updated = DonationsDb.get().update(php_sessid)

    if not is_updated:
        raise Exception("<!!> Can't retrieve donation, there must be an issue with login")

    return get_phpsessid(cj)


def login():
    global browser

    cfg = load_config()

    # Getting page
    response = browser.open("https://utip.io/login")

    # Getting token
    soup = BeautifulSoup(response.read(), features="html5lib")
    r = soup.find(id='login')
    csrf_token = r.login.attrs[":csrf-token"].strip('"')

    # Building cookies
    cookies = {}

    for c in browser.cookiejar:
        if c.domain == "utip.io":
            cookies[c.name] = c.value

    # Making login request
    r = requests.post(
        "https://utip.io/login_check",
        cookies=cookies,
        data={
            "_csrf_token": csrf_token,
            "_username": cfg["utip_username"],
            "_password": cfg["utip_password"],
            "_submit": "Sign in",
            "_remember_me": "on",
        }
    )

    # Updating cookiejar PHPSESSID
    c = get_phpsessid_cookie(browser.cookiejar)
    c.value = r.cookies["PHPSESSID"]
    browser.cookiejar.set_cookie(c)

    return r.cookies["PHPSESSID"]


def retrieve_users_activity(phpsessid):
    cookies = {
        "PHPSESSID": phpsessid
    }

    r = requests.get(
        "https://utip.io/community/list/quaranstream/2020-02-28/" + (datetime.datetime.now() + datetime.timedelta(1)).strftime("%Y-%m-%d"),
        cookies=cookies
    )
    
    if r.status_code != 200:
        print("<!!> Page return code was %s" % r.status_code)
        return None

    try:
        res = r.json()
    except:
        print("<!!> Can't parse JSON from returned content :\n%s" % r.text)
        return None

    return list(res["supporterList"])


def retrieve_last_donations(phpsessid):
    cookies = {
        "PHPSESSID": phpsessid
    }

    r = requests.get(
        "https://utip.io/dashboard/last/activities",
        cookies=cookies
    )
    
    if r.status_code != 200:
        print("<!!> Page return code was %s" % r.status_code)
        return None

    try:
        res = r.json()
    except:
        print("<!!> Can't parse JSON from returned content :\n%s" % r.text)
        return None

    return list(res["activities"])

    