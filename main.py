# this script will act as a central server.
from flask import Flask, jsonify, request
import time
import ast
import hashlib
from sqlalchemy import create_engine
import datetime

application = Flask(__name__)

@application.route('/')
def index():
    return "hello timetracker!"


@application.route('/login', methods=['POST'])
def login():
    response = str(request.get_data().decode())
    r = response.replace("username=", "")
    username, password = r.split("&password=")
    token = str(hashlib.sha256(str(username + password).encode()).hexdigest()[:20])
    print("auth token from login: "+token)
    engine = create_engine('mysql://tkkhhaarree:simoncommission@timetrackerdb.ctvxzstxobqa.ap-south-1.rds.amazonaws.com:3306/timetracker')

    db = engine.connect()

    query = "insert ignore into userinfo(username, password, auth) values(\"" + username + "\", \"" + password + "\", \"" + token + "\");"
    db.execute(query)
    db.close()

    return token, 200


def url_strip(url):
    if "http://" in url or "https://" in url:
        url = url.replace("https://", '').replace("http://", '').replace('\"', '')
    if "/" in url:
        url = url.split('/', 1)[0]
    return url


@application.route('/send_url', methods=['POST'])
def send_url():
    resp_json = request.get_data()
    params = resp_json.decode()
    y = params.replace("url=", "")
    url, a_s = y.split("&auth=")
    auth, session = a_s.split("&session=")
    print("currently viewing: " + url_strip(url))
    parent_url = url_strip(url)

    url_timestamp = {}
    url_viewtime = {}
    current_url = ""

    query_current_url = "select url from current_url where auth = \"" + auth + "\" and session = \"" + session + "\";"
    query_url_timestamp = "select url, ts from webstats where auth = \"" + auth + "\" and session = \"" + session + "\";"
    query_url_viewtime = "select url, viewtime from webstats where auth = \"" + auth + "\" and session = \"" + session + "\";"

    engine = create_engine('mysql://tkkhhaarree:simoncommission@timetrackerdb.ctvxzstxobqa.ap-south-1.rds.amazonaws.com:3306/timetracker')

    db = engine.connect()

    c_u_object = db.execute(query_current_url)
    for x in c_u_object:
        current_url = x[0]
        break
    u_t_object = db.execute(query_url_timestamp)
    for y in u_t_object:
        url_timestamp[y[0]] = int(y[1])

    u_v_object = db.execute(query_url_viewtime)
    for z in u_v_object:
        url_viewtime[z[0]] = int(z[1])

    print("initial db prev tab: ", current_url)
    print("initial db timestamp: ", url_timestamp)
    print("initial db viewtime: ", url_viewtime)

    if parent_url not in url_timestamp.keys():
        url_viewtime[parent_url] = 0
        db.execute(
            "insert into webstats (auth, session, url, viewtime) values (\"" + auth + "\", \"" + session + "\", \"" + parent_url + "\", 0);")

    if current_url != 'chrome:':
        time_spent = int(time.time() - url_timestamp[current_url])
        url_viewtime[current_url] = url_viewtime[current_url] + time_spent
        db.execute("update webstats set viewtime=" + str(url_viewtime[
                                                                 current_url]) + " where auth=\"" + auth + "\" and url=\"" + current_url + "\" and session=\"" + session + "\";")

    x = int(time.time())
    url_timestamp[parent_url] = x
    print("x: " + str(x))
    db.execute("update webstats set ts=" + str(
        x) + " where auth=\"" + auth + "\" and url=\"" + parent_url + "\" and session=\"" + session + "\";")

    db.execute(
        "update current_url set url=\"" + parent_url + "\" where auth=\"" + auth + "\" and session=\"" + session + "\";")

    print("final timestamps: ", url_timestamp)
    print("final viewtimes: ", url_viewtime)
    db.close()
    return jsonify({'message': 'add success!'}), 200


@application.route('/quit_url', methods=['POST'])
def quit_url():
    resp_json = request.get_data()
    print("Url closed: " + resp_json.decode())
    return jsonify({'message': 'quit success!'}), 200


@application.route('/quit_chrome', methods=['POST'])
def quit_chrome():
    resp = request.get_data().decode()
    a, session = resp.split("&session=")
    auth = a.replace("auth=", "")

    url_timestamp = {}
    url_viewtime = {}
    current_url = ""

    query_current_url = "select url from current_url where auth = \"" + auth + "\" and session = \"" + session + "\";"
    query_url_timestamp = "select url, ts from webstats where auth = \"" + auth + "\" and session = \"" + session + "\";"
    query_url_viewtime = "select url, viewtime from webstats where auth = \"" + auth + "\" and session = \"" + session + "\";"

    engine = create_engine('mysql://tkkhhaarree:simoncommission@timetrackerdb.ctvxzstxobqa.ap-south-1.rds.amazonaws.com:3306/timetracker')

    db = engine.connect()

    c_u_object = db.execute(query_current_url)
    for x in c_u_object:
        current_url = x[0]
        break
    u_t_object = db.execute(query_url_timestamp)
    for y in u_t_object:
        url_timestamp[y[0]] = int(y[1])

    u_v_object = db.execute(query_url_viewtime)
    for z in u_v_object:
        url_viewtime[z[0]] = int(z[1])

    if current_url != 'chrome:':
        t = int(time.time() - url_timestamp[current_url])
        tnow = time.time()
        url_timestamp[current_url] = tnow
        db.execute("update webstats set ts="+str(tnow)+" where url=\""+current_url+"\" and auth=\""+auth+"\" and session=\""+session+"\";")

        url_viewtime[current_url] = url_viewtime[current_url] + t
        db.execute("update webstats set viewtime="+str(url_viewtime[current_url])+" where url=\""+current_url+"\" and auth=\""+auth+"\" and session=\""+session+"\";")

        print("Chrome has been quit.")
        print("timestamps after quit: ", url_timestamp)
        print("viewtime after quit: ", url_viewtime)
    else:
        print("chrome not open currently")
    db.close()
    return jsonify({"message": 'quit chrome function activated'}), 200


