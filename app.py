from flask import Flask, current_app, request, flash,redirect,url_for,render_template
from flask_pymongo import PyMongo
from dateutil.parser import parse

app = Flask(__name__)
app.secret_key = 'secret'
app.config["MONGO_URI"] = "mongodb://localhost:27017/testdb"
mongo = PyMongo(app)


@app.route('/', methods=['GET'])
def show_entry():
    users = mongo.db.user.find()
    entries = []
    for row in users:
        entries.append({"name": row['name'], "birthday": row['birthday'].strftime("%Y/%m/%d")})

    return render_template('toppage.html', entries=entries)


@app.route('/add', methods=['POST'])
def add_entry():
    mongo.db.user.insert({"name": request.form['name'], "birthday": parse(request.form['birthday'])})
    flash('New entry was successfully posted')
    return redirect(url_for('show_entry'))


@app.route('/search', methods=['POST'])
def filter_entry():
    start = parse(request.form['start'])
    end = parse(request.form['end'])
    cur = mongo.db.user.find({'birthday': {'$lt': end, '$gte': start}})
    results = []
    for row in cur:
        results.append({"name": row['name'], "birthday": row['birthday'].strftime("%Y/%m/%d")})

    return render_template('result.html', results=results)


if __name__ == '__main__':
    app.run(host='127.0.0.1')

