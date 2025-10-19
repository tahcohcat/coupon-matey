from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import base64
import os
import json
from typing import Dict, List, Optional
import requests

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coupons.db'
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=30)

db = SQLAlchemy(app)
jwt = JWTManager(app)


# ============= DATABASE MODELS =============

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120))
    google_id = db.Column(db.String(255), unique=True)
    coupons = db.relationship('Coupon', backref='user', lazy=True, cascade='all, delete-orphan')
    settings = db.relationship('UserSettings', backref='user', uselist=False, cascade='all, delete-orphan')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
        }


class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    provider = db.Column(db.String(255))
    discount = db.Column(db.String(255))
    terms = db.Column(db.Text)
    expiry_date = db.Column(db.DateTime, nullable=False)
    deadline = db.Column(db.DateTime)
    claimed = db.Column(db.Boolean, default=False)
    notified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    image_path = db.Column(db.String(512))

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'title': self.title,
            'provider': self.provider,
            'discount': self.discount,
            'terms': self.terms,
            'expiryDate': self.expiry_date.isoformat(),
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'claimed': self.claimed,
            'scannedAt': self.created_at.isoformat(),
        }


class UserSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    auto_delete_expired = db.Column(db.Boolean, default=False)
    auto_delete_claimed = db.Column(db.Boolean, default=False)
    notify_before_expiry_days = db.Column(db.Integer, default=3)
    sync_google_calendar = db.Column(db.Boolean, default=False)
    ocr_provider = db.Column(db.String(50), default='gpt4o')

    def to_dict(self):
        return {
            'autoDeleteExpired': self.auto_delete_expired,
            'autoDeleteClaimed': self.auto_delete_claimed,
            'notifyBeforeExpiry': self.notify_before_expiry_days,
            'syncGoogleCalendar': self.sync_google_calendar,
            'ocrProvider': self.ocr_provider,
        }


# ============= OCR INTERFACE & IMPLEMENTATIONS =============

class OCRProvider(ABC):
    """Abstract base class for OCR providers"""

    @abstractmethod
    def extract_coupon_data(self, image_base64: str) -> Dict:
        """
        Extract coupon data from image.

        Returns:
        {
            'code': str,
            'title': str,
            'provider': str,
            'discount': str,
            'terms': str,
            'expiryDate': datetime,
            'deadline': datetime
        }
        """
        pass


class GPT4oOCR(OCRProvider):
    """GPT-4o Vision API OCR implementation"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "gpt-4o"
        self.base_url = "https://api.openai.com/v1"

    def extract_coupon_data(self, image_base64: str) -> Dict:
        prompt = """Analyze this coupon image and extract the following information in JSON format:
        {
            "code": "the coupon/promo code",
            "title": "coupon title or description",
            "provider": "business or merchant name",
            "discount": "discount amount or percentage",
            "terms": "terms and conditions visible",
            "expiryDate": "ISO format date when coupon expires",
            "deadline": "ISO format deadline date if different from expiry"
        }

        If a field is not visible or unclear, use null. Return only valid JSON."""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1024
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            content = result['choices'][0]['message']['content']

            # Parse JSON from response
            coupon_data = json.loads(content)

            # Convert date strings to datetime
            if coupon_data.get('expiryDate'):
                coupon_data['expiryDate'] = datetime.fromisoformat(coupon_data['expiryDate'].replace('Z', '+00:00'))
            if coupon_data.get('deadline'):
                coupon_data['deadline'] = datetime.fromisoformat(coupon_data['deadline'].replace('Z', '+00:00'))

            return coupon_data

        except Exception as e:
            print(f"GPT-4o OCR error: {e}")
            raise


class MockOCR(OCRProvider):
    """Mock OCR for testing/demo"""

    def extract_coupon_data(self, image_base64: str) -> Dict:
        return {
            'code': f'MOCK{hash(image_base64) % 10000:04d}',
            'title': 'Mock Coupon from Image',
            'provider': 'TestMerchant',
            'discount': '15% off',
            'terms': 'Valid on purchases over $50',
            'expiryDate': datetime.utcnow() + timedelta(days=30),
            'deadline': datetime.utcnow() + timedelta(days=25)
        }


class OCRFactory:
    """Factory to manage OCR provider instances"""

    _providers = {
        'gpt4o': GPT4oOCR,
        'mock': MockOCR,
    }

    @classmethod
    def create_provider(cls, provider_name: str, **kwargs) -> OCRProvider:
        if provider_name not in cls._providers:
            raise ValueError(f"Unknown OCR provider: {provider_name}")

        provider_class = cls._providers[provider_name]
        return provider_class(**kwargs)

    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """Register a new OCR provider"""
        cls._providers[name] = provider_class


# ============= ROUTES =============

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login with Google or email (mock implementation)"""
    data = request.get_json()
    email = data.get('email')
    name = data.get('name', 'User')

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, name=name)
        db.session.add(user)
        db.session.flush()

        # Create default settings
        settings = UserSettings(user_id=user.id)
        db.session.add(settings)

    db.session.commit()

    access_token = create_access_token(identity=user.id)
    return jsonify({
        'access_token': access_token,
        'user': user.to_dict()
    })


