import os
import time
import requests

from flask import Flask, session, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_session import Session

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker



app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

#Get Goodreads Developer key
my_developer_key = os.getenv("GOODREADS_KEY")



@app.route("/")
def index():
    """Returns index page with links to log in/register."""
     
    #If logged on, redirect to main page
    if session.get("logged_on", False):
        return redirect(url_for('find'))

    #Otherwise render page with register/login links
    return render_template("index.html")


@app.route("/register", methods = ["GET", "POST"])
def register():
    
    #If logged on, flash a msg to logout first and redirect to main page
    if session.get("logged_on", False):
       client_details = db.execute("""SELECT username FROM userdetails 
                                      WHERE user_id = :user_id1""",
                                      {"user_id1": session["user_id"]}).fetchone()
       client_username = client_details.username
       flash(f'''{client_username}, you are already logged on. 
                 If you want to register for a new account, please logout first''')
       return redirect(url_for('find'))
   
    #Register if data sent by post method and redirect to login page if successful  
    if request.method=="POST":
        client_username = request.form.get("username")
        client_password = request.form.get("password")
        
        if db.execute("""SELECT username FROM userdetails 
                         WHERE username = :username1""",
                         {"username1": client_username}).rowcount == 0:
            db.execute("""INSERT INTO userdetails (username, password) 
                          VALUES (:username1, :password1)""",
                          {"username1": client_username, "password1": client_password})
            db.commit()
            flash(f'Hello {client_username}! You were successfully registered!')
            return redirect(url_for('login'))

        else:
            flash(f'''Unfortunately the username {client_username} is already taken. 
                      Register with a new username''')
            
    #Render registration page in case of errors with registration/url accessed by get method
    return render_template("registration_page.html")



@app.route("/login", methods = ["GET", "POST"])
def login():
    
    #If logged on, flash a msg to logout first and redirect to main page
    if session.get("logged_on", False):
       client_details = db.execute("SELECT username FROM userdetails WHERE user_id = :user_id1",
                                    {"user_id1": session["user_id"]}).fetchone()
       client_username = client_details.username
       flash(f'{client_username}, you are already logged on. Please logout first')
       return redirect(url_for('find'))
   
    #Login if data sent by post method and redirect to main page if successful
    if request.method=="POST":
        client_username = request.form.get("username")
        client_password = request.form.get("password")
        client_details = db.execute("""SELECT user_id, username, password 
                                       FROM userdetails 
                                       WHERE username = :username1""",
                                       {"username1": client_username}).fetchone()
        
        if client_details is None:
            flash(f'''No username called {client_username} found. 
                      Please enter correct username or register and then log in!''')
            return redirect(url_for('index'))
        elif client_details.password != client_password:
            flash(f'Incorrect password. Please try again')    
        else:
            session["user_id"] = client_details.user_id
            session["logged_on"] = True
            flash(f'Hello {client_username}! You have successfully logged in!')
            return redirect(url_for('find'))

    #Render log in page in case of errors with log in/url accessed by get method    
    return render_template("login_page.html")


@app.route("/logout", methods = ["GET", "POST"])
def logout():
    
    #If not logged on, flash a msg
    if not session.get("logged_on", False):
       flash("Hello there, you are not logged in, so no need to logout ;) ")
    #Log out
    if request.method=="POST":
        client_details = db.execute("SELECT username FROM userdetails WHERE user_id = :user_id1",
                                    {"user_id1": session["user_id"]}).fetchone()
        client_username = client_details.username
        session.pop("user_id", None)
        session.pop("logged_on", None)
        flash(f'{client_username}, you have been successfully logged out!')

    return redirect(url_for('index'))

    
@app.route("/find_a_book", methods = ["GET"])
def find():
     """Returns main page"""
    
     #if not logged on, redirect to index page
     if not session.get("logged_on", False):
       flash("Hello there, you are not logged in! Please log in to view the content")
       return redirect(url_for('index'))
   
     #otherwise render main page
     else:
         return render_template("main.html")
  


@app.route("/shall_i_read", methods = ["GET"])
def search():
     """Searches for a book and returns the results of the search"""
     
     #if not logged on, redirect to index page
     if not session.get("logged_on", False):
         return redirect(url_for('index'))
     
     #otherwise get search field and search term and return results page
     else:
         if request.method=="GET":
             book_search_field = request.args.get("search_by_field")
             if book_search_field is None:
                flash("Search for a book by its isbn, title or author below")
                return redirect(url_for('find'))
             book_search_term = '%' + request.args.get("book_query", '') + '%'
             query = f"SELECT * FROM bookdetails WHERE LOWER({book_search_field}) LIKE LOWER(:search_term)"
             book_query_results = db.execute(query,{"search_term": book_search_term}).fetchall()
             book_query_results_exist = True
             if not book_query_results:
                 book_query_results_exist = False
             return render_template("results.html", books_to_be_displayed = book_query_results,
                                    results_exist = book_query_results_exist )



