#importaciones de funciones para ayudarnos
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from datetime import datetime
from pytz import timezone


#the * imports all the thins in helpers without specifing what
from helpers import *

# configure application, esto es para inicializar el programa
app = Flask(__name__)

# ensure responses aren't cached. so they go to the server to get fresh data and no to the cache memory
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
#db = SQL("sqlite:///finance.db")
db = SQL("postgres://bgpaphycyrjlid:7a88d94c94f9413c65eb77c227716ee66f48789f0d60e038493ba215a29c5ca4@ec2-54-83-58-222.compute-1.amazonaws.com:5432/daqaposu16bo6g")

#in order to acces to the route the user must be logeg in. that's why we use @login_required
@app.route("/")
@login_required
def index():

    #save current user
    currentUser1 = db.execute("SELECT * FROM users WHERE id = :idUser", idUser=session["user_id"])

    #check if the history/portfolio table is empty
    result = db.execute("SELECT COUNT(*) FROM history WHERE username = :username", username= currentUser1[0]["username"])
    if result[0]["COUNT(*)"] == 0:
        return render_template("index0stock.html")

    #show user portfolio: show to user stocks owned, quanty of shares, current price of each, total value of each, balance
    else:
        #get from the database the symbols of the current user agroping the same symbols and countig them. save in a list called:
        historyTable = db.execute("SELECT symbol, SUM(quanty) AS 'totalShares' , [symbol]  FROM history WHERE username = :username GROUP BY symbol", username= currentUser1[0]["username"])
        #print(historyTable)

        #create empty list called positions and int variable to iterate:
        positions = list()
        n = 0

        totalPrice = 0
        #loop over the table and append the lookup function, and other values to a dict(called lookupSymbol) first and then to the positions list
        for i in historyTable:
            #look up the price and name of each symbol
            lookupSymbol = lookup(historyTable[n]['symbol'])
            #get the number of shares of each symbol
            lookupSymbol['shares'] = historyTable[n]['totalShares']
            #create a dict key with the TOTAL value of each share
            lookupSymbol['total'] = lookupSymbol['price'] * lookupSymbol['shares']
            #append current dict to the list positions
            positions.append (lookupSymbol)
            #move to the next share
            n = n + 1
            totalPrice = totalPrice + lookupSymbol['total']

        totalCash = currentUser1[0]["cash"]
        #print(positions)

        total = currentUser1[0]["cash"] + totalPrice


        return render_template("index.html", index= positions, totalPrice= totalPrice, totalCash= totalCash, total= total)
        #return render_template("index.html", index= try2, name= symbolName['name'])


#get and post es para enviar y recibir informacion entre el cliente y servidor
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    if request.method == "POST":
        if request.form.get("symbol"):

            #symbol of the stock to buy
            symbolInput = lookup(request.form.get("symbol"))

            #ensure symbol exist
            if symbolInput == None:
                return apology("Symbol doesn't exist")

            #save the input of the shares number that user wants to buy in a variable and as a int
            sharesQuanty = int(request.form.get("shares"))

            #ensure that stocks to buy are 1 or grater
            if sharesQuanty <= 0:
                return apology("Must buy 1 or more shares")

            #save price in a variable and as a float
            priceShare = float(symbolInput['price'])

            #save curren time
            naive_dt = datetime.now(timezone('America/New_York'))

            #save id of current user
            idUser=session["user_id"]

            #can user afford to buy? save info of current user
            currentUser = db.execute("SELECT * FROM users WHERE id = :idUser", idUser=session["user_id"])

            #make sure user has enought cash to buy the shares
            totalPrice = priceShare * sharesQuanty
            if (totalPrice > currentUser[0]["cash"]):
                return apology("You don't have enought money!")

            else:
                #save name of user, symbol of shares, quantity and at what price he bought it
                insert = db.execute("INSERT INTO history (username, symbol, quanty, price, date) VALUES (:username, :symbol, :quanty, :price, :date)", username = currentUser[0]["username"], symbol = symbolInput["symbol"], quanty = sharesQuanty, price = totalPrice, date = naive_dt)

                #update user cash after the purchase
                db.execute("UPDATE users SET cash = cash - :totalPrice WHERE id = :idUser", totalPrice=totalPrice, idUser=session["user_id"])

                #redirect to index
                return redirect(url_for("index"))

    return render_template("buy.html")




@app.route("/history")
@login_required
def history():
    """Show history of transactions."""

    #save current user
    currentUser1 = db.execute("SELECT * FROM users WHERE id = :idUser", idUser=session["user_id"])

    #query to check if table is empty or not
    result1 = db.execute("SELECT COUNT(*) FROM history WHERE username = :username", username= currentUser1[0]["username"])
    if result1[0]["COUNT(*)"] == 0:
        return apology("empty table")

    else:
        #if is not empty save all the user history table in result.
        result = db.execute("SELECT symbol, quanty, price, date FROM history WHERE username = :username", username= currentUser1[0]["username"])

        print(result)

        return render_template("history.html", history= result)
        #pass all the variables needed to html

    return render_template("history.html")

