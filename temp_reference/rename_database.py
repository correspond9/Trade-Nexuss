#!/usr/bin/env python3
"""
Database Renaming Script
Renames openalgo.db to trading_terminal.db and updates all references
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path
import re

class DatabaseRenamer:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.old_name = "openalgo.db"
        self.new_name = "trading_terminal.db"
        self.backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Files that need updating (based on search results)
        self.files_to_update = [
            # Configuration
            ".env",
            
            # Shell scripts
            "start.sh",
            "STATIC_IP_DEPLOYMENT_GUIDE.md",
            
            # Python scripts
            "upgrade/migrate_security_columns.py",
            "upgrade/migrate_telegram_bot.py", 
            "fix_broker.py",
            "fix_broker_sandbox.py",
            
            # Test files
            "test/test_master_contract_instrumenttype.py",
            
            # Documentation
            "design/01_architecture.md",
            "design/04_database_layer.md",
            "design/07_configuration.md",
            "design/10_logging_system.md",
            "design/12_deployment_architecture.md",
            "docs/CACHE_ARCHITECTURE_AND_PLUGGABLE_SYSTEM.md",
            "docs/docker.md",
            "docs/SCHEDULED_ALERTS_PRD.md",
            "docs/rust/17-ZERO-CONFIG-ARCHITECTURE.md",
            "docs/rust/13-CONFIGURATION.md"
        ]
        
        self.update_log = []
        
    def log_update(self, file_path, old_content, new_content, line_num=None):
        """Log an update for verification"""
        log_entry = {
            'file': str(file_path),
            'line': line_num,
            'timestamp': datetime.now().isoformat(),
            'old': old_content,
            'new': new_content
        }
        self.update_log.append(log_entry)
        
    def backup_database(self):
        """Create backup of the original database"""
        db_path = self.project_root / "backend" / "db" / self.old_name
        backup_path = self.project_root / "backend" / "db" / f"{self.old_name}.backup_{self.backup_suffix}"
        
        if db_path.exists():
            print(f"🔄 Creating backup: {backup_path}")
            shutil.copy2(db_path, backup_path)
            print(f"✅ Backup created successfully")
            return True
        else:
            print(f"⚠️  Database file not found: {db_path}")
            return False
    
    def rename_database_file(self):
        """Rename the actual database file"""
        old_path = self.project_root / "backend" / "db" / self.old_name
        new_path = self.project_root / "backend" / "db" / self.new_name
        
        if old_path.exists():
            print(f"🔄 Renaming database file:")
            print(f"   From: {old_path}")
            print(f"   To:   {new_path}")
            
            old_path.rename(new_path)
            print(f"✅ Database file renamed successfully")
            return True
        else:
            print(f"⚠️  Database file not found: {old_path}")
            return False
    
    def update_file_content(self, file_path):
        """Update content of a single file"""
        full_path = self.project_root / file_path
        
        if not full_path.exists():
            print(f"⚠️  File not found: {file_path}")
            return False
        
        try:
            # Read file content
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Replace all occurrences of openalgo.db with trading_terminal.db
            updated_content = content.replace(self.old_name, self.new_name)
            
            # Also update path references
            updated_content = updated_content.replace(
                f"sqlite:///db/{self.old_name}", 
                f"sqlite:///db/{self.new_name}"
            )
            updated_content = updated_content.replace(
                f"sqlite:///databases/{self.old_name}", 
                f"sqlite:///databases/{self.new_name}"
            )
            updated_content = updated_content.replace(
                f"sqlite:///{self.old_name}", 
                f"sqlite:///{self.new_name}"
            )
            
            # Write back if changed
            if updated_content != original_content:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                print(f"✅ Updated: {file_path}")
                self.log_update(file_path, original_content, updated_content)
                return True
            else:
                print(f"ℹ️  No changes needed: {file_path}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating {file_path}: {str(e)}")
            return False
    
    def update_all_files(self):
        """Update all files that reference the database"""
        print(f"\n🔄 Updating {len(self.files_to_update)} files...")
        
        updated_count = 0
        for file_path in self.files_to_update:
            if self.update_file_content(file_path):
                updated_count += 1
        
        print(f"\n📊 Update Summary:")
        print(f"   Total files processed: {len(self.files_to_update)}")
        print(f"   Files updated: {updated_count}")
        print(f"   Files unchanged: {len(self.files_to_update) - updated_count}")
        
        return updated_count
    
    def verify_updates(self):
        """Verify that all updates were successful"""
        print(f"\n🔍 Verifying updates...")
        
        verification_results = []
        
        # Check database file exists
        new_db_path = self.project_root / "backend" / "db" / self.new_name
        verification_results.append({
            'check': 'Database file exists',
            'status': new_db_path.exists(),
            'details': str(new_db_path)
        })
        
        # Check backup exists
        backup_path = self.project_root / "backend" / "db" / f"{self.old_name}.backup_{self.backup_suffix}"
        verification_results.append({
            'check': 'Backup file exists',
            'status': backup_path.exists(),
            'details': str(backup_path)
        })
        
        # Check .env file was updated
        env_path = self.project_root / ".env"
        if env_path.exists():
            with open(env_path, 'r') as f:
                env_content = f.read()
            
            has_new_name = self.new_name in env_content
            has_old_name = self.old_name in env_content
            
            verification_results.append({
                'check': '.env file updated',
                'status': has_new_name and not has_old_name,
                'details': f'New name found: {has_new_name}, Old name removed: {not has_old_name}'
            })
        
        # Print verification results
        print(f"\n📋 Verification Results:")
        all_passed = True
        for result in verification_results:
            status_icon = "✅" if result['status'] else "❌"
            print(f"   {status_icon} {result['check']}: {result['details']}")
            if not result['status']:
                all_passed = False
        
        return all_passed
    
    def save_update_log(self):
        """Save detailed update log"""
        log_file = self.project_root / f"database_rename_log_{self.backup_suffix}.json"
        
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'operation': 'database_rename',
            'old_name': self.old_name,
            'new_name': self.new_name,
            'backup_suffix': self.backup_suffix,
            'files_processed': len(self.files_to_update),
            'updates': self.update_log,
            'verification': self.verify_updates()
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"📝 Update log saved: {log_file}")
    
    def run_renaming_process(self):
        """Execute the complete renaming process"""
        print(f"🚀 Starting database renaming process...")
        print(f"   Project root: {self.project_root}")
        print(f"   Old name: {self.old_name}")
        print(f"   New name: {self.new_name}")
        print(f"   Backup suffix: {self.backup_suffix}")
        
        try:
            # Step 1: Backup database
            if not self.backup_database():
                print("❌ Backup failed. Aborting process.")
                return False
            
            # Step 2: Rename database file
            if not self.rename_database_file():
                print("❌ Database file rename failed. Aborting process.")
                return False
            
            # Step 3: Update all file references
            updated_count = self.update_all_files()
            
            # Step 4: Verify updates
            verification_passed = self.verify_updates()
            
            # Step 5: Save log
            self.save_update_log()
            
            # Final summary
            print(f"\n🎉 Renaming process completed!")
            print(f"   Files updated: {updated_count}")
            print(f"   Verification: {'PASSED' if verification_passed else 'FAILED'}")
            
            if verification_passed:
                print(f"✅ All updates completed successfully!")
                print(f"🔄 You can now restart your application")
            else:
                print(f"⚠️  Some verifications failed. Please review the log file")
            
            return verification_passed
            
        except Exception as e:
            print(f"❌ Renaming process failed: {str(e)}")
            return False

def main():
    """Main execution function"""
    # Get project root (current directory)
    project_root = Path.cwd()
    
    print(f"📁 Project root detected as: {project_root}")
    
    # Confirm with user
    response = input(f"\n⚠️  This will rename 'openalgo.db' to 'trading_terminal.db' and update all references. Continue? (y/N): ")
    
    if response.lower() not in ['y', 'yes']:
        print("❌ Operation cancelled by user")
        return
    
    # Run the renaming process
    renamer = DatabaseRenamer(project_root)
    success = renamer.run_renaming_process()
    
    if success:
        print(f"\n✅ Database renaming completed successfully!")
        print(f"📝 Check the log file for detailed changes")
    else:
        print(f"\n❌ Database renaming failed. Check the log file for details")

if __name__ == "__main__":
    main()
