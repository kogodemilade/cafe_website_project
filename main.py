from flask import Flask, jsonify, render_template, request
from flask_bootstrap import Bootstrap
import random
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, SelectField, IntegerField
from wtforms.validators import DataRequired, URL, Email
from flask_ckeditor import CKEditor, CKEditorField
import os

app = Flask(__name__)
bootstrap = Bootstrap(app)
app.config['SECRET_KEY'] = os.environ.get('CSRF_KEY')
##CREATE DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cafes.db'
db = SQLAlchemy()
db.init_app(app)


# CREATE TABLE
class Cafe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    map_url = db.Column(db.String(500), nullable=False)
    img_url = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(250), nullable=False)
    seats = db.Column(db.String(250), nullable=False)
    has_toilet = db.Column(db.Boolean, nullable=False)
    has_wifi = db.Column(db.Boolean, nullable=False)
    has_sockets = db.Column(db.Boolean, nullable=False)
    can_take_calls = db.Column(db.Boolean, nullable=False)
    coffee_price = db.Column(db.String(250), nullable=True)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class SuggestCafeForm(FlaskForm):
    name = StringField('Name of the Cafe', validators=[DataRequired()])
    map = StringField('Cafe Map URL', validators=[DataRequired(), URL()])
    location = StringField("Cafe Location", validators=[DataRequired()])
    seats = StringField("A rough estimate (range also accepted) of the number of seats", validators=[DataRequired()])
    has_toilet = SelectField("Are Restrooms Available?", choices=[('Yes', 1), ('No', 0)], validators=[DataRequired()])
    has_wifi = SelectField("Is Public Wifi Available?", choices=[('Yes', 1), ('No', 0)], validators=[DataRequired()])
    has_sockets = SelectField("Are Sockets Available?", choices=[('Yes', 1), ('No', 0)], validators=[DataRequired()])
    can_take_calls = SelectField("Are customers allowed to make calls?", choices=[('Yes', 1), ('No', 0)], validators=[DataRequired()])
    img = StringField("Cafe Image URL", validators=[DataRequired(), URL()])
    coffee_price = StringField("Price of a cup of coffee (in pounds)", validators=[DataRequired()])
    submit = SubmitField("Submit Post")


class Contact(FlaskForm):
    reason = StringField('Reason for contacting', validators=[DataRequired()])
    email = StringField('Email', validators=[Email()])
    body = CKEditorField('Message', validators=[DataRequired()])
    submit = SubmitField("Submit Post")

with app.app_context():
    db.create_all()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/random")
def get_random_cafe():
    result = db.session.execute(db.select(Cafe))
    all_cafes = result.scalars().all()
    random_cafe = random.choice(all_cafes)
    return jsonify(cafe=random_cafe.to_dict())


@app.route("/contact")
def contact():
    contact_form = Contact()
    return render_template('contact.html', form=contact_form)


@app.route("/all")
def get_all_cafes():
    result = db.session.execute(db.select(Cafe).order_by(Cafe.name))
    all_cafes = result.scalars().all()
    # return jsonify(cafes=[cafe.to_dict() for cafe in all_cafes])
    return render_template('cafes.html', cafes=all_cafes, location=False)


@app.route("/cafe/<int:index>")
def show_cafe(index):
    requested_cafe = None
    cafes = db.session.execute(db.select(Cafe)).scalars().all()
    for cafe in cafes:
        if cafe.id == index:
            requested_cafe = cafe
    # return jsonify(cafes=[cafe.to_dict() for cafe in all_cafes])
    return render_template('selected_cafe.html', cafe=requested_cafe)


@app.route("/search/<loc>")
def get_cafes_at_location(loc):
    # query_location = request.args.get("loc")
    result = db.session.execute(db.select(Cafe).where(Cafe.location == loc))
    # Note, this may get more than one cafe per location
    all_cafes = result.scalars().all()
    if all_cafes:
        # return jsonify(cafes=[cafe.to_dict() for cafe in all_cafes])
        return render_template('cafes.html', cafes=all_cafes, locate=True, location=loc)
    else:
        return jsonify(error={"Not Found": "Sorry, we don't have a cafe at that location."}), 404


# Test this inside Postman. Request type: Post ->  Body ->  x-www-form-urlencoded
@app.route("/add", methods=["POST", "GET"])
def post_new_cafe():
    if request.method == 'POST':
        new_cafe = Cafe(
            name=request.form.get("name"),
            map_url=request.form.get("map_url"),
            img_url=request.form.get("img_url"),
            location=request.form.get("loc"),
            has_sockets=bool(request.form.get("sockets")),
            has_toilet=bool(request.form.get("toilet")),
            has_wifi=bool(request.form.get("wifi")),
            can_take_calls=bool(request.form.get("calls")),
            seats=request.form.get("seats"),
            coffee_price=request.form.get("coffee_price"),
        )
        db.session.add(new_cafe)
        db.session.commit()
        return jsonify(response={"success": "Successfully added the new cafe."})
    form = SuggestCafeForm()
    return render_template('suggest.html', form=form)

# Updating the price of a cafe based on a particular id:
# http://127.0.0.1:5000/update-price/CAFE_ID?new_price=£5.67
@app.route("/update-price/<int:cafe_id>", methods=["PATCH"])
def patch_new_price(cafe_id):
    new_price = request.args.get("new_price")
    cafe = db.get_or_404(Cafe, cafe_id)
    if cafe:
        cafe.coffee_price = new_price
        db.session.commit()
        return jsonify(response={"success": "Successfully updated the price."}), 200
    else:
        return jsonify(error={"Not Found": "Sorry a cafe with that id was not found in the database."}), 404

# Deletes a cafe with a particular id.
@app.route("/report-closed/<int:cafe_id>", methods=["DELETE"])
def delete_cafe(cafe_id):
    api_key = request.args.get("api-key")
    if api_key == "TopSecretAPIKey":
        cafe = db.get_or_404(Cafe, cafe_id)
        if cafe:
            db.session.delete(cafe)
            db.session.commit()
            return jsonify(response={"success": "Successfully deleted the cafe from the database."}), 200
        else:
            return jsonify(error={"Not Found": "Sorry a cafe with that id was not found in the database."}), 404
    else:
        return jsonify(error={"Forbidden": "Sorry, that's not allowed. Make sure you have the correct api_key."}), 403


if __name__ == '__main__':
    app.run(debug=True)
