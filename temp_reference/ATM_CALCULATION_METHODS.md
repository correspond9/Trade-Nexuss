# 🎯 ATM CALCULATION METHODS - OFFICIAL DOCUMENTATION
**Date**: 2026-01-31T06:19:00Z
**Status**: ✅ FINAL - DO NOT MODIFY
**Reference**: @[public/Prompts/8.Final_prompt_for ATM Calculations.txt]

---

## 📊 **TWO DISTINCT ATM CALCULATION METHODS**

### **🔧 METHOD 1: LTP-BASED CALCULATION (PRIMARY)**
**Used For**: All general option chain operations, instrument subscriptions, market data

**Formula**: 
```
ATM = round(LTP / strike_interval) * strike_interval
```

**Examples**:
- NIFTY LTP 25175 → interval 50 → ATM = 25200
- BANKNIFTY LTP 48610 → interval 100 → ATM = 48600

**Implementation Locations**:
- ✅ `instrument_subscription_service.py` (Line 623)
- ✅ `option_chain_service.py` (Line 337)
- ✅ `market.py` (Line 275)
- ✅ All other general market data operations

**Purpose**: 
- Generate strike ranges for subscriptions
- General option chain calculations
- Market data processing
- Instrument universe generation

---

### **🎯 METHOD 2: LOWEST PREMIUM METHOD (STRADDLE-SPECIFIC)**
**Used For**: **ONLY** the Straddle tab functionality

**Formula**:
```
ATM = strike_with_lowest_straddle_premium
```

**Implementation Location**:
- ✅ `option_chain_v2.py` (Line 127) - `/api/v1/option-chain-v2/atm/{underlying}/{expiry}`

**Purpose**:
- **Highlighting**: Center strike in straddle display
- **Dynamic ATM**: Changes based on market premium movements
- **Strike Range**: Fetch 12 strikes each side (total 25 strikes)
- **Straddle Tab Only**: Exclusive to straddle functionality

**Behavior**:
- ATM strike changes dynamically as premiums fluctuate
- Always shows the strike with minimum combined CE+PE premium
- Provides 12 strikes above and below the identified ATM
- Total of 25 strikes for straddle analysis

---

## 🚫 **STRICT SEPARATION RULES**

### **✅ LOWEST PREMIUM METHOD - ALLOWED ONLY IN:**
- Straddle tab display
- `/api/v1/option-chain-v2/atm/{underlying}/{expiry}` endpoint
- Straddle-specific UI components
- Dynamic straddle analysis

### **❌ LOWEST PREMIUM METHOD - NOT ALLOWED IN:**
- General option chain operations
- Instrument subscription logic
- Market data processing
- Strike range generation for subscriptions
- Any other functionality outside straddle tab

### **✅ LTP-BASED METHOD - USED IN:**
- All general market operations
- Instrument subscriptions
- Option chain generation
- Strike range calculations
- Market data processing

### **❌ LTP-BASED METHOD - NOT USED IN:**
- Straddle tab center strike identification
- Dynamic straddle premium analysis

---

## 🎯 **TECHNICAL IMPLEMENTATION**

### **Straddle Tab Flow**:
1. **Frontend Request**: `/api/v1/option-chain-v2/atm/NIFTY/2026-01-30`
2. **Backend Logic**: Find strike with lowest straddle premium
3. **Response**: ATM strike + 12 strikes above/below (total 25)
4. **UI Display**: Center highlighted as ATM, 12 strikes each side

### **General Market Flow**:
1. **Backend Logic**: `ATM = round(LTP / strike_interval) * strike_interval`
2. **Strike Generation**: Fixed ranges around calculated ATM
3. **Subscriptions**: Based on LTP-calculated ATM
4. **Market Data**: All other operations use LTP method

---

## 📋 **IMPLEMENTATION CHECKLIST**

### **✅ CORRECTLY IMPLEMENTED:**
- [x] LTP-based calculation in `instrument_subscription_service.py`
- [x] LTP-based calculation in `option_chain_service.py`
- [x] Lowest premium method in `option_chain_v2.py` for straddle tab
- [x] Strict separation between two methods

### **🔍 MAINTENANCE REQUIREMENTS:**
- [ ] Never mix the two methods
- [ ] Never use lowest premium outside straddle tab
- [ ] Always use LTP-based for general operations
- [ ] Keep straddle tab using lowest premium method
- [ ] Document any changes to this separation

---

## 🚨 **CRITICAL WARNINGS**

1. **NEVER** use lowest premium method outside straddle tab
2. **NEVER** use LTP-based method for straddle center identification
3. **ALWAYS** maintain strict separation between the two methods
4. **NEVER** modify straddle tab to use LTP-based calculation
5. **NEVER** modify general operations to use lowest premium method

---

## 📞 **CONTACT FOR CLARIFICATION**

If any confusion arises about which method to use:
1. **Straddle Tab?** → Use Lowest Premium Method
2. **Anything Else?** → Use LTP-Based Method
3. **Unsure?** → Ask for clarification before implementation

---

**🔒 This documentation is FINAL and BINDING for all future development.**

**Saved Location**: `d:\4.PROJECTS\Broking Terminal\ATM_CALCULATION_METHODS.md`

**Last Updated**: 2026-01-31T06:19:00Z
**Next Review**: Only if requirements change
