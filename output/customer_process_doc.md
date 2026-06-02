# 1. Introduction

### 1.1 Program Overview
The program `CUSTPROC` is a mainframe COBOL batch/online program designed to perform core customer business processing. It handles data ingestion, variable preparation, validation, and communicates with various backend services. It was authored by ANTIGRAVITY.

### 1.2 Objectives
The primary objectives of `CUSTPROC` are:
- Retrieve customer profile information from DB2 databases and IMS databases.
- Validate transactions and perform formatting on sensitive customer fields.
- Log status messages and transfer buffers to external message queues via IBM MQ.
- Present processed details on user screens via CICS interfaces.

### 1.3 Scope
This program serves as a processing module within the Customer Management subsystem. It manages VSAM database files, processes inbound linkage section parameters, and performs data staging.

### 1.4 Assumptions and Constraints
- **Assumptions**: DB2 tables and IMS databases are online and accessible. CICS transaction manager and MQ series queues are operational.
- **Constraints**: Fixed-length processing windows, strictly typed variable schemas defined in copybooks, and compliance with mainframe memory layouts.

# 2. Database Details

## 2.1 DB2 Tables
The program queries or updates the following database tables:
- `DB2_CUST_TABLE`

## 2.2 IMS Segments
The program interfaces with IMS databases using the following segment search arguments (SSAs) or IO areas:
- Segment/IO Area: `CUST-SEG-IO-AREA`
- Segment/IO Area: `CUST-SEG-SSA`

## 2.3 IDMS Records
The program retrieves or modifies the following IDMS database records:
- Record: `CUST-RECORD-IDMS`

## 2.4 External Module and Copybook Dependencies
The program relies on the following external files, copybooks, subprograms, and mapsets:

### Copybooks (Data Structures)
- `CUSTOMER-RECORD`: Imported layout definition defining record formats.
- `DB-STATUS`: Imported layout definition defining record formats.

- No external program calls detected in procedure division.

### VSAM and File Resources
- `CUSTFILE` (Dataset/DD: `VSAM-CUST-FILE`): Logical file reference for storage/transfer operations.

### CICS Screens and Maps
- Map `CUSTMAP`: User interface screen layout.
- Mapset `CUSTSET`: Set of screen map configurations.

# 3. System Architecture

## 3.1 Component Diagram
The diagram below outlines the external interfaces and components interfacing with the `CUSTPROC` program:

