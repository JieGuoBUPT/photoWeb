import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
# from flask.ext.login import current_user
import flask_login
# regular expression
import re
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

# These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = '7819'
app.config['MYSQL_DATABASE_DB'] = 'PHOTOSHARE'
app.config['MYSQL_DATABASE_HOST'] = '127.0.0.1'
mysql.init_app(app)

# begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email FROM Users")
users = cursor.fetchall()


def getUserList():
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM Users")
    return cursor.fetchall()


class User(flask_login.UserMixin):
    pass


@login_manager.user_loader
def user_loader(email):
    users = getUserList()
    if not (email) or email not in str(users):
        return
    user = User()
    user.id = email
    return user


@login_manager.request_loader
def request_loader(request):
    users = getUserList()
    email = request.form.get('email')
    if not (email) or email not in str(users):
        return
    user = User()
    user.id = email
    cursor = mysql.connect().cursor()
    cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
    data = cursor.fetchall()
    pwd = str(data[0][0])
    user.is_authenticated = request.form['password'] == pwd
    return user


'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
    return new_page_html
'''

'''
USER MANAGEMENT 

LOGIN AND REGISTER

'''


def getUserNameFromID(user_id):
    cursor = conn.cursor()
    cursor.execute("SELECT FNAME FROM Users WHERE UID = '{0}'".format(user_id))
    return cursor.fetchone()[0]


def getUserIdFromEmail(email):
    cursor = conn.cursor()
    cursor.execute("SELECT UID  FROM Users WHERE email = '{0}'".format(email))
    return cursor.fetchone()[0]


def getUserNameFromEmail(email):
    cursor = conn.cursor()
    cursor.execute("SELECT FName, LName  FROM Users WHERE email = '{0}'".format(email))
    setOfName = cursor.fetchone()
    setStr = [str(item) for item in setOfName]
    return setStr


def isEmailUnique(email):
    # use this to check if a email has already been registered
    cursor = conn.cursor()
    if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
        # this means there are greater than zero entries with that email
        return False
    else:
        return True


@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'GET':
        return "<form action='login' method='POST'>\
                    <input type='text' name='email' id='email' placeholder='email'></input>\
                    <input type='password' name='password' id='password' placeholder='password'></input>\
                    <input type='submit' name='submit'></input>\
                    </form></br>\
                   <a href='/'>Home</a>"

        # The request method is POST (page is recieving data)
    email = flask.request.form['email']
    cursor = conn.cursor()
    # check if email is registered
    if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
        data = cursor.fetchall()
        pwd = str(data[0][0])
        if flask.request.form['password'] == pwd:
            user = User()
            user.id = email
            flask_login.login_user(user)  # okay login in user
            return flask.redirect(flask.url_for('protected'))  # protected is a function defined in this file

    # information did not match
    return "<a href='/login'>Try again</a>\
                </br><a href='/register'>or make an account</a>"


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return render_template('hello.html', message='Logged out')


@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('unauth.html')


# you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
    return render_template('register.html', supress='True')


@app.route("/register", methods=['POST'])
def register_user():
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        dob = request.form.get('dob')
        gender = request.form.get('gender')
        hometown = request.form.get('hometown')
    except:
        print(
            "couldn't find all tokens")  # this prints to shell, end users will not see this (all print statements go to shell)
        return flask.redirect(flask.url_for('register'))
    cursor = conn.cursor()
    test = isEmailUnique(email)
    if test:
        print(cursor.execute(
            "INSERT INTO Users (email, password, fname, lname, dob,gender,hometown) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}','{5}','{6}')".format(
                email, password, fname, lname, dob, gender, hometown)))
        conn.commit()
        # log user in
        user = User()
        user.id = email
        flask_login.login_user(user)
        return flask.redirect(flask.url_for('protected'))
    else:
        return flask.redirect(flask.url_for('register'))


@app.route('/reregister')  # register again
def reregister():
    return render_template('register.html', supress='False')


'''
USER'S OWN PROFILE
'''


@app.route('/profile')
@flask_login.login_required
def protected():
    email = flask_login.current_user.id
    uid = getUserIdFromEmail(email)
    return render_template('profile.html', name=email,
                           albums=getUsersAlbums(uid),
                           recommendedPhotos=picturesRecommendation(),
                           message="Here's your profile")


'''
USER'S FRIENDS
'''


def usercontribution(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM photo WHERE uid='{0}'".format(uid))
    photonumber = len(cursor.fetchall())
    cursor.execute("SELECT * FROM comment WHERE uid='{0}'".format(uid))
    commentnumber = len(cursor.fetchall())
    contribution = photonumber + commentnumber
    return contribution


def isUserFriend(uid):
    uid1 = getUserIdFromEmail(flask_login.current_user.id)
    cursor = conn.cursor()
    if cursor.execute("SELECT * FROM FRIENDSHIP WHERE uid1='{0}' AND uid2={1}".format(uid1, uid)):
        return True
    else:
        return False


def getuserfriends(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT uid2,email FROM friendship,users WHERE friendship.uid2=users.uid AND uid1='{0}'".format(uid))
    return cursor.fetchall()


def isEmailExist(email):
    cursor = conn.cursor()
    if cursor.execute("SELECT email FROM Users WHERE email = '{0}'".format(email)):
        return True


@app.route('/friend')
@flask_login.login_required
def friend():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    return render_template('friend.html', name=flask_login.current_user.id, supress='True', friends=getuserfriends(uid))


@app.route('/addfriend', methods=['Get', 'Post'])
@flask_login.login_required
def addfriend():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
        except:
            return flask.redirect(flask.url_for('friend'))
        cursor = conn.cursor()
        test = isEmailExist(email)
        uid1 = getUserIdFromEmail(flask_login.current_user.id)
        if test:
            uid2 = getUserIdFromEmail(email)
            if uid1 == uid2:
                return flask.redirect(flask.url_for('refriend'))
            if cursor.execute("SELECT * FROM friendship WHERE uid1='{0}' AND uid2='{1}'".format(uid1, uid2)):
                return flask.redirect(flask.url_for('refriend'))
            else:
                cursor.execute("INSERT INTO FRIENDSHIP (uid1,uid2) VALUES ('{0}','{1}')".format(uid1, uid2))
                conn.commit()
                return render_template('friend.html', name=flask_login.current_user.id, message='Add success',
                                       friends=getuserfriends(uid1))
        else:
            return flask.redirect(flask.url_for('refriend'))
    else:
        return render_template('addfriend.html')


@app.route('/refriend')
@flask_login.login_required
def refriend():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    return render_template('friend.html', name=flask_login.current_user.id, supress='False',
                           friends=getuserfriends(uid))


# MOST ACTIVE
@app.route('/MVUsers')
def MVUser():
    cursor = conn.cursor()
    cursor.execute("SELECT uid,email FROM users")
    users = cursor.fetchall()
    table = list()
    for user in users:
        contribution = (user[1], usercontribution(user[0]))
        table.append(contribution)
        newtable = sorted(table, key=lambda table: table[1], reverse=True)
        newtable = newtable[:10]
    for a in newtable:
        print(a[0], a[1])
    return render_template('MVUsers.html', user=newtable)


@app.route('/recommendation')
@flask_login.login_required
def recommendation():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    cursor = conn.cursor()
    cursor.execute("SELECT f2.uid2,email "
                   "FROM friendship f1,friendship f2,users "
                   "WHERE f1.uid1='{0}' "
                   "AND f2.uid2=users.uid "
                   "AND f1.uid2=f2.uid1 "
                   "AND f2.uid2<>'{0}' "
                   "AND f2.uid2 NOT IN (SELECT uid2 FROM friendship WHERE uid1='{0}')"
                   "GROUP BY f2.uid2 "
                   "ORDER BY count(f2.uid1) DESC".format(uid))
    return render_template('recommendation.html', friends=cursor.fetchall())


#
@app.route('/deletefriend', methods=['Get', 'Post'])
@flask_login.login_required
def deletefriend():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
        except:
            return flask.redirect(flask.url_for('friend'))
        if isEmailExist(email):
            uid = getUserIdFromEmail(email)
            test = isUserFriend(uid)
            if test:
                uid1 = getUserIdFromEmail(flask_login.current_user.id)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM friendship WHERE uid1='{0}' AND uid2='{1}'".format(uid1, uid))
                conn.commit()
                return render_template('friend.html', name=flask_login.current_user.id, message='Delete success',
                                       friends=getuserfriends(uid1))
            else:
                return flask.redirect(flask.url_for('refriend'))
        else:
            return flask.redirect(flask.url_for('refriend'))
    else:
        return render_template('deletefriend.html')


'''
Album and photo management
'''


def getUsersAlbums(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT ANAME FROM ALBUM WHERE UID = '{0}'".format(uid))
    setOfName = cursor.fetchall()
    row = [item[0] for item in setOfName]
    return row


'''
Album  management
'''


@app.route('/album_creation', methods=['GET', 'POST'])
@flask_login.login_required
def create_album():
    if request.method == 'POST':
        user_id = getUserIdFromEmail(flask_login.current_user.id)
        albumName = request.form.get('albumName')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO ALBUM (ANAME, UID) VALUES ('{0}', '{1}')".format(albumName, user_id))
        conn.commit()
        return flask.redirect(flask.url_for('protected'))
    else:
        return flask.redirect(flask.url_for('protected'))


'''
Photo  management
'''


# same as before
def getAlbumIdFromName(albumName, user_id):
    cursor = conn.cursor()
    cursor.execute("SELECT AID  FROM ALBUM WHERE ANAME = '{0}' AND UID = '{1}'".format(albumName, user_id))
    return cursor.fetchone()[0]


def getPhotos():
    cursor = conn.cursor()
    cursor.execute("SELECT imgdata, caption, UID FROM PHOTO");
    Row = cursor.fetchall()
    row = [(item[0], item[1]) for item in Row]
    userNames = [getUserNameFromID(item[2]) for item in Row]
    cursor.execute("SELECT PID FROM PHOTO");
    setOfID = cursor.fetchall()
    ids = [item[0] for item in setOfID]
    return row, userNames, ids


def getPhotoFromAlbum(aid):
    cursor = conn.cursor()
    cursor.execute("SELECT imgdata, caption FROM PHOTO WHERE AID = '{0}'".format(aid))
    Photos = cursor.fetchall()
    cursor.execute("SELECT PID FROM PHOTO WHERE AID = '{0}'".format(aid))
    setOfPID = cursor.fetchall()
    pids = [item[0] for item in setOfPID]
    return Photos, pids


@app.route("/photos/<albumName>", methods=['GET'])
@flask_login.login_required
def show_photos(albumName):
    user_id = getUserIdFromEmail(flask_login.current_user.id)
    album_id = getAlbumIdFromName(albumName, user_id)
    tags = getTags(getPhotoFromAlbum(album_id)[1])
    return render_template('photos.html',
                           albumName=albumName,
                           message='Photo uploaded!',
                           photos=getPhotoFromAlbum(album_id)[0],
                           pids=getPhotoFromAlbum(album_id)[1],
                           tags=getTags(getPhotoFromAlbum(album_id)[1])
                           )


# begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


# UPLOAD_FOLDER = os.path.basename('upload')
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


# Show how to upload files and Request Methods and directing pages
@app.route("/photos/upload/<albumName>", methods=['GET', 'POST'])
@flask_login.login_required
def upload_file(albumName):
    if request.method == 'POST':
        uid = getUserIdFromEmail(flask_login.current_user.id)
        imgfile = request.files['photo']
        album_id = getAlbumIdFromName(albumName, uid)
        caption = request.form.get('caption')
        photo_data = base64.standard_b64encode(imgfile.read())
        # temp = bytearray(imgfile.read(), encoding='ascii')
        # photo_data = str(base64.standard_b64encode(imgfile.read()).decode('utf8'))
        cursor = conn.cursor()
        cursor.execute("INSERT INTO PHOTO (imgdata, UID, caption, AID) VALUES (%s, %s, %s, %s)",
                       (photo_data, uid, caption, album_id))
        conn.commit()
        return render_template('profile.html', name=flask_login.current_user.id, message='Photo uploaded!',
                               photos=getPhotoFromAlbum(album_id)[0], album=albumName)

    else:
        return render_template('upload.html', album=albumName)


@app.route("/photos/remove_album/<albumName>", methods=['GET', 'POST'])
@flask_login.login_required
def remove_album(albumName):
    if request.method == 'POST':
        uid = getUserIdFromEmail(flask_login.current_user.id)
        album_id = getAlbumIdFromName(albumName, uid)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ALBUM WHERE AID = '{0}'".format(album_id))
        conn.commit()
        return render_template('profile.html', name=flask_login.current_user.id, album=albumName)
    else:
        return render_template('remove_album.html', album=albumName)


"""
TAG MANAGEMENT
"""


def getTags(pids):
    cursor = conn.cursor()
    Tags = []
    for id in pids:
        cursor.execute("SELECT HASHTAG FROM TAG WHERE PID = '{0}'".format(id))
        setOfTag = cursor.fetchall()
        setOfTagstr = [(str(item[0])) for item in setOfTag]
        Tags.append(setOfTagstr)
    return Tags


# returns all the pictures with a given tag
def allTags(HASHTAG):
    cursor = conn.cursor()
    cursor.execute("SELECT PID FROM TAG WHERE HASHTAG = '{0}'".format(HASHTAG))
    setOfTagPhoto = cursor.fetchall()
    pids = [(int(item[0])) for item in setOfTagPhoto]
    photos = []
    for id in pids:
        cursor.execute("SELECT imgdata FROM PHOTO WHERE PID = '{0}'".format(id));
        setOfP = cursor.fetchall()
        setOfPitem = [item[0] for item in setOfP]
        photos.append(setOfPitem)
    return photos


def UsersTags(HASHTAG, UID):
    cursor = conn.cursor()
    cursor.execute("SELECT PID FROM TAG WHERE HASHTAG = '{0}'".format(HASHTAG))
    P = cursor.fetchall()
    pids = [(int(item[0])) for item in P]
    photos = []
    for id in pids:
        cursor.execute("SELECT imgdata FROM PHOTO WHERE UID = '{0}' AND PID = '{1}'".format(UID, id));
        setOfD = cursor.fetchone()
        if setOfD is not None:
            photos.append(setOfD)
    return photos


@app.route('/add_tag', methods=['GET', 'POST'])
@flask_login.login_required
def add_tag():
    if request.method == 'POST':
        user_id = getUserIdFromEmail(flask_login.current_user.id)
        albumName = request.values.get('albumName')
        album_id = getAlbumIdFromName(albumName, user_id)

        p = request.values.get('pid')
        picture_id = int(p)
        HASHTAG = request.form.get('word')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO TAG (HASHTAG, PID) VALUES ('{0}', '{1}')".format(HASHTAG, picture_id))
        conn.commit()
        return render_template('profile.html', albums=getUsersAlbums(user_id))
    else:
        user_id = getUserIdFromEmail(flask_login.current_user.id)
        return render_template('profile.html', albums=getUsersAlbums(user_id))


@app.route("/photos/tags/<word>", methods=['GET'])
@flask_login.login_required
def alltags(word):
    user_id = getUserIdFromEmail(flask_login.current_user.id)
    word = str(word)
    photos = allTags(word)
    return render_template('tags.html',
                           photos=allTags(word),
                           usersPhotos=UsersTags(word, user_id),
                           word=word)


def mostPopularTags():
    cursor = conn.cursor()
    cursor.execute("SELECT HASHTAG FROM TAG GROUP BY (HASHTAG) HAVING COUNT(*)>0 ORDER BY COUNT(*) DESC LIMIT 5")
    setOfTag = cursor.fetchall()
    tags = [(str(item[0])) for item in setOfTag]
    return tags


# select tage according to the words
@app.route("/public_tags/<word>", methods=['GET'])
def public_tags(word):
    word = str(word)
    return render_template('public_tags.html',
                           photos=allTags(word),
                           word=word
                           )


# returns pids of pictures with given tags
def searchByTagPid(tags):
    tags = re.split("\s|,|:|\.|!|\?|@|#|$|%|\(|\)|-|_|\+|=|{|}|\[|\]|\"", tags)
    cursor = conn.cursor()
    p_ids = []
    for tag in tags:
        cursor.execute("SELECT PID FROM TAG WHERE HASHTAG = '{0}'".format(tag));
        setOfPID = cursor.fetchall()
        setOfPID = [item[0] for item in setOfPID]
        p_ids.append(setOfPID)
    intersection = []
    if len(p_ids) >= 2:
        intersection = list(set(p_ids[0]) & set(p_ids[1]))
    else:
        intersection = p_ids[0]
    for i in range(len(p_ids) - 2):
        intersection = list(set(intersection) & set(p_ids[i]))
    return intersection


def searchByTag(tags):
    cursor = conn.cursor()
    intersection = searchByTagPid(tags);
    photos = []
    for id in intersection:
        cursor.execute("SELECT imgdata FROM PHOTO WHERE PID = '{0}'".format(id));
        row = cursor.fetchall()
        setOFtages = [item[0] for item in row]
        photos.append(setOFtages)
    return photos


@app.route('/search_by_tag', methods=['GET', 'POST'])
def search_by_tag():
    if request.method == 'POST':
        HASHTAG = request.form.get('tag_name')
        HASHTAG = str(HASHTAG)
        return render_template('hello.html', search_tags=searchByTag(HASHTAG))
    else:
        return render_template('hello.html')


"""
RECOMMENDATIONS
"""


def mostPopularUsersTags():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    cursor = conn.cursor()
    # select only current user's tags
    cursor.execute(
        "SELECT HASHTAG FROM TAG, PHOTO WHERE TAG.PID = PHOTO.PID and UID='{0}' GROUP BY (HASHTAG) HAVING COUNT(*)>0 ORDER BY COUNT(*) DESC LIMIT 5".format(
            uid))
    setOfTags = cursor.fetchall()
    setOfTags = [str(item[0]) for item in setOfTags]
    return setOfTags


def picturesRecommendation():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    popTags = mostPopularUsersTags()
    cursor = conn.cursor()
    cursor.execute("SELECT PID FROM PHOTO");
    setOfPID = cursor.fetchall()
    pids = [int(item[0]) for item in setOfPID]
    Count = [0] * len(pids)
    photos = []
    for i in range(len(pids)):
        for tag in popTags:
            # TAG EXISTS
            cursor.execute("SELECT COUNT(*) FROM TAG WHERE PID = '{0}' AND HASHTAG = '{1}'".format(pids[i], tag));
            C = cursor.fetchone()
            C = int(C[0])
            if C > 0:
                Count[i] = Count[i] + 1
                # SORT
    picRating = [(pids[i], Count[i]) for i in range(len(pids))]
    picRating = sorted(picRating, key=lambda x: (-x[1], x[0]))
    picRating = picRating[:5]  # pic 5 most popular ones
    for i in range(len(picRating)):
        cursor.execute("SELECT imgdata FROM PHOTO WHERE PID = '{0}'".format(picRating[i][0]))
        setOfimg = cursor.fetchall()
        setOfimg2 = [item[0] for item in setOfimg]
        photos.append(setOfimg2)
    return photos


def tagRecommendation(tags):
    cursor = conn.cursor()
    # show pids of pictures that have given tags
    pids = searchByTagPid(tags)
    # take the tags of these photos
    tags = []
    for id in pids:
        cursor.execute("SELECT HASHTAG FROM TAG WHERE PID = '{0}'".format(id))
        T = cursor.fetchall()
        T = [str(item[0]) for item in T]
        tags = tags + T
    print(tags)
    return 0


@app.route('/tag_recommend', methods=['GET', 'POST'])
@flask_login.login_required
def tag_recommend():
    if request.method == 'POST':
        tags = request.form.get('words')
        print(tags)
        recommendedTags = tagRecommendation(tags)
        return render_template('photos.html', tagsRecommended=tagRecommendation(tags))
    else:
        tags = request.form.get('words')
        return render_template('photos.html', tagsRecommended=tagRecommendation(tags))


"""
COMMENTS MANAGEMENT
"""


def getComments(pids):
    cursor = conn.cursor()
    Comments = []
    for id in pids:
        cursor.execute("SELECT CONTENT FROM COMMENT WHERE PID = '{0}'".format(id))
        setOFcomment = cursor.fetchall()
        setOFcommentStr = [(str(item[0])) for item in setOFcomment]
        Comments.append(setOFcommentStr)
    return Comments


@app.route('/add_comment', methods=['GET', 'POST'])
def picture_id():
    pid = request.form.get('picture_id')
    picture_id = int(pid)
    if request.method == 'POST':
        user_id = getUserIdFromEmail(flask_login.current_user.id)
        content = request.form.get('comment')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Comment (CONTENT, UID, PID) VALUES ('{0}', '{1}', '{2}')".format(content, user_id,
                                                                                          picture_id))
        conn.commit()
        return flask.redirect(flask.url_for('hello'))
    else:
        return flask.redirect(flask.url_for('hello'))


def searchByCommentCid(comments):
    comments = re.split("\s|,|:|\.|!|\?|@|#|$|%|\(|\)|-|_|\+|=|{|}|\[|\]|\"", comments)
    cursor = conn.cursor()
    c_ids = []
    for tag in comments:
        cursor.execute("SELECT CID FROM COMMENT WHERE CONTENT = '{0}'".format(tag));
        setOfPID = cursor.fetchall()
        setOfPID = [item[0] for item in setOfPID]
        c_ids.append(setOfPID)
    intersection = []
    if len(c_ids) >= 2:
        intersection = list(set(c_ids[0]) & set(c_ids[1]))
    else:
        intersection = c_ids[0]
    for i in range(len(c_ids) - 2):
        intersection = list(set(intersection) & set(c_ids[i]))
    return intersection


def searchByComment(comments):
    cursor = conn.cursor()
    intersection = searchByCommentCid(comments);
    comments = []
    for id in intersection:
        cursor.execute("SELECT CONTENT FROM COMMENT WHERE CID = '{0}'".format(id));
        row = cursor.fetchall()
        setOFcomments = [item[0] for item in row]
        comments.append(setOFcomments)
    return comments


@app.route('/search_by_comment', methods=['GET', 'POST'])
def search_by_comment():
    if request.method == 'POST':
        HASHTAG = request.form.get('comment_name')
        HASHTAG = str(HASHTAG)
        return render_template('hello.html', search_comments=searchByComment(HASHTAG))
    else:
        return render_template('hello.html')


"""
LIKES MANAGEMENT
"""


def getLikes(pids):
    cursor = conn.cursor()
    Likes = []
    Users = []
    for id in pids:
        cursor.execute("SELECT COUNT(*) FROM LIKETABLE WHERE PID = '{0}'".format(id))
        setOfLike = cursor.fetchone()
        setOfLike = int(setOfLike[0])
        Likes.append(setOfLike)
        cursor.execute("SELECT UID FROM LIKETABLE WHERE PID = '{0}'".format(id))
        setOfUid = cursor.fetchall()
        setOfUid = [str(getUserNameFromID(int(item[0]))) for item in setOfUid]
        Users.append(setOfUid)
    print(Users)
    return Likes, Users


@app.route('/add_like', methods=['GET', 'POST'])
@flask_login.login_required
def add_like():
    pid = request.form.get('picture_id')
    picture_id = int(pid)
    if request.method == 'POST':
        user_id = getUserIdFromEmail(flask_login.current_user.id)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO LIKETABLE (PID, UID) VALUES ('{0}', '{1}')".format(picture_id, user_id))
        conn.commit()
        return flask.redirect(flask.url_for('hello'))
    else:
        return flask.redirect(flask.url_for('hello'))


"""
USER ACTIVITY 
"""


@app.route("/", methods=['GET'])
def hello():
    # p = userActivity()
    print(getLikes(getPhotos()[1])[0])
    return render_template('hello.html',
                           photos=getPhotos()[0],
                           picture_ids=getPhotos()[1],
                           comments=getComments(getPhotos()[2]),
                           mostPopularTags=mostPopularTags(),
                           likes=getLikes(getPhotos()[2])[0],
                           usersLiked=getLikes(getPhotos()[2])[1]
                           )


if __name__ == "__main__":
    # this is invoked when in the shell  you run
    # $ python app.py
    app.run(port=5000, debug=True)
