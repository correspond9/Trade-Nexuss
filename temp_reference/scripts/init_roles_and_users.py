# scripts/init_roles_and_users.py

"""
Initialize roles database and create demo users for testing
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

from database.roles_db import init_db, Role, RoleBasedUser, db_session
from werkzeug.security import generate_password_hash
from utils.logging import get_logger

logger = get_logger(__name__)

def create_demo_users():
    """Create demo users for testing different roles"""
    
    demo_users = [
        {
            'username': 'admin',
            'password': 'admin123',
            'email': 'admin@tradingterminal.com',
            'full_name': 'System Administrator',
            'role_name': 'super_admin'
        },
        {
            'username': 'manager',
            'password': 'manager123',
            'email': 'manager@tradingterminal.com',
            'full_name': 'Trading Manager',
            'role_name': 'admin'
        },
        {
            'username': 'equity_user',
            'password': 'equity123',
            'email': 'equity@tradingterminal.com',
            'full_name': 'Equity Trader',
            'role_name': 'user_equity'
        },
        {
            'username': 'derivatives_user',
            'password': 'derivatives123',
            'email': 'derivatives@tradingterminal.com',
            'full_name': 'Derivatives Trader',
            'role_name': 'user_equity_derivatives'
        },
        {
            'username': 'commodity_user',
            'password': 'commodity123',
            'email': 'commodity@tradingterminal.com',
            'full_name': 'Commodity Trader',
            'role_name': 'user_commodity'
        },
        {
            'username': 'all_user',
            'password': 'all123',
            'email': 'all@tradingterminal.com',
            'full_name': 'All Markets Trader',
            'role_name': 'user_all'
        }
    ]
    
    created_users = []
    
    for user_data in demo_users:
        # Check if user already exists
        existing_user = RoleBasedUser.query.filter_by(username=user_data['username']).first()
        if existing_user:
            logger.info(f"RoleBasedUser {user_data['username']} already exists, skipping...")
            continue
        
        # Get role
        role = Role.query.filter_by(name=user_data['role_name']).first()
        if not role:
            logger.error(f"Role {user_data['role_name']} not found, skipping user {user_data['username']}")
            continue
        
        # Create user
        user = RoleBasedUser(
            username=user_data['username'],
            email=user_data['email'],
            password_hash=generate_password_hash(user_data['password'], method='pbkdf2:sha256'),
            full_name=user_data['full_name'],
            role_id=role.id,
            is_active=True
        )
        
        db_session.add(user)
        created_users.append(user_data)
        logger.info(f"Created user: {user_data['username']} with role: {user_data['role_name']}")
    
    db_session.commit()
    
    return created_users

def main():
    """Main function to initialize roles and create demo users"""
    print("🔧 Initializing Roles and Demo RoleBasedUsers")
    print("=" * 50)
    
    try:
        # Initialize roles database
        print("📊 Initializing roles database...")
        init_db()
        print("✅ Roles database initialized successfully")
        
        # Create demo users
        print("\n👥 Creating demo users...")
        created_users = create_demo_users()
        
        if created_users:
            print(f"\n✅ Created {len(created_users)} demo users:")
            for user in created_users:
                print(f"   📝 {user['username']} ({user['role_name']}) - Password: {user['password']}")
        
        print("\n🎯 Demo users created successfully!")
        print("\n📋 Login Credentials:")
        print("   🔐 Super Admin: admin / admin123")
        print("   🔐 Admin: manager / manager123")
        print("   🔐 Equity RoleBasedUser: equity_user / equity123")
        print("   🔐 Derivatives RoleBasedUser: derivatives_user / derivatives123")
        print("   🔐 Commodity RoleBasedUser: commodity_user / commodity123")
        print("   🔐 All Markets RoleBasedUser: all_user / all123")
        
        print("\n🚀 You can now test the role-based access system!")
        
    except Exception as e:
        logger.error(f"Error initializing roles and users: {str(e)}")
        print(f"❌ Error: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)