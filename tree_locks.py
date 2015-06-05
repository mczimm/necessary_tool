#!/usr/bin/python2.6

#***********************************
#Author: Filatov Maxim aka McZim
#Company: Yandex
#Date: 11.2013
#Encoding: en_US.UTF-8
#Description:
#
#Some locks stuff
#You need download tabulate.tar.gz from https://pypi.python.org/pypi/tabulate
#extract and copy tabulate.py to /usr/lib/python2.6/site-packages
#And download blessings.tar.gz from https://pypi.python.org/pypi/blessings
#extract and execute (cp blessings/__init__.py /usr/lib/python2.6/site-packages/blessings.py)
#**********************************

import cx_Oracle
from blessings import Terminal
import re
import sys
from tabulate import tabulate
import time

term = Terminal()
table_list = []
table_list2 = []

def connection():
  try:
    con = cx_Oracle.connect(mode = cx_Oracle.SYSDBA)
  except cx_Oracle.DatabaseError,info:
    print "Error: ",info
  return con

def curr_time():
  tm_year = str(time.localtime()[0])
  tm_mon = str(time.localtime()[1])
  tm_mday = str(time.localtime()[2])
  tm_hour = str(time.localtime()[3])
  tm_min = str(time.localtime()[4])
  tm_sec = str(time.localtime()[5])

  tm=tm_year+"-"+tm_mon+"-"+tm_mday+" "+tm_hour+":"+tm_min+":"+tm_sec
  print tm

