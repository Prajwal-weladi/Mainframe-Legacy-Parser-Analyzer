      * CUSTOMER-RECORD COPYBOOK
       01  CUSTOMER-RECORD.
           05  CUST-ID             PIC X(10).
           05  CUST-NAME           PIC X(30).
           05  CUST-SSN            PIC X(9).
           05  CUST-CONTACT.
               10  CUST-PHONE      PIC X(10).
               10  CUST-EMAIL      PIC X(40).
           05  CUST-ADDRESS.
               10  CUST-STREET     PIC X(30).
               10  CUST-CITY       PIC X(20).
               10  CUST-STATE      PIC X(2).
               10  CUST-ZIP        PIC X(5).
           05  CUST-ACCOUNT-NUM    PIC X(12).
           05  CUST-BALANCE        PIC S9(7)V99 COMP-3.
