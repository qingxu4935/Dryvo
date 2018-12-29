import binascii
import jwt
import datetime as dt
import hashlib
import os
from datetime import datetime, timedelta
from flask_login import UserMixin

from api.database.mixins import Column, Model, SurrogatePK, db, relationship, reference_col
from api.database.models.blacklist_token import BlacklistToken


HASH_NAME = 'sha1'
HASH_ROUNDS = 1000
SALT_LENGTH = 20


class User(UserMixin, SurrogatePK, Model):
    """A user of the app."""

    __tablename__ = 'users'
    email = Column(db.String(80), unique=True, nullable=False)
    password = Column(db.String(120), nullable=True)
    created_at = Column(db.DateTime, nullable=False,
                        default=dt.datetime.utcnow)
    last_login = Column(db.DateTime, nullable=False,
                        default=dt.datetime.utcnow)
    salt = Column(db.String(80), nullable=False)
    name = Column(db.String(80), nullable=False)
    is_admin = Column(db.Boolean, nullable=False, default=False)
    area = Column(db.String(80), nullable=False)

    def __init__(self, email, password='', **kwargs):
        if not password:
            password = os.urandom(20)
        db.Model.__init__(self, email=email, **kwargs)
        self.set_password(password)

    @staticmethod
    def _prepare_password(password, salt=None):
        salt = binascii.a2b_base64(salt) if salt else os.urandom(SALT_LENGTH)
        if isinstance(password, str):
            password = password.encode('utf-8')
        dk = hashlib.pbkdf2_hmac(
            hash_name=HASH_NAME, password=password, salt=salt, iterations=HASH_ROUNDS)
        return binascii.b2a_base64(salt).decode("utf-8"), binascii.b2a_base64(dk).decode("utf-8")

    def set_password(self, password):
        """Set password."""
        self.salt, self.password = self._prepare_password(password)

    def check_password(self, value):
        """Check password."""
        passhash = self._prepare_password(value, self.salt)[1]
        return passhash == self.password

    def encode_auth_token(self, user_id):
        """
        Generates the Auth Token
        :return: string
        """
        try:
            payload = {
                'exp': datetime.utcnow() + timedelta(days=10),
                'iat': datetime.utcnow(),
                'sub': user_id
            }
            return jwt.encode(
                payload,
                os.environ['SECRET_JWT'],
                algorithm='HS256'
            )
        except Exception as e:
            return e

    @staticmethod
    def decode_auth_token(auth_token):
        """
        Decodes the auth token
        :param auth_token:
        :return: integer|string
        """
        try:
            payload = jwt.decode(auth_token, os.environ['SECRET_JWT'])
            is_blacklisted_token = BlacklistToken.check_blacklist(auth_token)
            if is_blacklisted_token:
                return 'Token blacklisted. Please log in again.'
            else:
                return payload['sub']
        except jwt.ExpiredSignatureError:
            return 'Signature expired. Please log in again.'
        except jwt.InvalidTokenError:
            return 'Invalid token. Please log in again.'

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'area': self.area,
        }