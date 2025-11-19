class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///users.db'
    SQLALCHEMY_DATABASE_URI_VM = 'sqlite:///vms.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'change_this_secret_key'

