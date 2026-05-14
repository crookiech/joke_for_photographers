from flask import Flask
from flask import request
from flask import render_template
from flask import redirect
from flask import url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
import os
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    location = db.Column(db.String(300), nullable=False)
    props = db.Column(db.String(300), nullable=False)
    shoot_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    images = db.Column(db.Text, nullable=True)
    drawings = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return '<Article %r>' % self.id

@app.route('/')
def main():
    articles = Article.query.order_by(Article.shoot_date.asc()).all()
    return render_template('main.html', articles=articles)

@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        location = request.form['location']
        props = request.form['props']
        shoot_date_str = request.form['shoot_date']
        
        shoot_date = datetime.strptime(shoot_date_str, '%Y-%m-%d').date()

        uploaded_files = request.files.getlist('images[]')
        saved_images = []
        
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                saved_images.append(f'uploads/{unique_filename}')
        
        images_str = ','.join(saved_images) if saved_images else None
        
        drawing_files = request.files.getlist('drawings[]')
        saved_drawings = []
        
        for file in drawing_files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                unique_filename = f"drawing_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                saved_drawings.append(f'uploads/{unique_filename}')
        
        drawings_str = ','.join(saved_drawings) if saved_drawings else None
        
        article = Article(
            title=title, 
            description=description, 
            location=location,
            props=props,
            shoot_date=shoot_date,
            images=images_str, 
            drawings=drawings_str
        )

        try:
            db.session.add(article)
            db.session.commit()
            return redirect('/')
        except Exception as e:
            return f"При создании поста произошла ошибка: {str(e)}"
        
    else:
        return render_template('create.html')

@app.route('/main/<int:id>')
def post(id):
    article = Article.query.get(id)
    return render_template('post.html', article=article)

@app.route('/main/<int:id>/delete', methods=['GET', 'POST'])
def delete(id):
    article = Article.query.get_or_404(id)
    
    if article.images:
        for image_path in article.images.split(','):
            if image_path.strip():
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(image_path))
                if os.path.exists(full_path):
                    os.remove(full_path)
    
    if article.drawings:
        for drawing_path in article.drawings.split(','):
            if drawing_path.strip():
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(drawing_path))
                if os.path.exists(full_path):
                    os.remove(full_path)
    
    try:
        db.session.delete(article)
        db.session.commit()
        return redirect('/')
    except Exception as e:
        return f"При удалении поста произошла ошибка: {str(e)}"
    
@app.route('/main/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    article = Article.query.get_or_404(id)
    
    if request.method == 'POST':
        article.title = request.form['title']
        article.description = request.form['description']
        article.location = request.form['location']
        article.props = request.form['props']
        
        shoot_date_str = request.form['shoot_date']
        article.shoot_date = datetime.strptime(shoot_date_str, '%Y-%m-%d').date()
        
        removed_photos = request.form.get('removedPhotos', '[]')
        removed_photos_list = json.loads(removed_photos)
        
        for img_path in removed_photos_list:
            if img_path:
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(img_path))
                if os.path.exists(full_path):
                    os.remove(full_path)
        
        current_photos = article.images.split(',') if article.images else []
        remaining_photos = [img for img in current_photos if img.strip() and img not in removed_photos_list]
        
        new_photos = request.files.getlist('newPhotos[]')
        saved_photos = []
        
        for file in new_photos:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                saved_photos.append(f'uploads/{unique_filename}')
        
        removed_drawings = request.form.get('removedDrawings', '[]')
        removed_drawings_list = json.loads(removed_drawings)
        
        for img_path in removed_drawings_list:
            if img_path:
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(img_path))
                if os.path.exists(full_path):
                    os.remove(full_path)
        
        current_drawings = article.drawings.split(',') if article.drawings else []
        remaining_drawings = [img for img in current_drawings if img.strip() and img not in removed_drawings_list]
        
        new_drawings = request.files.getlist('newDrawings[]')
        saved_drawings = []
        
        for file in new_drawings:
            if file and file.filename:
                filename = secure_filename(file.filename)
                unique_filename = f"drawing_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                saved_drawings.append(f'uploads/{unique_filename}')
        
        all_photos = remaining_photos + saved_photos
        all_drawings = remaining_drawings + saved_drawings
        
        article.images = ','.join(all_photos) if all_photos else None
        article.drawings = ','.join(all_drawings) if all_drawings else None
        
        try:
            db.session.commit()
            return redirect(url_for('post', id=article.id))
        except Exception as e:
            return f"При редактировании поста произошла ошибка: {str(e)}"
        
    else:
        return render_template('edit.html', article=article)

if __name__ == '__main__':
    app.run(debug=True)