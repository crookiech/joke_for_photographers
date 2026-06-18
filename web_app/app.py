from flask import Flask
from flask import request
from flask import render_template
from flask import redirect
from flask import url_for
from flask import flash
from flask import send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from werkzeug.utils import secure_filename
import os
import json
import io
from fpdf import FPDF

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'

app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'sign_in'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('articles', lazy=True))

    def __repr__(self):
        return '<Article %r>' % self.id

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def main():
    if current_user.is_authenticated:
        articles = Article.query.filter_by(user_id=current_user.id).order_by(Article.shoot_date.asc()).all()
    else:
        articles = []
    
    return render_template('main.html', articles=articles, current_user=current_user)

@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    if current_user.is_authenticated:
        return redirect('/')
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            flash('Вход выполнен успешно!', 'success')
            return redirect(next_page or '/')
        else:
            flash('Неверный email или пароль', 'danger')
    
    return render_template('sign_in.html')

@app.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if current_user.is_authenticated:
        return redirect('/')
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Пользователь с таким email уже существует', 'danger')
            return redirect(url_for('sign_up'))
        
        if password != confirm_password:
            flash('Пароли не совпадают', 'danger')
            return redirect(url_for('sign_up'))
        
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'danger')
            return redirect(url_for('sign_up'))
        
        user = User(email=email)
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Регистрация успешно завершена! Теперь вы можете войти.', 'success')
            return redirect(url_for('sign_in'))
        except Exception as e:
            flash(f'Ошибка при регистрации: {str(e)}', 'danger')
    
    return render_template('sign_up.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect('/')

@app.route('/create', methods=['GET', 'POST'])
@login_required
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
            drawings=drawings_str,
            user_id=current_user.id
        )

        try:
            db.session.add(article)
            db.session.commit()
            flash('Статья успешно создана!', 'success')
            return redirect('/')
        except Exception as e:
            flash(f'При создании поста произошла ошибка: {str(e)}', 'danger')
            return redirect(url_for('create'))
        
    else:
        return render_template('create.html')

@app.route('/main/<int:id>')
def post(id):
    article = Article.query.get_or_404(id)
    return render_template('post.html', article=article, current_user=current_user)

@app.route('/main/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    article = Article.query.get_or_404(id)
    
    if article.user_id != current_user.id:
        flash('У вас нет прав для удаления этой статьи', 'danger')
        return redirect(url_for('post', id=id))
    
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
        flash('Статья успешно удалена!', 'success')
        return redirect('/')
    except Exception as e:
        flash(f'При удалении поста произошла ошибка: {str(e)}', 'danger')
        return redirect(url_for('post', id=id))
    
@app.route('/main/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    article = Article.query.get_or_404(id)
    
    # Проверка прав: редактировать может только автор
    if article.user_id != current_user.id:
        flash('У вас нет прав для редактирования этой статьи', 'danger')
        return redirect(url_for('post', id=id))
    
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
            flash('Статья успешно обновлена!', 'success')
            return redirect(url_for('post', id=article.id))
        except Exception as e:
            flash(f'При редактировании поста произошла ошибка: {str(e)}', 'danger')
            return redirect(url_for('edit', id=id))
        
    else:
        return render_template('edit.html', article=article)

from fpdf import FPDF

@app.route('/main/<int:id>/pdf')
@login_required
def generate_pdf(id):
    article = Article.query.get_or_404(id)
    
    if article.user_id != current_user.id:
        flash('У вас нет прав для скачивания этой статьи', 'danger')
        return redirect(url_for('post', id=id))
    
    pdf = FPDF()
    pdf.add_page()
    
    font_loaded = False
    try:
        pdf.add_font('DejaVu', '', 'DejaVuSansMono.ttf')
        pdf.set_font('DejaVu', '', 16)
        font_loaded = True
        print("Шрифт DejaVuSansMono.ttf успешно загружен")
    except Exception as e:
        print(f"Ошибка загрузки шрифта DejaVuSansMono.ttf: {e}")
    
    if not font_loaded:
        pdf.set_font('Helvetica', '', 16)
        print("Используется стандартный шрифт Helvetica")
    
    font_name = 'DejaVu' if font_loaded else 'Helvetica'

    pdf.set_font(font_name, '', 16)
    pdf.cell(0, 10, f'{article.title}', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.set_font(font_name, '', 12)
    pdf.cell(0, 10, f'Дата съемки: {article.shoot_date.strftime("%d.%m.%Y")}', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 10, f'Описание: {article.description}', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 10, f'Реквизит: {article.props}', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 10, f'Локация: {article.location}', new_x='LMARGIN', new_y='NEXT')
    if article.images:
        pdf.cell(0, 10, 'Мудборд и референсы:', new_x='LMARGIN', new_y='NEXT')
        images_list = article.images.split(',')
        for img_path in images_list[:4]:
            if img_path.strip():
                full_path = os.path.join('static', img_path.strip())
                if os.path.exists(full_path):
                    try:
                        pdf.image(full_path, x=10, w=80)
                        pdf.ln(5)
                    except Exception as e:
                        print(f"Ошибка загрузки изображения {full_path}: {e}")
    if article.drawings:
        drawings_list = article.drawings.split(',')
        for img_path in drawings_list[:4]:
            if img_path.strip():
                full_path = os.path.join('static', img_path.strip())
                if os.path.exists(full_path):
                    try:
                        pdf.image(full_path, x=10, w=80)
                        pdf.ln(5)
                    except Exception as e:
                        print(f"Ошибка загрузки рисунка {full_path}: {e}")
    
    try:
        pdf_output = pdf.output(dest='S')
        if isinstance(pdf_output, (bytes, bytearray)):
            buffer = io.BytesIO(pdf_output)
        else:
            buffer = io.BytesIO(pdf_output.encode('latin-1'))
        
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{article.title} {article.shoot_date.strftime('%d.%m.%Y')}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"Ошибка при создании PDF: {e}")
        flash(f'Ошибка при создании PDF: {str(e)}', 'danger')
        return redirect(url_for('post', id=id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)