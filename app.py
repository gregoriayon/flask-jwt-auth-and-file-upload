import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import create_access_token, JWTManager, get_jwt_identity, jwt_required
from lxml import etree

# from flask_restful import Resource, Api

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = '/e/home-practice/qfl-task/media'
app.config['ALLOWED_EXTENSIONS'] = {'xml'}

app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:201830011@localhost/test_02'

db = SQLAlchemy(app)
jwt = JWTManager(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=True)


class SharePosition(db.Model):
    # __table__ = "share_positions"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_code = db.Column(db.Integer, nullable=False)
    security_code = db.Column(db.String(225), nullable=False)
    isin = db.Column(db.String(225), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    position_type = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<Item {self.client_code} - {self.security_code}>'


with app.app_context():
    db.create_all()



os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/registration', methods=['POST'])
def user_registration():
    data = request.get_json()
    username = data['username']
    password = data['password']

    if not username or not password:
        return {
            "messsage": "Missing username or password!"
        }, 400
    if User.query.filter_by(username= username).first():
        return {
            "messsage": "Username already exits!"
        }, 400
    
    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()
    return {
        "message": "User created successfully"
    }, 201


@app.route('/login', methods=['POST'])
def user_login():
    data = request.get_json()
    username = data['username']
    password = data['password']

    if not username or not password:
        return {
            "messsage": "Missing username or password!"
        }, 400
    
    user = User.query.filter_by(username= username).first()
    if user and user.password == password:
        access_token = create_access_token(identity=user.id)
        return {
            "access_token": access_token
        }, 200
    
    return {
        "message": "Invalid credentials"
    }, 401



@app.route('/dashboard', methods=['GET'])
@jwt_required()
def user_dashboard():
    current_user_id = get_jwt_identity()

    return {
        "message": f"Hello user {current_user_id}, you access dashborad successfully!"
    }, 200



@app.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    if 'file' not in request.files:
        return jsonify(error='No file part'), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify(error='No selected file'), 400
    if file and allowed_file(file.filename):
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        try:
            # Parsing XML and save to database
            tree = etree.parse(filepath)
            root = tree.getroot()
            for item in root.findall('InsertOne'):
                client_code = int(item.find('ClientCode').text)
                security_code = item.find('SecurityCode').text
                isin = item.find('ISIN').text
                quantity = int(item.find('Quantity').text)
                total_cost = float(item.find('TotalCost').text)
                position_type = item.find('PositionType').text

                print(f"{client_code}, {security_code}, {isin}, {quantity}, {total_cost}, {position_type}", end='\n')
                
                new_person = SharePosition(client_code=client_code, security_code=security_code, isin=isin, quantity=quantity, total_cost=total_cost, position_type=position_type)
                db.session.add(new_person)
            
            db.session.commit()
            return jsonify(message='File successfully uploaded and data saved'), 200

        except Exception as e:
            return jsonify(error=str(e)), 500
        
    else:
        return jsonify(error='File type not allowed'), 400


if __name__ == '__main__':
    app.run(debug=True)
