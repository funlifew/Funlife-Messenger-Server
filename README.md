# 🚀 FunLife Messenger

A super-secure, privacy-focused messenger application built with Django and websockets. FunLife Messenger prioritizes security, encryption, and real-time communication.

![Django](https://img.shields.io/badge/Django-4.2-green)
![DRF](https://img.shields.io/badge/DRF-3.16.0-red)
![Channels](https://img.shields.io/badge/Channels-4.2.2-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🌟 Features

- 🔒 End-to-end encryption for all messages
- 👥 Friend management system
- 🔐 Two-factor authentication (optional)
- 📱 Session management across multiple devices
- 🕒 Real-time messaging using WebSockets
- 🛡️ Enhanced security with rate limiting, key rotation, and more
- 💾 Encrypted data backups
- 📊 Security logging and monitoring
- 📧 Comprehensive email notifications for important events
- 🔔 Security alerts for suspicious activities

## 💻 Tech Stack

- **Backend**: Django 4.2
- **API**: Django REST Framework 3.16
- **Real-time**: Channels 4.2 with Redis
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Encryption**: Cryptography library
- **OTP**: PyOTP
- **Email**: SMTP with HTML templates
- **Package Management**: Poetry

## 📋 Project Structure

```
📦 funlife-messenger-server
 ┣ 📂 accounts                 # User authentication and management
 ┣ 📂 backups                  # Encrypted user data backups
 ┃ ┣ 📂 management
 ┃ ┃ ┗ 📂 commands             # Management commands like backup cleanup
 ┣ 📂 config                   # Project settings and configuration
 ┣ 📂 friendships              # Friend requests and relationship management
 ┣ 📂 messagings               # Core messaging functionality
 ┣ 📂 profiles                 # User profile management
 ┣ 📂 realtime                 # WebSocket consumers for real-time features
 ┃ ┣ 📂 consumers              # WebSocket consumers for different features
 ┣ 📂 security_logs            # Security event logging and monitoring
 ┣ 📂 templates                # HTML templates for emails and backups
 ┃ ┣ 📂 backups
 ┃ ┣ 📂 emails                 # Email notification templates
 ┣ 📂 user_sessions            # Session management and device tracking
 ┣ 📂 utils                    # Utility functions and helpers
 ┃ ┣ 📜 encryption.py          # End-to-end encryption utilities
 ┃ ┣ 📜 email_service.py       # Email service for notifications
 ┃ ┣ 📜 password_validator.py  # Password validation utilities
 ┣ 📜 .env.example             # Example environment variables
 ┣ 📜 .gitignore               # Git ignore file
 ┣ 📜 LICENSE                  # MIT License
 ┣ 📜 manage.py                # Django management script
 ┣ 📜 poetry.lock              # Poetry dependencies lock file
 ┣ 📜 pyproject.toml           # Poetry configuration
 ┗ 📜 README.md                # This file
```

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Redis server (for Channels)
- Poetry (for dependency management)
- SMTP server (for sending emails)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/funlife-messenger-server.git
cd funlife-messenger-server
```

2. **Install dependencies with Poetry**

```bash
poetry install
```

3. **Set up environment variables**

```bash
cp .env.example .env
# Edit .env file with your settings
```

4. **Run migrations**

```bash
poetry run python manage.py migrate
```

5. **Create a superuser**

```bash
poetry run python manage.py createsuperuser
```

6. **Run the development server**

```bash
poetry run python manage.py runserver
```

## 📧 Email Features

FunLife Messenger includes a comprehensive email notification system that keeps users informed about important account activities:

- 📨 Account verification emails with OTP codes
- 🔑 Password reset emails with secure links
- 🔔 Login notifications for new devices or locations
- 🛡️ Security alerts for suspicious activities
- 🔐 Two-factor authentication setup notifications

Email templates are fully customizable and responsive, ensuring users receive well-formatted notifications on any device.

## 🔒 Security Features

- 🛡️ End-to-end encryption using asymmetric (RSA) and symmetric (AES) encryption
- 🔑 Secure password validation with HIBP (Have I Been Pwned) checking
- 👤 Two-factor authentication using TOTP
- 📱 Multi-device session management
- 🚫 Rate limiting to prevent brute force attacks
- 📝 Comprehensive security logging
- 🔄 OTP with refresh capability
- 💾 Encrypted backups
- 🔒 Friend request verification
- 📧 Security event email notifications

## 📚 Documentation

See the [DOCUMENTATION.md](DOCUMENTATION.md) file for detailed documentation on the API endpoints, models, and architecture.

## 🧪 Running Tests

```bash
poetry run python manage.py test
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

- **Mehdi Radfar** - [GitHub](https://github.com/yourusername)

## 🙏 Acknowledgments

- Django and Django REST Framework teams
- Channels project contributors
- All the open-source libraries that made this project possible