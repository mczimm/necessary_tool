#!/bin/bash

cp ./tabulate.py /usr/lib/python2.6/site-packages
cp ./blessings.py /usr/lib/python2.6/site-packages
cp ./snapper4.sql /opt/oracle
cp ./oratop.v13.2.2_X8664 /opt/oracle
cp ./tree_locks.py /opt/oracle
rpm -ihv /tmp/nec_tool/cx_Oracle-5.1.2-11g-py26-1.x86_64.rpm

chown oracle:oinstall /opt/oracle/oratop.v13.2.2_X8664
chown oracle:oinstall /opt/oracle/snapper4.sql
chown oracle:oinstall /opt/oracle/tree_locks.py

echo "Install has completed. Now you have snapper, oratop and tree_locks"
echo "\n"
echo "Hint: /opt/oracle/oratop.v13.2.2_X8664 -i 2 -f -d -m / as sysdba"
