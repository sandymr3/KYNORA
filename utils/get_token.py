#!/usr/bin/env python3
"""
Firebase Authentication Token Generator
Utility script to generate custom Firebase tokens for testing
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.firebase import firebase_config
from config.settings import settings
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TokenGenerator:
    """Firebase token generation utility"""
    
    def __init__(self):
        self.firebase = firebase_config
    
    def create_custom_token(self, uid: str, additional_claims: dict = None) -> str:
        """
        Create a custom Firebase token for a user
        
        Args:
            uid: User ID
            additional_claims: Additional claims to include in token
            
        Returns:
            str: Custom token as string
        """
        try:
            if additional_claims is None:
                additional_claims = {}
            
            # Add default claims
            additional_claims.update({
                'provider': 'custom',
                'created_at': datetime.utcnow().isoformat(),
                'app': settings.app_name
            })
            
            token_bytes = self.firebase.create_custom_token(uid, additional_claims)
            token_string = token_bytes.decode('utf-8')
            
            logger.info(f"✅ Custom token created for user: {uid}")
            return token_string
            
        except Exception as e:
            logger.error(f"❌ Failed to create custom token: {e}")
            raise
    
    def create_admin_token(self) -> str:
        """Create a token for the admin user"""
        admin_claims = {
            'role': 'admin',
            'permissions': [
                'read:all',
                'write:all',
                'delete:all',
                'admin:panel'
            ],
            'email': settings.admin_email
        }
        
        return self.create_custom_token('admin_001', admin_claims)
    
    def create_user_token(self, user_id: str, email: str = None, role: str = 'user') -> str:
        """Create a token for a regular user"""
        user_claims = {
            'role': role,
            'permissions': [
                'read:own',
                'write:own'
            ]
        }
        
        if email:
            user_claims['email'] = email
            
        return self.create_custom_token(user_id, user_claims)
    
    def verify_token(self, token: str) -> dict:
        """
        Verify a Firebase ID token
        
        Args:
            token: Firebase ID token to verify
            
        Returns:
            dict: Decoded token claims
        """
        try:
            decoded_token = self.firebase.verify_id_token(token)
            logger.info("✅ Token verified successfully")
            return decoded_token
        except Exception as e:
            logger.error(f"❌ Token verification failed: {e}")
            raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Generate Firebase Authentication Tokens')
    parser.add_argument('--type', choices=['admin', 'user', 'custom'], default='admin',
                       help='Type of token to generate')
    parser.add_argument('--uid', type=str, help='User ID for custom token')
    parser.add_argument('--email', type=str, help='Email for user token')
    parser.add_argument('--role', type=str, default='user', help='Role for user token')
    parser.add_argument('--claims', type=str, help='Additional claims as JSON string')
    parser.add_argument('--verify', type=str, help='Verify an existing token')
    parser.add_argument('--output', type=str, help='Output file to save token')
    
    args = parser.parse_args()
    
    try:
        generator = TokenGenerator()
        
        if args.verify:
            # Verify existing token
            logger.info("🔍 Verifying token...")
            claims = generator.verify_token(args.verify)
            print("\n" + "="*50)
            print("TOKEN VERIFICATION RESULT")
            print("="*50)
            print(json.dumps(claims, indent=2, default=str))
            return
        
        # Generate new token
        logger.info("🔑 Generating Firebase token...")
        
        if args.type == 'admin':
            token = generator.create_admin_token()
            token_info = {
                'type': 'admin',
                'uid': 'admin_001',
                'email': settings.admin_email,
                'role': 'admin'
            }
            
        elif args.type == 'user':
            if not args.uid:
                args.uid = f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            token = generator.create_user_token(args.uid, args.email, args.role)
            token_info = {
                'type': 'user',
                'uid': args.uid,
                'email': args.email,
                'role': args.role
            }
            
        elif args.type == 'custom':
            if not args.uid:
                logger.error("❌ --uid is required for custom tokens")
                sys.exit(1)
            
            additional_claims = {}
            if args.claims:
                try:
                    additional_claims = json.loads(args.claims)
                except json.JSONDecodeError:
                    logger.error("❌ Invalid JSON in --claims")
                    sys.exit(1)
            
            token = generator.create_custom_token(args.uid, additional_claims)
            token_info = {
                'type': 'custom',
                'uid': args.uid,
                'claims': additional_claims
            }
        
        # Display results
        print("\n" + "="*50)
        print("FIREBASE AUTHENTICATION TOKEN")
        print("="*50)
        print(f"Token Type: {token_info['type']}")
        print(f"User ID: {token_info['uid']}")
        if token_info.get('email'):
            print(f"Email: {token_info['email']}")
        if token_info.get('role'):
            print(f"Role: {token_info['role']}")
        print(f"Generated: {datetime.utcnow().isoformat()}")
        print("\nToken:")
        print("-" * 50)
        print(token)
        print("-" * 50)
        
        # Save to file if requested
        if args.output:
            token_data = {
                'token': token,
                'info': token_info,
                'generated_at': datetime.utcnow().isoformat(),
                'expires_in': '1 hour'
            }
            
            with open(args.output, 'w') as f:
                json.dump(token_data, f, indent=2)
            
            logger.info(f"✅ Token saved to: {args.output}")
        
        # Usage instructions
        print("\n" + "="*50)
        print("USAGE INSTRUCTIONS")
        print("="*50)
        print("1. Use this token in Authorization header:")
        print(f"   Authorization: Bearer {token}")
        print("\n2. Or use in API testing tools like Postman/Insomnia")
        print("\n3. Test with curl:")
        print(f'   curl -H "Authorization: Bearer {token}" http://localhost:8000/health')
        print("\n4. Token is valid for 1 hour")
        
    except Exception as e:
        logger.error(f"❌ Token generation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
