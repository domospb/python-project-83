from flask import Flask
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')


# Import routes after creating app instance
from page_analyzer import routes  # noqa: E402, F401

if __name__ == '__main__':
    app.run(debug=True)
