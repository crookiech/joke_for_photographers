from flask import Flask
from flask import request
from flask import render_template
from flask import redirect
from flask import url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    intro = db.Column(db.String(300), nullable=False)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<Article %r>' % self.id

@app.route('/')
def main():
    articles = Article.query.order_by(Article.date.desc()).all()
    return render_template('main.html', articles=articles)

@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        title = request.form['title']
        intro = request.form['intro']
        text = request.form['text']

        article = Article(title=title, intro=intro, text=text)

        try:
            db.session.add(article)
            db.session.commit()
            return redirect('/')
        except:
            return "При создании поста произошла ошибка"
        
    else:
        return render_template('create.html')

@app.route('/main/<int:id>')
def post(id):
    article = Article.query.get(id)
    return render_template('post.html', article=article)

@app.route('/main/<int:id>/delete', methods=['GET', 'POST'])
def delete(id):
    article = Article.query.get_or_404(id)
    try:
        db.session.delete(article)
        db.session.commit()
        return redirect('/')
    except:
        return "При удалении поста произошла ошибка"
    
@app.route('/main/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    article = Article.query.get(id)
    if request.method == 'POST':
        article.title = request.form['title']
        article.intro = request.form['intro']
        article.text = request.form['text']

        try:
            db.session.commit()
            return redirect('/')
        except:
            return "При редактировании поста произошла ошибка"
        
    else:
        return render_template('edit.html', article=article)

if __name__ == '__main__':
    app.run(debug=True)