def lock_tree(conn):
  cur = conn.cursor()

  try:
    LOCK_TREE="""
    with LOCKS as (select/*+ MATERIALIZE*/ * from gv$lock),S as (select/*+ MATERIALIZE*/ * from gv$session),BLOCKERS as
      (select distinct L1.inst_id, L1.sid
      from LOCKS L1, LOCKS L2
      where L1.block > 0
      and L1.ID1 = L2.ID1
      and L1.ID2 = L2.ID2
      and L2.REQUEST > 0),WAITERS as (select inst_id, sid from S where blocking_session is not null or blocking_instance is not null)
      select /*+ opt_param('_connect_by_use_union_all' 'false') */
      LPAD(' ', (LEVEL - 1) * 2) || 'INST#' || s.inst_id || ' SID#' || sid || ' SER#' || serial# || ' ' ||
      program as BLOCKING_TREE, client_identifier,EVENT,seconds_in_wait,blocking_session_status,s.sql_id,substr(trim(NVL(sa1.sql_text,sa2.sql_text)), 1, 35) SQL_TEXT
      from s, gv$sqlarea sa1, gv$sqlarea sa2
      where s.sql_id = sa1.sql_id(+)
      and s.inst_id = sa1.inst_id(+)
      and s.prev_sql_id = sa2.sql_id(+)
      and s.inst_id = sa2.inst_id(+)
      connect by NOCYCLE prior sid = blocking_session and prior s.inst_id = blocking_instance
      start with (s.inst_id, s.sid) in (select inst_id, sid from BLOCKERS minus select inst_id, sid from WAITERS)
    """
    cur.execute(LOCK_TREE)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list = []
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        match = re.search(ur"^ ",str_chk)
        if match:
          str_chk = term.red+str_chk+term.normal
        a_list.append(str_chk)
      table_list.append(a_list)
  
    headers = [term.blue+"BLOCKING_TREE","CLIENT","EVENT","WAIT(sec)","STATUS","SQL_ID","SQL_TEXT"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def active_sessions(conn):
  cur = conn.cursor()

  try:
    AS="""
    select inst_id,event,count(*) from gv$session
    where status = 'ACTIVE' and audsid != UserEnv('SESSIONID') and username is not null
    group by inst_id,event order by 3 desc
   """

    cur.execute(AS)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list = []
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        a_list.append(str_chk)
      table_list.append(a_list)

    headers = [term.blue+"INSTANCE","EVENT","COUNT"+term.normal]
 
    curr_time() 
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def stat_proc_memory(conn,sid):
  cur = conn.cursor()

  try:
    PROC_MEM="""
    SELECT pm.inst_id,s.sid,pm.serial#,pm.pid,pm.category,pm.allocated,pm.used,pm.max_allocated
    FROM gv$session s, gv$process p, gv$process_memory pm
    WHERE s.paddr = p.addr
    AND p.pid = pm.pid
    AND s.sid = %s 
    ORDER BY sid, category
   """

    SQL=PROC_MEM% (sid)
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list = []
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        a_list.append(str_chk)
      table_list.append(a_list)

    headers = [term.blue+"INST_ID","SID","SERIAL","PID","CATEGORY","ALLOCATED(Byte)","USED","MAX_ALLOCATED"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def temp_consume(conn):
  cur = conn.cursor()

  try:
    TMP="""select * from(
	SELECT   S.inst_id, S.sid, S.serial#, S.username, S.client_identifier, P.spid, S.module, S.program, SUM (T.blocks) * TBS.block_size / 1024 / 1024 as "mb_used", T.tablespace, COUNT(*) as "sort_ops"
	FROM     gv$sort_usage T, gv$session S, dba_tablespaces TBS, gv$process P
	WHERE    T.session_addr = S.saddr
	AND      S.paddr = P.addr
	AND      T.tablespace = TBS.tablespace_name
	GROUP BY S.inst_id, S.sid, S.serial#, S.username, S.client_identifier, P.spid, S.module, S.program, TBS.block_size, T.tablespace
	ORDER BY 9 desc) where rownum <= 20
   """

    cur.execute(TMP)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list = []
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        a_list.append(str_chk)
      table_list.append(a_list)

    headers = [term.blue+"INSTANCE","SID","SERIAL","USER","CLIENT","PID","MODULE","PROGRAM","MB_USED","TEMP","SORT_OPS"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def undo_consume(conn):
  cur = conn.cursor()

  try:
    UNDO="""
	with t1 as
		(
	     	select sum(dux.bytes) duxbt, dux.tablespace_name
	    	from dba_undo_extents dux
	     	where dux.STATUS IN ('ACTIVE', 'UNEXPIRED')     
	     	group by dux.tablespace_name
		),t2 as
		(
	     	select sum(df.maxbytes) dfbt, df.tablespace_name,count(df.file_id) cnt,df.maxbytes,df.autoextensible
	     	from dba_data_files df,dba_tablespaces dt
	     	where dt.contents = 'UNDO'
	     	and dt.tablespace_name = df.TABLESPACE_NAME
	     	group by df.TABLESPACE_NAME,df.maxbytes,df.autoextensible
		)
	select t1.tablespace_name,round(((t1.duxbt*100)/t2.dfbt),1),t2.cnt,t2.maxbytes,t2.autoextensible
	from t1,t2
	where t1.tablespace_name = t2.tablespace_name 
   """

    cur.execute(UNDO)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list = []
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        a_list.append(str_chk)
      table_list.append(a_list)

    headers = [term.blue+"TABLESPACE","ACTIVE/UNEXPIRED %","COUNT","MAX_BYTES","AUTOEXT"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def undo_stat(conn,sql_id):
  cur = conn.cursor()

  try:
    OBJ_STAT="""
	select inst_id,begin_time,end_time,undoblks,maxquerylen,maxqueryid,maxconcurrency,ssolderrcnt,nospaceerrcnt,activeblks,unexpiredblks,expiredblks,tuned_undoretention
	from gv$undostat
	where maxqueryid = '%s'
   """
    SQL=OBJ_STAT% (sql_id)
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list = []
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        a_list.append(str_chk)
      table_list.append(a_list)

    headers = [term.blue+"INST","BTIME","ETIME","BLKS","DURATION(S)","SQL_ID","CONCURRENCY","OLDERR","SPACEERR","ACTIVEBLKS","UNEXPBLKS","EXPBLKS","TUNED_UNDO"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def object_stat_by_object(conn,obj,sec_sleep):
  cur = conn.cursor()
  table_list_res = []

  try:
    UNDO_STAT1="""
	select sysdate,inst_id,owner,object_name,object_type,statistic_name,value from gv$segment_statistics where upper(object_name) = upper('%s') order by statistic_name
   """
    SQL=UNDO_STAT1% (obj)
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list = []
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        a_list.append(str_chk)
      table_list.append(a_list)

    time.sleep(float(sec_sleep))

    UNDO_STAT2="""
        select sysdate,inst_id,owner,object_name,object_type,statistic_name,value from gv$segment_statistics where upper(object_name) = upper('%s') order by statistic_name
   """
    SQL=UNDO_STAT2% (obj)
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list = []
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        a_list.append(str_chk)
      table_list2.append(a_list)

    for a in range(len(table_list)):
      b_list = []
      for b in range(len(table_list2)):
        if (str(table_list[a][5]) == str(table_list2[b][5]) and int(table_list[a][1] == table_list2[b][1])):
          b_list.append(table_list2[a][0])
          b_list.append(table_list2[a][1])
          b_list.append(table_list2[a][2])
          b_list.append(table_list2[a][3])
          b_list.append(table_list2[a][4])
          b_list.append(table_list2[a][5])
          b_list.append(table_list[a][6])
          b_list.append(table_list2[a][6])
          diff = int(table_list2[b][6]) - int(table_list[a][6])
          if (table_list2[b][6] > 0 and diff > 0):
            diff_pct = int((diff*100)/int(table_list2[a][6]))
          else:
            diff_pct = 0
          if diff > 0:
            diff = "+"+str(diff)
          b_list.append(diff)
          b_list.append(diff_pct)
      table_list_res.append(b_list)

    headers = [term.blue+"DATE","INST","OWNER","NAME","TYPE","STAT","BVALUE","EVALUE","DIFF","DIFF%"+term.normal]

    curr_time()
    print tabulate(table_list_res,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def lc_pin(conn):
  cur = conn.cursor()

  try:
    LCP="""
	select
 distinct
   ses.inst_id, ses.ksusenum sid, ses.ksuseser serial#, ses.KSUSECLID username,substr(ses.ksusemnm,10) module ,
   ob.kglnaown obj_owner, ob.kglnaobj obj_name
   ,pn.kglpncnt pin_cnt, pn.kglpnmod pin_mode, pn.kglpnreq pin_req
   , w.state, w.event, ses.KSUSESQI, w.seconds_in_Wait
 from
  x$kglpn pn,  x$kglob ob,x$ksuse ses
   , gv$session_wait w
where pn.kglpnhdl in
(select kglpnhdl from x$kglpn where kglpnreq >0 )
and ob.kglhdadr = pn.kglpnhdl
and pn.kglpnuse = ses.addr
and w.sid = ses.indx
and ses.inst_id = w.inst_id
order by seconds_in_wait desc
   """

    cur.execute(LCP)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list = []
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        a_list.append(str_chk)
      table_list.append(a_list)

    headers = [term.blue+"INST_ID","SID","SERIAL","UNAME","MODULE","OBJ_OWNER","OBJ_NAME","PIN_CNT","PIN_MODE","PIN_REQ","STATE","EVENT","SQL_ID","SEC"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def time_model(conn,inst_id):
  cur = conn.cursor()

  try:
    TIME_MODEL="""
    SELECT LPAD(' ', 2*level-1)||stat_name stat_name, 
       trunc(value/1000000,2) seconds 
  FROM (
select 0 id, 9 pid, null stat_name, null value from dual union
select decode(stat_name,'DB time',10) id ,
       decode(stat_name,'DB time',0) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'DB time' and inst_id = '%s' union
select decode(stat_name,'DB CPU',20) id ,
       decode(stat_name,'DB CPU',10) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'DB CPU' and inst_id = '%s' union
select decode(stat_name,'connection management call elapsed time',21) id ,
       decode(stat_name,'connection management call elapsed time',10) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'connection management call elapsed time' and inst_id = '%s' union
select decode(stat_name,'sequence load elapsed time',22) id ,
       decode(stat_name,'sequence load elapsed time',10) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'sequence load elapsed time' and inst_id = '%s' union
select decode(stat_name,'sql execute elapsed time',23) id ,
       decode(stat_name,'sql execute elapsed time',10) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'sql execute elapsed time' and inst_id = '%s' union
select decode(stat_name,'parse time elapsed',24) id ,
       decode(stat_name,'parse time elapsed',10) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'parse time elapsed' and inst_id = '%s' union
select decode(stat_name,'hard parse elapsed time',30) id ,
       decode(stat_name,'hard parse elapsed time',24) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'hard parse elapsed time' and inst_id = '%s' union
select decode(stat_name,'hard parse (sharing criteria) elapsed time',40) id ,
       decode(stat_name,'hard parse (sharing criteria) elapsed time',30) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'hard parse (sharing criteria) elapsed time' and inst_id = '%s' union
select decode(stat_name,'hard parse (bind mismatch) elapsed time',50) id ,
       decode(stat_name,'hard parse (bind mismatch) elapsed time',40) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'hard parse (bind mismatch) elapsed time' and inst_id = '%s' union
select decode(stat_name,'failed parse elapsed time',31) id ,
       decode(stat_name,'failed parse elapsed time',24) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'failed parse elapsed time' and inst_id = '%s' union
select decode(stat_name,'failed parse (out of shared memory) elapsed time',41) id ,
       decode(stat_name,'failed parse (out of shared memory) elapsed time',31) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'failed parse (out of shared memory) elapsed time' and inst_id = '%s' union
select decode(stat_name,'PL/SQL execution elapsed time',25) id ,
       decode(stat_name,'PL/SQL execution elapsed time',10) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'PL/SQL execution elapsed time' and inst_id = '%s' union
select decode(stat_name,'inbound PL/SQL rpc elapsed time',26) id ,
       decode(stat_name,'inbound PL/SQL rpc elapsed time',10) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'inbound PL/SQL rpc elapsed time' and inst_id = '%s' union
select decode(stat_name,'PL/SQL compilation elapsed time',27) id ,
       decode(stat_name,'PL/SQL compilation elapsed time',10) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'PL/SQL compilation elapsed time' and inst_id = '%s' union
select decode(stat_name,'Java execution elapsed time',28) id ,
       decode(stat_name,'Java execution elapsed time',10) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'Java execution elapsed time' and inst_id = '%s' union
select decode(stat_name,'repeated bind elapsed time',29) id ,
       decode(stat_name,'repeated bind elapsed time',10) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'repeated bind elapsed time' and inst_id = '%s' union
select decode(stat_name,'background elapsed time',1) id ,
       decode(stat_name,'background elapsed time',0) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'background elapsed time' and inst_id = '%s' union
select decode(stat_name,'background cpu time',2) id ,
       decode(stat_name,'background cpu time',1) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'background cpu time' and inst_id = '%s' union
select decode(stat_name,'RMAN cpu time (backup/restore)',3) id ,
       decode(stat_name,'RMAN cpu time (backup/restore)',2) pid , stat_name, value
  from gv$sys_time_model
 where stat_name = 'RMAN cpu time (backup/restore)' and inst_id = '%s') 
CONNECT BY PRIOR id = pid START WITH id = 0
   """

    SQL=TIME_MODEL% (inst_id,inst_id,inst_id,inst_id,inst_id,inst_id,inst_id,inst_id,inst_id,inst_id,inst_id,inst_id,inst_id,inst_id,inst_id,inst_id,inst_id,inst_id,inst_id)
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list = []
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
	match = re.search(ur"^ ",str_chk)
	if match:
	  str_chk = term.red+str_chk+term.normal
        a_list.append(str_chk)
      table_list.append(a_list)

    headers = [term.blue+"STAT_NAME","SECONDS"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def sql_stat(conn,sql_id,total):
  cur = conn.cursor()

  try:
    if total == 'true':
      SQL_STAT_TOTAL="""select * from (
	select hsqls.snap_id as ID,
	hsqls.sql_id as SQL,
	hsqls.optimizer_cost as COST,
	hsqls.sorts_total as SORTS,
	hsqls.executions_total as EXE,
	hsqls.parse_calls_total as PARSES,
	hsqls.buffer_gets_total as BUFFERS,
	hsqls.rows_processed_total as ROWS_,
	hsqls.cpu_time_total as CPU_TIME,
	hsqls.iowait_total as IOWAITS,
	hsqls.apwait_total as APWAITS,
	hsqls.ccwait_total as CCWAITS,
	hsqls.physical_read_bytes_total as BYTES_READ,
	hsqls.physical_write_bytes_total as BYTES_WRITE,
	hsqls.elapsed_time_total as ELAPSED
	from dba_hist_sqlstat hsqls
	where sql_id = '%s'
	order by 1 desc) where rownum <= 30
      """
      SQL=SQL_STAT_TOTAL% (sql_id)

    if total == 'false':
      SQL_STAT_DELTA="""select * from (
        select hsqls.snap_id as ID,
        hsqls.sql_id as SQL,
        hsqls.optimizer_cost as COST,
        hsqls.sorts_delta as SORTS,
        hsqls.executions_delta as EXE,
        hsqls.parse_calls_delta as PARSES,
        hsqls.buffer_gets_delta as BUFFERS,
        hsqls.rows_processed_delta as ROWS_,
        hsqls.cpu_time_delta as CPU_TIME,
        hsqls.iowait_delta as IOWAITS,
        hsqls.apwait_delta as APWAITS,
        hsqls.ccwait_delta as CCWAITS,
        hsqls.physical_read_bytes_delta as BYTES_READ,
        hsqls.physical_write_bytes_delta as BYTES_WRITE,
        hsqls.elapsed_time_delta as ELAPSED
        from dba_hist_sqlstat hsqls
        where sql_id = '%s'
        order by 1 desc) where rownum <= 30
      """
      SQL=SQL_STAT_DELTA% (sql_id)

    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list = []
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        a_list.append(str_chk)
      table_list.append(a_list)

    headers = [term.blue+"SNAP","SQL","COST","SORTS","EXEC","PARSES","BUFFERS","ROWS","CPU_TIME","IOWAITS","APWAITS","CCWAITS","BYTES_READ","BYTES_WRITE","ELAPSED"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def sql_stat_by_snap_id(conn,sql_id,snap_id,total):
  cur = conn.cursor()

  try:
    if total == 'true':
      SQL_STAT_TOTAL="""select * from (
        select hsqls.snap_id as ID,
        hsqls.sql_id as SQL,
        hsqls.optimizer_cost as COST,
        hsqls.sorts_total as SORTS,
        hsqls.executions_total as EXE,
        hsqls.parse_calls_total as PARSES,
        hsqls.buffer_gets_total as BUFFERS,
        hsqls.rows_processed_total as ROWS_,
        hsqls.cpu_time_total as CPU_TIME,
        hsqls.iowait_total as IOWAITS,
        hsqls.apwait_total as APWAITS,
        hsqls.ccwait_total as CCWAITS,
        hsqls.physical_read_bytes_total as BYTES_READ,
        hsqls.physical_write_bytes_total as BYTES_WRITE,
        hsqls.elapsed_time_total as ELAPSED
        from dba_hist_sqlstat hsqls
        where sql_id = '%s' and snap_id = %s
        order by 1 desc) where rownum <= 30
      """
      SQL=SQL_STAT_TOTAL% (sql_id,snap_id)

    if total == 'false':
      SQL_STAT_DELTA="""select * from (
        select hsqls.snap_id as ID,
        hsqls.sql_id as SQL,
        hsqls.optimizer_cost as COST,
        hsqls.sorts_delta as SORTS,
        hsqls.executions_delta as EXE,
        hsqls.parse_calls_delta as PARSES,
        hsqls.buffer_gets_delta as BUFFERS,
        hsqls.rows_processed_delta as ROWS_,
        hsqls.cpu_time_delta as CPU_TIME,
        hsqls.iowait_delta as IOWAITS,
        hsqls.apwait_delta as APWAITS,
        hsqls.ccwait_delta as CCWAITS,
        hsqls.physical_read_bytes_delta as BYTES_READ,
        hsqls.physical_write_bytes_delta as BYTES_WRITE,
        hsqls.elapsed_time_delta as ELAPSED
        from dba_hist_sqlstat hsqls
        where sql_id = '%s' and snap_id = %s
        order by 1 desc) where rownum <= 30
      """
      SQL=SQL_STAT_DELTA% (sql_id,snap_id)

    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list = []
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        a_list.append(str_chk)
      table_list.append(a_list)

    headers = [term.blue+"SNAP","SQL","COST","SORTS","EXEC","PARSES","BUFFERS","ROWS","CPU_TIME","IOWAITS","APWAITS","CCWAITS","BYTES_READ","BYTES_WRITE","ELAPSED"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def sql_stat_per_exec_between_snap(conn,sql_id,snap_s,snap_e):
  cur = conn.cursor()

  try:
    SQL_STAT_DELTA="""select hsql.snap_id as ID,
        hsql.sql_id as SQL,
        hsql.optimizer_cost as COST,
        round(hsql.sorts_delta/decode(hsql.executions_delta,0,1,hsql.executions_delta)) as SORTS,
        round(hsql.executions_delta) as EXEC,
        round(hsql.parse_calls_delta/decode(hsql.executions_delta,0,1,hsql.executions_delta)) as PARSES,
        round(hsql.buffer_gets_delta/decode(hsql.executions_delta,0,1,hsql.executions_delta)) as BUFFERS,
	round(hsql.fetches_delta/decode(hsql.executions_delta,0,1,hsql.executions_delta)) as FETCHES,
        round(hsql.rows_processed_delta/decode(hsql.executions_delta,0,1,hsql.executions_delta)) as ROWS_,
        round(hsql.cpu_time_delta/decode(hsql.executions_delta,0,1,hsql.executions_delta)) as CPU_TIME,
        round(hsql.iowait_delta/decode(hsql.executions_delta,0,1,hsql.executions_delta)) as IOWAITS,
        round(hsql.apwait_delta/decode(hsql.executions_delta,0,1,hsql.executions_delta)) as APWAITS,
        round(hsql.ccwait_delta/decode(hsql.executions_delta,0,1,hsql.executions_delta)) as CCWAITS,
        round(hsql.physical_read_bytes_delta/decode(hsql.executions_delta,0,1,hsql.executions_delta)) as BYTES_READ,
        round(hsql.physical_write_bytes_delta/decode(hsql.executions_delta,0,1,hsql.executions_delta)) as BYTES_WRITE,
        round(hsql.elapsed_time_delta/decode(hsql.executions_delta,0,1,hsql.executions_delta)) as ELAPSED,
	round(hsql.plsexec_time_delta/decode(hsql.executions_delta,0,1,hsql.executions_delta)) as PLSQL
        from dba_hist_sqlstat hsql
        where hsql.sql_id = '%s' and hsql.snap_id between %s and %s
        order by 1 desc
    """
    SQL=SQL_STAT_DELTA% (sql_id,snap_s,snap_e)

    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list = []
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        a_list.append(str_chk)
      table_list.append(a_list)

    headers = [term.blue+"SNAP","SQL","COST","SORTS","EXEC","PARSES","BUFFERS","FETCHES","ROWS","CPU_TIME","IOWAITS","APWAITS","CCWAITS","BYTES_READ","BYTES_WRITE","ELAPSED","PL/SQL"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def clinfo(conn,sid,serial,inst,sid2,serial2,inst2):
  cur = conn.cursor()

  try:
    SQL_INFO="""select * from (select ash.inst_id,ash.sql_exec_start,ash.sql_id,ash.sql_plan_hash_value,ash.top_level_sql_id,ash.event,ash.top_level_call_name,
				ash.action,ash.client_id,ash.machine,ash.temp_space_allocated 
				from gv$active_session_history ash
				where ash.session_id = %s and ash.session_serial# = %s and inst_id = %s
				order by sample_id desc)
		where rownum <= 20
    """
    SQL=SQL_INFO% (sid,serial,inst)

    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list = []
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        a_list.append(str_chk)
      table_list.append(a_list)

    headers = [term.blue+"INST","SQL_EXEC_START","SQL_ID","PLAN","TOP_LEVEL_SQL","EVENT","TOP_LEVEL_CALL_NAME","ACTION","CLIENT","MACHINE","TEMP"+term.normal]

    curr_time()
    print term.green+"INFORAMTION FROM ASH"+term.normal
    print tabulate(table_list,headers,tablefmt="plain")

    SQL_SESSION="""
	select inst_id,sql_exec_start,sql_id,sql_hash_value,prev_sql_id,prev_hash_value,module,action,row_wait_obj#,client_identifier,status,event
	from gv$session where sid = %s and serial# = %s and inst_id = %s
	"""

    SQL2=SQL_SESSION% (sid2,serial2,inst2)

    cur.execute(SQL2)  
    res2 = cur.fetchall()

    for a in range(len(res2)):
      a_list = []
      for b in range(len(res2[a])):
        str_chk = str(res2[a][b])
        a_list.append(str_chk)
      table_list2.append(a_list)

    headers = [term.blue+"INST","SQL_EXEC_START","SQL_ID","PLAN","PREV_LEVEL_SQL","PREV_PLAN","MODULE","ACTION","OBJECT_WAIT","CLIENT","STATUS","EVENT"+term.normal]

    curr_time()
    print term.green+"INFORMATION FROM SESSION"+term.normal   
    print tabulate(table_list2,headers,tablefmt="plain")


  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def top_sql_for_object(conn,obj,obj_type,sql_opt):
  cur = conn.cursor()

  try:
    SQL_INFO="""select * from (select count(sql_id),sql_id,sql_plan_hash_value from gv$active_session_history
                                where current_obj# in (select object_id from dba_objects
                                 where upper(object_name) = upper('%s') and upper(object_type) = upper('%s'))
				and upper(sql_plan_options) = upper('%s')
                                group by sql_id,sql_plan_hash_value order by 1 desc)
                where rownum <= 20
    """
    SQL=SQL_INFO% (obj,obj_type,sql_opt)

    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list = []
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        a_list.append(str_chk)
      table_list.append(a_list)

    headers = [term.blue+"COUNT","SQL_ID","PLAN"+term.normal]

    curr_time()
    print term.green+"INFORAMTION FROM ASH"+term.normal
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def blocks_involved_sql_hist(conn,obj,obj_type,sql_id,begin_s,end_s):
  cur = conn.cursor()

  try:
    SQL_INFO="""select * from (select count(p2),p2,p1 from dba_hist_active_sess_history
                                where current_obj# in (select object_id from dba_objects
                                 where upper(object_name) = upper('%s') and upper(object_type) = upper('%s'))
                                and lower(sql_id) = lower('%s') and p2text = 'block#' and p1text = 'file#' and snap_id between %s and %s
                                group by p2,p1 order by p2,p1 desc)
                where rownum <= 20
    """
    SQL=SQL_INFO% (obj,obj_type,sql_id,begin_s,end_s)

    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list = []
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        a_list.append(str_chk)
      table_list.append(a_list)

    headers = [term.blue+"COUNT","BLOCK","FILE"+term.normal]

    curr_time()
    print term.green+"INFORAMTION FROM ASH"+term.normal
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def rowid_from_block(conn,obj,fno,block):
  cur = conn.cursor()

  try:
    SQL_INFO="""select rowid from %s where dbms_rowid.rowid_relative_fno(rowid) = %s and dbms_rowid.rowid_block_number(rowid) in (%s) order by 1"""
    SQL=SQL_INFO% (obj,fno,block)

    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list = []
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        a_list.append(str_chk)
      table_list.append(a_list)

    headers = [term.blue+"ROWID"+term.normal]

    curr_time()
    print term.green+"INFORAMTION FROM ASH"+term.normal
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def snap_stat(conn,rows,snap):
  cur = conn.cursor()

  try:
    if rows:
      SQL_STAT="""select * from (
                  select instance_number,snap_id,begin_interval_time,end_interval_time from dba_hist_snapshot
                  order by 2 desc) where rownum <= %s
               """
      SQL=SQL_STAT% (rows)

    if snap:
      SQL_SNAP="""select instance_number,snap_id,begin_interval_time,end_interval_time from dba_hist_snapshot
                  where snap_id = %s
               """
      SQL=SQL_SNAP% (snap)

    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list = []
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        a_list.append(str_chk)
      table_list.append(a_list)

    headers = [term.blue+"INST","SNAP","BEGIN","END"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def ash_wait_tree(conn,event,sql_id):
  try:
    ASH_WAIT_TREE ="""
    with ash as (select /*+ materialize */ * from gv$active_session_history)
    select LPAD(' ',(LEVEL-1)*2)|| 'INST#' || inst_id || ' SID#' || session_id || ' '||decode(ash.session_type,'BACKGROUND',REGEXP_SUBSTR(program, '\([^\)]+\)'),'FOREGROUND') as BLOCKING_TREE,module,client_id,ash.EVENT,sql_id,sql_plan_hash_value,top_level_sql_id,
    count(*) as WAITS_COUNT,
    round(avg(time_waited) / 1000) as AVG_TIME_WAITED_MS
      from ash
      where session_state = 'WAITING'
      start with event like '%s' and sql_id = '%s'
      connect by nocycle prior ash.SAMPLE_ID = ash.SAMPLE_ID and ash.SESSION_ID = prior ash.BLOCKING_SESSION
    group by LEVEL,LPAD(' ',(LEVEL-1)*2)|| 'INST#' || inst_id || ' SID#' || session_id || ' '||decode(ash.session_type,'BACKGROUND',REGEXP_SUBSTR(program, '\([^\)]+\)'),'FOREGROUND'),module,client_id,ash.EVENT,sql_id,sql_plan_hash_value,top_level_sql_id
    order by LEVEL, count(*) desc
    """

    SQL=ASH_WAIT_TREE% (event,sql_id)

    cur = conn.cursor()
    cur.execute(SQL)
    res = cur.fetchall()
    
    for a in range(len(res)):
    	a_list=[]
    	for b in range(len(res[a])):
    		str_chk = str(res[a][b])
    		match = re.search(ur"^ ",str_chk)
    		if match:
    		  str_chk = term.red+str_chk+term.normal
    		a_list.append(str_chk)
    	table_list.append(a_list)
    	
    headers = [term.blue+"BLOCKING_TREE","MODULE","CLIENT_ID","EVENT","SQL_ID","PLAN","TOP_LEVEL_SQL_ID","WAIT_COUNT","AVG_WAIT(ms)"+term.normal]
    	
    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")
  
  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def sql_text(conn,sql_id):
  try:
    SQL_TEXT ="""
	select sql_fulltext from gv$sql where sql_id = '%s' and rownum <=1
    """

    SQL=SQL_TEXT% (sql_id)

    cur = conn.cursor()
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
        a_list=[]
        for b in range(len(res[a])):
                str_chk = str(res[a][b])
                #match = re.search(ur"\n",str_chk)
                #if match:
                  #str_chk = str_chk+"  "
                a_list.append(str_chk)
        table_list.append(a_list)

    headers = [term.blue+"SQL_TEXT"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def sql_bind(conn,sql_id,snap_id):
  try:
    SQL_BIND ="""
        select snap_id,sql_id,name,datatype_string,value_string,last_captured from dba_hist_sqlbind where sql_id = '%s' and snap_id = %s
    """

    SQL=SQL_BIND% (sql_id,snap_id)

    cur = conn.cursor()
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
        a_list=[]
        for b in range(len(res[a])):
                str_chk = str(res[a][b])
                #match = re.search(ur"^ ",str_chk)
                #if match:
                  #str_chk = term.red+str_chk+term.normal
                a_list.append(str_chk)
        table_list.append(a_list)

    headers = [term.blue+"SNAP","SQL_ID","NAME","TYPE","VALUE","CAPTURED"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info


def ash_wait_tree_hist(conn,sql_or_event,sql_or_event_value,snap_b,snap_e):
  try:
    ASH_WAIT_TREE_HIST ="""
		with ash as (select /*+ materialize */ * from dba_hist_active_sess_history where '%s' is null OR snap_id between '%s' and nvl('%s','%s'))
		select LPAD(' ',(LEVEL-1)*2)|| 'INST#' || instance_number || ' SID#' || session_id || ' '||decode(ash.session_type,'BACKGROUND',REGEXP_SUBSTR(program, '\([^\)]+\)'), nvl2(qc_session_id, 'PX', 'FOREGROUND')) as BLOCKING_TREE,module,client_id,sql_id,sql_plan_hash_value,
       decode(session_state, 'WAITING', EVENT, 'On CPU / runqueue') as EVENT,
       count(*) as WAITS_COUNT,
       count(distinct session_id) as SESS_COUNT,
       round(avg(time_waited) / 1000) as AVG_WAIT_TIME_MS
			 from ash
			 start with %s like '%s'
			 connect by nocycle prior ash.SAMPLE_ID = ash.SAMPLE_ID
       and ash.SESSION_ID = prior ash.BLOCKING_SESSION
       and ash.instance_number = prior ash.BLOCKING_inst_id
			 group by LEVEL,
          instance_number,
          LPAD(' ',(LEVEL-1)*2)|| 'INST#' || instance_number || ' SID#' || session_id || ' '||decode(ash.session_type,'BACKGROUND',REGEXP_SUBSTR(program, '\([^\)]+\)'),nvl2(qc_session_id, 'PX', 'FOREGROUND')),module,client_id,sql_id,sql_plan_hash_value,
          decode(session_state, 'WAITING', EVENT, 'On CPU / runqueue')
					order by instance_number, LEVEL, count(*) desc
		"""
		
    SQL=ASH_WAIT_TREE_HIST% (snap_b,snap_b,snap_e,snap_b,sql_or_event,sql_or_event_value)
		
    cur = conn.cursor()
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list=[]
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        match = re.search(ur"^ ",str_chk)
        if match:
          str_chk = term.red+str_chk+term.normal
        a_list.append(str_chk)
      table_list.append(a_list)
    	
    headers = [term.blue+"BLOCKING_TREE","MODULE","CLIENT_ID","SQL_ID","PLAN","EVENT","WAITS_COUNT","SESS_COUNT","AVG_WAIT(ms)"+term.normal]
    	
    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")
		
  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def ash_wait_tree_hist_sum(conn,sql_or_event,sql_or_event_value,snap_b,snap_e):
  try:
    ASH_WAIT_TREE_HIST ="""
        with ash as (select /*+ materialize */ * from dba_hist_active_sess_history where '%s' is null OR snap_id between '%s' and nvl('%s','%s')) select
	module,client_id,sql_id,sql_plan_hash_value,
        decode(session_state, 'WAITING', EVENT, 'On CPU / runqueue') as EVENT,
        count(*) as WAITS_COUNT,
        count(distinct session_id) as SESS_COUNT,
        round(avg(time_waited) / 1000) as AVG_WAIT_TIME_MS
                         from ash
                         start with %s = '%s'
                         connect by nocycle prior ash.SAMPLE_ID = ash.SAMPLE_ID
       and ash.SESSION_ID = prior ash.BLOCKING_SESSION
       and ash.instance_number = prior ash.BLOCKING_inst_id
                         group by 
          instance_number,module,client_id,sql_id,sql_plan_hash_value,
          decode(session_state, 'WAITING', EVENT, 'On CPU / runqueue')
                                        order by instance_number, count(*) desc
                """

    SQL=ASH_WAIT_TREE_HIST% (snap_b,snap_b,snap_e,snap_b,sql_or_event,sql_or_event_value)

    cur = conn.cursor()
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list=[]
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        match = re.search(ur"^ ",str_chk)
        if match:
          str_chk = term.red+str_chk+term.normal
        a_list.append(str_chk)
      table_list.append(a_list)

    headers = [term.blue+"MODULE","CLIENT_ID","SQL_ID","PLAN","EVENT","WAITS_COUNT","SESS_COUNT","AVG_WAIT(ms)"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def ash_sqlmon(conn,sql_id,inst_id,child,sql_plan):
  try:
    ASH_SQLMON ="""
	with ash as
 (select sql_id,
         sql_plan_hash_value,
         nvl(sql_plan_line_id, 0) as SQL_PLAN_LINE_ID,
         decode(session_state,'WAITING',event,session_state) as EVENT,
         count(*) as WAIT_COUNT
    from gv$active_session_history
   where sql_id = '%s' and inst_id = '%s' and sql_child_number = '%s'
     and sql_plan_hash_value = nvl('%s', sql_plan_hash_value)
     --and NVL(sql_exec_id, 0) = nvl('&3', NVL(sql_exec_id, 0))
   group by sql_id, sql_plan_hash_value, sql_plan_line_id, decode(session_state,'WAITING',event,session_state)),
ash_stat as
(select  sql_id,
        sql_plan_hash_value,
        sql_plan_line_id,
        rtrim(xmlagg(xmlelement(s, EVENT || '(' ||WAIT_COUNT, '); ').extract('//text()') order by WAIT_COUNT desc),',') as WAIT_PROFILE
from ash
group by sql_id,
         sql_plan_hash_value,
         sql_plan_line_id),
pt as
 (select
        id,
        operation,
        options,
        object_owner,
        object_name,
        parent_id
    from dba_hist_sql_plan
   where (sql_id, plan_hash_value) =
         (select distinct sql_id, sql_plan_hash_value from ash_stat)
  union -- for plans not in dba_hist_sql_plan yet
  select
        id,
        operation,
        options,
        object_owner,
        object_name,
        parent_id
    from gv$sql_plan
   where (sql_id, plan_hash_value) =
         (select distinct sql_id, sql_plan_hash_value from ash_stat))
SELECT pt.id,
       lpad(' ', 2 * level) || pt.operation || ' ' || pt.options as PLAN_OPERATION,
       pt.object_owner,
       pt.object_name,
       ash_stat.WAIT_PROFILE
  FROM pt
  left join ash_stat
    on pt.id = ash_stat.sql_plan_line_id
CONNECT BY PRIOR pt.id = pt.parent_id
 START WITH pt.id = 0
                """

    SQL=ASH_SQLMON% (sql_id,inst_id,child,sql_plan)
                
    cur = conn.cursor()
    cur.execute(SQL)
    res = cur.fetchall()
    
    for a in range(len(res)):
      a_list=[]
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        match = re.search(ur"^ ",str_chk)
        if match:
          str_chk = term.normal+str_chk+term.normal
        a_list.append(str_chk)
      table_list.append(a_list)
        
    headers = [term.blue+"ID","OPERATION","OBJECT_OWNER","OBJECT_NAME","PARENT_ID","WAIT_PROFILE"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

    SQLMON ="""
        select inst_id,status,module,action,sid,session_serial#,elapsed_time,cpu_time,fetches,buffer_gets,physical_read_bytes from gv$sql_monitor where sql_id= '%s' and inst_id = '%s'
    """

    SQLL=SQLMON% (sql_id,inst_id)

    cur2 = conn.cursor()
    cur2.execute(SQLL)
    resa = cur2.fetchall()

    for aa in range(len(resa)):
      aa_list=[]
      for bb in range(len(resa[aa])):
        str_chka = str(resa[aa][bb])
        #matcha = re.search(ur"^ ",str_chka)
        #if matcha:
          #str_chka = term.normal+str_chka+term.normal
        aa_list.append(str_chka)
      table_list2.append(aa_list)

    headers2 = [term.blue+"INST","STATUS","MODULE","ACTION","SID","SER#","ELA","CPU","FETCH","BUFFER_GETS","PHY_READ_BYTE"+term.normal]

    curr_time()
    print tabulate(table_list2,headers2,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def ash_sqlmon_hist(conn,sql_id,sql_plan,snap_b,snap_e):
  try:
    ASH_SQLMON_HIST ="""
  	with ash as
 (select sql_id,
         sql_plan_hash_value,
         nvl(sql_plan_line_id, 0) as SQL_PLAN_LINE_ID,
         decode(session_state,'WAITING',event,session_state) as EVENT,
         count(*) as WAIT_COUNT
    from dba_hist_active_sess_history
   where sql_id = '%s'
     and sql_plan_hash_value = nvl('%s', sql_plan_hash_value)
     --and NVL(sql_exec_id, 0) = nvl('&3', NVL(sql_exec_id, 0))
     and snap_id between %s and %s
   group by sql_id, sql_plan_hash_value, sql_plan_line_id, decode(session_state,'WAITING',event,session_state)),
ash_stat as
(select  sql_id,
        sql_plan_hash_value,
        sql_plan_line_id,
        rtrim(xmlagg(xmlelement(s, EVENT || '(' ||WAIT_COUNT, '); ').extract('//text()') order by WAIT_COUNT desc),',') as WAIT_PROFILE
from ash
group by sql_id,
         sql_plan_hash_value,
         sql_plan_line_id),
pt as
 (select *
    from dba_hist_sql_plan
   where (sql_id, plan_hash_value) =
         (select distinct sql_id, sql_plan_hash_value from ash_stat))
SELECT pt.id,
       lpad(' ', 2 * level) || pt.operation || ' ' || pt.options as PLAN_OPERATION,
       pt.object_owner,
       pt.object_name,
       pt.cost,
       pt.cardinality,
       pt.bytes,
       pt.qblock_name,
       pt.temp_space,
       ash_stat.WAIT_PROFILE
  FROM pt
  left join ash_stat
    on pt.id = ash_stat.sql_plan_line_id
CONNECT BY PRIOR pt.id = pt.parent_id
 START WITH pt.id = 0
	"""
    SQL=ASH_SQLMON_HIST% (sql_id,sql_plan,snap_b,snap_e)

    cur = conn.cursor()
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
      a_list=[]
      for b in range(len(res[a])):
        str_chk = str(res[a][b])
        match = re.search(ur"^ ",str_chk)
        if match:
          str_chk = term.normal+str_chk+term.normal
        a_list.append(str_chk)
      table_list.append(a_list)

    headers = [term.blue+"ID","OPERATION","OBJECT_OWNER","OBJECT_NAME","COST","CARDINALITY","BYTES","QBLOCK","TMP_SPACE","WAIT_PROFILE"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def top_30_event(conn):
  try:
    SQL_BIND ="""
        select * from (select event, sum(wait_time+time_waited) ttl_wait_time from gv$active_session_history where sample_time between sysdate - 60/2880 and sysdate and event is not null
        group by event order by 2 desc) where rownum <= 30
    """

    SQL=SQL_BIND% ()

    cur = conn.cursor()
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
        a_list=[]
        for b in range(len(res[a])):
                str_chk = str(res[a][b])
                #match = re.search(ur"^ ",str_chk)
                #if match:
                  #str_chk = term.red+str_chk+term.normal
                a_list.append(str_chk)
        table_list.append(a_list)

    headers = [term.blue+"EVENT","WAIT_TIME+TIME_WAITED"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def eventh(conn,snap_begin,snap_end,event):
  try:
    SQL_BIND ="""
        select he.snap_id,he.wait_count,he.wait_time_milli,he.event_name from dba_hist_event_histogram he where he.snap_id between %s and %s and he.event_name like '%s'
        order by 1 desc,he.wait_time_milli
    """

    SQL=SQL_BIND% (snap_begin,snap_end,event)

    cur = conn.cursor()
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
        a_list=[]
        for b in range(len(res[a])):
                str_chk = str(res[a][b])
                #match = re.search(ur"^ ",str_chk)
                #if match:
                  #str_chk = term.red+str_chk+term.normal
                a_list.append(str_chk)
        table_list.append(a_list)

    headers = [term.blue+"SNAP_ID","WAIT_COUNT","WAIT_TIME_MILLI","EVENT"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def tab_stat(conn,table_name):
  try:
    SQL_TAB ="""
	select owner,table_name,tablespace_name,status,num_rows,blocks,last_analyzed,partitioned,temporary,chain_cnt from all_tables where table_name = '%s'
    """

    SQL=SQL_TAB% (table_name)
       
    cur = conn.cursor()
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
        a_list=[]
        for b in range(len(res[a])):
                str_chk = str(res[a][b])
                #match = re.search(ur"^ ",str_chk)
                #if match:
                  #str_chk = term.red+str_chk+term.normal
                a_list.append(str_chk)
        table_list.append(a_list)

    headers = [term.blue+"OWNER","NAME","TSPACE","STATUS","ROWS","BLOCKS","LAST_ANALYZED","PARTITIONED","TEMPORARY","CHAINED"+term.normal]

    curr_time()
    print term.green+"TABLE"+term.normal
    print tabulate(table_list,headers,tablefmt="plain")
  
    SQL_IND ="""
        select owner,index_name,index_type,table_name,uniqueness,clustering_factor,leaf_blocks,num_rows,status,last_analyzed,partitioned,visibility,degree from dba_indexes where table_name = '%s'
    """

    SQL2=SQL_IND% (table_name)

    cur2 = conn.cursor()
    cur2.execute(SQL2)
    res2 = cur2.fetchall()

    for a in range(len(res2)):
        a_list2=[]
        for b in range(len(res2[a])):
                str_chk = str(res2[a][b])
                #match = re.search(ur"^ ",str_chk)
                #if match:
                  #str_chk = term.red+str_chk+term.normal
                a_list2.append(str_chk)
        table_list2.append(a_list2)

    headers = [term.blue+"OWNER","NAME","TYPE","TABLE","UNIQ","CLUST_FACTOR","LEAF_BLOCKS","ROWS","STATUS","LAST_ANALYZED","PARTITIONED","VISIBLE","DEGREE"+term.normal]

    print "\n"
    print term.green+"INDEXES"+term.normal
    print tabulate(table_list2,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def top_30_modules(conn):
  try:
    SQL_BIND ="""
        select * from (select distinct(module),count(*) from gv$active_session_history where module not like '%%greed%%' and module not like '%%SCHEDULER%%' and module not like '%%oratop%%' and module not like '%%Developer%%' group by module order by 2 desc) where rownum <= 30
    """

    SQL=SQL_BIND% ()

    cur = conn.cursor()
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
        a_list=[]
        for b in range(len(res[a])):
                str_chk = str(res[a][b])
                #match = re.search(ur"^ ",str_chk)
                #if match:
                  #str_chk = term.red+str_chk+term.normal
                a_list.append(str_chk)
        table_list.append(a_list)

    headers = [term.blue+"MODULE","COUNT"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def top_30_modulesh(conn,snap_begin,snap_end):
  try:
    SQL_BIND ="""
        select * from (select distinct(module),count(*),snap_id from dba_hist_active_sess_history where snap_id between %s and %s and module not like '%%greed%%' and module not like '%%SCHEDULER%%' and module not like '%%oratop%%' and module not like '%%Developer%%' group by module,snap_id order by 2 desc) where rownum <= 30
    """ 

    SQL=SQL_BIND% (snap_begin,snap_end)

    cur = conn.cursor()
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
        a_list=[]
        for b in range(len(res[a])):
                str_chk = str(res[a][b])
                #match = re.search(ur"^ ",str_chk)
                #if match:
                  #str_chk = term.red+str_chk+term.normal
                a_list.append(str_chk)
        table_list.append(a_list)

    headers = [term.blue+"MODULE","COUNT","SNAP_ID"+term.normal]

    curr_time() 
    print tabulate(table_list,headers,tablefmt="plain")
  
  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def sql_by_module(conn,module):
  try:
    SQL_BIND ="""
        select * from (select distinct(sql_id),event,count(*) from gv$active_session_history where module = '%s' and sql_id is not null group by sql_id,event order by 3 desc) where rownum <= 30
    """

    SQL=SQL_BIND% (module)

    cur = conn.cursor()
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
        a_list=[]
        for b in range(len(res[a])):
                str_chk = str(res[a][b])
                #match = re.search(ur"^ ",str_chk)
                #if match:
                  #str_chk = term.red+str_chk+term.normal
                a_list.append(str_chk)
        table_list.append(a_list)

    headers = [term.blue+"SQL_ID"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def shared_cu(conn,sql_id):
  try:
    SQL_BIND ="""
        select s.inst_id as INST,
       s.EXECUTIONS as EXECS,
       to_char(to_date(s.last_load_time, 'yyyy-mm-dd/hh24:mi:ss'), 'dd.mm hh24:mi') as last_load_time,
       s.users_opening,
       to_char(s.last_active_time, 'dd.mm hh24:mi') as last_active_time,
       round(s.elapsed_time/decode(s.EXECUTIONS,0,1,s.EXECUTIONS)) as ELA_PER_EXEC,
       s.PLAN_HASH_VALUE,
       s.optimizer_cost,
       s.child_number as CHILD,
       s.IS_BIND_SENSITIVE as "BIND_SENSE",
       s.IS_BIND_AWARE as "BIND_AWARE",
       s.IS_SHAREABLE as "SHAREABLE",
       use_feedback_stats as USE_FEEDBACK_STATS,
       load_optimizer_stats as OPTIMIZER_STATS,
       bind_equiv_failure as BIND_EQ_FAILURE,
       ROLL_INVALID_MISMATCH,
       s.ROWS_PROCESSED,
       s.PARSE_CALLS
  from gv$sql_shared_cursor sc, gv$sql s
 where sc.sql_id = '%s'
   and sc.inst_id = s.inst_id
   and sc.child_address = s.child_address
   and sc.sql_id = s.sql_id
   and sc.inst_id > 0
and (s.EXECUTIONS>0 or s.users_opening>0)
order by s.inst_id, --s.child_number
    s.last_active_time desc
    """

    SQL=SQL_BIND% (sql_id)

    cur = conn.cursor()
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
        a_list=[]
        for b in range(len(res[a])):
                str_chk = str(res[a][b])
                #match = re.search(ur"^ ",str_chk)
                #if match:
                  #str_chk = term.red+str_chk+term.normal
                a_list.append(str_chk)
        table_list.append(a_list)

    desc = "EPE - ELA_PER_EXEC\n"+"BS - BIND_SENSITIVE\n"+"BA - BIND_AWARE\n"+"SH - SHARABLE\n"+"FS - FEEDBACK_STATISTIC\n"+"OS - OPTIMIZER_STATISTIC\n"+"BEF - BIND_EQUIV_FAILURE\n"+"RIM - ROLL_INVALID_MISMATCH\n"
    print desc
    headers = [term.blue+"INST","EXEC","LOAD_TIME","OPENING","ACTIVE_TIME","EPE","PLAN","COST","CHILD","BS","BA","SH","FS","OS","BEF","RIM","ROWS","PARSE_CALLS"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

    SQL_BIND2 ="""
       select s.inst_id
       ROLL_INVALID_MISMATCH,
       (select reasons || '  |  ' || details
          from xmltable('/ChildNode' passing
                        (select case when dbms_lob.instr(reason, '<ChildNode>', 1, 2) = 0 then
                                   xmltype(reason)
                                  else
                                    xmltype(dbms_lob.substr(reason, dbms_lob.instr(reason, '<ChildNode>', 1, 2) - 1))
                                  end as xmlval
                           from gv$sql_shared_cursor
                          where dbms_lob.substr(reason, 256) <> ' '
                            and sql_id = sc.sql_id
                            and inst_id = sc.inst_id
                            and child_address = sc.child_address)
                        columns Reasons varchar2(60) path '/ChildNode/reason',
                        Details varchar2(60) path '/ChildNode/details')) as Reason1,
       SQL_PLAN_BASELINE, 
       SQL_PATCH,
       OUTLINE_CATEGORY,
       SQL_PROFILE,
       IS_OBSOLETE
  from gv$sql_shared_cursor sc, gv$sql s
 where sc.sql_id = '%s'
   and sc.inst_id = s.inst_id
   and sc.child_address = s.child_address
   and sc.sql_id = s.sql_id
   and sc.inst_id > 0
and (s.EXECUTIONS>0 or s.users_opening>0)
order by s.inst_id, --s.child_number
    s.last_active_time desc
    """
    SQL2=SQL_BIND2% (sql_id)

    cur2 = conn.cursor()
    cur2.execute(SQL2)  
    res2 = cur2.fetchall()

    for a in range(len(res2)):
        a_list2=[]
        for b in range(len(res2[a])):
                str_chk2 = str(res2[a][b])
                #match = re.search(ur"^ ",str_chk)
                #if match:
                  #str_chk = term.red+str_chk+term.normal
                a_list2.append(str_chk2)
        table_list2.append(a_list2)

    headers2 = [term.blue+"INST","REASON","BASELINE","SQL_PATCH","OUTLINE_CATEGORY","SQL_PROFILE","OBSOLETE"+term.normal]

    print tabulate(table_list2,headers2,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def shared_cu_sum(conn,sql_id):
  try:
    SQL_BIND ="""
	with R as
 (select sc.inst_id as INST,
         is_obsolete,
         pq_slave_mismatch,
         top_level_rpi_cursor,
         (select reasons || '  |  ' || details
            from xmltable('/ChildNode' passing
                          (select case when dbms_lob.instr(reason, '', 1, 2) = 0 then xmltype(reason)
                                    else xmltype(dbms_lob.substr(reason, dbms_lob.instr(reason, '', 1, 2) - 1))
                                  end as xmlval
                             from gv$sql_shared_cursor
                            where dbms_lob.substr(reason, 256) <> ' '
                              and sql_id = sc.sql_id
                              and inst_id = sc.inst_id
                              and child_address = sc.child_address) columns
                          Reasons varchar2(60) path '/ChildNode/reason',
                          Details varchar2(60) path '/ChildNode/details')) as Reason
    from gv$sql_shared_cursor sc, gv$sql s
   where sc.sql_id = '%s'
     and sc.inst_id = s.inst_id
     and sc.sql_id = s.sql_id
     and sc.child_address = s.child_address)
select inst, count(*), is_obsolete, Reason
  from R
 group by inst, is_obsolete, Reason
 order by count(*) desc
    """ 

    SQL=SQL_BIND% (sql_id)

    cur = conn.cursor()
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
        a_list=[]
        for b in range(len(res[a])):
                str_chk = str(res[a][b])
                #match = re.search(ur"^ ",str_chk)
                #if match:
                  #str_chk = term.red+str_chk+term.normal
                a_list.append(str_chk)
        table_list.append(a_list)

    headers = [term.blue+"INST","COUNT","OBSOLETE","REASON"+term.normal]

    curr_time() 
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def purge_cu(conn,sql_id):
  try:
    SQL_BIND ="""
	declare
  v_address_hash varchar2(60);
begin
  select address || ', ' || hash_value
    into v_address_hash
    from v$sqlarea
   where sql_id = '%s';
  sys.dbms_shared_pool.purge(v_address_hash, 'c');
end;
    """ 

    SQL=SQL_BIND% (sql_id)

    cur = conn.cursor()
    cur.execute(SQL)

    curr_time() 
  
  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def kill_sess_by_username(conn,username):
  try:
    SQL_BIND ="""
        declare
begin
  for i in (select sid as ssid,serial# as sser,inst_id as sinst from gv$session where upper(client_identifier) = upper('%s')) loop
    execute immediate 'alter system kill session '''||i.ssid||','||i.sser||',@'||i.sinst||'''';
  end loop;
end;
    """

    SQL=SQL_BIND% (username)

    cur = conn.cursor()
    cur.execute(SQL)

    curr_time()

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def dbwr_bottleneck(conn,rownum):
  try:
    SQL_BIND ="""
	select * from(
select INSTANCE_NUMBER,
  snap_id,
  event_name,
  total_waits,
  time_waited_micro
from
  dba_hist_system_event
where
  event_name = 'free buffer waits' or
  event_name = 'write complete waits'
order by
  time_waited_micro desc)
where rownum <= '%s'
    """

    SQL=SQL_BIND% (rownum)

    cur = conn.cursor()
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
        a_list=[]
        for b in range(len(res[a])):
                str_chk = str(res[a][b])
                #match = re.search(ur"^ ",str_chk)
                #if match:
                  #str_chk = term.red+str_chk+term.normal
                a_list.append(str_chk)
        table_list.append(a_list)

    headers = [term.blue+"INST","SNAP_ID","EVENT","TOT_WAITS","TIME_WAIT_MICRO"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def top_pga(conn):
  try:
    SQL_BIND ="""
	WITH pga AS 
    (SELECT sid,
            ROUND(SUM(CASE name WHEN 'session pga memory' 
                       THEN VALUE / 1048576 END),2) pga_memory_mb,
            ROUND(SUM(CASE name WHEN 'session pga memory max' 
                      THEN VALUE / 1048576  END),2) max_pga_memory_mb
      FROM gv$sesstat  
      JOIN gv$statname  USING (statistic#)
     WHERE name IN ('session pga memory','session pga memory max' )
     GROUP BY sid)
SELECT s.inst_id,sid, username,s.module, 
       pga_memory_mb, 
       max_pga_memory_mb, s.sql_id
  FROM gv$session s
  JOIN (SELECT sid, pga_memory_mb, max_pga_memory_mb,
               RANK() OVER (ORDER BY pga_memory_mb DESC) pga_ranking
         FROM pga)
  USING (sid)
  LEFT OUTER JOIN gv$sql sql 
    ON  (s.sql_id=sql.sql_id and s.sql_child_number=sql.child_number)
 WHERE pga_ranking <=5
 ORDER BY  pga_ranking
    """

    SQL=SQL_BIND% ()

    cur = conn.cursor()
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
        a_list=[]
        for b in range(len(res[a])):
                str_chk = str(res[a][b])
                #match = re.search(ur"^ ",str_chk)
                #if match:
                  #str_chk = term.red+str_chk+term.normal
                a_list.append(str_chk)
        table_list.append(a_list)

    headers = [term.blue+"INST","SID","USER","MODULE","PGA(MB)","MAX_PGA(MB)","SQL_ID"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def pga_by_sid(conn,sid,inst):
  try:
    SQL_BIND ="""
	WITH pga AS 
    (SELECT sid,
            ROUND(SUM(CASE name WHEN 'session pga memory' 
                       THEN VALUE / 1048576 END),2) pga_memory_mb,
            ROUND(SUM(CASE name WHEN 'session pga memory max' 
                      THEN VALUE / 1048576  END),2) max_pga_memory_mb
      FROM gv$sesstat st
      JOIN gv$statname  USING (statistic#)
     WHERE name IN ('session pga memory','session pga memory max' ) and st.sid = '%s'
     GROUP BY sid)
SELECT s.inst_id,sid, username,s.module, 
       pga_memory_mb, 
       max_pga_memory_mb, s.sql_id
  FROM gv$session s
  JOIN (SELECT sid, pga_memory_mb, max_pga_memory_mb,
               RANK() OVER (ORDER BY pga_memory_mb DESC) pga_ranking
         FROM pga)
  USING (sid)
  LEFT OUTER JOIN gv$sql sql 
    ON  (s.sql_id=sql.sql_id and s.sql_child_number=sql.child_number)
 WHERE s.inst_id = '%s' and pga_ranking <=5
 ORDER BY  pga_ranking
    """

    SQL=SQL_BIND% (sid,inst)

    cur = conn.cursor()
    cur.execute(SQL)
    res = cur.fetchall()

    for a in range(len(res)):
        a_list=[]
        for b in range(len(res[a])):
                str_chk = str(res[a][b])
                #match = re.search(ur"^ ",str_chk)
                #if match:
                  #str_chk = term.red+str_chk+term.normal
                a_list.append(str_chk)
        table_list.append(a_list)

    headers = [term.blue+"INST","SID","USER","MODULE","PGA(MB)","MAX_PGA(MB)","SQL_ID"+term.normal]

    curr_time()
    print tabulate(table_list,headers,tablefmt="plain")

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def bl_create(conn,sql,plan,desc):
  try:
    SQL_BIND ="""
	declare
    res number;
    v_sql_handle      varchar2(30);
    v_plan_name       varchar2(30);
    v_sql_id          varchar2(13) := '%s';
    v_plan_hash_value number       :=  %s;
    v_desc            varchar2(30) := '%s';
begin
   for reco in (select sql_handle, plan_name
                  from dba_sql_plan_baselines bl, v$sqlarea sa
                 where dbms_lob.compare(bl.sql_text, sa.sql_fulltext) = 0
                   and sa.sql_id = v_sql_id)
   loop res := DBMS_SPM.drop_sql_plan_baseline(reco.sql_handle, reco.plan_name); end loop;
   res := dbms_spm.load_plans_from_cursor_cache(sql_id => v_sql_id, plan_hash_value => v_plan_hash_value );
   select sql_handle, plan_name
    into v_sql_handle, v_plan_name
    from dba_sql_plan_baselines bl, v$sqlarea sa
   where dbms_lob.compare(bl.sql_text, sa.sql_fulltext) = 0
     and sa.sql_id = v_sql_id
     and origin = 'MANUAL-LOAD';
   res := DBMS_SPM.alter_sql_plan_baseline(v_sql_handle, v_plan_name,'fixed','yes');
   res := DBMS_SPM.alter_sql_plan_baseline(v_sql_handle, v_plan_name,'autopurge','no');
   res := DBMS_SPM.alter_sql_plan_baseline(v_sql_handle, v_plan_name,'description',v_desc);
   dbms_output.put_line('');
   dbms_output.put_line('Baseline '||v_sql_handle||' '||v_plan_name||' was [re]created');
   dbms_output.put_line('for SQL_ID='||v_sql_id||', SQL_PLAN_HASH='||v_plan_hash_value);
end;
    """

    SQL=SQL_BIND% (sql,plan,desc)

    cur = conn.cursor()
    cur.execute(SQL)

    curr_time()

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def sql_patch_create(conn,sql_id,hint,desc):
  try:
    SQL_BIND ="""
	begin
for reco in (select sql_fulltext from v$sqlarea where sql_id = '%s')
loop
dbms_sqldiag_internal.i_create_patch(
sql_text => reco.sql_fulltext,
hint_text => '%s',
name => '%s');
end loop;
end;
    """

    SQL=SQL_BIND% (sql_id,hint,desc)

    cur = conn.cursor()
    cur.execute(SQL)

    curr_time()

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def sql_patch_drop(conn,name):
  try:
    SQL_BIND ="""
        begin
sys.dbms_sqldiag.drop_sql_patch('%s');
end;
    """

    SQL=SQL_BIND% (name)

    cur = conn.cursor()
    cur.execute(SQL)

    curr_time()

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

def sql_profile_create(conn,sql_id,plan,desc):
  try:
    SQL_BIND ="""
        declare
pln_sql_id varchar2(20) :='%s';
pln_plan_hash_value number := '%s';
new_prof_name varchar2(20) := '%s';
ar_profile_hints sys.sqlprof_attr;
cl_sql_text clob;
begin

select extractvalue(value(d), '/hint') as outline_hints
bulk collect into ar_profile_hints
from xmltable('/*/outline_data/hint'
passing (select xmltype(other_xml) as xmlval from dba_hist_sql_plan
where sql_id = pln_sql_id and plan_hash_value = pln_plan_hash_value
and other_xml is not null)) d;

select sql_text into cl_sql_text
from dba_hist_sqltext where sql_id = pln_sql_id;

dbms_sqltune.import_sql_profile(
sql_text => cl_sql_text,
profile => ar_profile_hints,
name => new_prof_name,
force_match => true);

end;
    """

    SQL=SQL_BIND% (sql_id,plan,desc)

    cur = conn.cursor()
    cur.execute(SQL)

    curr_time()

  except cx_Oracle.DatabaseError,info:
    print "Error: ",info

try:
	if sys.argv[1] == '-awt':
		conn = connection()
		ash_wait_tree(conn,sys.argv[2],sys.argv[3])
	if sys.argv[1] == '-lt':
		conn = connection()
		lock_tree(conn)
	if sys.argv[1] == '-as':
		conn = connection()
		active_sessions(conn)
	if sys.argv[1] == '-awth':
		conn = connection()
		ash_wait_tree_hist(conn,sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5])
	if sys.argv[1] == '-sqlst':
		conn = connection()
		sql_stat(conn,sys.argv[2],'true')
	if sys.argv[1] == '-sqlsd':
		conn = connection()
		sql_stat(conn,sys.argv[2],'false')
	if sys.argv[1] == '-sqlsts':
		conn = connection()
		sql_stat_by_snap_id(conn,sys.argv[2],sys.argv[3],'true')
	if sys.argv[1] == '-sqlsds':
		conn = connection()
		sql_stat_by_snap_id(conn,sys.argv[2],sys.argv[3],'false')
	if sys.argv[1] == '-sqls_perexec':
		conn = connection()
		sql_stat_per_exec_between_snap(conn,sys.argv[2],sys.argv[3],sys.argv[4])
	if sys.argv[1] == '-snaps':
		conn = connection()
		snap_stat(conn,'',sys.argv[2])
	if sys.argv[1] == '-snapr':
		conn = connection()
		snap_stat(conn,sys.argv[2],'')
	if sys.argv[1] == '-sqlmon':
		conn = connection()
		ash_sqlmon(conn,sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5])
	if sys.argv[1] == '-sqlmonh':
		conn = connection()
		ash_sqlmon_hist(conn,sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[4])
	if sys.argv[1] == '-awth_sum':
		conn = connection()
		ash_wait_tree_hist_sum(conn,sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5])
	if sys.argv[1] == '-clinfo':
		conn = connection()
		clinfo(conn,sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[2],sys.argv[3],sys.argv[4])
	if sys.argv[1] == '-sqltext':
		conn = connection()
		sql_text(conn,sys.argv[2])
	if sys.argv[1] == '-sqlbind':
		conn = connection()
		sql_bind(conn,sys.argv[2],sys.argv[3])
	if sys.argv[1] == '-tmp_consume':
		conn = connection()
		temp_consume(conn)
	if sys.argv[1] == '-undo_consume':
		conn = connection()
		undo_consume(conn)
	if sys.argv[1] == '-undo_stat':
		conn = connection()
		undo_stat(conn,sys.argv[2])
	if sys.argv[1] == '-lc_pin':
		conn = connection()
		lc_pin(conn)
	if sys.argv[1] == '-obj_stat':
		conn = connection()
		object_stat_by_object(conn,sys.argv[2],sys.argv[3])
	if sys.argv[1] == '-time_model':
		conn = connection()
		time_model(conn,sys.argv[2])
	if sys.argv[1] == '-proc_mem':
		conn = connection()
		stat_proc_memory(conn,sys.argv[2])
	if sys.argv[1] == '-top_sql_for_obj':
		conn = connection()
		top_sql_for_object(conn,sys.argv[2],sys.argv[3],sys.argv[4])
	if sys.argv[1] == '-blocks_inv_sql':
		conn = connection()
		blocks_involved_sql_hist(conn,sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6])
	if sys.argv[1] == '-rowid_from_block':
		conn = connection()
		rowid_from_block(conn,sys.argv[2],sys.argv[3],sys.argv[4])
        if sys.argv[1] == '-top_30_event':
                conn = connection()
                top_30_event(conn)
        if sys.argv[1] == '-eventh':
                conn = connection()
                eventh(conn,sys.argv[2],sys.argv[3],sys.argv[4])
	if sys.argv[1] == '-tab_stat':
		conn = connection()
		tab_stat(conn,sys.argv[2])
	if sys.argv[1] == '-top_30_modules':
		conn = connection()
		top_30_modules(conn)
	if sys.argv[1] == '-sql_by_module':
		conn = connection()
		sql_by_module(conn,sys.argv[2])
	if sys.argv[1] == '-top_30_modulesh':
		conn = connection()
		top_30_modulesh(conn,sys.argv[2],sys.argv[3])
	if sys.argv[1] == '-shared_cu':
		conn = connection()
		shared_cu(conn,sys.argv[2])
	if sys.argv[1] == '-shared_cu_sum':
		conn = connection()
		shared_cu_sum(conn,sys.argv[2])
	if sys.argv[1] == '-purge_cu':
		conn = connection()
		purge_cu(conn,sys.argv[2])
	if sys.argv[1] == '-dbwr_bottleneck':
		conn = connection()
		dbwr_bottleneck(conn,sys.argv[2])
	if sys.argv[1] == '-top_pga':
		conn = connection()
		top_pga(conn)
	if sys.argv[1] == '-pga_by_sid':
		conn = connection()
		pga_by_sid(conn,sys.argv[2],sys.argv[3])
	if sys.argv[1] == '-bl_create':
		conn = connection()
		bl_create(conn,sys.argv[2],sys.argv[3],sys.argv[4])
	if sys.argv[1] == '-sql_patch_create':
		conn = connection()
		sql_patch_create(conn,sys.argv[2],sys.argv[3],sys.argv[4])
	if sys.argv[1] == '-sql_patch_drop':
		conn = connection()
		sql_patch_drop(conn,sys.argv[2])
	if sys.argv[1] == '-sql_profile_create':
		conn = connection()
		sql_profile_create(conn,sys.argv[2],sys.argv[3],sys.argv[4])
	if sys.argv[1] == '-kill_sess_by_name':
		conn = connection()
		kill_sess_by_username(conn,sys.argv[2])

except IndexError:
	headers = [term.blue+"KEY","PARAMETERS","DESCRIPTIONS"+term.normal]
	table_list=[]

	param=[("-awt","\"enq: UL - contention\" \"fsf84tsn20htr\"","ash wait tree"),("-awth","\"event\" \"enq: TX - row lock contention\" 187370 187380", "ash wait tree history by event between snap_id"),("-awth","\"sql_id/top_level_sql_id\" \"fsf84tsn20htr\" 208030 208080","ash wait tree history by sql_id or top_level_sql_id between snap_id"),("-lt","none","lock tree"),("-as","none","active sessions"),("-sqlst","\"fsf84tsn20htr\"","sql_id statistics total"),("-sqlsd","\"fsf84tsn20htr\"","sql_id statistics delta"),("-sqlsts", "\"fsf84tsn20htr\" 208030","sql_id statistics total by snap_ip"),("-sqlsds", "\"fsf84tsn20htr\" 208030","sql_id statistics delta by snap_ip"),("-sqls_perexec", "\"fsf84tsn20htr\" 208030 208031","sql_id statistics per execution between snap_ip"),("-snapr","10","list of snapshots with limit rows"),("-snaps","62384","list when snap_id start and stop"),("-sqlmon","sql_id inst_id child_num plan_hash","sql plan for sql_id by sql_plan"),("-sqlmonh","\"05v2954zu3jgs\" \"3603852551\" 187370 187380","sql plan for sql_id by sql_plan between snap_id"),("-awth_sum", " sql_id/event \"05v2954zu3jgs\" 208030 208031","ash wait tree history by sql_id without group by sessions, just summarize the events"),("-clinfo","sid serial# inst_id","Shows information about session by sid and serial#"),("-sqltext","\"fsf84tsn20htr\"","Shows sql text"),("-sqlbind","\"fsf84tsn20htr\" snap_id","Shows related valiables"),("-tmp_consume","none","Shows how many temp space was consumed"),("-undo_consume","none","Shows some undo information"),("-undo_stat","\"05v2954zu3jgs\"","Shows undo statistic for sql_id"),("-lc_pin","none","library cache pin"),("-obj_stat","object_name sec in wait","Shows segment statistic for object"),("-time_model","inst_id","Shows time model by system"),("-proc_mem","sid","Shows consumed private memory"),("-top_sql_for_obj","object_name object_type operation","Shows top sql for object for special operation from ASH"),("-blocks_inv_sql","object_name object_type sql_id between snaps","Shows top blocks involved after sql had access to object. Info from dba_hist"),("-rowid_from_block","schema.table fno block","Shows ordered rowid by object"),("-top_30_event","","Show top 30 events for last 30 minutes"),("-eventh","snap_begin snap_end event","Shows events between snapshots. Be carefull with gap of snapshots, use one or two snapshots because there are to much information"),("-tab_stat","some table","Shows table and index statistics without partitions"),("-top_30_modules","","Shows top 30 modules from ASH"),("-sql_by_module","some module","Shows sql_id by module"),("-top_30_modulesh","snap_begin snap_end","Shows top modules between snaphots"),("-shared_cu","sql_id","Shows some information about shared cursors"),("-shared_cu_sum","sql_id","Shows versions of cursor"),("-purge_cu","sql_id","Purge cursor from SGA by sql_id"),("-dbwr_bottleneck","num_row","Shows dbwr bottleneck"),("-top_pga","","Shows top pga"),("-pga_by_sid","sid inst_id","Shows pga by sid"),("-bl_create","sql_id plan_hash description","Make base line for sql"),("-sql_patch_create","sql_id hint description","Make sql_patch for sql"),("-sql_patch_drop","patch name","Drop sql_patch"),("-sql_profile_create","sql_id plan_hash description","Make SQL PROFILE for sql. You can take plan_hash from dba_hist_sql_plan"),("-kill_sess_by_name","username","Killing all user sessions by username")]

	for a in range(len(param)):
	  a_list=[]
	  for b in range(len(param[a])):
	    str_res = str(param[a][b])
	    a_list.append(str_res)
	  table_list.append(a_list)
	print tabulate(table_list,headers,tablefmt="plain")
