import os
import webapp2
import jinja2
import urllib
import re
import random
import string
import hashlib
import hmac
import json
import time
from google.appengine.ext import db
from google.appengine.api import memcache
SECRET = "kendhia is the best"
template_dir = os.path.join(os.path.dirname(__file__), 'templates')

jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = False)

def hash_str(s):
    return hashlib.md5(s).hexdigest()

def make_secure_val(s,password):
    return "%s,%s" % (s, hash_str(password))

def check_secure_val(h):
    val = h.split(',')[0]
    if h == make_secure_val(val):
        return val

user_re = re.compile("^[a-zA-Z0-9_-]{3,20}$")
password_re = re.compile("^.{3,20}$")
email_re = re.compile("^[\S]+@[\S]+\.[\S]+$")


def valid_username(username):
    return user_re.match(username)
def valid_password(password):
    return password_re.match(password)
def valid_email(email):
    return email_re.match(email)
def hash_str(s):
    return hmac.new(SECRET, s).hexdigest()

def make_salt():
    return ''.join(random.choice(string.letters) for x in xrange(5))

def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s|%s' % (h, salt)

def valid_pw(name, pw, h):
    salt = h.split('|')[1]
    return h == make_pw_hash(name, pw, salt)

def posts_caching(update = False):
    key = ('post')
    contents = memcache.get(key)
    if contents is None or update:
        contents = db.GqlQuery("SELECT * FROM Content ORDER BY created DESC")
        contents = list(contents)
        memcache.set(key, contents)
        last_query = int(time.time())
        memcache.set('last', last_query)


    return contents

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
    
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))
class Content(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)

class User(db.Model):
    user_data =  db.StringProperty(required = True)
    username = db.StringProperty(required = True)
class WIKI(db.Model):
    content = db.StringProperty()
    name = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)





class signup(Handler):
    def get(self):
        self.render('signup.html')
    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')
        repassword = self.request.get('repassword')
        email = self.request.get('email')

        username_valid = valid_username(username)
        password_valid = valid_password(password)
        email_valid =  valid_email(email)


        if not username_valid:
            error_usr = "That's not a valid name"
        else:
            datausers = db.GqlQuery("SELECT * FROM User where username = :1", username).get()
            if  datausers:
               error_usr = "This username already exist."
            else:
                error_usr = ""
        if not password_valid:
            error_pass = "That's not a valid password "
        else:
            error_pass = ""

        if not email_valid and email != "":
            error_email = "That's not a valid email"
        else:
            error_email = ""
        
        if not repassword == password :
            error_repass = "Don't match"
        else:
            error_repass = ""
        if error_usr != "" or error_pass != "" or  error_pass != "" or  error_email != "":
            self.render("signup.html", error_repass = error_repass,error_usr = error_usr,error_pass = error_pass, error_email = error_email,username = username, email = email)
        else:
            user_data = make_pw_hash(username, password)
            a = User(user_data = user_data,username = username)
            a.put()
            id = a.key().id()
            users = make_secure_val(id, str(password))
            self.response.headers.add_header('Set-Cookie', 'username=%s; Path=/' % users, )
            self.redirect("/")
class Blog(Handler):
    def Home_Page(self):
        contents= posts_caching()
        last_query = memcache.get('last')
        last = int(time.time()) - last_query
        self.render("Home_Page.html", contents=contents,last=last)
    def get(self):
        self.Home_Page()
class NewPost(Handler):
    def render_front(self, subject="", content="", error=""):
        self.render("NewPost.html", subject=subject, content=content, error=error)
    def get(self):
         self.render_front()
    def post(self):
        subject = self.request.get("subject")
        content = self.request.get("content")
        if subject and content: 
            a = Content(subject = subject, content = content)
            a.put()
            id = a.key().id()
            self.redirect("/%s" % id)
            post_only = Content.get_by_id(id)     
            posts_caching(update = True)
            last_query = int(time.time())
            memcache.set('%s' % id, last_query)

        else:
            error = "we need both a subject and some artwork!" 
            self.render_front(subject, content, error)

class show_single_post(Handler):
    def get(self, resource):
        post_id = urllib.unquote(resource)
        #check = db.GqlQuery("select * from Content where id = :1",id).get()
        #if check:
	blog = Content.get_by_id(int(post_id))
	if blog:
	  
           text = blog.content
           subject = blog.subject
           last_query  = memcache.get(post_id) 
           if last_query:
              last =  int(time.time()) - int(last_query)
           else:
              last = 0
           self.render("blog.html",content=text,subject=subject, last=last)
        else:
	   self.write("Error 404")
	    
        
        



