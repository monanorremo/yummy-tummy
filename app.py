import os
import random
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env

app = Flask(__name__)


app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")


mongo = PyMongo(app)


@app.route("/")
def index():
    recipes = list(mongo.db.recipes.find().limit(3))
    return render_template("index.html", recipes=recipes)


@app.route("/get_recipes")
def get_recipes():
    recipes = list(mongo.db.recipes.find().sort("food_name", 1))
    return render_template("recipes.html", recipes=recipes)


@app.route("/recipe_description/<recipe_id>")
def recipe_description(recipe_id):
    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    return render_template("recipe_description.html", recipe=recipe)


@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    recipes = list(mongo.db.recipes.find({"$text": {"$search": query}}))
    return render_template("recipes.html", recipes=recipes)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # check if username already exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("This chef already exists")
            return redirect(url_for("register"))

        register = {
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password"))
        }
        mongo.db.users.insert_one(register)

        # put the new user into 'session' cookie
        session["user"] = request.form.get("username").lower()
        flash("Registration Successful!")
        return redirect(url_for("profile", username=session["user"]))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # check if username exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                session["user"] = request.form.get("username").lower()
                flash("Welcome, {}".format(
                    request.form.get("username")))
                return redirect(url_for(
                    "profile", username=session["user"]))
            else:
                # invalid password match
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            # username doesn't exist
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    # grab the session user's username from db
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]

    # show users own recipes(code with some help from
    # another CI student https://github.com/brimurphy/
    # share-a-plate/blob/master/templates/my_recipes.html

    recipes = list(mongo.db.recipes.find())

    if session["user"]:
        return render_template("profile.html", username=username,
                               recipes=recipes)

    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    # remove user from session cookie
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("login"))


@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        recipes = {
            "food_type": request.form.get("food_type"),
            "food_name": request.form.get("food_name"),
            "ingredients": split_strip(request.form.get("ingredients")),
            "prep": split_strip(request.form.get("prep")),
            "food_img": request.form.get("food_img"),
            "created_by": session["user"]
        }
        mongo.db.recipes.insert_one(recipes)
        flash("Recipe Successfully Added")
        return redirect(url_for("get_recipes"))

    categories = mongo.db.categories.find().sort("food_type", 1)
    return render_template("add_recipe.html", categories=categories)


@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    if request.method == "POST":
        submit = {
            "food_type": request.form.get("food_type"),
            "food_name": request.form.get("food_name"),
            "ingredients": split_strip(request.form.get("ingredients")),
            "prep": split_strip(request.form.get("prep")),
            "food_img": request.form.get("food_img"),
            "created_by": session["user"]
        }
        mongo.db.recipes.update({"_id": ObjectId(recipe_id)}, submit)
        flash("Recipe Successfully Updated")

    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    recipe["ingredients"] = format_array(recipe["ingredients"])
    recipe["prep"] = format_array(recipe["prep"])
    categories = mongo.db.categories.find().sort("food_type", 1)
    return render_template("edit_recipe.html",
                           recipe=recipe, categories=categories)


# list comprehension to split array from input in StackOverflow:
# https://stackoverflow.com/questions/4071396/split-by-comma-and-strip-whitespace-in-python


def split_strip(array_string):
    return [x.strip( ) for x in array_string.split(':')]


def format_array(arr):
    return ":".join(arr)


@app.route("/delete_recipe/<recipe_id>")
def delete_recipe(recipe_id):
    mongo.db.recipes.remove({"_id": ObjectId(recipe_id)})
    flash("Recipe Successfully Deleted")
    return redirect(url_for("get_recipes"))


@app.route("/manage_recipes")
def manage_recipes():
    recipes = list(mongo.db.recipes.find().sort("food_name", 1))
    return render_template("manage_recipes.html", recipes=recipes)


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=False)