@app.route('/api/coupons', methods=['GET'])
@jwt_required()
def get_coupons():
    """Get all coupons for authenticated user"""
    user_id = get_jwt_identity()
    coupons = Coupon.query.filter_by(user_id=user_id).all()
    return jsonify([coupon.to_dict() for coupon in coupons])


@app.route('/api/coupons', methods=['POST'])
@jwt_required()
def create_coupon():
    """Create coupon from image (OCR processing)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        image_base64 = data.get('image')

        if not image_base64:
            return jsonify({'error': 'No image provided'}), 400

        # Remove data:image/jpeg;base64, prefix if present
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]

    except Exception as e:
        print(f"Error parsing request: {e}")
        return jsonify({'error': f'Request parsing error: {str(e)}'}), 400

    try:
        # Get user's OCR provider settings
        settings = user.settings or UserSettings(user_id=user_id)
        provider_name = settings.ocr_provider

        # Initialize OCR provider
        if provider_name == 'gpt4o':
            ocr_provider = OCRFactory.create_provider('gpt4o', api_key=os.getenv('OPENAI_API_KEY'))
        else:
            ocr_provider = OCRFactory.create_provider('mock')

        # Extract coupon data
        coupon_data = ocr_provider.extract_coupon_data(image_base64)

        # Create coupon record
        coupon = Coupon(
            user_id=user_id,
            code=coupon_data.get('code', 'UNKNOWN'),
            title=coupon_data.get('title', 'Coupon'),
            provider=coupon_data.get('provider', ''),
            discount=coupon_data.get('discount', ''),
            terms=coupon_data.get('terms', ''),
            expiry_date=coupon_data.get('expiryDate', datetime.utcnow() + timedelta(days=30)),
            deadline=coupon_data.get('deadline'),
        )

        db.session.add(coupon)
        db.session.commit()

        return jsonify(coupon.to_dict()), 201

    except Exception as e:
        print(f"Error processing coupon: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/coupons/<int:coupon_id>', methods=['PATCH'])
@jwt_required()
def update_coupon(coupon_id):
    """Update coupon (mark as claimed, etc.)"""
    user_id = get_jwt_identity()
    coupon = Coupon.query.filter_by(id=coupon_id, user_id=user_id).first()

    if not coupon:
        return jsonify({'error': 'Coupon not found'}), 404

    data = request.get_json()
    if 'claimed' in data:
        coupon.claimed = data['claimed']

    db.session.commit()
    return jsonify(coupon.to_dict())


@app.route('/api/coupons/<int:coupon_id>', methods=['DELETE'])
@jwt_required()
def delete_coupon(coupon_id):
    """Delete coupon"""
    user_id = get_jwt_identity()
    coupon = Coupon.query.filter_by(id=coupon_id, user_id=user_id).first()

    if not coupon:
        return jsonify({'error': 'Coupon not found'}), 404

    db.session.delete(coupon)
    db.session.commit()
    return jsonify({'message': 'Coupon deleted'})


@app.route('/api/settings', methods=['GET'])
@jwt_required()
def get_settings():
    """Get user settings"""
    user_id = get_jwt_identity()
    settings = UserSettings.query.filter_by(user_id=user_id).first()

    if not settings:
        settings = UserSettings(user_id=user_id)
        db.session.add(settings)
        db.session.commit()

    return jsonify(settings.to_dict())


@app.route('/api/settings', methods=['POST'])
@jwt_required()
def update_settings():
    """Update user settings"""
    user_id = get_jwt_identity()
    settings = UserSettings.query.filter_by(user_id=user_id).first()

    if not settings:
        settings = UserSettings(user_id=user_id)
        db.session.add(settings)

    data = request.get_json()
    if 'autoDeleteExpired' in data:
        settings.auto_delete_expired = data['autoDeleteExpired']
    if 'autoDeleteClaimed' in data:
        settings.auto_delete_claimed = data['autoDeleteClaimed']
    if 'notifyBeforeExpiry' in data:
        settings.notify_before_expiry_days = data['notifyBeforeExpiry']
    if 'syncGoogleCalendar' in data:
        settings.sync_google_calendar = data['syncGoogleCalendar']
    if 'ocrProvider' in data:
        settings.ocr_provider = data['ocrProvider']

    db.session.commit()
    return jsonify(settings.to_dict())


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})


@app.route('/api/test-auth', methods=['GET'])
def test_auth():
    """Test endpoint - no auth required"""
    return jsonify({'message': 'Backend is working', 'cors': 'enabled'})


# ============= ERROR HANDLERS =============

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server error'}), 500


# ============= DATABASE INITIALIZATION =============

def init_db():
    """Initialize database"""
    with app.app_context():
        db.create_all()
        print("Database initialized")


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)