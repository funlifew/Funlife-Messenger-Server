# 📚 FunLife Messenger Documentation

This document provides detailed technical documentation for the FunLife Messenger application, including architecture, models, and API endpoints.

## 📋 Project Structure

```
📦 funlife-messenger-server
 ┣ 📂 accounts                 # User authentication and management
 ┃ ┣ 📂 migrations             # Database migrations
 ┃ ┣ 📜 admin.py               # Admin panel configuration
 ┃ ┣ 📜 apps.py                # App configuration
 ┃ ┣ 📜 models.py              # User and OTP models
 ┃ ┣ 📜 serializers.py         # API serializers
 ┃ ┣ 📜 tests.py               # Unit tests
 ┃ ┣ 📜 urls.py                # URL routing
 ┃ ┗ 📜 views.py               # API views
 ┣ 📂 backups                  # Encrypted user data backups
 ┃ ┣ 📂 management
 ┃ ┃ ┣ 📂 commands
 ┃ ┃ ┃ ┗ 📜 cleanup_old_backups.py  # Command to cleanup old backups
 ┃ ┣ 📜 api.py                 # Backup API endpoints
 ┃ ┣ 📜 apps.py                # App configuration
 ┃ ┣ 📜 models.py              # Backup model
 ┃ ┣ 📜 serializers.py         # API serializers
 ┃ ┣ 📜 services.py            # Backup services
 ┃ ┣ 📜 signals.py             # Signal handlers
 ┃ ┣ 📜 urls.py                # URL routing
 ┃ ┣ 📜 utils.py               # Backup utilities
 ┃ ┗ 📜 views.py               # API views
 ┣ 📂 config                   # Project settings and configuration
 ┃ ┣ 📜 asgi.py                # ASGI configuration
 ┃ ┣ 📜 settings.py            # Django settings
 ┃ ┣ 📜 urls.py                # Main URL routing
 ┃ ┗ 📜 wsgi.py                # WSGI configuration
 ┣ 📂 friendships              # Friend requests and relationship management
 ┃ ┣ 📂 migrations             # Database migrations
 ┃ ┣ 📜 admin.py               # Admin panel configuration
 ┃ ┣ 📜 apps.py                # App configuration
 ┃ ┣ 📜 models.py              # Friendship model
 ┃ ┣ 📜 serializers.py         # API serializers
 ┃ ┣ 📜 signals.py             # Signal handlers
 ┃ ┣ 📜 tests.py               # Unit tests
 ┃ ┣ 📜 urls.py                # URL routing
 ┃ ┗ 📜 views.py               # API views
 ┣ 📂 messagings               # Core messaging functionality
 ┃ ┣ 📂 migrations             # Database migrations
 ┃ ┣ 📜 admin.py               # Admin panel configuration
 ┃ ┣ 📜 apps.py                # App configuration
 ┃ ┣ 📜 models.py              # Message and TypingStatus models
 ┃ ┣ 📜 serializers.py         # API serializers
 ┃ ┣ 📜 tests.py               # Unit tests
 ┃ ┣ 📜 urls.py                # URL routing
 ┃ ┗ 📜 views.py               # API views
 ┣ 📂 profiles                 # User profile management
 ┃ ┣ 📂 migrations             # Database migrations
 ┃ ┣ 📜 admin.py               # Admin panel configuration
 ┃ ┣ 📜 apps.py                # App configuration
 ┃ ┣ 📜 models.py              # Profile model
 ┃ ┣ 📜 serializers.py         # API serializers
 ┃ ┣ 📜 tests.py               # Unit tests
 ┃ ┣ 📜 urls.py                # URL routing
 ┃ ┗ 📜 views.py               # API views
 ┣ 📂 realtime                 # WebSocket consumers for real-time features
 ┃ ┣ 📂 consumers              # WebSocket consumers for different features
 ┃ ┃ ┣ 📜 backup.py            # Backup consumer
 ┃ ┃ ┣ 📜 base.py              # Base consumer class
 ┃ ┃ ┣ 📜 friend.py            # Friend consumer
 ┃ ┃ ┣ 📜 message.py           # Message consumer
 ┃ ┃ ┣ 📜 notification.py      # Notification consumer
 ┃ ┃ ┣ 📜 profile.py           # Profile consumer
 ┃ ┃ ┣ 📜 security.py          # Security consumer
 ┃ ┃ ┗ 📜 session.py           # Session consumer
 ┃ ┣ 📜 apps.py                # App configuration
 ┃ ┣ 📜 middlewares.py         # WebSocket middleware
 ┃ ┣ 📜 routing.py             # WebSocket routing
 ┃ ┣ 📜 signals.py             # Signal handlers
 ┃ ┗ 📜 tests.py               # Unit tests
 ┣ 📂 security_logs            # Security event logging and monitoring
 ┃ ┣ 📂 migrations             # Database migrations
 ┃ ┣ 📜 admin.py               # Admin panel configuration
 ┃ ┣ 📜 apps.py                # App configuration
 ┃ ┣ 📜 middleware.py          # Security logging middleware
 ┃ ┣ 📜 models.py              # SecurityLog model
 ┃ ┣ 📜 serializers.py         # API serializers
 ┃ ┣ 📜 tests.py               # Unit tests
 ┃ ┣ 📜 urls.py                # URL routing
 ┃ ┣ 📜 utils.py               # Security logging utilities
 ┃ ┗ 📜 views.py               # API views
 ┣ 📂 templates                # HTML templates (backup viewer)
 ┃ ┣ 📂 backups
 ┃ ┃ ┗ 📜 backup_template.html # Backup HTML template
 ┣ 📂 user_sessions            # Session management and device tracking
 ┃ ┣ 📂 migrations             # Database migrations
 ┃ ┣ 📜 admin.py               # Admin panel configuration
 ┃ ┣ 📜 apps.py                # App configuration
 ┃ ┣ 📜 middleware.py          # Session activity middleware
 ┃ ┣ 📜 models.py              # UserSession model
 ┃ ┣ 📜 serializers.py         # API serializers
 ┃ ┣ 📜 tests.py               # Unit tests
 ┃ ┣ 📜 urls.py                # URL routing
 ┃ ┗ 📜 views.py               # API views
 ┣ 📂 utils                    # Utility functions and helpers
 ┃ ┣ 📜 encryption.py          # End-to-end encryption utilities
 ┃ ┗ 📜 password_validator.py  # Password validation utilities
```

