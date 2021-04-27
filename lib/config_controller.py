import os
from dotenv import load_dotenv


class ConfigController:
    environment = ''
    debug = ''

    def __init__(self):
        # load_dotenv(verbose=True)  # docker 돌릴 떄는 문장 주석
        self.environment = os.getenv('PYTHON_ENV')
        if self.environment != 'production':
            load_dotenv(verbose=True)
            self.debug = True
        else:
            self.debug = False

    def load(self):
        self.DB_HOST = os.getenv('DB_HOST')
        self.DB_USER = os.getenv('DB_USER')
        self.DB_PASSWORD = os.getenv('DB_PASSWORD')
        self.DB_DATABASE = os.getenv('DB_DATABASE')
        self.DB_CHARSET = os.getenv('DB_CHARSET')
        self.DB_PORT = os.getenv('DB_PORT')
        self.TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
        self.TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')
