from flask import Flask, request, render_template, jsonify
import jwt
import requests
import cohere
import smtplib
from email.mime.text import MIMEText
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # optional if frontend hosted separately

# CONFIGURATION
JWT_SECRET_KEY = 'hs7&d82jJs0#zLKf9qp!23nX^Ty76Pm@'
WORDPRESS_SITE_URL = 'https://zzapkart.com'
COHERE_API_KEY = 'Ox97SolGnL68xrDjbNAMiVaWCqZ5Fny3d7hYAub6'
SITE_OWNER_EMAIL = 'your_email@example.com'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = 'your_email@example.com'
SMTP_PASS = 'your_email_password_or_app_password'

co = cohere.Client(COHERE_API_KEY)

@app.route('/')
def dashboard():
    token = request.args.get('token')
    user_name = "Guest"
    orders_data = []

    if token:
        try:
            decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            user_id = decoded['data']['user']['id']
        except Exception as e:
            return f'Invalid token: {e}', 400

        headers = {'Content-Type': 'application/json'}

        user_info_url = f'{WORDPRESS_SITE_URL}/wp-json/chatbot-api/v1/user/?token={token}'
        user_response = requests.get(user_info_url, headers=headers)
        if user_response.status_code == 200:
            user_data = user_response.json()
            user_name = user_data.get("name", "Guest")

        orders_url = f'{WORDPRESS_SITE_URL}/wp-json/chatbot-api/v1/orders/?token={token}'
        orders_response = requests.get(orders_url, headers=headers)
        if orders_response.status_code == 200:
            orders_data = orders_response.json()

    return render_template('dashboard.html', user_name=user_name, orders=orders_data, token=token)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message')
    user_name = data.get('user_name', 'Guest')
    orders = data.get('orders', [])
    token = data.get('token')

    intent = detect_intent(message)

    if intent in ['cancel', 'replace'] and orders:
        actions = []
        for order in orders:
            actions.append({
                'label': f"Order {order['order_id']}",
                'type': intent,
                'order_id': order['order_id']
            })
        reply = f"Sure {user_name}, please select the order you want to {intent}."
        return jsonify({'reply': reply, 'actions': actions})

    response = co.chat(
        model="command-r-plus",
        message=message,
        preamble=f"You are a helpful assistant for Zzapkart. The user's name is {user_name}.",
        chat_history=[]
    )
    reply = response.text
    return jsonify({'reply': reply})

@app.route('/action', methods=['POST'])
def action():
    data = request.get_json()
    action_type = data.get('action')
    order_id = data.get('order_id')

    subject = f"{action_type.capitalize()} Request for Order {order_id}"
    body = f"A user has requested to {action_type} order {order_id}."

    send_email(SITE_OWNER_EMAIL, subject, body)

    return jsonify({'message': f"Your {action_type} request for Order {order_id} has been received. We'll notify you soon."})

def detect_intent(msg):
    msg = msg.lower()
    if "cancel" in msg: return "cancel"
    if "replace" in msg: return "replace"
    return "general"

def send_email(to_email, subject, body):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = to_email

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
    except Exception as e:
        print("Email failed:", e)

if __name__ == '__main__':
    app.run(debug=True)
