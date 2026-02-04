const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// Security Configuration Generator
class SecurityConfig {
  static generateSecureSecret(length = 64) {
    return crypto.randomBytes(length).toString('hex');
  }

  static validateSecret(secret, minLength = 32) {
    return secret && secret.length >= minLength && !this.isDefaultSecret(secret);
  }

  static isDefaultSecret(secret) {
    const defaultSecrets = [
      'your_api_key_here',
      'your_secret_here',
      'change_this_in_production',
      'default_secret_key',
      '3daa0403ce2501ee7432b75bf100048e3cf510d63d2754f952e93d88bf07ea84',
      'a25d94718479b170c16278e321ea6c989358bf499a658fd20c90033cef8ce772'
    ];
    return defaultSecrets.includes(secret);
  }

  static checkProductionSecurity() {
    const errors = [];
    
    // Check if running with default secrets
    if (process.env.NODE_ENV === 'production') {
      if (this.isDefaultSecret(process.env.APP_KEY)) {
        errors.push('CRITICAL: Using default APP_KEY in production');
      }
      
      if (this.isDefaultSecret(process.env.API_KEY_PEPPER)) {
        errors.push('CRITICAL: Using default API_KEY_PEPPER in production');
      }
      
      if (!process.env.JWT_SECRET || this.isDefaultSecret(process.env.JWT_SECRET)) {
        errors.push('CRITICAL: Missing or default JWT_SECRET in production');
      }
    }

    // Check file permissions
    const envFile = path.join(process.cwd(), '.env');
    if (fs.existsSync(envFile)) {
      const stats = fs.statSync(envFile);
      if (stats.mode & 0o077) { // Check if others can read
        errors.push('WARNING: .env file has too permissive permissions');
      }
    }

    return errors;
  }

  static generateInstallationScript() {
    return '#!/bin/bash\n' +
           '# Trading Terminal Security Setup Script\n' +
           '# This script generates secure secrets for production deployment\n' +
           '\n' +
           'set -e\n' +
           '\n' +
           'echo "🔒 Trading Terminal Security Setup"\n' +
           'echo "================================="\n' +
           '\n' +
           '# Generate secure secrets\n' +
           'APP_KEY=$(openssl rand -hex 32)\n' +
           'API_KEY_PEPPER=$(openssl rand -hex 32)\n' +
           'JWT_SECRET=$(openssl rand -hex 32)\n' +
           'SESSION_SECRET=$(openssl rand -hex 32)\n' +
           '\n' +
           '# Create .env file if it doesn\'t exist\n' +
           'if [ ! -f .env ]; then\n' +
           '    cp .sample.env .env\n' +
           '    echo "Created .env from .sample.env"\n' +
           'fi\n' +
           '\n' +
           '# Update .env with secure secrets\n' +
           'sed -i.bak "s/^APP_KEY=.*/APP_KEY=${APP_KEY}/" .env\n' +
           'sed -i "s/^API_KEY_PEPPER=.*/API_KEY_PEPPER=${API_KEY_PEPPER}/" .env\n' +
           'sed -i "s/^JWT_SECRET=.*/JWT_SECRET=${JWT_SECRET}/" .env\n' +
           'sed -i "s/^SESSION_SECRET=.*/SESSION_SECRET=${SESSION_SECRET}/" .env\n' +
           '\n' +
           '# Set secure file permissions\n' +
           'chmod 600 .env\n' +
           'chmod 755 scripts/\n' +
           '\n' +
           'echo "✅ Security configuration complete!"\n' +
           'echo "🔑 Generated secure secrets:"\n' +
           'echo "   - APP_KEY: ${APP_KEY:0:16}..."\n' +
           'echo "   - API_KEY_PEPPER: ${API_KEY_PEPPER:0:16}..."\n' +
           'echo "   - JWT_SECRET: ${JWT_SECRET:0:16}..."\n' +
           'echo "   - SESSION_SECRET: ${SESSION_SECRET:0:16}..."\n' +
           'echo ""\n' +
           'echo "⚠️  IMPORTANT: Save these secrets in a secure location!"\n' +
           'echo "📁 Backup .env file to secure storage"\n' +
           'echo "🔒 Never commit secrets to version control"\n';
  }

  static createStartupCheck() {
    return '// Startup Security Check\n' +
           'const security = require(\'./middleware/security\');\n' +
           '\n' +
           'function checkSecurityOnStartup() {\n' +
           '  const errors = security.checkProductionSecurity();\n' +
           '  \n' +
           '  if (errors.length > 0) {\n' +
           '    console.error(\'🚨 SECURITY ISSUES DETECTED:\');\n' +
           '    errors.forEach(error => console.error(`   - ${error}`));\n' +
           '    \n' +
           '    if (process.env.NODE_ENV === \'production\') {\n' +
           '      console.error(\'\\\\n❌ Cannot start in production with security issues\');\n' +
           '      process.exit(1);\n' +
           '    } else {\n' +
           '      console.warn(\'\\\\n⚠️  Running in development mode with security issues\');\n' +
           '    }\n' +
           '  } else {\n' +
           '    console.log(\'✅ Security checks passed\');\n' +
           '  }\n' +
           '}\n' +
           '\n' +
           'module.exports = { checkSecurityOnStartup };\n';
  }
}

module.exports = SecurityConfig;