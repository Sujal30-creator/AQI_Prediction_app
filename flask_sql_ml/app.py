import os
import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert import HTMLExporter
import tempfile
import io
import base64
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import asyncio
from asyncio import WindowsSelectorEventLoopPolicy
import pickle
import Updated_Visualization as vis
import traceback

base_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(base_dir, "rf_model.pkl")
# Load trained Random Forest model
try:
    with open(model_path, "rb") as f:
        rf_model = pickle.load(f)
    print("Random Forest model loaded successfully.")
except Exception as e:
    print(f"Error loading model: {e}")
    rf_model = None

# Set the event loop policy at the very beginning of your application
asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

# Flask App Initialization
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)

# AQI Request History Model
class AQIRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    month_index = db.Column(db.Integer, nullable=False)
    aqi_value = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# Create database tables
with app.app_context():
    db.create_all()

# Helper functions
def validate_json(payload, required_fields):
    if not payload:
        return False
    return all(field in payload and payload[field] for field in required_fields)

def fig_to_base64(fig):
    """Convert matplotlib figure to base64 encoded image"""
    img = io.BytesIO()
    fig.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    return base64.b64encode(img.getvalue()).decode('utf-8')

# Routes
@app.route('/check-user', methods=['POST'])
def check_user():
    """Check if a username exists in the database"""
    data = request.get_json()
    if not validate_json(data, ['username']):
        return jsonify({'error': 'Username is required'}), 400

    exists = User.query.filter_by(username=data['username']).first() is not None
    return jsonify({'exists': exists}), 200

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    print(f"Received Signup Data: {data}")
    
    if not validate_json(data, ['username', 'password', 'category']):
        return jsonify({'error': 'All fields are required'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400

    try:
        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        new_user = User(
            username=data['username'],
            password=hashed_password,
            category=data['category']
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User created successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not validate_json(data, ['username', 'password']):
        return jsonify({'error': 'Username and password required'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if not user or not bcrypt.check_password_hash(user.password, data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    return jsonify({
        'status': 'success',
        'username': user.username,
        'category': user.category
    }), 200

# AQI Dataset (Mock Data)
aqidata = [338, 355, 300, 250, 240, 200, 210, 226, 200, 310, 320, 330]

@app.route('/aqi/<int:index>', methods=['GET'])
def aqi(index):
    if not 1 <= index <= len(aqidata):
        return jsonify({'error': 'Invalid month index (1-12)'}), 400
    return jsonify({'month_index': index, 'aqi_value': aqidata[index - 1]})

@app.route('/predict/<int:index>', methods=['POST'])
def get_aqi(index):
    data = request.get_json()
    if not validate_json(data, ['username']):
        return jsonify({'error': 'Username is required'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 401

    if not 1 <= index <= len(aqidata):
        return jsonify({'error': 'Invalid month index (1-12)'}), 400

    aqi_value = aqidata[index - 1]
    try:
        new_request = AQIRequest(
            user_id=user.id,
            month_index=index,
            aqi_value=aqi_value
        )
        db.session.add(new_request)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

    if aqi_value <= 50:
        solutions = {
            "Lung Disease/Asthma": "Air quality is safe. No special precautions are needed.",
            "Old Age": "Enjoy fresh air, but avoid dust exposure.",
            "Normal People": "No restrictions. Enjoy outdoor activities."
        }

    elif aqi_value <= 100:
        solutions = {
            "Lung Disease/Asthma": "Air quality is acceptable but be cautious with prolonged outdoor activities.",
            "Old Age": "Consider avoiding high-traffic areas.",
            "Normal People": "Outdoor activities are fine, but stay aware of air changes."
        }

    elif aqi_value <= 150:
        solutions = {
            "Lung Disease/Asthma": "Limit outdoor activities. Always carry an inhaler if needed.",
            "Old Age": "Reduce prolonged outdoor exposure.",
            "Normal People": "Most people are fine, but sensitive individuals should be cautious."
        }

    elif aqi_value <= 200:
        solutions = {
            "Lung Disease/Asthma": "Wear an N95 mask outdoors. Use an air purifier indoors.",
            "Old Age": "Stay indoors as much as possible and keep windows closed.",
            "Normal People": "Reduce outdoor activities and avoid prolonged exposure."
        }

    elif aqi_value <= 300:
        solutions = {
            "Lung Disease/Asthma": "Avoid going outside. If necessary, wear a mask and take medication as prescribed.",
            "Old Age": "Serious health risks. Stay inside with air purification if possible.",
            "Normal People": "Avoid strenuous outdoor activities. Consider working indoors."
        }

    else:
        solutions = {
            "Lung Disease/Asthma": "Severe risk! Stay indoors with an air purifier. Seek medical attention if breathing issues arise.",
            "Old Age": "Health emergency! Avoid going outside completely. Keep emergency contacts ready.",
            "Normal People": "Everyone should remain indoors and reduce physical activity."
        }

    return jsonify({
        'month_index': index,
        'aqi_value': aqi_value,
        'solution': solutions.get(user.category, 'No specific solution available.')
    })


@app.route('/history', methods=['POST'])
def get_history():
    data = request.get_json()
    if not validate_json(data, ['username']):
        return jsonify({'error': 'Username is required'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 401

    history = AQIRequest.query.filter_by(user_id=user.id)\
                 .order_by(AQIRequest.timestamp.desc())\
                 .limit(10).all()
    
    history_data = [{
        'month_index': record.month_index,
        'aqi_value': record.aqi_value,
        'timestamp': record.timestamp.isoformat()
    } for record in history]

    return jsonify({'history': history_data})

# Load AQI dataset
try:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(base_dir, 'Final_Dataset.csv')
    df = pd.read_csv(dataset_path)
    print(f"Successfully loaded AQI dataset from {dataset_path}")
except Exception as e:
    print(f"Error loading AQI dataset: {e}")
    df = pd.DataFrame()  # Empty dataframe as fallback

@app.route('/debug-dataset', methods=['GET'])
def debug_dataset():
    if df.empty:
        return jsonify({"error": "Dataset not loaded or empty"})
    return jsonify({"columns": df.columns.tolist(), "rows": len(df)})



@app.route('/run-notebook', methods=['POST'])
def get_aqi_graphs():
    try:
        data = request.get_json()
        if not data or 'month' not in data:
            return jsonify({"error": "Month parameter is required"}), 400

        month = int(data.get("month"))
        print(f"Received month for visualization: {month}")

        # Generate base64 images directly (they're already base64!)
        histogram_img = vis.plot_aqi_histogram(month)
        trend_img = vis.plot_aqi_trend(month)
        heatmap_img = vis.plot_aqi_heatmap(month)
        pollutants_img = vis.plot_pollutant_contribution(month)

        # Only include non-None images (pie chart can return None)
        visualizations = {}
        if histogram_img:
            visualizations["histogram"] = histogram_img
        if trend_img:
            visualizations["trend"] = trend_img
        if heatmap_img:
            visualizations["heatmap"] = heatmap_img
        if pollutants_img:
            visualizations["pollutants"] = pollutants_img

        return jsonify({
            "message": "Visualizations generated successfully",
            "visualizations": visualizations
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate visualizations: {str(e)}"}), 500



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)





"""# Add this at the ABSOLUTE TOP of your Python file (before any other imports)
import asyncio
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import os
import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert import HTMLExporter
import tempfile
import io
import base64
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns
# Add this at the VERY TOP of your Python file (before other imports)
import matplotlib
matplotlib.use('Agg')  # Set backend to non-interactive
from matplotlib import pyplot as plt



# Load your AQI data
df = pd.read_csv('Final_Dataset.csv')  # Make sure this is loaded globally


# Flask App Initialization
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')  # Added secret key

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)

# AQI Request History Model
class AQIRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    month_index = db.Column(db.Integer, nullable=False)
    aqi_value = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# Create database tables
with app.app_context():
    db.create_all()

# Helper functions
def validate_json(payload, required_fields):
    if not payload:
        return False
    return all(field in payload and payload[field] for field in required_fields)

def get_visualization_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir,'Updated_Visualization.ipynb')

# Routes
@app.route('/check-user', methods=['POST'])
def check_user():
    data = request.get_json()
    if not validate_json(data, ['username']):
        return jsonify({'error': 'Username is required'}), 400

    exists = User.query.filter_by(username=data['username']).first() is not None
    return jsonify({'exists': exists}), 200

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    print(f"Received Signup Data: {data}")
    
    if not validate_json(data, ['username', 'password', 'category']):
        return jsonify({'error': 'All fields are required'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400

    try:
        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        new_user = User(
            username=data['username'],
            password=hashed_password,
            category=data['category']
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User created successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not validate_json(data, ['username', 'password']):
        return jsonify({'error': 'Username and password required'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if not user or not bcrypt.check_password_hash(user.password, data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    return jsonify({
        'status': 'success',
        'username': user.username,
        'category': user.category
    }), 200

# AQI Dataset (Mock Data)
aqidata = [338, 355, 300, 250, 240, 200, 210, 226, 200, 310, 320, 330]

@app.route('/aqi/<int:index>', methods=['GET'])
def aqi(index):
    if not 1 <= index <= len(aqidata):
        return jsonify({'error': 'Invalid month index (1-12)'}), 400
    return jsonify({'month_index': index, 'aqi_value': aqidata[index - 1]})

@app.route('/predict/<int:index>', methods=['POST'])
def get_aqi(index):
    data = request.get_json()
    if not validate_json(data, ['username']):
        return jsonify({'error': 'Username is required'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 401

    if not 1 <= index <= len(aqidata):
        return jsonify({'error': 'Invalid month index (1-12)'}), 400

    aqi_value = aqidata[index - 1]
    try:
        new_request = AQIRequest(
            user_id=user.id,
            month_index=index,
            aqi_value=aqi_value
        )
        db.session.add(new_request)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

    solutions = {
        "Lung Disease/Asthma": "Avoid outdoor activities, use an air purifier, and wear a mask.",
        "Old Age": "Stay indoors, keep windows closed, and consult a doctor if needed.",
        "Normal People": "Reduce outdoor exposure and stay hydrated."
    }
    return jsonify({
        'month_index': index,
        'aqi_value': aqi_value,
        'solution': solutions.get(user.category, 'No specific solution available.')
    })

@app.route('/history', methods=['POST'])
def get_history():
    data = request.get_json()
    if not validate_json(data, ['username']):
        return jsonify({'error': 'Username is required'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 401

    history = AQIRequest.query.filter_by(user_id=user.id)\
                 .order_by(AQIRequest.timestamp.desc())\
                 .limit(10).all()
    
    history_data = [{
        'month_index': record.month_index,
        'aqi_value': record.aqi_value,
        'timestamp': record.timestamp.isoformat()
    } for record in history]

    return jsonify({'history': history_data})

# Load AQI dataset
try:
    df = pd.read_csv("Final_Dataset.csv")
    print("Successfully loaded AQI dataset")
except Exception as e:
    print(f"Error loading AQI dataset: {e}")
    df = pd.DataFrame()


# Add these at the VERY TOP of your file
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import traceback
from matplotlib import pyplot as plt
import numpy as np
# Add at the VERY TOP
import asyncio
import sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
import numpy as np
import traceback

def create_aqi_visualizations(month):
    visualizations = {}
    
    if df.empty:
        return visualizations
        
    try:
        # Data cleaning
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        df_filtered = df[(df["month"] == month) & (df['year'].notna())]
        
        if df_filtered.empty:
            return visualizations
            
        # AQI Trend Plot
        aqi_trend = df_filtered.groupby("year")["AQI"].mean()
        
        plt.figure(figsize=(10, 5))
        plt.plot(aqi_trend.index.astype(int), aqi_trend.values, 
                marker="o", color="b", linestyle="-")
        plt.title(f"AQI Trend for Month {month}")
        plt.xlabel("Year")
        plt.ylabel("Average AQI")
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight', dpi=100)
        img.seek(0)
        plt.close()
        visualizations['trend'] = base64.b64encode(img.getvalue()).decode('utf-8')
        
        # Pollutant Pie Chart
        numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns
        pollutants = [col for col in numeric_cols 
                    if col not in ["year", "month", "AQI"]]
        
        if pollutants:
            pollutant_sums = df_filtered[pollutants].sum()
            plt.figure(figsize=(8, 8))
            plt.pie(pollutant_sums, labels=pollutant_sums.index, 
                    autopct="%1.1f%%", startangle=90)
            plt.title(f"Pollutant Contribution for Month {month}")
            img = io.BytesIO()
            plt.savefig(img, format='png', bbox_inches='tight', dpi=100)
            img.seek(0)
            plt.close()
            visualizations['pollutants'] = base64.b64encode(img.getvalue()).decode('utf-8')
        
    except Exception as e:
        print(f"Visualization error: {e}")
        traceback.print_exc()
    
    return visualizations

@app.route('/run-notebook', methods=['POST'])
def run_notebook():
    try:
        data = request.get_json()
        
        # Validation
        if not validate_json(data, ['username', 'month']):
            return jsonify({'error': 'Username and month are required'}), 400

        user = User.query.filter_by(username=data['username']).first()
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401

        try:
            month = int(data['month'])
            if not 1 <= month <= 12:
                return jsonify({'error': 'Month must be 1-12'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid month format'}), 400

        # Notebook execution
        notebook_path = get_visualization_path()
        if not os.path.exists(notebook_path):
            return jsonify({'error': 'Analysis module unavailable'}), 503

        with open(notebook_path) as f:
            nb = nbformat.read(f, as_version=4)

        ep = ExecutePreprocessor(
            timeout=600,
            kernel_name='python3',
            allow_errors=True
        )

        try:
            # CORRECTED EXECUTION
            ep.preprocess(nb, resources={'metadata': {'path': os.path.dirname(notebook_path)}})
        except Exception as e:
            return jsonify({'error': f'Notebook execution failed: {str(e)}'}), 500

        # Generate output
        html_exporter = HTMLExporter()
        body, _ = html_exporter.from_notebook_node(nb)

        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(body.encode('utf-8'))
            temp_path = f.name

        visualizations = create_aqi_visualizations(month)

        return jsonify({
            'status': 'success',
            'html_path': temp_path,
            'visualizations': visualizations,
            'message': 'Analysis completed successfully'
        })
        
    except Exception as e:
        print(f"Server error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(debug=True)

"""









"""
import datetime
import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_cors import CORS

# Flask App Initialization
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Enable CORS for all routes
CORS(app)

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)

# AQI Request History Model
class AQIRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    month_index = db.Column(db.Integer, nullable=False)
    aqi_value = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# Ensure the database is created and tables are initialized
def initialize_database():
    with app.app_context():
        db.create_all()  # Create tables if they don't exist

# Call the function to initialize the database
initialize_database()

# Helper function to validate JSON payload
def validate_json(payload, required_fields):
    return payload and all(field in payload and payload[field] for field in required_fields)

# Signup Route
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not validate_json(data, ['username', 'password', 'category']):
        return jsonify({'error': 'All fields (username, password, category) are required'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'User already exists'}), 400

    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    new_user = User(username=data['username'], password=hashed_password, category=data['category'])
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User created successfully'}), 201

# Login Route
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not validate_json(data, ['username', 'password']):
        return jsonify({'error': 'Username and password are required'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if user and bcrypt.check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Login successful'}), 200
    return jsonify({'error': 'Invalid credentials'}), 401

# AQI Dataset
aqidata = [338, 355, 300, 250, 240, 200, 210, 226, 200, 310, 320, 330]

# AQI Retrieval
@app.route('/aqi/<int:index>', methods=['GET'])
def aqi(index):
    if not (1 <= index <= len(aqidata)):
        return jsonify({'error': 'Invalid index. Choose between 1 and 12.'}), 400

    aqi_value = aqidata[index - 1]
    response = {'month_index': index, 'aqi_value': aqi_value}
    return jsonify(response)

# AQI Retrieval API
@app.route('/predict/<int:index>', methods=['POST'])
def get_aqi(index):
    data = request.get_json()
    if not validate_json(data, ['username']):
        return jsonify({'error': 'Username is required'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 401

    if not (1 <= index <= len(aqidata)):
        return jsonify({'error': 'Invalid month index. Choose between 1 and 12.'}), 400

    aqi_value = aqidata[index - 1]
    new_request = AQIRequest(user_id=user.id, month_index=index, aqi_value=aqi_value)
    db.session.add(new_request)
    db.session.commit()

    solutions = {
        "Lung Disease/Asthma": "Avoid outdoor activities, use an air purifier, and wear a mask.",
        "Old Age": "Stay indoors, keep windows closed, and consult a doctor if needed.",
        "Normal People": "Reduce outdoor exposure and stay hydrated."
    }
    return jsonify({
        'month_index': index,
        'aqi_value': aqi_value,
        'solution': solutions.get(user.category, 'No specific solution available.')
    })

# Get User AQI History
@app.route('/history', methods=['POST'])
def get_history():
    data = request.get_json()
    if not validate_json(data, ['username']):
        return jsonify({'error': 'Username is required'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 401

    history = AQIRequest.query.filter_by(user_id=user.id).order_by(AQIRequest.timestamp.desc()).limit(10).all()
    history_data = [{
        'month_index': record.month_index,
        'aqi_value': record.aqi_value,
        'timestamp': record.timestamp
    } for record in history]

    return jsonify({'history': history_data})

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)


"""