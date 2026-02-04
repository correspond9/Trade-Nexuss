#!/usr/bin/env python3
"""
Database Renaming Script - Backend Files Update
Updates remaining references to openalgo.db in backend directory
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

class BackendDatabaseUpdater:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.backend_root = self.project_root / "backend"
        self.old_name = "openalgo.db"
        self.new_name = "trading_terminal.db"
        
        # Files in backend directory that need updating
        self.backend_files_to_update = [
            "upgrade/migrate_security_columns.py",
            "upgrade/migrate_telegram_bot.py", 
            "fix_broker.py",
            "fix_broker_sandbox.py",
            "test/test_master_contract_instrumenttype.py",
            "STATIC_IP_DEPLOYMENT_GUIDE.md",
            "start.sh",
            "design/01_architecture.md",
            "design/04_database_layer.md",
            "design/07_configuration.md",
            "design/10_logging_system.md",
            "design/12_deployment_architecture.md",
            "docs/CACHE_ARCHITECTURE_AND_PLUGGABLE_SYSTEM.md",
            "docs/docker.md",
            "docs/PASSWORD_RESET.md",
            "docs/SCHEDULED_ALERTS_PRD.md",
            "docs/rust/13-CONFIGURATION.md",
            "docs/rust/17-ZERO-CONFIG-ARCHITECTURE.md"
        ]
        
        self.update_log = []
        
    def log_update(self, file_path, changes_count):
        """Log an update for verification"""
        log_entry = {
            'file': str(file_path),
            'changes_count': changes_count,
            'timestamp': datetime.now().isoformat()
        }
        self.update_log.append(log_entry)
        
    def update_file_content(self, file_path):
        """Update content of a single file"""
        full_path = self.backend_root / file_path
        
        if not full_path.exists():
            print(f"⚠️  File not found: {file_path}")
            return 0
        
        try:
            # Read file content
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            changes_count = 0
            
            # Replace all occurrences of openalgo.db with trading_terminal.db
            if self.old_name in content:
                content = content.replace(self.old_name, self.new_name)
                changes_count += 1
            
            # Also update path references
            old_patterns = [
                f"sqlite:///db/{self.old_name}",
                f"sqlite:///databases/{self.old_name}",
                f"sqlite:///{self.old_name}",
                f"db/{self.old_name}",
                f"/db/{self.old_name}",
                f"./db/{self.old_name}",
                f"backend/db/{self.old_name}",
                f"/app/backend/db/{self.old_name}",
                f"/var/python/openalgo/db/{self.old_name}"
            ]
            
            new_patterns = [
                f"sqlite:///db/{self.new_name}",
                f"sqlite:///databases/{self.new_name}",
                f"sqlite:///{self.new_name}",
                f"db/{self.new_name}",
                f"/db/{self.new_name}",
                f"./db/{self.new_name}",
                f"backend/db/{self.new_name}",
                f"/app/backend/db/{self.new_name}",
                f"/var/python/openalgo/db/{self.new_name}"
            ]
            
            for old_pattern, new_pattern in zip(old_patterns, new_patterns):
                if old_pattern in content:
                    content = content.replace(old_pattern, new_pattern)
                    changes_count += 1
            
            # Write back if changed
            if content != original_content:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"✅ Updated: {file_path} ({changes_count} changes)")
                self.log_update(file_path, changes_count)
                return changes_count
            else:
                print(f"ℹ️  No changes needed: {file_path}")
                return 0
                
        except Exception as e:
            print(f"❌ Error updating {file_path}: {str(e)}")
            return 0
    
    def update_all_backend_files(self):
        """Update all backend files that reference the database"""
        print(f"\n🔄 Updating {len(self.backend_files_to_update)} backend files...")
        
        total_changes = 0
        updated_files = 0
        
        for file_path in self.backend_files_to_update:
            changes = self.update_file_content(file_path)
            if changes > 0:
                total_changes += changes
                updated_files += 1
        
        print(f"\n📊 Backend Update Summary:")
        print(f"   Total files processed: {len(self.backend_files_to_update)}")
        print(f"   Files updated: {updated_files}")
        print(f"   Files unchanged: {len(self.backend_files_to_update) - updated_files}")
        print(f"   Total changes made: {total_changes}")
        
        return updated_files, total_changes
    
    def verify_backend_updates(self):
        """Verify that backend updates were successful"""
        print(f"\n🔍 Verifying backend updates...")
        
        verification_results = []
        
        # Check that no backend files still contain old references
        for file_path in self.backend_files_to_update:
            full_path = self.backend_root / file_path
            
            if full_path.exists():
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    has_old_name = self.old_name in content
                    has_new_name = self.new_name in content
                    
                    verification_results.append({
                        'file': file_path,
                        'old_removed': not has_old_name,
                        'new_found': has_new_name,
                        'status': not has_old_name or self.new_name not in content  # OK if old name gone or new name present
                    })
                    
                except Exception as e:
                    verification_results.append({
                        'file': file_path,
                        'error': str(e),
                        'status': False
                    })
        
        # Print verification results
        print(f"\n📋 Backend Verification Results:")
        all_passed = True
        for result in verification_results:
            if 'error' in result:
                status_icon = "❌"
                print(f"   {status_icon} {result['file']}: ERROR - {result['error']}")
                all_passed = False
            else:
                status_icon = "✅" if result['status'] else "⚠️"
                status_text = f"Old removed: {result['old_removed']}, New found: {result['new_found']}"
                print(f"   {status_icon} {result['file']}: {status_text}")
                if not result['status']:
                    all_passed = False
        
        return all_passed
    
    def save_backend_update_log(self):
        """Save detailed backend update log"""
        log_file = self.project_root / f"backend_database_update_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'operation': 'backend_database_update',
            'old_name': self.old_name,
            'new_name': self.new_name,
            'files_processed': len(self.backend_files_to_update),
            'updates': self.update_log,
            'verification': self.verify_backend_updates()
        }
        
        import json
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"📝 Backend update log saved: {log_file}")
    
    def run_backend_update_process(self):
        """Execute the complete backend update process"""
        print(f"🚀 Starting backend database reference update...")
        print(f"   Backend root: {self.backend_root}")
        print(f"   Old name: {self.old_name}")
        print(f"   New name: {self.new_name}")
        
        try:
            # Update all backend file references
            updated_files, total_changes = self.update_all_backend_files()
            
            # Verify updates
            verification_passed = self.verify_backend_updates()
            
            # Save log
            self.save_backend_update_log()
            
            # Final summary
            print(f"\n🎉 Backend update process completed!")
            print(f"   Files updated: {updated_files}")
            print(f"   Total changes: {total_changes}")
            print(f"   Verification: {'PASSED' if verification_passed else 'FAILED'}")
            
            if verification_passed:
                print(f"✅ All backend updates completed successfully!")
            else:
                print(f"⚠️  Some verifications failed. Please review the log file")
            
            return verification_passed
            
        except Exception as e:
            print(f"❌ Backend update process failed: {str(e)}")
            return False

def main():
    """Main execution function"""
    # Get project root (current directory)
    project_root = Path.cwd()
    
    print(f"📁 Project root detected as: {project_root}")
    
    # Confirm with user
    response = input(f"\n⚠️  This will update all backend references from 'openalgo.db' to 'trading_terminal.db'. Continue? (y/N): ")
    
    if response.lower() not in ['y', 'yes']:
        print("❌ Operation cancelled by user")
        return
    
    # Run the backend update process
    updater = BackendDatabaseUpdater(project_root)
    success = updater.run_backend_update_process()
    
    if success:
        print(f"\n✅ Backend database reference update completed successfully!")
    else:
        print(f"\n❌ Backend update failed. Check the log file for details")

if __name__ == "__main__":
    main()