@app.route("/shall_i_read/<queried_isbn>", methods = ["GET"])
def bookdetails(queried_isbn):
     """Returns book details of the queried_book's isbn"""
     
     #if not logged on, redirect to index page
     if not session.get("logged_on", False):
         return redirect(url_for('index'))
     
     #otherwise get queried book's details and search book page
     else:
         if request.method=="GET":
              queried_book_details = db.execute("""SELECT * FROM bookdetails 
                                           WHERE isbn =:isbn1""",
                                        {"isbn1": queried_isbn}).fetchone()
              
              queried_reviews = db.execute("""SELECT reviewdetails.review, reviewdetails.rating, 
                                              reviewdetails.reviewer_id, userdetails.username
                                              FROM reviewdetails JOIN userdetails 
                                              ON reviewdetails.reviewer_id = userdetails.user_id
                                              WHERE reviewdetails.book_isbn =:isbn1 AND 
                                              reviewdetails.reviewer_id <> :client_id""",
                                              {"isbn1": queried_isbn, "client_id": session["user_id"]}).fetchall()
              queried_reviews_exist = True
              if not queried_reviews:
                   queried_reviews_exist = False                  

              client_review = db.execute("""SELECT review, rating FROM reviewdetails 
                                           WHERE book_isbn =:isbn1 AND reviewer_id =:client_id""",
                                        {"isbn1": queried_isbn, "client_id": session["user_id"]}).fetchone()

              
              #goodreads data
              goodreads_data_available = False
              goodreads_data = {"ratings_count" : None, "avg_rating": None}
              
              #The average rating and number of ratings the work has received from Goodreads.
              res = requests.get("https://www.goodreads.com/book/review_counts.json",
                                params={"key":my_developer_key, "isbns":queried_isbn})
              try:
                  res.raise_for_status()
                  goodreads_data_available = True
                  data = res.json()
                  goodreads_data["avg_rating"] = data['books'][0]['average_rating']
                  goodreads_data["ratings_count"] = data['books'][0]['work_ratings_count']
              #except requests.exceptions.RequestException as e:
              #except requests.exceptions.HTTPError as e: 
              except Exception as e:
                  print(f"{res.status_code}: API request unsuccessful")
                  print(e.response.text)
                  
              return render_template("book.html", book_details_to_be_displayed = queried_book_details,
                                     reviews_to_be_displayed = queried_reviews,
                                     reviews_exist = queried_reviews_exist,
                                     client_review_to_be_displayed =  client_review,
                                     goodreads_data_to_be_displayed = goodreads_data,
                                     goodreads_flag = goodreads_data_available)


@app.route("/review/<queried_isbn>", methods = ["POST"])
def review(queried_isbn):
     """Submits book review of the queried_book's isbn"""

     #if not logged on, redirect to index page
     if not session.get("logged_on", False):
         return redirect(url_for('index'))
     
     #otherwise submit review and redirect to updated book page
     else:
         if request.method=="POST":
              client_rating = request.form.get("rating")
              client_review = request.form.get("text_review")
              db.execute("""INSERT INTO reviewdetails (book_isbn, review, reviewer_id, rating)
                            VALUES (:isbn1, :review1, :reviewer_id1, :rating1)""",
                            {"isbn1": queried_isbn, "review1":client_review,
                             "reviewer_id1":session["user_id"], "rating1":client_rating})
              db.commit()
              flash(f'Your review is up!')
              
              print(client_rating)
              print(client_review)
              return redirect(url_for('bookdetails', queried_isbn = queried_isbn))

@app.route("/api/<queried_isbn>")
def book_api(queried_isbn):
    """Returns details about book with isbn = queried_isbn."""
    
    queried_book = db.execute("""SELECT AVG(reviewdetails.rating) AS avg_score,
                                 COUNT(reviewdetails.reviewer_id) AS reviewer_count, 
                                 bookdetails.title, bookdetails.author,
                                 bookdetails.isbn, bookdetails.year 
                                 FROM reviewdetails 
                                 JOIN bookdetails ON reviewdetails.book_isbn = bookdetails.isbn 
                                 WHERE bookdetails.isbn =:isbn1 GROUP BY bookdetails.isbn
                                 """, {"isbn1": queried_isbn}).fetchone()

    if queried_book is None:
        abort(404, description=f"ISBN {queried_isbn} not found in our database")
        #return jsonify({"Error": f"ISBN {queried_isbn} not found in our database"}), 404
    else:
        return jsonify({"title": queried_book.title,
                        "author": queried_book.author,
                        "year": queried_book.year,
                        "isbn": queried_book.isbn,
                        "review_count": queried_book.reviewer_count,
                        "average_score": str(round(queried_book.avg_score,2))
                       })