![Component Diagram](file:///C:/GlideCloud Internship Stuff/cobol_parser_analyzer/output/single_component_diagram.png)

## 3.2 Control Flow Diagram
The diagram below shows the control flow and call relationships between the internal paragraphs of the program:

![Control Flow Diagram](file:///C:/GlideCloud Internship Stuff/cobol_parser_analyzer/output/single_control_flow_diagram.png)

# 4. Detailed Design

## 4.1 Program Structure
### 4.1.1 Paragraph and Section Architecture
The following table details all sections and paragraphs defined in the program:

| Paragraph / Section | Start Line | End Line | Section Group | Description |
| --- | --- | --- | --- | --- |
| `PROC-ENTRY` | 42 | 53 | A000-MAIN-PROCESSING | Internal processing logic |
| `B000-INITIALIZATION` | 54 | 63 | A000-MAIN-PROCESSING | Internal processing logic |
| `C000-READ-CUSTOMER-DATA` | 64 | 89 | A000-MAIN-PROCESSING | Queries DB2, Calls IMS, Accesses VSAM files |
| `D000-PROCESS-PII-DATA` | 90 | 95 | A000-MAIN-PROCESSING | Internal processing logic |
| `E000-LOG-TO-MQ` | 96 | 107 | A000-MAIN-PROCESSING | Outputs to IBM MQ |
| `F000-SEND-CICS-MAP` | 108 | 116 | A000-MAIN-PROCESSING | Invokes CICS Maps |
| `G000-HANDLE-ERROR` | 117 | 121 | A000-MAIN-PROCESSING | Internal processing logic |
| `H000-TERMINATION` | 122 | 124 | A000-MAIN-PROCESSING | Internal processing logic |
| `X999-DEAD-PARAGRAPH` | 125 | 128 | A000-MAIN-PROCESSING | Internal processing logic |

### 4.1.2 Data Division Layout and Key Variable Structures
#### WORKING-STORAGE SECTION Variables
| Variable Name | Level | PIC Clause | Initial Value | Source Copybook |
| --- | --- | --- | --- | --- |
| `CUSTOMER-RECORD` | 1 | `N/A` | `N/A` | `CUSTOMER-RECORD` |
| `CUST-ID` | 5 | `X(10)` | `N/A` | `CUSTOMER-RECORD` |
| `CUST-NAME` | 5 | `X(30)` | `N/A` | `CUSTOMER-RECORD` |
| `CUST-SSN` | 5 | `X(9)` | `N/A` | `CUSTOMER-RECORD` |
| `CUST-CONTACT` | 5 | `N/A` | `N/A` | `CUSTOMER-RECORD` |
| `CUST-PHONE` | 10 | `X(10)` | `N/A` | `CUSTOMER-RECORD` |
| `CUST-EMAIL` | 10 | `X(40)` | `N/A` | `CUSTOMER-RECORD` |
| `CUST-ADDRESS` | 5 | `N/A` | `N/A` | `CUSTOMER-RECORD` |
| `CUST-STREET` | 10 | `X(30)` | `N/A` | `CUSTOMER-RECORD` |
| `CUST-CITY` | 10 | `X(20)` | `N/A` | `CUSTOMER-RECORD` |
| `CUST-STATE` | 10 | `X(2)` | `N/A` | `CUSTOMER-RECORD` |
| `CUST-ZIP` | 10 | `X(5)` | `N/A` | `CUSTOMER-RECORD` |
| `CUST-ACCOUNT-NUM` | 5 | `X(12)` | `N/A` | `CUSTOMER-RECORD` |
| `CUST-BALANCE` | 5 | `S9(7)V99` | `N/A` | `CUSTOMER-RECORD` |
| `DB-STATUS` | 1 | `N/A` | `N/A` | `DB-STATUS` |
| `SQL-CODE-VAL` | 5 | `S9(9)` | `N/A` | `DB-STATUS` |
| `IMS-STATUS-CODE` | 5 | `X(2)` | `N/A` | `DB-STATUS` |
| `IDMS-ERR-CODE` | 5 | `X(4)` | `N/A` | `DB-STATUS` |
| `MQ-REASON-CODE` | 5 | `S9(9)` | `N/A` | `DB-STATUS` |
| `VSAM-FEEDBACK` | 5 | `X(2)` | `N/A` | `DB-STATUS` |
| `ERR-MSG` | 5 | `X(80)` | `N/A` | `DB-STATUS` |
| `WS-VARIABLES` | 1 | `N/A` | `N/A` | `Local` |
| `VSAM-STATUS` | 5 | `X(2)` | `N/A` | `Local` |
| `WS-PII-LOG-SSN` | 5 | `X(9)` | `N/A` | `Local` |
| `WS-MQ-MSG-BUFF` | 5 | `X(200)` | `N/A` | `Local` |
| `WS-SYS-DATE` | 5 | `X(8)` | `N/A` | `Local` |
| `IMS-CONSTANTS` | 1 | `N/A` | `N/A` | `Local` |
| `IMS-GU` | 5 | `X(4)` | `GU` | `Local` |
| `IMS-GN` | 5 | `X(4)` | `GN` | `Local` |

#### LINKAGE SECTION Variables (Input/Output Parameters)
| Variable Name | Level | PIC Clause | Source Copybook |
| --- | --- | --- | --- |
| `LK-INPUT-DATA` | 1 | `X(50)` | `Local` |

## 4.2 Algorithms
### 4.2.1 Overall Program Logic
The `CUSTPROC` program logic coordinates execution through distinct structural stages:
1. **Initialization**: The program prepares internal processing variables, initializes database cursor areas, and opens any referenced files or screen resources. It establishes base variables needed for loop processing.
2. **Main Processing Loop**: It reads input data sequentially (either via files or cursor fetches). For each item: it performs validations, retrieves related entity details from DB2 tables/IMS databases, propagates key data elements, and handles business updates or queuing operations.
3. **Termination and Shutdown**: Once input limits or end-of-file indicators are hit, the program cleanly terminates. It closes all active database cursors, releases VSAM files, executes final output prints/displays, and runs GOBACK/STOP RUN.

### 4.2.2 Key Algorithmic Details
- **Branching & Decisions**: The control path is heavily governed by conditional branching checking SQL execution feedback (SQLCODE) or VSAM file statuses. For example, successful reads proceed to data manipulation while failures trigger specific error recovery paragraphs.
- **Data Translation & Formatting**: Variables parsed from database sources are mapped to intermediate fields, formatted according to PIC specifications, and stored in target records for output (e.g. IBM MQ buffers or CICS map displays).
- **Fault Tolerance**: The logic implements dedicated paragraph paths for error capture, logging, and application recovery to prevent uncontrolled program abends.

## 4.3 Input/Output Specifications
The primary files and UI interfaces are defined below:

| Interface Channel | Technical Resource / DD Name | Description | Data Format | Direction |
| --- | --- | --- | --- | --- |
| VSAM File | `VSAM-CUST-FILE` | File variable `CUSTFILE` | Index Keyed Record | In/Out |
| IBM MQ | `MQ Series Queue` | Buffer message transmission | MQ Descriptor Block | Output |
| CICS Terminal | `CUSTMAP Screen` | Terminal user-interface map | Screen Layout Fields | Output |

## 4.4 DB2 Database Details
- **Paragraph `C000-READ-CUSTOMER-DATA`**: Executes `SELECT` on table `DB2_CUST_TABLE`. SQL Query:
  ```sql
  SELECT CUST_NAME, CUST_SSN, CUST_ACCOUNT_NUM
        INTO :CUST-NAME, :CUST-SSN, :CUST-ACCOUNT-NUM
        FROM DB2_CUST_TABLE
        WHERE CUST_ID = :CUST-ID
  ```

## 4.5 IMS Database Details
- **Paragraph `C000-READ-CUSTOMER-DATA`**: Invokes IMS command `GU` using parameters: `CUST-SEG-IO-AREA`, `CUST-SEG-SSA`

## 4.6 IDMS Database Details
- **Paragraph `C000-READ-CUSTOMER-DATA`**: Executes IDMS `OBTAIN` on record `CUST-RECORD-IDMS` within Area `CUST-AREA-IDMS`

## 4.7 Called Sub-routine/Program Details/Copybook
**Included Copybooks:**
- `CUSTOMER-RECORD`: Pulled into DATA DIVISION structures.
- `DB-STATUS`: Pulled into DATA DIVISION structures.

## 4.8 VSAM File Details
- **Paragraph `C000-READ-CUSTOMER-DATA`**: Performs `READ` on file variable `CUSTFILE` (Dataset/DD: `VSAM-CUST-FILE`)

## 4.9 IBM MQ Details
- **Paragraph `E000-LOG-TO-MQ`**: Executes IBM MQ function `MQPUT` with argument trace: `MQ-HCONN`, `MQ-HOBJ`, `MQ-MD`, `MQ-PMO`, `WS-MQ-MSG-BUFF`, `MQ-REASON-CODE`

## 4.10 CICS Details
- **Paragraph `F000-SEND-CICS-MAP`**: Runs `SEND MAP('CUSTMAP')` on map `CUSTMAP` (Mapset: `CUSTSET`). CICS details: `SEND MAP('CUSTMAP') MAPSET('CUSTSET') FROM(CUSTOMER-RECORD) ERASE`

## 4.11 Error Handling
- **Error Paragraph `G000-HANDLE-ERROR`**: Handles faults by logging or displaying errors. Code snippet:
  ```cobol
      DISPLAY 'ERROR OCCURRED. SQL-CODE=' SQL-CODE-VAL
    DISPLAY 'VSAM-STATUS=' VSAM-STATUS
    MOVE 'AN ERROR WAS ENCOUNTERED IN PROCESSING' TO ERR-MSG.

  ```

# 5. Interface Design

### 5.1 External Interfaces
The program exposes external interfaces through data transfer protocols and database links:
- **DB2 Database Link**: Communicates using embedded SQL over the mainframe SQL engine.
- **VSAM File Access**: Interfaces with datasets on disk through the operating system's Virtual Storage Access Method.
- **IBM MQ Queue Manager**: Exchanges messages asynchronously with downstream applications.

### 5.2 User Interface
The user interface is a CICS character-mode screen designed using CUSTMAP. It displays formatted customer fields, allows basic input parameters, and outputs system alerts on completion.

# 6. Testing Strategy

### 6.1 Test Plan
To verify correct behavior, the test plan includes:
1. **Unit Testing**: Stub out external database queries. Verify that paragraphs are performed in the correct sequence.
2. **DB2 Integration Testing**: Verify database query syntax and error codes (such as SQLCODE = -811, 0, or 100).
3. **VSAM File Verification**: Validate VSAM file read operations and handling of 'record not found' exceptions.
4. **CICS Screen Verification**: Test terminal displays through CICS transaction simulators.

### 6.2 Testing Environment
The test environment requires standard IBM z/OS development environments. This includes:
- IBM Developer for z/OS (IDz) or similar IDE.
- IBM MQ simulator or test queue managers.
- CICS testing region equipped with the compiled map set (`CUSTSET`).
- DB2 test tables mirroring production schemas with masked/synthesized test data.

# 7. Performance Considerations

### 7.1 Performance Analysis
The program's performance is dominated by external input/output operations:
- **DB2 Access**: SQL query execution uses CPU MIPS. Lack of indexes can trigger table scans.
- **IMS & VSAM Reads**: Accessing files/segments causes disk I/O wait states.
- **MQ Messaging**: Network/queue synchronization calls introduce thread-blocking latencies.

### 7.2 Optimization Recommendations
- Ensure the `DB2_CUST_TABLE` has a primary index on `CUST_ID` to avoid costly full table scans.
- Optimize VSAM buffer sizes (BUFND/BUFNI) in JCL definitions to cache file index nodes.
- Replace repetitive queries with bulk SELECT cursors where feasible.
- Ensure MQ calls are performed asynchronously (`MQPMO-NO-SYNCPOINT`) if transactional guarantees are not required.

# 8. Dead Code Analysis

The control flow reachability analysis has identified **1** unreachable paragraphs:

- `X999-DEAD-PARAGRAPH`

**Risk/Impact:** These paragraphs represent dead code. Having dead code increases maintenance overhead, confuses developer comprehension, and can indicate orphaned logical blocks or legacy routines that are no longer in use. It is recommended to safely comment out or delete these blocks after verifying no dynamic/computed performance routes (e.g. dynamic CALLs) target them.

# 9. Security Risk Assessment

## 9.1 PII (Personally Identifiable Information) Analysis

### 9.1.1 PII Data Elements Identification
The following variables contain or handle PII based on name pattern rules:

| Variable Name | Level | PIC Clause | PII Classification Reason |
| --- | --- | --- | --- |
| `CUST-NAME` | 5 | `X(30)` | Declared definition (from copybook CUSTOMER-RECORD) |
| `CUST-EMAIL` | 10 | `X(40)` | Declared definition (from copybook CUSTOMER-RECORD) |
| `CUST-ADDRESS` | 5 | `N/A` | Declared definition (from copybook CUSTOMER-RECORD) |
| `CUST-ACCOUNT-NUM` | 5 | `X(12)` | Declared definition (from copybook CUSTOMER-RECORD) |
| `CUST-PHONE` | 10 | `X(10)` | Declared definition (from copybook CUSTOMER-RECORD) |
| `WS-PII-LOG-SSN` | 5 | `X(9)` | Declared definition |
| `WS-MQ-MSG-BUFF` | 5 | `X(200)` | Tainted in D000-PROCESS-PII-DATA from CUST-ACCOUNT-NUM |
| `CUST-SSN` | 5 | `X(9)` | Declared definition (from copybook CUSTOMER-RECORD) |

### 9.1.2 PII Data Flow Analysis
Static taint tracking shows the propagation of PII data across variable reassignments:

| Step | Source Variable | Destination Variable | Code Location (Paragraph) | Instruction Statement |
| --- | --- | --- | --- | --- |
| 1 | `CUST-ACCOUNT-NUM` | `WS-MQ-MSG-BUFF` | `D000-PROCESS-PII-DATA` | `MOVE CUST-ACCOUNT-NUM TO WS-MQ-MSG-BUFF` |

### 9.1.3 PII Security Analysis
The analysis revealed critical exposures regarding Personally Identifiable Information (PII):
- **Unencrypted Transmission**: PII data elements like `CUST-ACCOUNT-NUM` are copied to the MQ buffer and sent over queues without field-level encryption.
- **Log Exposure Risk**: Staging PII records in general logging blocks (e.g. `WS-PII-LOG-SSN` or displays) can leak sensitive data into system spools (SDSF) where unauthorized users can view them.
- **Mitigation Recommendations**: Use IBM InfoSphere Guardium or DFSMS/RACF file encryption. Mask fields (e.g. XXX-XX-1234) before writing to message buffers or system logs.

### 9.1.4 PII Inventory Summary
A summary of PII egress points and risk classifications:

| Egress Channel | Data Element | Risk Level | Mitigation Strategy |
| --- | --- | --- | --- |
| DB2 SQL (Table: DB2_CUST_TABLE (SELECT)) | `CUST-NAME` | **MEDIUM** | Apply field masking |
| DB2 SQL (Table: DB2_CUST_TABLE (SELECT)) | `CUST-ACCOUNT-NUM` | **MEDIUM** | Apply field masking |
| DB2 SQL (Table: DB2_CUST_TABLE (SELECT)) | `CUST-SSN` | **MEDIUM** | Apply field masking |
| IBM MQ (MQ queue via MQPUT) | `WS-MQ-MSG-BUFF` | **HIGH** | Encrypt before transmission |

# 10. Appendices

## 10.1 Glossary

| Term | Definition |
| --- | --- |
| **Copybook** | A reusable source file that contains data structures or declarations in COBOL. |
| **DB2** | IBM's relational database management system for z/OS mainframe environments. |
| **IMS** | Information Management System, a database and transaction management system. |
| **VSAM** | Virtual Storage Access Method, a high-performance file management system on IBM mainframes. |
| **IBM MQ** | Message queue middleware facilitating secure, asynchronous system-to-system communications. |
| **CICS** | Customer Information Control System, an online transaction manager for mainframe systems. |
| **PII** | Personally Identifiable Information; sensitive data elements that can identify individuals. |
| **Dead Code** | Program blocks or paragraphs that cannot be reached or executed under any conditions. |

## 10.2 Data Structures

#### Copybook `CUSTOMER-RECORD` Layout
```cobol
  01  CUSTOMER-RECORD.
  05  CUST-ID PIC X(10).
  05  CUST-NAME PIC X(30).
  05  CUST-SSN PIC X(9).
  05  CUST-CONTACT.
  10  CUST-PHONE PIC X(10).
  10  CUST-EMAIL PIC X(40).
  05  CUST-ADDRESS.
  10  CUST-STREET PIC X(30).
  10  CUST-CITY PIC X(20).
  10  CUST-STATE PIC X(2).
  10  CUST-ZIP PIC X(5).
  05  CUST-ACCOUNT-NUM PIC X(12).
  05  CUST-BALANCE PIC S9(7)V99.
```
#### Copybook `DB-STATUS` Layout
```cobol
  01  DB-STATUS.
  05  SQL-CODE-VAL PIC S9(9).
  05  IMS-STATUS-CODE PIC X(2).
  05  IDMS-ERR-CODE PIC X(4).
  05  MQ-REASON-CODE PIC S9(9).
  05  VSAM-FEEDBACK PIC X(2).
  05  ERR-MSG PIC X(80).
```

## 10.3 References

- IBM Enterprise COBOL for z/OS Language Reference
- DB2 SQL Reference Guide
- CICS Application Programming Guide
- IBM MQ Application Programming Reference