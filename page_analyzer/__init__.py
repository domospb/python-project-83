from flask import Flask

app = Flask(__name__)

from page_analyzer import routes # noqa
