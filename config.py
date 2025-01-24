import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', '@C828zAaU%$V5V#9PX6G22Yqpip&VGw&')  # Noklusējuma atslēga
    SQLALCHEMY_DATABASE_URI = 'postgresql://janis:Airites1243!@10.9.9.204/lptps'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
