# 1. Introduction

# 1.1 Program Overview
The mainframe application suite is a comprehensive set of tools designed to manage and process various business critical processes for an enterprise. The suite consists of multiple interconnected components that work together to provide a robust and efficient solution.

The application suite utilizes COBOL programming language for developing and maintaining the core logic of the system, which includes data processing, reporting, and business rules management. The COBOL programs are compiled into executable code that runs on the z/OS operating system.

JCL (Job Control Language) jobs are used to manage the execution of these COBOL programs. JCL jobs are used to schedule, monitor, and control the execution of COBOL programs, as well as other tasks such as data transfers and reporting.

The application suite also leverages BMS (Business Management System) mapsets to define the mapping between the COBOL program variables and the database records. This enables the system to accurately retrieve and manipulate data from the underlying database.

Assembler modules are used to optimize performance-critical sections of code, where the z/OS operating system provides a low-level API for direct memory manipulation. These optimized modules are then integrated with the rest of the COBOL codebase.

The application suite is designed to be highly configurable and extensible, allowing users to tailor the system to meet their specific business needs. The integration of multiple technologies and frameworks enables the development of complex systems that can handle a wide range of tasks, from data processing and reporting to user interfaces and business rules management.

# 1.2 Objectives
The primary objectives of this application suite are:

*   To provide a scalable and flexible solution for managing business critical processes.
*   To enable real-time data processing and reporting capabilities.
*   To ensure data integrity and security through robust data validation and verification mechanisms.
*   To support multi-user and multi-process environments, with efficient resource utilization and low overhead.

These objectives are achieved by integrating multiple technologies and frameworks, including COBOL programming language, JCL jobs, BMS mapsets, and Assembler modules. The system is designed to be highly configurable and extensible, allowing users to tailor the system to meet their specific business needs.

# 1.3 Scope
The analysis scope covers the following files, copybooks, database references, and CICS maps:

*   COBOL programs:
    *   `CBACT01C`, `CBACT02C`, `CBACT03C`, etc.
*   JCL jobs:
    *   `ACCTFILE`, `CARDFILE`, `CBADMCDJ`, etc.
*   BMS mapsets:
    *   `COACTUP`, `COACTVW`, `COADM01`, etc.
*   Database references:
    *   `COBIL00C` database reference
*   CICS maps:
    *   `COMEN01` CICS map

This scope covers the majority of the application suite components, but may not include all specific details or edge cases.

# 1.4 Assumptions and Constraints
The following technical assumptions and constraints apply to this analysis:

*   z/OS operating system environment.
*   COBOL programming language version 5.2 or higher.
*   JCL jobs are executed using the `JES2` job scheduler.
*   BMS mapsets are defined using the `BMS` software development kit (SDK).
*   Database references are made to a local database named `COBIL00C`.
*   CICS maps are used for mapping between COBOL program variables and database records.

These assumptions and constraints apply to the overall analysis scope, but may not be applicable in all specific cases or environments.

---

# 2. Database Details

### 2.1 DB2 Tables
The application workspace references the following DB2 SQL tables:

- No DB2 tables referenced in the workspace.

**Relational DB2 Access Analysis:**
Mainframe COBOL programs execute embedded SQL statements (within `EXEC SQL ... END-EXEC` blocks) to query and update these DB2 tables. These queries are processed by the DB2 precompiler, which replaces the SQL code with call statements to the DB2 database engine. The primary relational tables, such as credit card registries or customer profile tables, are accessed via index keys to maintain low-latency response times during CICS online executions. Host variables defined in the COBOL Working-Storage Section are mapped to table columns during SELECT INTO, INSERT, and UPDATE operations. The system relies on appropriate index definitions to avoid full table scans that would consume high CPU MIPS in batch jobs like `INTCALC` or `POSTTRAN`.

### 2.2 IMS Segments
The application workspace communicates with IMS hierarchal segments as detailed below:

- No IMS segments referenced in the workspace.

**Hierarchical IMS Access Analysis:**
IMS (Information Management System) database interactions are performed using DL/I call statements by executing the interface module `CBLTDLI` using parameters: Function code (such as `GU` for Get Unique, `GN` for Get Next, `REPL` for Replace), Program Communication Block (PCB), Segment Search Arguments (SSA), and I/O area variables. SSAs specify the path through the hierarchical structure to locate the target segment. Unlike SQL's set-based processing, DL/I requires navigational cursor-based access where the program iterates down a parent-child path, from parent root segments to dependent child segments. This model is highly optimized for sequential tree-based data access patterns but demands careful programming to handle boundary/status code check conditions (such as `GB` for end of database, or `GE` for segment not found).

### 2.3 IDMS Records
The application workspace contains references to these network database IDMS records:

- **`ASSOCIATED`**: Record structure accessed in program(s) `COACTUPC`, `COACTVWC`.
- **`CARDS`**: Record structure accessed in program(s) `COACTUPC`, `COCRDSLC`, `COCRDUPC`.
- **`THIS`**: Record structure accessed in program(s) `COACTUPC`, `COACTVWC`, `COCRDSLC`, `COCRDUPC`.
- **`TO`**: Record structure accessed in program(s) `COUSR02C`.

**Network IDMS Access Analysis:**
IDMS (Integrated Database Management System) uses a network database model based on the CODASYL standard. It represents data structures as a network of Records organized into Sets (where a set represents a one-to-many relationship between an Owner record and Member records). Programs navigate the database by running commands like `OBTAIN FIRST/NEXT`, `FIND`, `STORE`, and `MODIFY` to traverse owner-member set pointers. Transactions must bind to specific logical database Areas and run within DB record lock scopes to prevent concurrency deadlocks. While DB2 utilizes logical relational links and IMS relies on physical hierarchies, IDMS provides physical pointer chains (next, prior, and owner pointers) embedded in the record headers. This delivers exceptionally fast retrieval times for complex, pre-defined relationships but introduces structural rigidity, as changing the schema requires restructuring the physical pointer links.

---

# 3. System Architecture

## 3.1 Component Diagram
Below is the component diagram highlighting how Job runs trigger various programs, along with database SQL queries and dataset interactions:

