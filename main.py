from flask import Flask, render_template, redirect, url_for, request, flash

import datetime
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from statistics import mean


app = Flask(__name__, static_url_path='', static_folder='static')
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
current_year = datetime.datetime.now().year

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cafes.db'
db = SQLAlchemy()
db.init_app(app)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    cafes = relationship("MyCafe", back_populates="author")
    ratings = relationship("Rating", back_populates="author")


class MyCafe(db.Model):
    __tablename__ = "my_cafe"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    location = db.Column(db.String(250), nullable=False)
    opening = db.Column(db.Time, nullable=False)
    closing = db.Column(db.Time, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    ratings = relationship("Rating", back_populates="cafe")
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="cafes")


class Rating(db.Model):
    __tablename__ = "ratings"
    id = db.Column(db.Integer, primary_key=True)
    wifi = db.Column(db.Integer, nullable=False)
    coffee = db.Column(db.Integer, nullable=False)
    power = db.Column(db.Integer)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    author = relationship("User", back_populates="ratings")
    cafe_id = db.Column(db.Integer, db.ForeignKey("my_cafe.id", ondelete="CASCADE"))
    cafe = relationship("MyCafe", back_populates="ratings")


with app.app_context():
    db.create_all()


@app.route("/")
def landing():
    return render_template("landing.html", year=current_year)


@app.route("/home")
def home():
    cafes = db.session.execute(db.select(MyCafe)).scalars().all()
    ratings = db.session.query(Rating.cafe_id,
                               func.avg(Rating.wifi).label('avg_wifi'),
                               func.avg(Rating.coffee).label('avg_coffee'),
                               func.avg(Rating.power).label('avg_power')
                               ).group_by(Rating.cafe_id).all()
    average_ratings = {rating[0]: mean([rating[1], rating[2], rating[3]]) for rating in ratings}
    return render_template("home.html", cafes=cafes, ratings=average_ratings, year=current_year)


@app.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        print('POST')
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        if name == "" or email == "" or password == "":
            flash('please fill in all fields')
            return redirect(url_for('sign_up'))
        if db.session.execute(db.select(User).where(User.email == email)).scalar():
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        new_user = User(name=name,
                        email=email,
                        password=generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
                        )
        db.session.add(new_user)
        db.session.commit()
        print("new user added")
        login_user(new_user)
        return redirect(url_for('home'))
    print('GET')
    return render_template("sign_up.html", year=current_year)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if not user:
            flash("No user registered with this email")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash("Wrong password, please try again")
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('home'))

    return render_template("login.html", year=current_year)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/account')
@login_required
def account():
    users_cafes = db.session.execute(db.select(MyCafe).where(MyCafe.author_id == current_user.id)).scalars().all()
    user_ratings = (db.session.query(Rating.cafe_id,
                                     func.avg(Rating.wifi).label('avg_wifi'),
                                     func.avg(Rating.coffee).label('avg_coffee'),
                                     func.avg(Rating.power).label('avg_power')
                                     ).filter(Rating.author_id == current_user.id)
                    .group_by(Rating.cafe_id)
                    .all())
    average_user_ratings = {rating[0]: mean([rating[1], rating[2], rating[3]]) for rating in user_ratings}
    return render_template("account.html", year=current_year, cafes=users_cafes,
                           ratings=average_user_ratings)


@app.route("/delete_account/", methods=['POST'])
@login_required
def delete_account():
    account_to_delete = db.get_or_404(User, current_user.id)
    if account_to_delete.id == current_user.id:
        logout_user()
        db.session.delete(account_to_delete)
        db.session.commit()
        flash(f"{account_to_delete.name}'s account deleted successfully")
    else:
        flash(f"You don't have permission to delete {account_to_delete.name}'s account")
    return redirect(url_for('sign_up'))


@app.route("/change_email", methods=['POST'])
@login_required
def change_email():
    account_to_change = db.get_or_404(User, current_user.id)
    new_email = request.form['new_email']
    if new_email != "":
        if account_to_change.email == current_user.email:
            account_to_change.email = new_email
            db.session.commit()
            flash(f"{account_to_change.name}'s email updated successfully")
        else:
            flash(f"You don't have permission to change {account_to_change.name}'s email")
    else:
        flash("Please provide a valid email address")
    return redirect(url_for('account'))


@app.route("/change_password", methods=['POST'])
@login_required
def change_password():
    account_to_change = db.get_or_404(User, current_user.id)
    old_password = request.form['old_password']
    new_password = request.form['new_password']

    if not check_password_hash(account_to_change.password, old_password):
        flash("Wrong password, please try again")
    elif new_password == "":
        flash("Please provide a new password")
    else:
        account_to_change.password = generate_password_hash(new_password, method='pbkdf2:sha256', salt_length=8)
        db.session.commit()
        flash(f"{account_to_change.name}'s password updated successfully")
    return redirect(url_for('account'))


