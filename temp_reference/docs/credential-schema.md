# DhanHQ Credential Schema Documentation

**Date**: January 31, 2026  
**Version**: 2.0  
**Status**: Active Implementation

---

## 📋 **CREDENTIAL SCHEMA OVERVIEW**

### **Authentication Modes**
The system supports two authentication modes for DhanHQ API integration:

1. **DAILY_TOKEN** - 24-hour validity access token
2. **STATIC_IP** - Static IP-based authentication

---

## 🔐 **CREDENTIAL DATA STRUCTURE**

### **Core Fields**
```json
{
  "client_id": "string",
  "access_token": "string", 
  "api_key": "string",
  "secret_api": "string",
  "daily_token": "string",
  "auth_mode": "DAILY_TOKEN|STATIC_IP",
  "last_updated": "ISO_8601_timestamp"
}
```

### **Field Descriptions**

| **Field** | **Type** | **Required** | **Description** |
|-----------|----------|------------|-------------|
| `client_id` | string | ✅ Yes | DhanHQ account client ID |
| `access_token` | string | ✅ Yes | JWT access token for authentication |
| `api_key` | string | ✅ Yes | DhanHQ API key |
| `secret_api` | string | ✅ Yes | DhanHQ secret API key |
| `daily_token` | string | ✅ Yes | 24-hour validity token |
| `auth_mode` | string | ✅ Yes | Authentication mode (DAILY_TOKEN/STATIC_IP) |
| `last_updated` | string | ✅ Yes | Last update timestamp (ISO 8601) |

---

## 🗂️ **STORAGE STRUCTURE**

### **File-Based Storage**
- **Location**: `dhan_credentials.json`
- **Format**: JSON
- **Structure**:
```json
{
  "active_mode": "DAILY_TOKEN",
  "DAILY_TOKEN": {
    "client_id": "1100353799",
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9...",
    "api_key": "fc94762c",
    "secret_api": "9d08b90e-8905-40dd-9cd3-1126696ae0c2",
    "daily_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9...",
    "auth_mode": "DAILY_TOKEN",
    "last_updated": "2026-01-31T05:27:00.000Z"
  },
  "STATIC_IP": {
    "client_id": "1100353799",
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9...",
    "api_key": "fc94762c",
    "secret_api": "9d08b90e-8905-40dd-9cd3-1126696ae0c2",
    "daily_token": "",
    "auth_mode": "STATIC_IP",
    "last_updated": "2026-01-31T05:27:00.000Z"
  }
}
```

---

## 🚀 **API ENDPOINTS**

### **1. Get Active Credentials**
```
GET /api/v1/credentials/active
```

**Response**:
```json
{
  "success": true,
  "message": "Active credentials for DAILY_TOKEN",
  "data": {
    "client_id": "1100353799",
    "auth_mode": "DAILY_TOKEN",
    "has_token": true,
    "last_updated": "2026-01-31T05:27:00.000Z"
  }
}
```

### **2. Save Credentials**
```
POST /api/v1/credentials/save
```

**Request Body**:
```json
{
  "client_id": "1100353799",
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9...",
  "api_key": "fc94762c",
  "secret_api": "9d08b90e-8905-40dd-9cd3-1126696ae0c2",
  "daily_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9...",
  "auth_mode": "DAILY_TOKEN"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Credentials saved successfully for DAILY_TOKEN",
  "data": {
    "auth_mode": "DAILY_TOKEN"
  }
}
```

### **3. Switch Authentication Mode**
```
POST /api/v1/credentials/switch-mode
```

**Request Body**:
```json
"DAILY_TOKEN"
```

**Response**:
```json
{
  "success": true,
  "message": "Switched to DAILY_TOKEN mode",
  "data": {
    "active_mode": "DAILY_TOKEN"
  }
}
```

### **4. Get Available Modes**
```
GET /api/v1/credentials/modes
```

**Response**:
```json
{
  "success": true,
  "message": "Available modes retrieved",
  "data": {
    "available_modes": [
      {
        "mode": "DAILY_TOKEN",
        "has_credentials": true,
        "client_id": "1100353799",
        "last_updated": "2026-01-31T05:27:00.000Z"
      },
      {
        "mode": "STATIC_IP",
        "has_credentials": false,
        "client_id": "",
        "last_updated": ""
      }
    ],
    "active_mode": "DAILY_TOKEN"
  }
}
```

### **5. Clear All Credentials**
```
DELETE /api/v1/credentials/clear
```

**Response**:
```json
{
  "success": true,
  "message": "All credentials cleared successfully"
}
```

---

## 🔒 **SECURITY CONSIDERATIONS**

### **Token Validation**
- **Access Token**: JWT format with 24-hour expiry
- **Daily Token**: Separate token for daily operations
- **API Keys**: Used for REST API authentication

### **Storage Security**
- **File Permissions**: Restricted to application user
- **Encryption**: Credentials stored in plain text (consider encryption for production)
- **Backup**: Manual backup recommended

### **Mode Switching**
- **Instant Switch**: No server restart required
- **Session Persistence**: Active mode preserved across restarts
- **Validation**: Mode validation before switching

---

## 📝 **USAGE EXAMPLES**

### **Save Daily Token Credentials**
```bash
curl -X POST "http://localhost:5000/api/v1/credentials/save" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "1100353799",
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9...",
    "api_key": "fc94762c",
    "secret_api": "9d08b90e-8905-40dd-9cd3-1126696ae0c2",
    "daily_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9...",
    "auth_mode": "DAILY_TOKEN"
  }'
```

### **Switch to Static IP Mode**
```bash
curl -X POST "http://localhost:5000/api/v1/credentials/switch-mode" \
  -H "Content-Type: application/json" \
  -d '"STATIC_IP"'
```

### **Get Current Active Credentials**
```bash
curl -X GET "http://localhost:5000/api/v1/credentials/active"
```

---

## 🔄 **MIGRATION NOTES**

### **From Complex Database System**
- ✅ **Simplified**: Removed database dependencies
- ✅ **File-Based**: Simple JSON storage
- ✅ **No Circular Imports**: Clean architecture
- ✅ **Fast**: Direct file operations

### **Data Migration**
- **Old Data**: Preserved in database (if exists)
- **New Data**: Stored in `dhan_credentials.json`
- **Compatibility**: API endpoints maintained
- **Rollback**: Easy to revert if needed

---

## 🎯 **IMPLEMENTATION STATUS**

### **✅ Completed Features**
- [x] Simple file-based credential storage
- [x] Dual authentication mode support
- [x] Mode switching functionality
- [x] RESTful API endpoints
- [x] Error handling and validation
- [x] No circular import issues

### **🔧 Technical Details**
- **Backend**: FastAPI with Pydantic models
- **Storage**: JSON file with atomic operations
- **Security**: Input validation and sanitization
- **Performance**: Fast file I/O operations
- **Reliability**: Error recovery mechanisms

---

## 📞 **SUPPORT**

For any issues with the credential system:
1. Check the API documentation at `/docs`
2. Verify file permissions for `dhan_credentials.json`
3. Ensure proper JSON format
4. Contact development team for assistance

---

**Last Updated**: January 31, 2026  
**Next Review**: As needed for feature updates