#login is already done (use them as a example of how to implement the others ones)
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username") #calling apology function

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        #SAVE USERNAME
        session["user_name"] = rows[0]["username"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

#logout is already done
@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

#display form, retriveve stock quote, display stock quote
@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    #return render_template("quote.html")
    if request.method == "POST":
        #look in yahoo finance for requested symbol
        if request.form.get("symbol"):
            #return the dictnionary found. (name, price, symbol)
            symbolInput = lookup(request.form.get("symbol"))
            #print example accesing only one key in the dict
            #print (symbolInput['name'])

            #ensure symbol is not none
            if symbolInput != None:
                return render_template("stock.html", name= symbolInput['name'], price= symbolInput['price'], symbol= symbolInput['symbol'])
        #return to quote html with message symbol dosent exist if symbolInput = None

        #return apology("SKULKER")

    return render_template("quote.html")


#display a form so the user can register a account. check if password is valid and add the user to database
#log them in
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    if request.method == "POST":
        # ensure username was submitted
        if not request.form.get("username"):
            return failure("must provide username") #calling apology function

        if request.form.get("password") != request.form.get("password2"):
            return failure("must provide username")

        # we dont store de password that they type in to add security, we store a hash
        hash = pwd_context.hash(request.form.get("password"))

        #save data in table
        result = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username = request.form.get("username"), hash = hash)

        #check for failure becouse of same username
        if not result:
            return badusername("Username already exist")

        else:
            #log them in automatically if they register
            #session["user_id"] = rows[0]["id"]
            # query database for username
            rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
            session["user_id"] = rows[0]["id"]
            #redirect user to homepage
            return redirect(url_for("index"))

    return render_template("register.html")
    #return render_template("login.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    #save current user
    currentUser1 = db.execute("SELECT * FROM users WHERE id = :idUser", idUser=session["user_id"])

    #check if the history/portfolio table is empty
    result = db.execute("SELECT COUNT(*) FROM history WHERE username = :username", username= currentUser1[0]["username"])
    if result[0]["COUNT(*)"] == 0:
        return render_template("index0stock.html")

    else:

        historyTable = db.execute("SELECT symbol, SUM(quanty) AS 'totalShares' , [symbol]  FROM history WHERE username = :username GROUP BY symbol", username= currentUser1[0]["username"])

        #print(historyTable)

        #create empty list called positions and int variable to iterate:
        positions = list()
        n = 0

        totalPrice = 0

        #loop over the table and append the lookup function, and other values to a dict(called lookupSymbol) first and then to the positions list
        for i in historyTable:
            #look up the price and name of each symbol
            lookupSymbol = lookup(historyTable[n]['symbol'])
            #get the number of shares of each symbol
            lookupSymbol['shares'] = historyTable[n]['totalShares']
            #create a dict key with the TOTAL value of each share
            lookupSymbol['total'] = lookupSymbol['price'] * lookupSymbol['shares']
            #append current dict to the list positions
            positions.append (lookupSymbol)
            #move to the next share
            n = n + 1
            totalPrice = totalPrice + lookupSymbol['total']

        #print(totalPrice)

        if request.method == "POST":

            #save the input of the shares number that user wants to buy in a variable and as a int
            symbolName = request.form.get("symbol")
            numberToSell = int(request.form.get("shares"))

            #sell only if the input is 1 or more shares
            if numberToSell <= 0:
                return apology("Sell one or more shares")

            if request.form["symbol"] == "" or request.form["shares"] == "":
                return apology("Symbol or number of shares are incorrect")

            #search for symbol in user list. (check if the user has at least 1 share)
            if any(d['symbol'] == symbolName.upper() for d in positions):

                shares_index = next(index for (index, d) in enumerate(positions) if d["symbol"] == symbolName.upper())

                #check if el numero que queremos vender es igual o menor a lo que tenemos
                if numberToSell <= positions[shares_index]['shares']:

                    print(positions)
                    print(positions[shares_index]['price'])
                    updateCash = positions[shares_index]['price'] * numberToSell
                    print(updateCash)
                    totalPrice = updateCash

                    #generate a negative purchase, query
                    insert = db.execute("INSERT INTO history (username, symbol, quanty, price, date) VALUES (:username, :symbol, :quanty, :price, :date)", username = currentUser1[0]["username"], symbol = symbolName.upper(), quanty = (numberToSell * -1), price = (totalPrice * -1), date = datetime.now())

                    #update user cash after selling the shares
                    #db.execute("UPDATE users SET cash = cash + :sellPrice WHERE id = :idUser", sellPrice= updateCash, idUser=session["user_id"])

                    db.execute("UPDATE users SET cash = cash + :totalPrice WHERE id = :idUser", totalPrice=totalPrice, idUser=session["user_id"])

                    return redirect(url_for("index"))
                else:
                    return apology("You don't have that many shares")


    return render_template("sell.html", index= positions, totalPrice= totalPrice)