@app.route("/add_cafe", methods=['GET', 'POST'])
@login_required
def add_cafe():
    if request.method == 'POST':
        new_cafe = MyCafe(
            name=request.form['name'],
            location=request.form['location'],
            opening=datetime.datetime.strptime(request.form['opening'], "%H:%M").time(),
            closing=datetime.datetime.strptime(request.form['closing'], "%H:%M").time(),
            img_url=request.form['img_url'],
            author=current_user
        )
        db.session.add(new_cafe)
        new_rating = Rating(
                            wifi=int(request.form['wifi']),
                            coffee=int(request.form['coffee']),
                            power=int(request.form['power']),
                            cafe=new_cafe,
                            author=current_user
                            )
        db.session.add(new_rating)
        db.session.commit()
        return redirect(url_for('show_cafe', cafe_id=new_cafe.id))

    return render_template("add_cafe.html", year=current_year)


@app.route("/edit_cafe/<int:cafe_id>", methods=['GET', 'POST'])
@login_required
def edit_cafe(cafe_id):
    cafe_to_edit = db.get_or_404(MyCafe, cafe_id)
    cafe_ratings = db.session.execute(db.select(Rating).where(Rating.cafe_id == cafe_id,
                                                              Rating.author_id == current_user.id)).scalar()
    if request.method == 'POST':
        print(request.form['opening'])
        print(request.form['closing'])
        if cafe_to_edit.author_id == current_user.id:
            cafe_to_edit.name = request.form['name']
            cafe_to_edit.location = request.form['location']
            cafe_to_edit.opening = datetime.datetime.strptime(request.form['opening'], "%H:%M").time()
            cafe_to_edit.closing = datetime.datetime.strptime(request.form['closing'], "%H:%M").time()
            cafe_to_edit.img_url = request.form['img_url']
            db.session.commit()
            flash(f'My Wify Cafe {cafe_to_edit.name} has been updated')
            return redirect(url_for('show_cafe', cafe_id=cafe_id))
        else:
            flash(f"You don't have permission to edit the cafe {cafe_to_edit.name}")
            return redirect(url_for('show_cafe', cafe_id=cafe_id))
    return render_template('edit_cafe.html', year=current_year, cafe=cafe_to_edit, ratings=cafe_ratings)


@app.route("/delete_cafe/<int:cafe_id>")
@login_required
def delete_cafe(cafe_id):
    cafe_to_delete = db.get_or_404(MyCafe, cafe_id)
    db.session.delete(cafe_to_delete)
    db.session.commit()
    flash(f"{cafe_to_delete.Name}'s account deleted successfully")

    return redirect(url_for('home'))


@app.route("/cafe/<int:cafe_id>")
def show_cafe(cafe_id):
    cafe_to_show = db.get_or_404(MyCafe, cafe_id)
    ratings = db.session.execute(db.select(Rating).where(Rating.cafe_id == cafe_id)).scalars().all()
    number_of_ratings = len(ratings)
    average_rating = {"wifi": mean([rating.wifi for rating in ratings]),
                      "coffee": mean([rating.coffee for rating in ratings]),
                      "power": mean([rating.power for rating in ratings]),
                      }

    return render_template("cafe.html", year=current_year, cafe=cafe_to_show,
                           number_of_ratings=number_of_ratings, average=average_rating)


@app.route("/rate_cafe/<int:cafe_id>", methods=['GET', 'POST'])
@login_required
def rate_cafe(cafe_id):
    cafe_to_rate = db.get_or_404(MyCafe, cafe_id)
    cafe_ratings = db.session.execute(db.select(Rating).where(Rating.cafe_id == cafe_id,
                                                         Rating.author_id == current_user.id)).scalar()

    if request.method == 'POST':
        wifi = int(request.form['wifi'])
        coffee = int(request.form['coffee'])
        power = int(request.form['power'])
        if cafe_ratings:
            cafe_ratings.wifi = wifi
            cafe_ratings.coffee = coffee
            cafe_ratings.power = power
            db.session.commit()
            flash("Your rating has been updated")
        else:
            new_rating = Rating(wifi=wifi,
                                coffee=coffee,
                                power=power,
                                author=current_user,
                                cafe=cafe_to_rate)
            db.session.add(new_rating)
            db.session.commit()
            flash("Your rating has been saved")
        return redirect(url_for('show_cafe', cafe_id=cafe_id))

    if not cafe_ratings:
        cafe_ratings = Rating(wifi=3,
                              coffee=3,
                              power=3)
    return render_template("rate_cafe.html", year=current_year, cafe=cafe_to_rate, ratings=cafe_ratings)

# with app.app_context():
#     new_user = User(
#         name='Giulio Biagini',
#         email='email@yahoo.it',
#         password=generate_password_hash('********', method='pbkdf2:sha256', salt_length=8)
#     )
#     new_cafe = MyCafe(
#                 name="Starbucks",
#                 author_id=1,
#                 location='https://maps.app.goo.gl/KVjjzQSJFfzUcHn39',
#                 opening=datetime.time(8),
#                 closing=datetime.time(21),
#                 img_url='https://maps.app.goo.gl/Z1NUXBozQFKQUnBQ9')
#
#     new_rating = Rating(
#     wifi=3,
#     coffee=4,
#     power=4,
#     author_id=1,
#     cafe_id=1,
#     )
#
#     db.session.add(new_user)
#     db.session.add(new_cafe)
#     db.session.add(new_rating)
#     db.session.commit()


if __name__ == '__main__':
    app.run(debug=True, port=5001)
