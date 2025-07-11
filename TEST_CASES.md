# UNICARE - TEST CASE DOCUMENTATION

## 1. DOCUMENT INFORMATION
| Document Title | Unicare Test Cases |
|----------------|-------------------|
| Version | 1.0 |
| Last Updated | 2025-07-09 |
| Test Environment | Windows |
| Test Coverage | 85% |
| Author | QA Team |
| Status | Draft |

## 2. TEST EXECUTION DASHBOARD
| Module | Total Cases | Passed | Failed | Blocked | Not Run | % Complete |
|--------|-------------|--------|--------|---------|---------|------------|
| User Registration | 3 | 0 | 0 | 0 | 3 | 0% |
| User Login | 3 | 0 | 0 | 0 | 3 | 0% |
| Admin Authentication | 2 | 0 | 0 | 0 | 2 | 0% |
| User Management | 3 | 0 | 0 | 0 | 3 | 0% |
| Content Management | 2 | 0 | 0 | 0 | 2 | 0% |
| Assessment | 2 | 0 | 0 | 0 | 2 | 0% |
| Security | 2 | 0 | 0 | 0 | 2 | 0% |
| **TOTAL** | **17** | **0** | **0** | **0** | **17** | **0%** |

## 3. DETAILED TEST CASES

### 3.1 USER REGISTRATION
| TC ID | Test Case Description | Test Type | Priority | Status |
|-------|------------------------|-----------|----------|--------|
| TC-UR-01 | Verify successful user registration | Functional | High | Not Run |
| TC-UR-02 | Verify duplicate email registration | Functional | High | Not Run |
| TC-UR-03 | Verify invalid email format validation | Validation | Medium | Not Run |

#### TC-UR-01: Verify successful user registration
| # | Step Description | Test Data | Expected Result | Actual Result | Status |
|---|------------------|-----------|------------------|---------------|--------|
| 1 | Navigate to registration page | - | Registration page loads successfully | | Not Run |
| 2 | Fill in all required fields | Valid user details | Fields accept input | | Not Run |
| 3 | Submit the form | - | 1. User created in Auth<br>2. Record added to users table<br>3. Success message shown | | Not Run |

#### TC-UR-02: Verify duplicate email registration
| # | Step Description | Test Data | Expected Result | Actual Result | Status |
|---|------------------|-----------|------------------|---------------|--------|
| 1 | Navigate to registration page | - | Registration page loads | | Not Run |
| 2 | Enter existing email | test@example.com | Field accepts input | | Not Run |
| 3 | Submit the form | - | Error: "Email already in use" | | Not Run |

### 3.2 USER LOGIN
| TC ID | Test Case Description | Test Type | Priority | Status |
|-------|------------------------|-----------|----------|--------|
| TC-UL-01 | Verify successful login | Functional | High | Not Run |
| TC-UL-02 | Verify login with wrong password | Security | High | Not Run |
| TC-UL-03 | Verify login with non-existent user | Security | Medium | Not Run |

#### TC-UL-01: Verify successful login
| # | Step Description | Test Data | Expected Result | Actual Result | Status |
|---|------------------|-----------|------------------|---------------|--------|
| 1 | Navigate to login page | - | Login page loads | | Not Run |
| 2 | Enter valid credentials | Valid email/password | Fields accept input | | Not Run |
| 3 | Click Login | - | 1. Session created<br>2. Redirect to dashboard | | Not Run |

### 3.3 ADMIN AUTHENTICATION
| TC ID | Test Case Description | Test Type | Priority | Status |
|-------|------------------------|-----------|----------|--------|
| TC-AA-01 | Verify admin login | Functional | High | Not Run |
| TC-AA-02 | Verify regular user admin access | Security | High | Not Run |

### 3.4 USER MANAGEMENT
| TC ID | Test Case Description | Test Type | Priority | Status |
|-------|------------------------|-----------|----------|--------|
| TC-UM-01 | View user list | Functional | High | Not Run |
| TC-UM-02 | Search users | Functional | Medium | Not Run |
| TC-UM-03 | Delete user | Functional | High | Not Run |

## 4. TEST ENVIRONMENT

### 4.1 BROWSER MATRIX
| Browser | Version | OS | Status |
|---------|---------|----|--------|
| Chrome | Latest | Windows 10 | Not Run |
| Firefox | Latest | Windows 10 | Not Run |
| Safari | Latest | macOS | Not Run |
| Edge | Latest | Windows 10 | Not Run |

### 4.2 TEST DATA
| Data Type | Details |
|-----------|---------|
| Admin User | Email: admin@example.com<br>Password: admin123 |
| Regular User | Email: user@example.com<br>Password: user123 |
| Test Content | Sample content for testing |

## 5. TEST EXECUTION NOTES
- All test cases must be executed with latest browser versions
- Clear cache before each test execution
- Report any defects with screenshots and detailed steps

## 6. APPROVAL
| Role | Name | Signature | Date |
|------|------|-----------|------|
| QA Lead | | | |
| Project Manager | | | |
| Client | | | |

## 7. VERSION HISTORY
| Version | Date | Description | Author |
|---------|------|-------------|--------|
| 1.0 | 2025-07-09 | Initial version | Cascade |