![Component Diagram](file:///C:/GlideCloud Internship Stuff/cobol_parser_analyzer/output/component_diagram.png)

## 3.2 Control Flow Diagram
Below is the control flow mapping CICS transactional entry codes to target program routines and CICS BMS maps:

![Control Flow Diagram](file:///C:/GlideCloud Internship Stuff/cobol_parser_analyzer/output/control_flow_diagram.png)

## 3.3 Architectural Narrative & Execution Flow

The application workspace is structured around a classic two-tier mainframe architectural pattern, splitting operations into high-volume offline batch streams (managed by JCL schedules) and interactive real-time online terminal services (hosted by CICS transaction processors):

### 3.3.1 Batch Job Stream Processing
The batch execution model leverages Job Control Language (JCL) scripts to configure step sequences, set up system boundaries, allocate physical datasets, and execute binary load modules. Batch streams perform high-throughput tasks like credit card data loading, daily transaction ingest updates, account interest fee calculations, and database statement exports. JCL streams sequence steps to ensure data integrity: a preprocessing step typically reads flat files from tape or sequential datasets, executes sorting routines via DFSORT control cards to align keys, and stages intermediate VSAM files. Subsequent steps execute COBOL programs that open these VSAM files, execute business logic (such as balance accrual), modify DB2 tables, and output formatted summaries. For example, job streams like `CARDFILE` and `ACCTFILE` execute program chains sequentially, staging outputs using JCL DISP parameters (`DISP=(NEW,CATLG,DELETE)`) to manage lifecycle stages across steps.

### 3.3.2 CICS Real-Time Online Transactions
Online operations are triggered by character-coded terminal inputs defined in CICS System Definitions (CSD). When an operator types a transaction ID (like `COSG` or `COAC`), the CICS listener maps the transaction ID to a target COBOL control program (such as `COSGN00C` or `COACTVWC`). CICS coordinates the execution within a logical unit of work (LUW). The program interacts with the operator by sending and receiving BMS (Basic Mapping Support) map layouts. These maps define text fields, input markers, color schemes, and position offsets for 3270 character terminals. Online programs use CICS command instructions (`EXEC CICS SEND MAP`, `EXEC CICS RECEIVE MAP`) to communicate with the user, validate user credentials, query VSAM file records using primary indexes to ensure sub-second search latencies, and commit changes back to the database. Transactions route to menu hubs like `COMEN01C` which manage navigation paths based on function keys (PF keys) typed by terminal users, ensuring decoupled but clean flow control.

### 3.3.3 Subroutine Hierarchy and Decoupling
To maximize reuse, programs call utility subroutines synchronously using standard linkage section conventions (`CALL 'PROGRAM' USING ...`). Common utilities include date formatting routines (`CSUTLDTC`) and wait intervals helper subroutines (`COBSWAIT` invoking Assembler module `MVSWAIT`). By decoupling core transaction logic from helper subroutines, the application retains clean modular boundaries, making it easier to verify changes without recompiling the entire suite.

---

# 4. Detailed Design

## 4.1 Program Structure
The table below inventories all files parsed in the workspace including code sizes, copybooks, calls, and external accesses:

| Component Name | File Type | Code Size (Lines) | Copybooks Used | Calls Made | Description / External References |
| --- | --- | --- | --- | --- | --- |
| `ACCTFILE` | JCL Script | 3 steps | None | Execs: `IDCAMS`, `IDCAMS`, `IDCAMS` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `CARDFILE` | JCL Script | 8 steps | None | Execs: `SDSF`, `IDCAMS`, `IDCAMS`, `IDCAMS`, `IDCAMS`, `IDCAMS`, `IDCAMS`, `SDSF` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `CBADMCDJ` | JCL Script | 1 steps | None | Execs: `DFHCSDUP` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `CBEXPORT` | JCL Script | 2 steps | None | Execs: `IDCAMS`, `CBEXPORT` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `CBIMPORT` | JCL Script | 1 steps | None | Execs: `CBIMPORT` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `CLOSEFIL` | JCL Script | 1 steps | None | Execs: `SDSF` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `COMBTRAN` | JCL Script | 2 steps | None | Execs: `SORT`, `IDCAMS` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `CREASTMT` | JCL Script | 5 steps | None | Execs: `IDCAMS`, `SORT`, `IDCAMS`, `IEFBR14`, `CBSTM03A` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `CUSTFILE` | JCL Script | 5 steps | None | Execs: `SDSF`, `IDCAMS`, `IDCAMS`, `IDCAMS`, `SDSF` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `DALYREJS` | JCL Script | 1 steps | None | Execs: `IDCAMS` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `DEFCUST` | JCL Script | 2 steps | None | Execs: `IDCAMS`, `IDCAMS` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `DEFGDGB` | JCL Script | 1 steps | None | Execs: `IDCAMS` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `DEFGDGD` | JCL Script | 6 steps | None | Execs: `IDCAMS`, `IEBGENER`, `IDCAMS`, `IEBGENER`, `IDCAMS`, `IEBGENER` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `DISCGRP` | JCL Script | 3 steps | None | Execs: `IDCAMS`, `IDCAMS`, `IDCAMS` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `DUSRSECJ` | JCL Script | 4 steps | None | Execs: `IEFBR14`, `IEBGENER`, `IDCAMS`, `IDCAMS` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `ESDSRRDS` | JCL Script | 6 steps | None | Execs: `IEFBR14`, `IEBGENER`, `IDCAMS`, `IDCAMS`, `IDCAMS`, `IDCAMS` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `FTPJCLS` | JCL Script | 1 steps | None | Execs: `FTP` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `INTCALC` | JCL Script | 1 steps | None | Execs: `CBACT04C` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `INTRDRJ1` | JCL Script | 2 steps | None | Execs: `IDCAMS`, `IEBGENER` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `INTRDRJ2` | JCL Script | 1 steps | None | Execs: `IDCAMS` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `OPENFIL` | JCL Script | 1 steps | None | Execs: `SDSF` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `POSTTRAN` | JCL Script | 1 steps | None | Execs: `CBTRN02C` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `PRTCATBL` | JCL Script | 3 steps | None | Execs: `IEFBR14`, `REPROC`, `SORT` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `READACCT` | JCL Script | 2 steps | None | Execs: `IEFBR14`, `CBACT01C` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `READCARD` | JCL Script | 1 steps | None | Execs: `CBACT02C` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `READCUST` | JCL Script | 1 steps | None | Execs: `CBCUS01C` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `READXREF` | JCL Script | 1 steps | None | Execs: `CBACT03C` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `REPTFILE` | JCL Script | 1 steps | None | Execs: `IDCAMS` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `TCATBALF` | JCL Script | 3 steps | None | Execs: `IDCAMS`, `IDCAMS`, `IDCAMS` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `TRANBKP` | JCL Script | 3 steps | None | Execs: `REPROC`, `IDCAMS`, `IDCAMS` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `TRANCATG` | JCL Script | 3 steps | None | Execs: `IDCAMS`, `IDCAMS`, `IDCAMS` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `TRANFILE` | JCL Script | 8 steps | None | Execs: `SDSF`, `IDCAMS`, `IDCAMS`, `IDCAMS`, `IDCAMS`, `IDCAMS`, `IDCAMS`, `SDSF` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `TRANIDX` | JCL Script | 3 steps | None | Execs: `IDCAMS`, `IDCAMS`, `IDCAMS` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `TRANREPT` | JCL Script | 3 steps | None | Execs: `REPROC`, `SORT`, `CBTRN03C` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `TRANTYPE` | JCL Script | 3 steps | None | Execs: `IDCAMS`, `IDCAMS`, `IDCAMS` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `TXT2PDF1` | JCL Script | 1 steps | None | Execs: `IKJEFT1B` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `WAITSTEP` | JCL Script | 1 steps | None | Execs: `COBSWAIT` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `XREFFILE` | JCL Script | 6 steps | None | Execs: `IDCAMS`, `IDCAMS`, `IDCAMS`, `IDCAMS`, `IDCAMS`, `IDCAMS` | Batch orchestration stream. Modernize as a Java/Spring Batch configuration or AWS Batch Job definition. |
| `CBACT01C` | COBOL Source | 379 lines | `CVACT01Y`, `CODATECN` | `COBDATFT`, `CEE3ABD` | Read Account File batch module. Validates account status flags and coordinates billing updates. |
| `CBACT02C` | COBOL Source | 144 lines | `CVACT02Y` | `CEE3ABD` | Read Card File batch module. Parses credit card info and updates transaction database. |
| `CBACT03C` | COBOL Source | 145 lines | `CVACT03Y` | `CEE3ABD` | Read Xref File batch module. Handles mappings of credit card numbers to customer account IDs. |
| `CBACT04C` | COBOL Source | 599 lines | `CVTRA01Y`, `CVACT03Y`, `CVTRA02Y`, `CVACT01Y`, `CVTRA05Y` | `CEE3ABD` | Interest Calculation batch module. Calculates monthly interest charges and updates account ledger balances. |
| `CBCUS01C` | COBOL Source | 145 lines | `CVCUS01Y` | `CEE3ABD` | Read Customer File batch module. Extracts details like name, address, and SSN for ingestion. |
| `CBEXPORT` | COBOL Source | 491 lines | `CVCUS01Y`, `CVACT01Y`, `CVACT03Y`, `CVTRA05Y`, `CVACT02Y`, `CVEXPORT` | `CEE3ABD` | Data Export batch utility. Backs up VSAM KSDS files into sequential data files. |
| `CBIMPORT` | COBOL Source | 413 lines | `CVCUS01Y`, `CVACT01Y`, `CVACT03Y`, `CVTRA05Y`, `CVACT02Y`, `CVEXPORT` | `CEE3ABD` | Data Import batch utility. Restores sequential backups into VSAM KSDS database files. |
| `CBSTM03A` | COBOL Source | 863 lines | `COSTM01`, `CVACT03Y`, `CUSTREC`, `CVACT01Y` | `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CEE3ABD` | Statement Generation batch processor. Compiles monthly account details and writes statement summaries. |
| `CBSTM03B` | COBOL Source | 204 lines | None | None | Statement Generation helper sub-routine. Manages PDF rendering details. |
| `CBTRN01C` | COBOL Source | 449 lines | `CVTRA06Y`, `CVCUS01Y`, `CVACT03Y`, `CVACT02Y`, `CVACT01Y`, `CVTRA05Y` | `CEE3ABD` | Daily Transaction Ingestion module. Verifies transactions against active credit cards. |
| `CBTRN02C` | COBOL Source | 672 lines | `CVTRA06Y`, `CVTRA05Y`, `CVACT03Y`, `CVACT01Y`, `CVTRA01Y` | `CEE3ABD` | Daily Transaction Posting batch module. Deducts amounts and updates card accounts balances. |
| `CBTRN03C` | COBOL Source | 596 lines | `CVTRA05Y`, `CVACT03Y`, `CVTRA03Y`, `CVTRA04Y`, `CVTRA07Y` | `CEE3ABD` | Transaction Report generator batch utility. Reports daily totals categorized by transaction types. |
| `COACTUPC` | COBOL Source | 3744 lines | `CVCRD01Y`, `CSLKPCDY`, `DFHBMSCA`, `DFHAID`, `COTTL01Y`, `COACTUP`, `CSDAT01Y`, `CSMSG01Y`, `CSMSG02Y`, `CSUSR01Y`, `CVACT01Y`, `CVACT03Y`, `CVCUS01Y`, `COCOM01Y`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSUTLDPY` | None | CICS Online Account Update screen controller. Updates customer contact profiles. |
| `COACTVWC` | COBOL Source | 811 lines | `CVCRD01Y`, `COCOM01Y`, `DFHBMSCA`, `DFHAID`, `COTTL01Y`, `COACTVW`, `CSDAT01Y`, `CSMSG01Y`, `CSMSG02Y`, `CSUSR01Y`, `CVACT01Y`, `CVACT02Y`, `CVACT03Y`, `CVCUS01Y` | None | CICS Online Account View screen controller. Searches and displays customer account summaries. |
| `COADM01C` | COBOL Source | 230 lines | `COCOM01Y`, `COADM02Y`, `COADM01`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CSUSR01Y`, `DFHAID`, `DFHBMSCA` | None | CICS Online Admin Menu screen controller. Routes to admin tools. |
| `COBIL00C` | COBOL Source | 493 lines | `COCOM01Y`, `COBIL00`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CVACT01Y`, `CVACT03Y`, `CVTRA05Y`, `DFHAID`, `DFHBMSCA` | None | CICS Online Bill Payment screen controller. Logs payments and checks balances. |
| `COBSWAIT` | COBOL Source | 19 lines | None | `MVSWAIT` | Wait utility module. Uses Assembler subroutine MVSWAIT to pause step executions. |
| `COCRDLIC` | COBOL Source | 1256 lines | `CVCRD01Y`, `COCOM01Y`, `DFHBMSCA`, `DFHAID`, `COTTL01Y`, `COCRDLI`, `CSDAT01Y`, `CSMSG01Y`, `CSUSR01Y`, `CVACT02Y` | None | CICS Online Credit Card List screen controller. Lists credit card details. |
| `COCRDSLC` | COBOL Source | 757 lines | `CVCRD01Y`, `COCOM01Y`, `DFHBMSCA`, `DFHAID`, `COTTL01Y`, `COCRDSL`, `CSDAT01Y`, `CSMSG01Y`, `CSMSG02Y`, `CSUSR01Y`, `CVACT02Y`, `CVCUS01Y` | None | CICS Online Credit Card Detail screen controller. Displays credit card balances and interest rates. |
| `COCRDUPC` | COBOL Source | 1365 lines | `CVCRD01Y`, `COCOM01Y`, `DFHBMSCA`, `DFHAID`, `COTTL01Y`, `COCRDUP`, `CSDAT01Y`, `CSMSG01Y`, `CSMSG02Y`, `CSUSR01Y`, `CVACT02Y`, `CVCUS01Y` | None | CICS Online Credit Card Update screen controller. Modifies credit card limits and expiration dates. |
| `COMEN01C` | COBOL Source | 255 lines | `COCOM01Y`, `COMEN02Y`, `COMEN01`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CSUSR01Y`, `DFHAID`, `DFHBMSCA` | None | CICS Online Main Menu controller. Main navigation hub routing CICS terminal sessions. |
| `CORPT00C` | COBOL Source | 586 lines | `COCOM01Y`, `CORPT00`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CVTRA05Y`, `DFHAID`, `DFHBMSCA` | `CSUTLDTC`, `CSUTLDTC` | CICS Online Report viewer. Displays calculated statements on CICS terminal panels. |
| `COSGN00C` | COBOL Source | 211 lines | `COCOM01Y`, `COSGN00`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CSUSR01Y`, `DFHAID`, `DFHBMSCA` | None | CICS Online Signon screen controller. Performs terminal user authentication and security checks. |
| `COTRN00C` | COBOL Source | 617 lines | `COCOM01Y`, `COTRN00`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CVTRA05Y`, `DFHAID`, `DFHBMSCA` | None | CICS Online Transaction Menu screen controller. Lists transaction histories. |
| `COTRN01C` | COBOL Source | 273 lines | `COCOM01Y`, `COTRN01`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CVTRA05Y`, `DFHAID`, `DFHBMSCA` | None | CICS Online Transaction Detail screen controller. Displays details of a specific transaction. |
| `COTRN02C` | COBOL Source | 698 lines | `COCOM01Y`, `COTRN02`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CVTRA05Y`, `CVACT01Y`, `CVACT03Y`, `DFHAID`, `DFHBMSCA` | `CSUTLDTC`, `CSUTLDTC` | CICS Online Transaction Add screen controller. Enters new transaction entries. |
| `COUSR00C` | COBOL Source | 615 lines | `COCOM01Y`, `COUSR00`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CSUSR01Y`, `DFHAID`, `DFHBMSCA` | None | CICS Online User Control screen controller. Inventories CICS account profile logins. |
| `COUSR01C` | COBOL Source | 238 lines | `COCOM01Y`, `COUSR01`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CSUSR01Y`, `DFHAID`, `DFHBMSCA` | None | CICS Online User Add screen controller. Adds new user credentials. |
| `COUSR02C` | COBOL Source | 351 lines | `COCOM01Y`, `COUSR02`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CSUSR01Y`, `DFHAID`, `DFHBMSCA` | None | CICS Online User Edit screen controller. Updates user roles. |
| `COUSR03C` | COBOL Source | 296 lines | `COCOM01Y`, `COUSR03`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CSUSR01Y`, `DFHAID`, `DFHBMSCA` | None | CICS Online User Delete screen controller. Removes CICS credentials. |
| `CSUTLDTC` | COBOL Source | 128 lines | None | `CEEDAYS` | Date Converter utility sub-routine. Standardizes various date formats. |
| `COBDATFT` | Assembler Source | N/A | `COCDATFT` | None | Assembler date formatting subroutine. |
| `MVSWAIT` | Assembler Source | N/A | None | None | Assembler interval wait subroutine. |
| `COACTUP` | BMS Mapset | N/A | None | Maps: CACTUPA | CICS Screen layout mapset definitions. |
| `COACTVW` | BMS Mapset | N/A | None | Maps: CACTVWA | CICS Screen layout mapset definitions. |
| `COADM01` | BMS Mapset | N/A | None | Maps: COADM1A | CICS Screen layout mapset definitions. |
| `COBIL00` | BMS Mapset | N/A | None | Maps: COBIL0A | CICS Screen layout mapset definitions. |
| `COCRDLI` | BMS Mapset | N/A | None | Maps: CCRDLIA | CICS Screen layout mapset definitions. |
| `COCRDSL` | BMS Mapset | N/A | None | Maps: CCRDSLA | CICS Screen layout mapset definitions. |
| `COCRDUP` | BMS Mapset | N/A | None | Maps: CCRDUPA | CICS Screen layout mapset definitions. |
| `COMEN01` | BMS Mapset | N/A | None | Maps: COMEN1A | CICS Screen layout mapset definitions. |
| `CORPT00` | BMS Mapset | N/A | None | Maps: CORPT0A | CICS Screen layout mapset definitions. |
| `COSGN00` | BMS Mapset | N/A | None | Maps: COSGN0A | CICS Screen layout mapset definitions. |
| `COTRN00` | BMS Mapset | N/A | None | Maps: COTRN0A | CICS Screen layout mapset definitions. |
| `COTRN01` | BMS Mapset | N/A | None | Maps: COTRN1A | CICS Screen layout mapset definitions. |
| `COTRN02` | BMS Mapset | N/A | None | Maps: COTRN2A | CICS Screen layout mapset definitions. |
| `COUSR00` | BMS Mapset | N/A | None | Maps: COUSR0A | CICS Screen layout mapset definitions. |
| `COUSR01` | BMS Mapset | N/A | None | Maps: COUSR1A | CICS Screen layout mapset definitions. |
| `COUSR02` | BMS Mapset | N/A | None | Maps: COUSR2A | CICS Screen layout mapset definitions. |
| `COUSR03` | BMS Mapset | N/A | None | Maps: COUSR3A | CICS Screen layout mapset definitions. |

## 4.2 Algorithms

The application workspace implements batch execution flows and online transaction navigations suited for cloud migration (e.g. Spring Batch, Spring Boot, or AWS environments):

### 4.2.1 Batch Job Sequencing & Staging Details (Modernization View)
- **Card Ingestion & Cross-Reference Flow (`CARDFILE` & `ACCTFILE`)**:
  - Sequential data files are parsed and processed. Any legacy sorting utilities (DFSORT/ICETOOL steps) are modernized as DB sorting queries or local collection sort algorithms.
  - Core application program `CBACT01C` executes accounts validation. This can be migrated to a Spring Batch tasklet/chunk reader executing equivalent Java billing logic.
  - Program `CBACT02C` handles card details validation, mapping records into layout schemas, which can be migrated to relational databases.
  - Program `CBACT03C` coordinates customer card mappings, serving as an ingestion linkage layer.
- **Daily Transaction Posting & Ledger Posting (`POSTTRAN` & `INTCALC`)**:
  - Job step running `CBTRN02C` posts credit transactions to accounts. Modernized implementation routes incoming message packets directly through messaging queues (like RabbitMQ/SQS) and runs database transaction updates with transactional integrity.
  - Job step running `CBACT04C` processes interest calculation batch cycle runs. This maps to a nightly Spring Batch task using optimized SQL queries to apply interest formulas to ledger tables.
- **Statements Render & Export (`CREASTMT` & `CBEXPORT`)**:
  - Job step running `CBSTM03A` generates billing statements. The modern equivalent parses templates and saves customer statements to target folders or cloud objects (AWS S3) for web downloads.
  - Job step running `CBEXPORT` runs data backup functions, modernized as standard database export commands or cron backup tasks.

### 4.2.2 CICS Screen Navigation & Menu Layouts
- **User Authentication Menu (`COSGN00C` & `COMEN01C`)**:
  - Online terminal sequences start with signon controller `COSGN00C`. In modern web targets, this is replaced by standard authentication (e.g. OAuth2, Spring Security, or Cognito panels).
  - Menu navigation program `COMEN01C` maps to routing layers in React/Angular frontend controllers.
- **Customer Profile & Card Details Controllers (`COACTUPC`, `COACTVWC`, `COCRDLIC`, `COCRDUPC`)**:
  - Map views (CACTVWA, CACTUPA) map to corresponding web UI screens. Backend COBOL business validation logic is modernized as REST controller endpoints (Java/Spring Boot or C# .NET) handling JSON/JSON Schema structures instead of BMS characters arrays.

## 4.3 Input/Output Specifications
The table below details the dataset assignments. It maps the COBOL logical file `SELECT` statements directly to JCL `DD` names and their associated physical datasets (DSN) on disk:

| Program ID | JCL Job | JCL Step | Logical DD Name | Physical Dataset (DSN) | Allocation Disp |
| --- | --- | --- | --- | --- | --- |
| `CBEXPORT` | `CBEXPORT` | `STEP02` | `CUSTFILE` | `AWS.M2.CARDDEMO.CUSTDATA.VSAM.KSDS` | `SHR` |
| `CBEXPORT` | `CBEXPORT` | `STEP02` | `ACCTFILE` | `AWS.M2.CARDDEMO.ACCTDATA.VSAM.KSDS` | `SHR` |
| `CBEXPORT` | `CBEXPORT` | `STEP02` | `XREFFILE` | `AWS.M2.CARDDEMO.CARDXREF.VSAM.KSDS` | `SHR` |
| `CBEXPORT` | `CBEXPORT` | `STEP02` | `TRANSACT` | `AWS.M2.CARDDEMO.TRANSACT.VSAM.KSDS` | `SHR` |
| `CBEXPORT` | `CBEXPORT` | `STEP02` | `CARDFILE` | `AWS.M2.CARDDEMO.CARDDATA.VSAM.KSDS` | `SHR` |
| `CBEXPORT` | `CBEXPORT` | `STEP02` | `EXPFILE` | `AWS.M2.CARDDEMO.EXPORT.DATA` | `SHR` |
| `CBIMPORT` | `CBIMPORT` | `STEP01` | `EXPFILE` | `AWS.M2.CARDDEMO.EXPORT.DATA` | `SHR` |
| `CBIMPORT` | `CBIMPORT` | `STEP01` | `CUSTOUT` | `AWS.M2.CARDDEMO.CUSTDATA.IMPORT` | `NEW,CATLG,DELETE` |
| `CBIMPORT` | `CBIMPORT` | `STEP01` | `ACCTOUT` | `AWS.M2.CARDDEMO.ACCTDATA.IMPORT` | `NEW,CATLG,DELETE` |
| `CBIMPORT` | `CBIMPORT` | `STEP01` | `XREFOUT` | `AWS.M2.CARDDEMO.CARDXREF.IMPORT` | `NEW,CATLG,DELETE` |
| `CBIMPORT` | `CBIMPORT` | `STEP01` | `TRNXOUT` | `AWS.M2.CARDDEMO.TRANSACT.IMPORT` | `NEW,CATLG,DELETE` |
| `CBIMPORT` | `CBIMPORT` | `STEP01` | `ERROUT` | `AWS.M2.CARDDEMO.IMPORT.ERRORS` | `NEW,CATLG,DELETE` |
| `CBSTM03A` | `CREASTMT` | `STEP040` | `STMTFILE` | `SYSOUT` | `NEW,CATLG,DELETE` |
| `CBSTM03A` | `CREASTMT` | `STEP040` | `HTMLFILE` | `AWS.M2.CARDDEMO.STATEMNT.HTML` | `NEW,CATLG,DELETE` |
| `CBACT04C` | `INTCALC` | `STEP15` | `TCATBALF` | `AWS.M2.CARDDEMO.TCATBALF.VSAM.KSDS` | `SHR` |
| `CBACT04C` | `INTCALC` | `STEP15` | `XREFFILE` | `AWS.M2.CARDDEMO.CARDXREF.VSAM.KSDS` | `SHR` |
| `CBACT04C` | `INTCALC` | `STEP15` | `ACCTFILE` | `AWS.M2.CARDDEMO.ACCTDATA.VSAM.KSDS` | `SHR` |
| `CBACT04C` | `INTCALC` | `STEP15` | `DISCGRP` | `AWS.M2.CARDDEMO.DISCGRP.VSAM.KSDS` | `SHR` |
| `CBACT04C` | `INTCALC` | `STEP15` | `TRANSACT` | `AWS.M2.CARDDEMO.SYSTRAN(` | `NEW,CATLG,DELETE` |
| `CBTRN02C` | `POSTTRAN` | `STEP15` | `DALYTRAN` | `AWS.M2.CARDDEMO.DALYTRAN.PS` | `SHR` |
| `CBTRN02C` | `POSTTRAN` | `STEP15` | `TRANFILE` | `AWS.M2.CARDDEMO.TRANSACT.VSAM.KSDS` | `SHR` |
| `CBTRN02C` | `POSTTRAN` | `STEP15` | `XREFFILE` | `AWS.M2.CARDDEMO.CARDXREF.VSAM.KSDS` | `SHR` |
| `CBTRN02C` | `POSTTRAN` | `STEP15` | `DALYREJS` | `AWS.M2.CARDDEMO.DALYREJS(` | `NEW,CATLG,DELETE` |
| `CBTRN02C` | `POSTTRAN` | `STEP15` | `ACCTFILE` | `AWS.M2.CARDDEMO.ACCTDATA.VSAM.KSDS` | `SHR` |
| `CBTRN02C` | `POSTTRAN` | `STEP15` | `TCATBALF` | `AWS.M2.CARDDEMO.TCATBALF.VSAM.KSDS` | `SHR` |
| `CBACT01C` | `READACCT` | `STEP05` | `ACCTFILE` | `AWS.M2.CARDDEMO.ACCTDATA.VSAM.KSDS` | `SHR` |
| `CBACT01C` | `READACCT` | `STEP05` | `OUTFILE` | `AWS.M2.CARDDEMO.ACCTDATA.PSCOMP` | `NEW,CATLG,DELETE` |
| `CBACT01C` | `READACCT` | `STEP05` | `ARRYFILE` | `AWS.M2.CARDDEMO.ACCTDATA.ARRYPS` | `NEW,CATLG,DELETE` |
| `CBACT01C` | `READACCT` | `STEP05` | `VBRCFILE` | `AWS.M2.CARDDEMO.ACCTDATA.VBPS` | `NEW,CATLG,DELETE` |
| `CBACT02C` | `READCARD` | `STEP05` | `CARDFILE` | `AWS.M2.CARDDEMO.CARDDATA.VSAM.KSDS` | `SHR` |
| `CBCUS01C` | `READCUST` | `STEP05` | `CUSTFILE` | `AWS.M2.CARDDEMO.CUSTDATA.VSAM.KSDS` | `SHR` |
| `CBACT03C` | `READXREF` | `STEP05` | `XREFFILE` | `AWS.M2.CARDDEMO.CARDXREF.VSAM.KSDS` | `SHR` |
| `CBTRN03C` | `TRANREPT` | `STEP10R` | `TRANFILE` | `AWS.M2.CARDDEMO.TRANSACT.DALY(` | `SHR` |
| `CBTRN03C` | `TRANREPT` | `STEP10R` | `CARDXREF` | `AWS.M2.CARDDEMO.CARDXREF.VSAM.KSDS` | `SHR` |
| `CBTRN03C` | `TRANREPT` | `STEP10R` | `TRANTYPE` | `AWS.M2.CARDDEMO.TRANTYPE.VSAM.KSDS` | `SHR` |
| `CBTRN03C` | `TRANREPT` | `STEP10R` | `TRANCATG` | `AWS.M2.CARDDEMO.TRANCATG.VSAM.KSDS` | `SHR` |
| `CBTRN03C` | `TRANREPT` | `STEP10R` | `TRANREPT` | `AWS.M2.CARDDEMO.TRANREPT(` | `NEW,CATLG,DELETE` |
| `CBTRN03C` | `TRANREPT` | `STEP10R` | `DATEPARM` | `AWS.M2.CARDDEMO.DATEPARM` | `SHR` |

## 4.4 Individual Program Analysis

A granular breakdown of each COBOL program, outlining files, copybooks, database operations, and subprogram calls:

### Program: `CBACT01C`
- **Description**: Read Account File batch module. Validates account status flags and coordinates billing updates.
- **Lines of Code**: 379
- **Author**: AWS
- **Logical Files**: `ACCTFILE-FILE` (DD: `ACCTFILE`), `OUT-FILE` (DD: `OUTFILE`), `ARRY-FILE` (DD: `ARRYFILE`), `VBRC-FILE` (DD: `VBRCFILE`)
- **Copybooks Referenced**: `CVACT01Y`, `CODATECN`
- **Subprograms Called**: `COBDATFT`, `CEE3ABD`

### Program: `CBACT02C`
- **Description**: Read Card File batch module. Parses credit card info and updates transaction database.
- **Lines of Code**: 144
- **Author**: AWS
- **Logical Files**: `CARDFILE-FILE` (DD: `CARDFILE`)
- **Copybooks Referenced**: `CVACT02Y`
- **Subprograms Called**: `CEE3ABD`

### Program: `CBACT03C`
- **Description**: Read Xref File batch module. Handles mappings of credit card numbers to customer account IDs.
- **Lines of Code**: 145
- **Author**: AWS
- **Logical Files**: `XREFFILE-FILE` (DD: `XREFFILE`)
- **Copybooks Referenced**: `CVACT03Y`
- **Subprograms Called**: `CEE3ABD`

### Program: `CBACT04C`
- **Description**: Interest Calculation batch module. Calculates monthly interest charges and updates account ledger balances.
- **Lines of Code**: 599
- **Author**: AWS
- **Logical Files**: `TCATBAL-FILE` (DD: `TCATBALF`), `XREF-FILE` (DD: `XREFFILE`), `ACCOUNT-FILE` (DD: `ACCTFILE`), `DISCGRP-FILE` (DD: `DISCGRP`), `TRANSACT-FILE` (DD: `TRANSACT`)
- **Copybooks Referenced**: `CVTRA01Y`, `CVACT03Y`, `CVTRA02Y`, `CVACT01Y`, `CVTRA05Y`
- **Subprograms Called**: `CEE3ABD`

### Program: `CBCUS01C`
- **Description**: Read Customer File batch module. Extracts details like name, address, and SSN for ingestion.
- **Lines of Code**: 145
- **Author**: AWS
- **Logical Files**: `CUSTFILE-FILE` (DD: `CUSTFILE`)
- **Copybooks Referenced**: `CVCUS01Y`
- **Subprograms Called**: `CEE3ABD`

### Program: `CBEXPORT`
- **Description**: Data Export batch utility. Backs up VSAM KSDS files into sequential data files.
- **Lines of Code**: 491
- **Author**: CARDDEMO TEAM
- **Logical Files**: `CUSTOMER-INPUT` (DD: `CUSTFILE`), `ACCOUNT-INPUT` (DD: `ACCTFILE`), `XREF-INPUT` (DD: `XREFFILE`), `TRANSACTION-INPUT` (DD: `TRANSACT`), `CARD-INPUT` (DD: `CARDFILE`), `EXPORT-OUTPUT` (DD: `EXPFILE`)
- **Copybooks Referenced**: `CVCUS01Y`, `CVACT01Y`, `CVACT03Y`, `CVTRA05Y`, `CVACT02Y`, `CVEXPORT`
- **Subprograms Called**: `CEE3ABD`

### Program: `CBIMPORT`
- **Description**: Data Import batch utility. Restores sequential backups into VSAM KSDS database files.
- **Lines of Code**: 413
- **Author**: CARDDEMO TEAM
- **Logical Files**: `EXPORT-INPUT` (DD: `EXPFILE`), `CUSTOMER-OUTPUT` (DD: `CUSTOUT`), `ACCOUNT-OUTPUT` (DD: `ACCTOUT`), `XREF-OUTPUT` (DD: `XREFOUT`), `TRANSACTION-OUTPUT` (DD: `TRNXOUT`), `CARD-OUTPUT` (DD: `CARDOUT`), `ERROR-OUTPUT` (DD: `ERROUT`)
- **Copybooks Referenced**: `CVCUS01Y`, `CVACT01Y`, `CVACT03Y`, `CVTRA05Y`, `CVACT02Y`, `CVEXPORT`
- **Subprograms Called**: `CEE3ABD`

### Program: `CBSTM03A`
- **Description**: Statement Generation batch processor. Compiles monthly account details and writes statement summaries.
- **Lines of Code**: 863
- **Author**: AWS
- **Logical Files**: `STMT-FILE` (DD: `STMTFILE`), `HTML-FILE` (DD: `HTMLFILE`)
- **Copybooks Referenced**: `COSTM01`, `CVACT03Y`, `CUSTREC`, `CVACT01Y`
- **Subprograms Called**: `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CBSTM03B`, `CEE3ABD`

### Program: `CBSTM03B`
- **Description**: Statement Generation helper sub-routine. Manages PDF rendering details.
- **Lines of Code**: 204
- **Author**: AWS
- **Logical Files**: `TRNX-FILE` (DD: `TRNXFILE`), `XREF-FILE` (DD: `XREFFILE`), `CUST-FILE` (DD: `CUSTFILE`), `ACCT-FILE` (DD: `ACCTFILE`)
- **Copybooks Referenced**: None
- **Subprograms Called**: None

### Program: `CBTRN01C`
- **Description**: Daily Transaction Ingestion module. Verifies transactions against active credit cards.
- **Lines of Code**: 449
- **Author**: AWS
- **Logical Files**: `DALYTRAN-FILE` (DD: `DALYTRAN`), `CUSTOMER-FILE` (DD: `CUSTFILE`), `XREF-FILE` (DD: `XREFFILE`), `CARD-FILE` (DD: `CARDFILE`), `ACCOUNT-FILE` (DD: `ACCTFILE`), `TRANSACT-FILE` (DD: `TRANFILE`)
- **Copybooks Referenced**: `CVTRA06Y`, `CVCUS01Y`, `CVACT03Y`, `CVACT02Y`, `CVACT01Y`, `CVTRA05Y`
- **Subprograms Called**: `CEE3ABD`

### Program: `CBTRN02C`
- **Description**: Daily Transaction Posting batch module. Deducts amounts and updates card accounts balances.
- **Lines of Code**: 672
- **Author**: AWS
- **Logical Files**: `DALYTRAN-FILE` (DD: `DALYTRAN`), `TRANSACT-FILE` (DD: `TRANFILE`), `XREF-FILE` (DD: `XREFFILE`), `DALYREJS-FILE` (DD: `DALYREJS`), `ACCOUNT-FILE` (DD: `ACCTFILE`), `TCATBAL-FILE` (DD: `TCATBALF`)
- **Copybooks Referenced**: `CVTRA06Y`, `CVTRA05Y`, `CVACT03Y`, `CVACT01Y`, `CVTRA01Y`
- **Subprograms Called**: `CEE3ABD`

### Program: `CBTRN03C`
- **Description**: Transaction Report generator batch utility. Reports daily totals categorized by transaction types.
- **Lines of Code**: 596
- **Author**: AWS
- **Logical Files**: `TRANSACT-FILE` (DD: `TRANFILE`), `XREF-FILE` (DD: `CARDXREF`), `TRANTYPE-FILE` (DD: `TRANTYPE`), `TRANCATG-FILE` (DD: `TRANCATG`), `REPORT-FILE` (DD: `TRANREPT`), `DATE-PARMS-FILE` (DD: `DATEPARM`)
- **Copybooks Referenced**: `CVTRA05Y`, `CVACT03Y`, `CVTRA03Y`, `CVTRA04Y`, `CVTRA07Y`
- **Subprograms Called**: `CEE3ABD`

### Program: `COACTUPC`
- **Description**: CICS Online Account Update screen controller. Updates customer contact profiles.
- **Lines of Code**: 3744
- **Author**: UNKNOWN
- **Logical Files**: None
- **Copybooks Referenced**: `CVCRD01Y`, `CSLKPCDY`, `DFHBMSCA`, `DFHAID`, `COTTL01Y`, `COACTUP`, `CSDAT01Y`, `CSMSG01Y`, `CSMSG02Y`, `CSUSR01Y`, `CVACT01Y`, `CVACT03Y`, `CVCUS01Y`, `COCOM01Y`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSSETATY`, `CSUTLDPY`
- **Subprograms Called**: None
- **IDMS Records**: `ASSOCIATED`, `CARDS`, `THIS`

### Program: `COACTVWC`
- **Description**: CICS Online Account View screen controller. Searches and displays customer account summaries.
- **Lines of Code**: 811
- **Author**: UNKNOWN
- **Logical Files**: None
- **Copybooks Referenced**: `CVCRD01Y`, `COCOM01Y`, `DFHBMSCA`, `DFHAID`, `COTTL01Y`, `COACTVW`, `CSDAT01Y`, `CSMSG01Y`, `CSMSG02Y`, `CSUSR01Y`, `CVACT01Y`, `CVACT02Y`, `CVACT03Y`, `CVCUS01Y`
- **Subprograms Called**: None
- **IDMS Records**: `ASSOCIATED`, `THIS`

### Program: `COADM01C`
- **Description**: CICS Online Admin Menu screen controller. Routes to admin tools.
- **Lines of Code**: 230
- **Author**: AWS
- **Logical Files**: None
- **Copybooks Referenced**: `COCOM01Y`, `COADM02Y`, `COADM01`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CSUSR01Y`, `DFHAID`, `DFHBMSCA`
- **Subprograms Called**: None

### Program: `COBIL00C`
- **Description**: CICS Online Bill Payment screen controller. Logs payments and checks balances.
- **Lines of Code**: 493
- **Author**: AWS
- **Logical Files**: None
- **Copybooks Referenced**: `COCOM01Y`, `COBIL00`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CVACT01Y`, `CVACT03Y`, `CVTRA05Y`, `DFHAID`, `DFHBMSCA`
- **Subprograms Called**: None

### Program: `COBSWAIT`
- **Description**: Wait utility module. Uses Assembler subroutine MVSWAIT to pause step executions.
- **Lines of Code**: 19
- **Author**: UNKNOWN
- **Logical Files**: None
- **Copybooks Referenced**: None
- **Subprograms Called**: `MVSWAIT`

### Program: `COCRDLIC`
- **Description**: CICS Online Credit Card List screen controller. Lists credit card details.
- **Lines of Code**: 1256
- **Author**: UNKNOWN
- **Logical Files**: None
- **Copybooks Referenced**: `CVCRD01Y`, `COCOM01Y`, `DFHBMSCA`, `DFHAID`, `COTTL01Y`, `COCRDLI`, `CSDAT01Y`, `CSMSG01Y`, `CSUSR01Y`, `CVACT02Y`
- **Subprograms Called**: None

### Program: `COCRDSLC`
- **Description**: CICS Online Credit Card Detail screen controller. Displays credit card balances and interest rates.
- **Lines of Code**: 757
- **Author**: UNKNOWN
- **Logical Files**: None
- **Copybooks Referenced**: `CVCRD01Y`, `COCOM01Y`, `DFHBMSCA`, `DFHAID`, `COTTL01Y`, `COCRDSL`, `CSDAT01Y`, `CSMSG01Y`, `CSMSG02Y`, `CSUSR01Y`, `CVACT02Y`, `CVCUS01Y`
- **Subprograms Called**: None
- **IDMS Records**: `CARDS`, `THIS`

### Program: `COCRDUPC`
- **Description**: CICS Online Credit Card Update screen controller. Modifies credit card limits and expiration dates.
- **Lines of Code**: 1365
- **Author**: UNKNOWN
- **Logical Files**: None
- **Copybooks Referenced**: `CVCRD01Y`, `COCOM01Y`, `DFHBMSCA`, `DFHAID`, `COTTL01Y`, `COCRDUP`, `CSDAT01Y`, `CSMSG01Y`, `CSMSG02Y`, `CSUSR01Y`, `CVACT02Y`, `CVCUS01Y`
- **Subprograms Called**: None
- **IDMS Records**: `CARDS`, `THIS`

### Program: `COMEN01C`
- **Description**: CICS Online Main Menu controller. Main navigation hub routing CICS terminal sessions.
- **Lines of Code**: 255
- **Author**: AWS
- **Logical Files**: None
- **Copybooks Referenced**: `COCOM01Y`, `COMEN02Y`, `COMEN01`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CSUSR01Y`, `DFHAID`, `DFHBMSCA`
- **Subprograms Called**: None

### Program: `CORPT00C`
- **Description**: CICS Online Report viewer. Displays calculated statements on CICS terminal panels.
- **Lines of Code**: 586
- **Author**: AWS
- **Logical Files**: None
- **Copybooks Referenced**: `COCOM01Y`, `CORPT00`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CVTRA05Y`, `DFHAID`, `DFHBMSCA`
- **Subprograms Called**: `CSUTLDTC`, `CSUTLDTC`

### Program: `COSGN00C`
- **Description**: CICS Online Signon screen controller. Performs terminal user authentication and security checks.
- **Lines of Code**: 211
- **Author**: AWS
- **Logical Files**: None
- **Copybooks Referenced**: `COCOM01Y`, `COSGN00`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CSUSR01Y`, `DFHAID`, `DFHBMSCA`
- **Subprograms Called**: None

### Program: `COTRN00C`
- **Description**: CICS Online Transaction Menu screen controller. Lists transaction histories.
- **Lines of Code**: 617
- **Author**: AWS
- **Logical Files**: None
- **Copybooks Referenced**: `COCOM01Y`, `COTRN00`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CVTRA05Y`, `DFHAID`, `DFHBMSCA`
- **Subprograms Called**: None

### Program: `COTRN01C`
- **Description**: CICS Online Transaction Detail screen controller. Displays details of a specific transaction.
- **Lines of Code**: 273
- **Author**: AWS
- **Logical Files**: None
- **Copybooks Referenced**: `COCOM01Y`, `COTRN01`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CVTRA05Y`, `DFHAID`, `DFHBMSCA`
- **Subprograms Called**: None

### Program: `COTRN02C`
- **Description**: CICS Online Transaction Add screen controller. Enters new transaction entries.
- **Lines of Code**: 698
- **Author**: AWS
- **Logical Files**: None
- **Copybooks Referenced**: `COCOM01Y`, `COTRN02`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CVTRA05Y`, `CVACT01Y`, `CVACT03Y`, `DFHAID`, `DFHBMSCA`
- **Subprograms Called**: `CSUTLDTC`, `CSUTLDTC`

### Program: `COUSR00C`
- **Description**: CICS Online User Control screen controller. Inventories CICS account profile logins.
- **Lines of Code**: 615
- **Author**: AWS
- **Logical Files**: None
- **Copybooks Referenced**: `COCOM01Y`, `COUSR00`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CSUSR01Y`, `DFHAID`, `DFHBMSCA`
- **Subprograms Called**: None

### Program: `COUSR01C`
- **Description**: CICS Online User Add screen controller. Adds new user credentials.
- **Lines of Code**: 238
- **Author**: AWS
- **Logical Files**: None
- **Copybooks Referenced**: `COCOM01Y`, `COUSR01`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CSUSR01Y`, `DFHAID`, `DFHBMSCA`
- **Subprograms Called**: None

### Program: `COUSR02C`
- **Description**: CICS Online User Edit screen controller. Updates user roles.
- **Lines of Code**: 351
- **Author**: AWS
- **Logical Files**: None
- **Copybooks Referenced**: `COCOM01Y`, `COUSR02`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CSUSR01Y`, `DFHAID`, `DFHBMSCA`
- **Subprograms Called**: None
- **IDMS Records**: `TO`

### Program: `COUSR03C`
- **Description**: CICS Online User Delete screen controller. Removes CICS credentials.
- **Lines of Code**: 296
- **Author**: AWS
- **Logical Files**: None
- **Copybooks Referenced**: `COCOM01Y`, `COUSR03`, `COTTL01Y`, `CSDAT01Y`, `CSMSG01Y`, `CSUSR01Y`, `DFHAID`, `DFHBMSCA`
- **Subprograms Called**: None

### Program: `CSUTLDTC`
- **Description**: Date Converter utility sub-routine. Standardizes various date formats.
- **Lines of Code**: 128
- **Author**: UNKNOWN
- **Logical Files**: None
- **Copybooks Referenced**: None
- **Subprograms Called**: `CEEDAYS`


## 4.5 JCL Job Stream Analysis (Modernization Targets)

Functional operational sequence of JCL jobs, highlighting executed modules and modernization-critical business datasets while filtering out temporary system utility datasets:

### JCL Job: `ACCTFILE`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (3)**:
  1. **Step `STEP05`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  2. **Step `STEP10`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  3. **Step `STEP15`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
     - Modernization File Inputs/Outputs: `ACCTDATA` (DSN: `AWS.M2.CARDDEMO.ACCTDATA.PS`, DISP: `SHR`), `ACCTVSAM` (DSN: `AWS.M2.CARDDEMO.ACCTDATA.VSAM.KSDS`, DISP: `SHR`)

### JCL Job: `CARDFILE`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (8)**:
  1. **Step `CLCIFIL`**: Runs `SDSF` (Executes program `SDSF`).
  2. **Step `STEP05`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  3. **Step `STEP10`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  4. **Step `STEP15`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
     - Modernization File Inputs/Outputs: `CARDDATA` (DSN: `AWS.M2.CARDDEMO.CARDDATA.PS`, DISP: `SHR`), `CARDVSAM` (DSN: `AWS.M2.CARDDEMO.CARDDATA.VSAM.KSDS`, DISP: `SHR`)
  5. **Step `STEP40`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  6. **Step `STEP50`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  7. **Step `STEP60`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  8. **Step `OPCIFIL`**: Runs `SDSF` (Executes program `SDSF`).

### JCL Job: `CBADMCDJ`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (1)**:
  1. **Step `STEP1`**: Runs `DFHCSDUP` (Executes program `DFHCSDUP`).
     - Modernization File Inputs/Outputs: `STEPLIB` (DSN: `OEM.CICSTS.V05R06M0.CICS.SDFHLOAD`, DISP: `SHR`), `DFHCSD` (DSN: `OEM.CICSTS.DFHCSD`, DISP: `SHR`)

### JCL Job: `CBEXPORT`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (2)**:
  1. **Step `STEP01`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  2. **Step `STEP02`**: Runs `CBEXPORT` (Executes target application COBOL program `CBEXPORT`).
     - Modernization File Inputs/Outputs: `STEPLIB` (DSN: `AWS.M2.CARDDEMO.LOADLIB`, DISP: `SHR`), `CUSTFILE` (DSN: `AWS.M2.CARDDEMO.CUSTDATA.VSAM.KSDS`, DISP: `SHR`), `ACCTFILE` (DSN: `AWS.M2.CARDDEMO.ACCTDATA.VSAM.KSDS`, DISP: `SHR`), `XREFFILE` (DSN: `AWS.M2.CARDDEMO.CARDXREF.VSAM.KSDS`, DISP: `SHR`), `TRANSACT` (DSN: `AWS.M2.CARDDEMO.TRANSACT.VSAM.KSDS`, DISP: `SHR`), `CARDFILE` (DSN: `AWS.M2.CARDDEMO.CARDDATA.VSAM.KSDS`, DISP: `SHR`), `EXPFILE` (DSN: `AWS.M2.CARDDEMO.EXPORT.DATA`, DISP: `SHR`)

### JCL Job: `CBIMPORT`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (1)**:
  1. **Step `STEP01`**: Runs `CBIMPORT` (Executes target application COBOL program `CBIMPORT`).
     - Modernization File Inputs/Outputs: `STEPLIB` (DSN: `AWS.M2.CARDDEMO.LOADLIB`, DISP: `SHR`), `EXPFILE` (DSN: `AWS.M2.CARDDEMO.EXPORT.DATA`, DISP: `SHR`), `CUSTOUT` (DSN: `AWS.M2.CARDDEMO.CUSTDATA.IMPORT`, DISP: `NEW,CATLG,DELETE`), `ACCTOUT` (DSN: `AWS.M2.CARDDEMO.ACCTDATA.IMPORT`, DISP: `NEW,CATLG,DELETE`), `XREFOUT` (DSN: `AWS.M2.CARDDEMO.CARDXREF.IMPORT`, DISP: `NEW,CATLG,DELETE`), `TRNXOUT` (DSN: `AWS.M2.CARDDEMO.TRANSACT.IMPORT`, DISP: `NEW,CATLG,DELETE`), `ERROUT` (DSN: `AWS.M2.CARDDEMO.IMPORT.ERRORS`, DISP: `NEW,CATLG,DELETE`)

### JCL Job: `CLOSEFIL`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (1)**:
  1. **Step `CLCIFIL`**: Runs `SDSF` (Executes program `SDSF`).

### JCL Job: `COMBTRAN`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (2)**:
  1. **Step `STEP05R`**: Runs `SORT` (Data sorting utility; replaced by DB order-by queries or local sorting logic).
     - Modernization File Inputs/Outputs: `SORTIN` (DSN: `AWS.M2.CARDDEMO.TRANSACT.BKUP(0)`, DISP: `SHR`), `SORTOUT` (DSN: `AWS.M2.CARDDEMO.TRANSACT.COMBINED(`, DISP: `NEW,CATLG,DELETE`)
  2. **Step `STEP10`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
     - Modernization File Inputs/Outputs: `TRANSACT` (DSN: `AWS.M2.CARDDEMO.TRANSACT.COMBINED(`, DISP: `SHR`), `TRANVSAM` (DSN: `AWS.M2.CARDDEMO.TRANSACT.VSAM.KSDS`, DISP: `SHR`)

### JCL Job: `CREASTMT`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (5)**:
  1. **Step `DELDEF01`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  2. **Step `STEP010`**: Runs `SORT` (Data sorting utility; replaced by DB order-by queries or local sorting logic).
     - Modernization File Inputs/Outputs: `SORTIN` (DSN: `AWS.M2.CARDDEMO.TRANSACT.VSAM.KSDS`, DISP: `SHR`), `SORTOUT` (DSN: `AWS.M2.CARDDEMO.TRXFL.SEQ`, DISP: `NEW,CATLG,DELETE`)
  3. **Step `STEP020`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
     - Modernization File Inputs/Outputs: `INFILE` (DSN: `AWS.M2.CARDDEMO.TRXFL.SEQ`, DISP: `SHR`), `OUTFILE` (DSN: `AWS.M2.CARDDEMO.TRXFL.VSAM.KSDS`, DISP: `SHR`)
  4. **Step `STEP030`**: Runs `IEFBR14` (System utility for file allocation/deletion; redundant in modernized environments).
     - Modernization File Inputs/Outputs: `HTMLFILE` (DSN: `AWS.M2.CARDDEMO.STATEMNT.HTML`, DISP: `MOD,DELETE,DELETE`), `STMTFILE` (DSN: `AWS.M2.CARDDEMO.STATEMNT.PS`, DISP: `MOD,DELETE,DELETE`)
  5. **Step `STEP040`**: Runs `CBSTM03A` (Executes target application COBOL program `CBSTM03A`).
     - Modernization File Inputs/Outputs: `STEPLIB` (DSN: `AWS.M2.CARDDEMO.LOADLIB`, DISP: `SHR`), `TRNXFILE` (DSN: `AWS.M2.CARDDEMO.TRXFL.VSAM.KSDS`, DISP: `SHR`), `XREFFILE` (DSN: `AWS.M2.CARDDEMO.CARDXREF.VSAM.KSDS`, DISP: `SHR`), `ACCTFILE` (DSN: `AWS.M2.CARDDEMO.ACCTDATA.VSAM.KSDS`, DISP: `SHR`), `CUSTFILE` (DSN: `AWS.M2.CARDDEMO.CUSTDATA.VSAM.KSDS`, DISP: `SHR`), `HTMLFILE` (DSN: `AWS.M2.CARDDEMO.STATEMNT.HTML`, DISP: `NEW,CATLG,DELETE`)

### JCL Job: `CUSTFILE`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (5)**:
  1. **Step `CLCIFIL`**: Runs `SDSF` (Executes program `SDSF`).
  2. **Step `STEP05`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  3. **Step `STEP10`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  4. **Step `STEP15`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
     - Modernization File Inputs/Outputs: `CUSTDATA` (DSN: `AWS.M2.CARDDEMO.CUSTDATA.PS`, DISP: `SHR`), `CUSTVSAM` (DSN: `AWS.M2.CARDDEMO.CUSTDATA.VSAM.KSDS`, DISP: `SHR`)
  5. **Step `OPCIFIL`**: Runs `SDSF` (Executes program `SDSF`).

### JCL Job: `DALYREJS`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (1)**:
  1. **Step `STEP05`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).

### JCL Job: `DEFCUST`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (2)**:
  1. **Step `STEP05`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  2. **Step `STEP05`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).

### JCL Job: `DEFGDGB`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (1)**:
  1. **Step `STEP05`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).

### JCL Job: `DEFGDGD`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (6)**:
  1. **Step `STEP10`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  2. **Step `STEP20`**: Runs `IEBGENER` (System copy utility; replaced by standard OS file copy or cloud storage commands).
  3. **Step `STEP30`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  4. **Step `STEP40`**: Runs `IEBGENER` (System copy utility; replaced by standard OS file copy or cloud storage commands).
  5. **Step `STEP50`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  6. **Step `STEP60`**: Runs `IEBGENER` (System copy utility; replaced by standard OS file copy or cloud storage commands).

### JCL Job: `DISCGRP`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (3)**:
  1. **Step `STEP05`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  2. **Step `STEP10`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  3. **Step `STEP15`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
     - Modernization File Inputs/Outputs: `DISCGRP` (DSN: `AWS.M2.CARDDEMO.DISCGRP.PS`, DISP: `SHR`), `DISCVSAM` (DSN: `AWS.M2.CARDDEMO.DISCGRP.VSAM.KSDS`, DISP: `SHR`)

### JCL Job: `DUSRSECJ`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (4)**:
  1. **Step `PREDEL`**: Runs `IEFBR14` (System utility for file allocation/deletion; redundant in modernized environments).
     - Modernization File Inputs/Outputs: `DD01` (DSN: `AWS.M2.CARDDEMO.USRSEC.PS`, DISP: `MOD,DELETE,DELETE`)
  2. **Step `STEP01`**: Runs `IEBGENER` (System copy utility; replaced by standard OS file copy or cloud storage commands).
  3. **Step `STEP02`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  4. **Step `STEP03`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
     - Modernization File Inputs/Outputs: `IN` (DSN: `AWS.M2.CARDDEMO.USRSEC.PS`, DISP: `SHR`), `OUT` (DSN: `AWS.M2.CARDDEMO.USRSEC.VSAM.KSDS`, DISP: `SHR`)

### JCL Job: `ESDSRRDS`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (6)**:
  1. **Step `PREDEL`**: Runs `IEFBR14` (System utility for file allocation/deletion; redundant in modernized environments).
     - Modernization File Inputs/Outputs: `DD01` (DSN: `AWS.M2.CARDDEMO.ESDSRRDS.PS`, DISP: `MOD,DELETE,DELETE`)
  2. **Step `STEP01`**: Runs `IEBGENER` (System copy utility; replaced by standard OS file copy or cloud storage commands).
  3. **Step `STEP02`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  4. **Step `STEP03`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
     - Modernization File Inputs/Outputs: `IN` (DSN: `AWS.M2.CARDDEMO.ESDSRRDS.PS`, DISP: `SHR`), `OUT` (DSN: `AWS.M2.CARDDEMO.USRSEC.VSAM.ESDS`, DISP: `SHR`)
  5. **Step `STEP04`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  6. **Step `STEP05`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
     - Modernization File Inputs/Outputs: `IN` (DSN: `AWS.M2.CARDDEMO.ESDSRRDS.PS`, DISP: `SHR`), `OUT` (DSN: `AWS.M2.CARDDEMO.USRSEC.VSAM.RRDS`, DISP: `SHR`)

### JCL Job: `FTPJCLS`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (1)**:
  1. **Step `STEP1`**: Runs `FTP` (Executes program `FTP`).

### JCL Job: `INTCALC`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (1)**:
  1. **Step `STEP15`**: Runs `CBACT04C` (Executes target application COBOL program `CBACT04C`).
     - Modernization File Inputs/Outputs: `STEPLIB` (DSN: `AWS.M2.CARDDEMO.LOADLIB`, DISP: `SHR`), `TCATBALF` (DSN: `AWS.M2.CARDDEMO.TCATBALF.VSAM.KSDS`, DISP: `SHR`), `XREFFILE` (DSN: `AWS.M2.CARDDEMO.CARDXREF.VSAM.KSDS`, DISP: `SHR`), `XREFFIL1` (DSN: `AWS.M2.CARDDEMO.CARDXREF.VSAM.AIX.PATH`, DISP: `SHR`), `ACCTFILE` (DSN: `AWS.M2.CARDDEMO.ACCTDATA.VSAM.KSDS`, DISP: `SHR`), `DISCGRP` (DSN: `AWS.M2.CARDDEMO.DISCGRP.VSAM.KSDS`, DISP: `SHR`), `TRANSACT` (DSN: `AWS.M2.CARDDEMO.SYSTRAN(`, DISP: `NEW,CATLG,DELETE`)

### JCL Job: `INTRDRJ1`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (2)**:
  1. **Step `IDCAMS`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
     - Modernization File Inputs/Outputs: `IN` (DSN: `AWS.M2.CARDEMO.FTP.TEST`, DISP: `SHR`), `OUT` (DSN: `AWS.M2.CARDEMO.FTP.TEST.BKUP`, DISP: `SHR`)
  2. **Step `STEP01`**: Runs `IEBGENER` (System copy utility; replaced by standard OS file copy or cloud storage commands).

### JCL Job: `INTRDRJ2`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (1)**:
  1. **Step `IDCAMS`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
     - Modernization File Inputs/Outputs: `IN` (DSN: `AWS.M2.CARDEMO.FTP.TEST.BKUP`, DISP: `SHR`), `OUT` (DSN: `AWS.M2.CARDEMO.FTP.TEST.BKUP.INTRDR`, DISP: `SHR`)

### JCL Job: `OPENFIL`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (1)**:
  1. **Step `OPCIFIL`**: Runs `SDSF` (Executes program `SDSF`).

### JCL Job: `POSTTRAN`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (1)**:
  1. **Step `STEP15`**: Runs `CBTRN02C` (Executes target application COBOL program `CBTRN02C`).
     - Modernization File Inputs/Outputs: `STEPLIB` (DSN: `AWS.M2.CARDDEMO.LOADLIB`, DISP: `SHR`), `TRANFILE` (DSN: `AWS.M2.CARDDEMO.TRANSACT.VSAM.KSDS`, DISP: `SHR`), `DALYTRAN` (DSN: `AWS.M2.CARDDEMO.DALYTRAN.PS`, DISP: `SHR`), `XREFFILE` (DSN: `AWS.M2.CARDDEMO.CARDXREF.VSAM.KSDS`, DISP: `SHR`), `DALYREJS` (DSN: `AWS.M2.CARDDEMO.DALYREJS(`, DISP: `NEW,CATLG,DELETE`), `ACCTFILE` (DSN: `AWS.M2.CARDDEMO.ACCTDATA.VSAM.KSDS`, DISP: `SHR`), `TCATBALF` (DSN: `AWS.M2.CARDDEMO.TCATBALF.VSAM.KSDS`, DISP: `SHR`)

### JCL Job: `PRTCATBL`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (3)**:
  1. **Step `DELDEF`**: Runs `IEFBR14` (System utility for file allocation/deletion; redundant in modernized environments).
     - Modernization File Inputs/Outputs: `THEFILE` (DSN: `AWS.M2.CARDDEMO.TCATBALF.REPT`, DISP: `MOD,DELETE`)
  2. **Step `STEP05R`**: Runs `REPROC` (Executes program `REPROC`).
  3. **Step `STEP10R`**: Runs `SORT` (Data sorting utility; replaced by DB order-by queries or local sorting logic).
     - Modernization File Inputs/Outputs: `SORTIN` (DSN: `AWS.M2.CARDDEMO.TCATBALF.BKUP(`, DISP: `SHR`), `SORTOUT` (DSN: `AWS.M2.CARDDEMO.TCATBALF.REPT`, DISP: `NEW,CATLG,DELETE`)

### JCL Job: `READACCT`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (2)**:
  1. **Step `PREDEL`**: Runs `IEFBR14` (System utility for file allocation/deletion; redundant in modernized environments).
     - Modernization File Inputs/Outputs: `DD01` (DSN: `AWS.M2.CARDDEMO.ACCTDATA.PSCOMP`, DISP: `MOD,DELETE,DELETE`), `DD02` (DSN: `AWS.M2.CARDDEMO.ACCTDATA.ARRYPS`, DISP: `MOD,DELETE,DELETE`), `DD03` (DSN: `AWS.M2.CARDDEMO.ACCTDATA.VBPS`, DISP: `MOD,DELETE,DELETE`)
  2. **Step `STEP05`**: Runs `CBACT01C` (Executes target application COBOL program `CBACT01C`).
     - Modernization File Inputs/Outputs: `STEPLIB` (DSN: `AWS.M2.CARDDEMO.LOADLIB`, DISP: `SHR`), `ACCTFILE` (DSN: `AWS.M2.CARDDEMO.ACCTDATA.VSAM.KSDS`, DISP: `SHR`), `OUTFILE` (DSN: `AWS.M2.CARDDEMO.ACCTDATA.PSCOMP`, DISP: `NEW,CATLG,DELETE`), `ARRYFILE` (DSN: `AWS.M2.CARDDEMO.ACCTDATA.ARRYPS`, DISP: `NEW,CATLG,DELETE`), `VBRCFILE` (DSN: `AWS.M2.CARDDEMO.ACCTDATA.VBPS`, DISP: `NEW,CATLG,DELETE`)

### JCL Job: `READCARD`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (1)**:
  1. **Step `STEP05`**: Runs `CBACT02C` (Executes target application COBOL program `CBACT02C`).
     - Modernization File Inputs/Outputs: `STEPLIB` (DSN: `AWS.M2.CARDDEMO.LOADLIB`, DISP: `SHR`), `CARDFILE` (DSN: `AWS.M2.CARDDEMO.CARDDATA.VSAM.KSDS`, DISP: `SHR`)

### JCL Job: `READCUST`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (1)**:
  1. **Step `STEP05`**: Runs `CBCUS01C` (Executes target application COBOL program `CBCUS01C`).
     - Modernization File Inputs/Outputs: `STEPLIB` (DSN: `AWS.M2.CARDDEMO.LOADLIB`, DISP: `SHR`), `CUSTFILE` (DSN: `AWS.M2.CARDDEMO.CUSTDATA.VSAM.KSDS`, DISP: `SHR`)

### JCL Job: `READXREF`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (1)**:
  1. **Step `STEP05`**: Runs `CBACT03C` (Executes target application COBOL program `CBACT03C`).
     - Modernization File Inputs/Outputs: `STEPLIB` (DSN: `AWS.M2.CARDDEMO.LOADLIB`, DISP: `SHR`), `XREFFILE` (DSN: `AWS.M2.CARDDEMO.CARDXREF.VSAM.KSDS`, DISP: `SHR`)

### JCL Job: `REPTFILE`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (1)**:
  1. **Step `STEP05`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).

### JCL Job: `TCATBALF`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (3)**:
  1. **Step `STEP05`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  2. **Step `STEP10`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  3. **Step `STEP15`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
     - Modernization File Inputs/Outputs: `TCATBAL` (DSN: `AWS.M2.CARDDEMO.TCATBALF.PS`, DISP: `SHR`), `TCATBALV` (DSN: `AWS.M2.CARDDEMO.TCATBALF.VSAM.KSDS`, DISP: `SHR`)

### JCL Job: `TRANBKP`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (3)**:
  1. **Step `STEP05R`**: Runs `REPROC` (Executes program `REPROC`).
  2. **Step `STEP05`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  3. **Step `STEP10`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).

### JCL Job: `TRANCATG`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (3)**:
  1. **Step `STEP05`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  2. **Step `STEP10`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  3. **Step `STEP15`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
     - Modernization File Inputs/Outputs: `TRANCATG` (DSN: `AWS.M2.CARDDEMO.TRANCATG.PS`, DISP: `SHR`), `TCATVSAM` (DSN: `AWS.M2.CARDDEMO.TRANCATG.VSAM.KSDS`, DISP: `SHR`)

### JCL Job: `TRANFILE`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (8)**:
  1. **Step `CLCIFIL`**: Runs `SDSF` (Executes program `SDSF`).
  2. **Step `STEP05`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  3. **Step `STEP10`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  4. **Step `STEP15`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
     - Modernization File Inputs/Outputs: `TRANSACT` (DSN: `AWS.M2.CARDDEMO.DALYTRAN.PS.INIT`, DISP: `SHR`), `TRANVSAM` (DSN: `AWS.M2.CARDDEMO.TRANSACT.VSAM.KSDS`, DISP: `SHR`)
  5. **Step `STEP20`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  6. **Step `STEP25`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  7. **Step `STEP30`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  8. **Step `OPCIFIL`**: Runs `SDSF` (Executes program `SDSF`).

### JCL Job: `TRANIDX`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (3)**:
  1. **Step `STEP20`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  2. **Step `STEP25`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  3. **Step `STEP30`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).

### JCL Job: `TRANREPT`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (3)**:
  1. **Step `STEP05R`**: Runs `REPROC` (Executes program `REPROC`).
  2. **Step `STEP05R`**: Runs `SORT` (Data sorting utility; replaced by DB order-by queries or local sorting logic).
     - Modernization File Inputs/Outputs: `SORTIN` (DSN: `AWS.M2.CARDDEMO.TRANSACT.BKUP(`, DISP: `SHR`), `SORTOUT` (DSN: `AWS.M2.CARDDEMO.TRANSACT.DALY(`, DISP: `NEW,CATLG,DELETE`)
  3. **Step `STEP10R`**: Runs `CBTRN03C` (Executes target application COBOL program `CBTRN03C`).
     - Modernization File Inputs/Outputs: `STEPLIB` (DSN: `AWS.M2.CARDDEMO.LOADLIB`, DISP: `SHR`), `TRANFILE` (DSN: `AWS.M2.CARDDEMO.TRANSACT.DALY(`, DISP: `SHR`), `CARDXREF` (DSN: `AWS.M2.CARDDEMO.CARDXREF.VSAM.KSDS`, DISP: `SHR`), `TRANTYPE` (DSN: `AWS.M2.CARDDEMO.TRANTYPE.VSAM.KSDS`, DISP: `SHR`), `TRANCATG` (DSN: `AWS.M2.CARDDEMO.TRANCATG.VSAM.KSDS`, DISP: `SHR`), `DATEPARM` (DSN: `AWS.M2.CARDDEMO.DATEPARM`, DISP: `SHR`), `TRANREPT` (DSN: `AWS.M2.CARDDEMO.TRANREPT(`, DISP: `NEW,CATLG,DELETE`)

### JCL Job: `TRANTYPE`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (3)**:
  1. **Step `STEP05`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  2. **Step `STEP10`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  3. **Step `STEP15`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
     - Modernization File Inputs/Outputs: `TRANTYPE` (DSN: `AWS.M2.CARDDEMO.TRANTYPE.PS`, DISP: `SHR`), `TTYPVSAM` (DSN: `AWS.M2.CARDDEMO.TRANTYPE.VSAM.KSDS`, DISP: `SHR`)

### JCL Job: `TXT2PDF1`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (1)**:
  1. **Step `TXT2PDF`**: Runs `IKJEFT1B` (TSO monitor program executing DB2 batch commands; modernized as direct Spring/Java database tasks).
     - Modernization File Inputs/Outputs: `STEPLIB` (DSN: `AWS.M2.LBD.TXT2PDF.LOAD`, DISP: `SHR`), `SYSEXEC` (DSN: `AWS.M2.LBD.TXT2PDF.EXEC`, DISP: `SHR`), `INDD` (DSN: `AWS.M2.CARDDEMO.STATEMNT.PS`, DISP: `SHR`)

### JCL Job: `WAITSTEP`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (1)**:
  1. **Step `WAIT`**: Runs `COBSWAIT` (Executes target application COBOL program `COBSWAIT`).
     - Modernization File Inputs/Outputs: `STEPLIB` (DSN: `AWS.M2.CARDDEMO.LOADLIB`, DISP: `SHR`)

### JCL Job: `XREFFILE`
- **Job Stream Description**: Sequential execution of batch components. Map to Spring Batch tasklets or AWS Batch definition configurations.
- **Steps Defined (6)**:
  1. **Step `STEP05`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  2. **Step `STEP10`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  3. **Step `STEP15`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
     - Modernization File Inputs/Outputs: `XREFDATA` (DSN: `AWS.M2.CARDDEMO.CARDXREF.PS`, DISP: `SHR`), `XREFVSAM` (DSN: `AWS.M2.CARDDEMO.CARDXREF.VSAM.KSDS`, DISP: `SHR`)
  4. **Step `STEP20`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  5. **Step `STEP25`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).
  6. **Step `STEP30`**: Runs `IDCAMS` (VSAM Access Method Services utility; replaced by schema creation or cleanup scripts).


## 4.6 Assembler Module Analysis

Lower-level HLASM modules referenced by subprograms in execution flows:

### Assembler Module: `COBDATFT`
- **Description**: Assembler date formatting subroutine.
- **Entry Points**: `COBDATFT`
- **Calls Made**: None

### Assembler Module: `MVSWAIT`
- **Description**: Assembler interval wait subroutine.
- **Entry Points**: 
- **Calls Made**: None


## 4.7 CICS BMS Mapset Layouts

Defined CICS terminal screens, field layouts, and positioning mappings:

### Mapset: `COACTUP`
- **Maps Included**: `CACTUPA`
- **Field Layouts (Top 20)**: `FILLER` (Pos: N/A, Len: 0), `TRNNAME` (Pos: N/A, Len: 0), `TITLE01` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURDATE` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PGMNAME` (Pos: N/A, Len: 0), `TITLE02` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURTIME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `ACCTSID` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `ACSTTUS` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `OPNYEAR` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 1)

### Mapset: `COACTVW`
- **Maps Included**: `CACTVWA`
- **Field Layouts (Top 20)**: `FILLER` (Pos: N/A, Len: 0), `TRNNAME` (Pos: N/A, Len: 0), `TITLE01` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURDATE` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PGMNAME` (Pos: N/A, Len: 0), `TITLE02` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURTIME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `ACCTSID` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `ACSTTUS` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `ADTOPEN` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0)

### Mapset: `COADM01`
- **Maps Included**: `COADM1A`
- **Field Layouts (Top 20)**: `FILLER` (Pos: N/A, Len: 0), `TRNNAME` (Pos: N/A, Len: 0), `TITLE01` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURDATE` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PGMNAME` (Pos: N/A, Len: 0), `TITLE02` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURTIME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `OPTN001` (Pos: N/A, Len: 0), `OPTN002` (Pos: N/A, Len: 0), `OPTN003` (Pos: N/A, Len: 0), `OPTN004` (Pos: N/A, Len: 0), `OPTN005` (Pos: N/A, Len: 0), `OPTN006` (Pos: N/A, Len: 0), `OPTN007` (Pos: N/A, Len: 0), `OPTN008` (Pos: N/A, Len: 0), `OPTN009` (Pos: N/A, Len: 0)

### Mapset: `COBIL00`
- **Maps Included**: `COBIL0A`
- **Field Layouts (Top 20)**: `FILLER` (Pos: N/A, Len: 0), `TRNNAME` (Pos: N/A, Len: 0), `TITLE01` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURDATE` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PGMNAME` (Pos: N/A, Len: 0), `TITLE02` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURTIME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `ACTIDIN` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURBAL` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CONFIRM` (Pos: N/A, Len: 0)

### Mapset: `COCRDLI`
- **Maps Included**: `CCRDLIA`
- **Field Layouts (Top 20)**: `FILLER` (Pos: N/A, Len: 0), `TRNNAME` (Pos: N/A, Len: 0), `TITLE01` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURDATE` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PGMNAME` (Pos: N/A, Len: 0), `TITLE02` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURTIME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 5), `PAGENO` (Pos: N/A, Len: 3), `FILLER` (Pos: N/A, Len: 0), `ACCTSID` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CARDSID` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0)

### Mapset: `COCRDSL`
- **Maps Included**: `CCRDSLA`
- **Field Layouts (Top 20)**: `FILLER` (Pos: N/A, Len: 0), `TRNNAME` (Pos: N/A, Len: 0), `TITLE01` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURDATE` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PGMNAME` (Pos: N/A, Len: 0), `TITLE02` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURTIME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `ACCTSID` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CARDSID` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CRDNAME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0)

### Mapset: `COCRDUP`
- **Maps Included**: `CCRDUPA`
- **Field Layouts (Top 20)**: `FILLER` (Pos: N/A, Len: 0), `TRNNAME` (Pos: N/A, Len: 0), `TITLE01` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURDATE` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PGMNAME` (Pos: N/A, Len: 0), `TITLE02` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURTIME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `ACCTSID` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CARDSID` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CRDNAME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0)

### Mapset: `COMEN01`
- **Maps Included**: `COMEN1A`
- **Field Layouts (Top 20)**: `FILLER` (Pos: N/A, Len: 0), `TRNNAME` (Pos: N/A, Len: 0), `TITLE01` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURDATE` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PGMNAME` (Pos: N/A, Len: 0), `TITLE02` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURTIME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `OPTN001` (Pos: N/A, Len: 0), `OPTN002` (Pos: N/A, Len: 0), `OPTN003` (Pos: N/A, Len: 0), `OPTN004` (Pos: N/A, Len: 0), `OPTN005` (Pos: N/A, Len: 0), `OPTN006` (Pos: N/A, Len: 0), `OPTN007` (Pos: N/A, Len: 0), `OPTN008` (Pos: N/A, Len: 0), `OPTN009` (Pos: N/A, Len: 0)

### Mapset: `CORPT00`
- **Maps Included**: `CORPT0A`
- **Field Layouts (Top 20)**: `FILLER` (Pos: N/A, Len: 0), `TRNNAME` (Pos: N/A, Len: 0), `TITLE01` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURDATE` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PGMNAME` (Pos: N/A, Len: 0), `TITLE02` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURTIME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `MONTHLY` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `YEARLY` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CUSTOM` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0)

### Mapset: `COSGN00`
- **Maps Included**: `COSGN0A`
- **Field Layouts (Top 20)**: `FILLER` (Pos: N/A, Len: 0), `TRNNAME` (Pos: N/A, Len: 0), `TITLE01` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURDATE` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PGMNAME` (Pos: N/A, Len: 0), `TITLE02` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURTIME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `APPLID` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `SYSID` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0)

### Mapset: `COTRN00`
- **Maps Included**: `COTRN0A`
- **Field Layouts (Top 20)**: `FILLER` (Pos: N/A, Len: 0), `TRNNAME` (Pos: N/A, Len: 0), `TITLE01` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURDATE` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PGMNAME` (Pos: N/A, Len: 0), `TITLE02` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURTIME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PAGENUM` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `TRNIDIN` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0)

### Mapset: `COTRN01`
- **Maps Included**: `COTRN1A`
- **Field Layouts (Top 20)**: `FILLER` (Pos: N/A, Len: 0), `TRNNAME` (Pos: N/A, Len: 0), `TITLE01` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURDATE` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PGMNAME` (Pos: N/A, Len: 0), `TITLE02` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURTIME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `TRNIDIN` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `TRNID` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CARDNUM` (Pos: N/A, Len: 0)

### Mapset: `COTRN02`
- **Maps Included**: `COTRN2A`
- **Field Layouts (Top 20)**: `FILLER` (Pos: N/A, Len: 0), `TRNNAME` (Pos: N/A, Len: 0), `TITLE01` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURDATE` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PGMNAME` (Pos: N/A, Len: 0), `TITLE02` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURTIME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `ACTIDIN` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CARDNIN` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0)

### Mapset: `COUSR00`
- **Maps Included**: `COUSR0A`
- **Field Layouts (Top 20)**: `FILLER` (Pos: N/A, Len: 0), `TRNNAME` (Pos: N/A, Len: 0), `TITLE01` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURDATE` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PGMNAME` (Pos: N/A, Len: 0), `TITLE02` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURTIME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PAGENUM` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `USRIDIN` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0)

### Mapset: `COUSR01`
- **Maps Included**: `COUSR1A`
- **Field Layouts (Top 20)**: `FILLER` (Pos: N/A, Len: 0), `TRNNAME` (Pos: N/A, Len: 0), `TITLE01` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURDATE` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PGMNAME` (Pos: N/A, Len: 0), `TITLE02` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURTIME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FNAME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `LNAME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `USERID` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0)

### Mapset: `COUSR02`
- **Maps Included**: `COUSR2A`
- **Field Layouts (Top 20)**: `FILLER` (Pos: N/A, Len: 0), `TRNNAME` (Pos: N/A, Len: 0), `TITLE01` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURDATE` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PGMNAME` (Pos: N/A, Len: 0), `TITLE02` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURTIME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `USRIDIN` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FNAME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `LNAME` (Pos: N/A, Len: 0)

### Mapset: `COUSR03`
- **Maps Included**: `COUSR3A`
- **Field Layouts (Top 20)**: `FILLER` (Pos: N/A, Len: 0), `TRNNAME` (Pos: N/A, Len: 0), `TITLE01` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURDATE` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `PGMNAME` (Pos: N/A, Len: 0), `TITLE02` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `CURTIME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `USRIDIN` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FNAME` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `FILLER` (Pos: N/A, Len: 0), `LNAME` (Pos: N/A, Len: 0)

