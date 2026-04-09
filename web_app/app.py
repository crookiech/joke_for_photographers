from flask import Flask
from flask import request
from flask import jsonify
from flask import render_template
from flask import redirect
from flask import url_for

app = Flask(__name__)

@app.route('/')
def main():
    return render_template('main.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        return redirect(url_for('admin'))
    return render_template('admin_login.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

if __name__ == '__main__':
    app.run(debug=True)