## 🏛️ Architecture

FunLife Messenger follows a clean architecture approach with the following layers:

1. **Models**: Database schemas and business logic
2. **Serializers**: Transform data between API and model formats
3. **Views**: Handle HTTP requests and responses
4. **Consumers**: Handle WebSocket connections and events
5. **Utilities**: Shared functionality across apps

The application uses Django REST Framework for the HTTP API and Django Channels for real-time WebSocket communication.

## 📊 Data Models

### User Model (`accounts.models.User`)

Extended Django user model with additional security features:

| Field | Type | Description |
|-------|------|-------------|
| `username` | CharField | Unique username with validation |
| `email` | EmailField | User's email address |
| `is_verified` | BooleanField | Email verification status |
| `is_active` | BooleanField | Account active status |
| `role` | CharField | User role (user/admin) |
| `login_failed_attempts` | IntegerField | Count of failed login attempts |
| `ban_until` | DateTimeField | Timestamp until user is banned |
| `forget_attempts` | IntegerField | Count of password reset attempts |
| `public_key` | TextField | User's public encryption key |
| `is_2fa_enabled` | BooleanField | Two-factor authentication status |

### OTP Model (`accounts.models.OTP`)

One-time password model for various verification purposes:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `user` | ForeignKey | Associated user |
| `code` | CharField | OTP code |
| `purpose` | CharField | Purpose of OTP (verification, reset, 2FA) |
| `is_used` | BooleanField | Whether the OTP has been used |
| `expires_at` | DateTimeField | Expiration timestamp |
| `refreshes_at` | DateTimeField | Refresh timestamp |
| `refresh_attempts` | IntegerField | Count of refresh attempts |

### Profile Model (`profiles.models.Profile`)

User profile information:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `user` | OneToOneField | Associated user |
| `status` | CharField | User status message |
| `display_name` | CharField | Display name |
| `bio` | TextField | User biography |
| `is_online` | BooleanField | Online status |
| `last_seen` | DateTimeField | Last seen timestamp |

### Message Model (`messagings.models.Message`)