@application.route('/get_session', methods=['POST'])
def get_session():
    resp = request.get_data()
    a, init_url = resp.decode().split("&current_url=")
    auth = a.replace("auth=", "")
    engine = create_engine('mysql://tkkhhaarree:simoncommission@timetrackerdb.ctvxzstxobqa.ap-south-1.rds.amazonaws.com:3306/timetracker')

    db = engine.connect()
    now  = datetime.datetime.now()
    session = str(now.day)+"/"+str(now.month)+"/"+str(now.year)
    u = url_strip(init_url)
    try:
        db.execute("insert into current_session values (\"" + auth + "\", \"" + session + "\");")
    except:
        db.execute("update current_session set c_s = \"" + session + "\" where auth = \"" + auth + "\";")

    try:
        db.execute(
            "insert into current_url(auth, session, url) values (\"" + auth + "\", \"" + session + "\", \"" + u + "\");")
    except:
        pass
    ts = int(time.time())
    try:
        db.execute("insert into webstats(auth, session, url, ts, viewtime) values (\""+auth+"\", \""+session+"\", \""+u+"\", "+str(ts)+", 0);")
        print("init url inserted: "+u)
    except:
        pass
    print("auth from set_session: "+auth)
    print("session from set_session: "+session)
    print("init url from set_session: "+init_url)
    db.close()
    return session, 200


@application.route('/get_app_session', methods=['POST'])
def get_app_session():
    resp = request.get_data()
    auth = resp.decode().replace("auth=", "")
    engine = create_engine('mysql://tkkhhaarree:simoncommission@timetrackerdb.ctvxzstxobqa.ap-south-1.rds.amazonaws.com:3306/timetracker')

    db = engine.connect()
    now = datetime.datetime.now()
    session = str(now.day)+"/"+str(now.month)+"/"+str(now.year)
    try:
        db.execute("insert into current_session values (\"" + auth + "\", \"" + session + "\");")
    except:
        db.execute("update current_session set c_s = \"" + session + "\" where auth = \"" + auth + "\";")

    db.close()
    return session, 200


@application.route('/generate_auth', methods=['POST'])
def generate_auth():
    resp = request.get_data()
    u, password = resp.decode().split("&password=")
    username = u.replace("username=", "")
    token = str(hashlib.sha256(str(username + password).encode()).hexdigest()[:20])
    print(username)
    print(password)
    print(token)
    return token, 200

@application.route('/restore_chrome', methods=['POST'])
def restore_chrome():
    print("restore chrome: "+str(time.time()))
    resp = request.get_data().decode()
    a, session = resp.split("&session=")
    auth = a.replace("auth=", "")

    url_timestamp = {}
    current_url = ""

    engine = create_engine('mysql://tkkhhaarree:simoncommission@timetrackerdb.ctvxzstxobqa.ap-south-1.rds.amazonaws.com:3306/timetracker')

    db = engine.connect()
    query_current_url = "select url from current_url where auth = \"" + auth + "\" and session = \"" + session + "\";"
    query_url_timestamp = "select url, ts from webstats where auth = \"" + auth + "\" and session = \"" + session + "\";"

    c_u_object = db.execute(query_current_url)
    for x in c_u_object:
        current_url = x[0]
        break
    u_t_object = db.execute(query_url_timestamp)
    for y in u_t_object:
        url_timestamp[y[0]] = int(y[1])

    if current_url != 'chrome://newtab/':
        tnow = time.time()
        url_timestamp[current_url] = tnow
        db.execute("update webstats set ts=" + str(
            tnow) + " where url=\"" + current_url + "\" and auth=\"" + auth + "\" and session=\"" + session + "\";")

    db.close()
    return jsonify({'message': 'chrome restore activated.'}), 200

@application.route('/save_app', methods=['POST'])
def save_app():
    resp = request.get_data().decode()
    a, s = resp.split("&session=")
    auth = a.replace("auth=", "")
    session, pt = s.split("&apptime=")
    process_time = ast.literal_eval(pt)
    print("session: "+session)
    print(process_time)
    engine = create_engine('mysql://tkkhhaarree:simoncommission@timetrackerdb.ctvxzstxobqa.ap-south-1.rds.amazonaws.com:3306/timetracker')

    db = engine.connect()
    ts = int(time.time())
    for k in process_time.keys():
        db.execute("insert into appstats values (\""+auth+"\", \""+session+"\", \""+str(k)+"\", "+str(process_time[k])+", "+str(ts)+");")
    db.execute("delete from appstats where auth=\""+auth+"\" and session=\""+session+"\" and added_ts <>"+str(ts)+";")

    db.close()

    return "ok", 200

@application.route('/display_webstats', methods=['POST'])
def display_webstats():
    engine = create_engine('mysql://tkkhhaarree:simoncommission@timetrackerdb.ctvxzstxobqa.ap-south-1.rds.amazonaws.com:3306/timetracker')

    db = engine.connect()
    ws = db.execute("select * from webstats")
    table = []
    x=""
    for w in ws:
        for i in range(len(w)):
            x = x + str(w[i]) + "---"
        table.append(x[:-3])
    db.close()
    return jsonify(table), 200