class Login(Handler):
    def get(self):
        self.render("login.html")
    def post(self):
        username = self.request.get("username")
        password = self.request.get("password")
        username_valid = valid_username(str(username))
        password_valid = valid_password(str(username))

        if username_valid and password_valid:
            datausers = db.GqlQuery("SELECT * FROM User where username = :1", username).get()
            if datausers:
                id = datausers.key().id()
                userdata = User.get_by_id(id)                
                userhash = userdata.user_data
                before_salt = userhash.split('|')
                salt = before_salt[1]
                new_hash = make_pw_hash(username,password,salt)
                if new_hash == userhash:
                    users = make_secure_val(username,str(password))
                    self.response.headers.add_header('Set-Cookie', 'username=%s; Path=/' % str(username))
                    self.redirect("/")
                else:
                    error_usr = ("Invalid login")
                    self.render("login.html", error_usr = error_usr)
            else:
                error_usr = ("Invalid login")
                self.render("login.html", error_usr = error_usr)
        else:
            error_usr = ("please enter a valid  username and password")

class Logout(Handler):
    def get(self):
        self.response.headers.add_header('Set-Cookie','username=; Path=/')
        self.redirect("/")
class JsonArticleList(Handler): 

    def get(self):
        articles = db.GqlQuery('SELECT * FROM Content '
                               'ORDER BY created DESC '
                               )
        json_list = [{'subject': article.subject,
                    'content': article.content} for article in articles]

        content_list = json.dumps(json_list)
        self.response.headers['Content-Type'] = 'application/json'
        self.write(content_list)
class JsonSingleArticle(Handler): 
    def get(self, resource):
        id = urllib.unquote(resource)
        blog = Content.get_by_id(int(id))
        text = blog.content
        subject = blog.subject
        created = blog.created
        self.response.headers['Content-Type'] = 'application/json'
        content = [{'subject':subject, 'content':text}]
        content = json.dumps(content)
        self.write(content)

class Flush(Handler):
    def get(self):
        memcache.flush_all()
        self.redirect('/')
		
class WikiPage(Handler):
    def get(self, resource):
        name = resource.rstrip('/wiki/').split('/')[-1]
        wiki_valid = db.GqlQuery("SELECT * FROM WIKI where name = :1 ORDER BY created DESC",name).get()
        if wiki_valid:
            id = wiki_valid.key().id()
            text = WIKI.get_by_id(int(id))
            content = text.content
            self.render('wiki_page.html',content=content )
        else:
            self.redirect('/wiki/_edit/%s' % name)


class EditPage(Handler):
    def get(self, resourse):
        h = self.request.cookies.get('username')
        if h:
            username = h.split('|')[0]
            user_name = db.GqlQuery("SELECT * FROM User where name = :1", username)
            if user_name:
                name = resourse.rstrip('/wiki/').split('/')[-1]
                wiki_valid = db.GqlQuery("SELECT * FROM WIKI where name = :1 ORDER BY created DESC",name).get()
                if wiki_valid:
                    id = wiki_valid.key().id()
                    text = WIKI.get_by_id(int(id))
                    wiki = text.content
                    self.render('/wiki_edit.html', text = wiki)
                else:
                    self.render('/wiki_edit.html')
        else:
            self.redirect("/login")
    def post(self, resourse):
        h = self.request.cookies.get('username')
        if h:
            username = h.split('|')[0]
            user_name = db.GqlQuery("SELECT * FROM User where name = :1", username)
            if user_name:
                name = resourse.rstrip('/wiki/').split('/')[-1]
                text_area = self.request.get('content')
                wiki_valid = db.GqlQuery("SELECT * FROM WIKI where name = :1", name).get()
                if wiki_valid:
                    a = WIKI(content = str(text_area), name = name)
                    a.put()
                    self.redirect('/wiki/%s' % name)
                else:
                    a = WIKI(content = text_area, name = name)
                    a.put()
                    self.redirect('/wiki/%s' % name)
            else:
                self.redirect('/login')
		
class wiki_history(Handler):
    def get(self, resourse):
        name = resourse.rstrip('/wiki/').split('/')[-1]
        posts = db.GqlQuery("SELECT * FROM WIKI where name = :1", name)
        self.render('history.html', posts = posts, name = name)

PAGE_RE = r'(/(?:[a-zA-Z0-9_-]+/?)*)'	

app = webapp2.WSGIApplication([('/',Blog),('/newpost',NewPost),('/([0-9]+)', show_single_post)
                               ,('/signup',signup),('/login', Login),('/logout', Logout),('/.json',JsonArticleList)
                               ,('/([0-9]+).json',JsonSingleArticle),('/flush', Flush),('/wiki/_edit' + PAGE_RE, EditPage),('/wiki/_history' + PAGE_RE, wiki_history)
                               , (PAGE_RE, WikiPage)],debug= True)