Encrypted messages between users:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `sender` | ForeignKey | Message sender |
| `receiver` | ForeignKey | Message receiver |
| `encrypted_content` | TextField | End-to-end encrypted message content |
| `is_read` | BooleanField | Read status |
| `is_delivered` | BooleanField | Delivery status |
| `is_deleted` | BooleanField | Deletion status |
| `created_at` | DateTimeField | Creation timestamp |
| `delivered_at` | DateTimeField | Delivery timestamp |
| `read_at` | DateTimeField | Read timestamp |

### Friendship Model (`friendships.models.Friendship`)

Manages relationships between users:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `user` | ForeignKey | Friendship initiator |
| `friend` | ForeignKey | Friend user |
| `status` | CharField | Status (pending, accepted, rejected, blocked) |
| `created_at` | DateTimeField | Creation timestamp |
| `updated_at` | DateTimeField | Update timestamp |

### UserSession Model (`user_sessions.models.UserSession`)

Tracks user sessions across devices:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `user` | ForeignKey | Associated user |
| `token` | TextField | Session token |
| `device_info` | TextField | Device information |
| `ip_address` | GenericIPAddressField | IP address |
| `is_active` | BooleanField | Active status |
| `expires_at` | DateTimeField | Expiration timestamp |
| `last_activity` | DateTimeField | Last activity timestamp |

### SecurityLog Model (`security_logs.models.SecurityLog`)

Security event logging:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `user` | ForeignKey | Associated user |
| `event_type` | CharField | Type of security event |
| `ip_address` | GenericIPAddressField | IP address |
| `device_info` | TextField | Device information |
| `severity` | IntegerField | Severity level |
| `details` | JSONField | Additional event details |
| `created_at` | DateTimeField | Creation timestamp |

### Backup Model (`backups.models.Backup`)

Encrypted user data backups:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `user` | ForeignKey | Associated user |
| `session` | ForeignKey | Associated session |
| `encrypted_data` | TextField | Encrypted backup data |
| `checksum` | CharField | Data integrity checksum |
| `size` | PositiveIntegerField | Size in bytes |
| `created_at` | DateTimeField | Creation timestamp |

## 🔌 API Endpoints

### Authentication API (`/api/auth/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/register/` | POST | Register a new user |
| `/login/` | POST | Authenticate user and get tokens |
| `/logout/` | POST | Logout and invalidate session |
| `/token/refresh/` | POST | Refresh JWT token |
| `/verify-email/` | POST | Verify email with OTP |
| `/password/reset-request/` | POST | Request password reset |
| `/password/reset-confirm/` | POST | Confirm password reset with OTP |
| `/password/change/` | POST | Change password |
| `/2fa/setup/` | POST | Set up two-factor authentication |
| `/2fa/verify/` | POST | Verify 2FA code |
| `/otp/refresh/` | POST | Refresh OTP code |
| `/profile/` | GET/PUT | Get or update user profile |

### Profile API (`/api/profile/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/me/` | GET/PUT | Get or update current user's profile |
| `/friend/<uuid:profile_id>/` | GET | View friend's profile |
| `/status/update/` | POST | Update profile status |

### Friendship API (`/api/friend/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | List all friends |
| `/pending/` | GET | List pending friend requests |
| `/sent/` | GET | List sent friend requests |
| `/blocked/` | GET | List blocked users |
| `/request/` | POST | Send friend request |
| `/action/<str:action>/` | POST | Accept/reject/block friend request |
| `/search/` | GET | Search for users |

### Messaging API (`/api/messages/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/send/` | POST | Send encrypted message |
| `/conversation/<uuid:user_id>/` | GET | Get conversation with user |
| `/conversations/` | GET | List all conversations |
| `/read/<uuid:message_id>/` | POST | Mark message as read |
| `/read-all/<uuid:user_id>/` | POST | Mark all messages from user as read |
| `/delete/<uuid:message_id>/` | POST | Delete message |
| `/typing/update/` | POST | Update typing status |
| `/typing/<uuid:user_id>/` | GET | Get typing status |
| `/keys/generate/` | POST | Generate encryption key pair |
| `/keys/public/` | POST | Get user's public key |

### User Sessions API (`/api/sessions/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | List active sessions |
| `/<uuid:session_id>/` | GET/PATCH/DELETE | Get/update/delete session |
| `/invalidate-all/` | POST | Invalidate all other sessions |
| `/extend/` | POST | Extend session expiration |
| `/update-activity/` | POST | Update session activity |

