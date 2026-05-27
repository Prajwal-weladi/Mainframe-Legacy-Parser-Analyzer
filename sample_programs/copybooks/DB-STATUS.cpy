      * DATABASE STATUS COPYBOOK
       01  DB-STATUS.
           05  SQL-CODE-VAL        PIC S9(9) COMP.
           05  IMS-STATUS-CODE     PIC X(2).
           05  IDMS-ERR-CODE       PIC X(4).
           05  MQ-REASON-CODE      PIC S9(9) COMP.
           05  VSAM-FEEDBACK       PIC X(2).
           05  ERR-MSG             PIC X(80).