### Security Logs API (`/api/security/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/logs/` | GET | List security logs with filtering |
| `/me/` | GET | Get current user's security logs |
| `/activity/` | GET | Get security activity summary |
| `/suspicious/` | GET | List suspicious activity (admin) |
| `/ip/<str:ip_address>/` | GET | List logs for IP address (admin) |

### Backups API (`/api/backups/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | List all backups |
| `/create/` | POST | Create new backup |
| `/download/` | POST | Download backup as HTML |
| `/<uuid:pk>/` | DELETE | Delete backup |
| `/prepare/` | POST | Prepare backup data |
| `/decrypt/` | POST | Decrypt backup with private key |

## 📡 WebSocket Endpoints

### Profile WebSocket (`/ws/profile/`)

Real-time profile status updates.

Events:
- `update_status`: Update user status
- `presence_update`: Friend online/offline notifications

### Friends WebSocket (`/ws/friends/`)

Real-time friend request management.

Events:
- `friend_request`: Send friend request
- `friend_response`: Accept/reject/block friend
- `block_user`: Block user

### Messages WebSocket (`/ws/messages/<user_id>/`)

Real-time messaging with a specific user.

Events:
- `message`: Send encrypted message
- `typing`: Update typing status
- `read`: Mark message as read
- `delete`: Delete message

### Notifications WebSocket (`/ws/notifications/`)

System-wide notifications.

Events:
- `mark_read`: Mark notification as read
- `clear_all`: Clear all notifications

### Sessions WebSocket (`/ws/sessions/`)

Session management across devices.

Events:
- `invalidate_session`: Log out from a session
- `invalidate_all_sessions`: Log out from all sessions
- `extend_session`: Extend session expiration

### Security WebSocket (`/ws/security/`)

Security alerts and monitoring.

Events:
- `get_security_logs`: Fetch security logs
- `security_event`: Real-time security notifications

## 🔒 Security Implementation

### End-to-End Encryption

Messages are encrypted using a hybrid approach:
1. RSA for key exchange (asymmetric)
2. AES for message content (symmetric)

The process:
1. Each user generates and stores an RSA key pair
2. Sender encrypts message with AES using a random session key
3. Sender encrypts the session key with recipient's public RSA key
4. Recipient uses their private key to decrypt the session key
5. Recipient uses the session key to decrypt the message

### Two-Factor Authentication

Implemented using TOTP (Time-based One-Time Password):
1. User enables 2FA in settings
2. Server generates a secret key
3. User configures their authenticator app
4. During login, user must provide code from authenticator

### Password Security

Enhanced password security:
1. Complex password requirements (length, character types)
2. Check against common passwords
3. Check against Have I Been Pwned database
4. Rate limiting for login attempts
5. Account lockout after repeated failures

### Session Management

Secure session handling:
1. JWT authentication with short-lived tokens
2. Device tracking and identification
3. IP address logging
4. Activity timestamps
5. Session expiration
6. Ability to invalidate sessions remotely

## 🧪 Testing

The project includes comprehensive test suites for all major components:

1. **Model Tests**: Test database models and business logic
2. **API Tests**: Test HTTP endpoints
3. **WebSocket Tests**: Test real-time communication
4. **Integration Tests**: Test interactions between components

Run tests with:

```bash
python manage.py test
```

## 📚 Libraries and Dependencies

- **Django**: Web framework
- **Django REST Framework**: API framework
- **Channels**: WebSocket support
- **Channels Redis**: Redis backend for Channels
- **PyJWT**: JWT token handling
- **Cryptography**: Encryption implementation
- **PyOTP**: OTP generation and verification
- **python-decouple**: Environment variable management
- **Daphne**: ASGI server

## 🛠️ Development Guidelines

1. **Code Style**: Follow PEP 8 guidelines
2. **Documentation**: Add docstrings to functions and classes
3. **Testing**: Write tests for new features
4. **Security**: Follow security best practices
5. **Error Handling**: Implement proper error handling and logging

## 📝 API Versioning

Currently using API v1 (implicit). Future versions should use explicit versioning in the URL path (e.g., `/api/v2/`).

## 🔍 Logging

Security events are logged to:
1. Database (`SecurityLog` model)
2. Console (in development)
3. File (in production)

Log levels:
- INFO: Normal events
- WARNING: Suspicious activity
- ERROR: Security concerns
- CRITICAL: Severe security issues