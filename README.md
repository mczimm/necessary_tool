# necessary_tool

This tool made for Oracle DBA to make their working days easier :)
If you have some question don't hesitate, contact me.
email: mczimm@gmail.com
skype: mczimm

Features of Tree_locks tool

./tree_locks.py 
KEY                  PARAMETERS                                               DESCRIPTIONS
-awt                 "enq: UL - contention" "fsf84tsn20htr"                   ash wait tree
-awth                "event" "enq: TX - row lock contention" 187370 187380    ash wait tree history by event between snap_id
-awth                "sql_id/top_level_sql_id" "fsf84tsn20htr" 208030 208080  ash wait tree history by sql_id or top_level_sql_id between snap_id
-lt                  none                                                     lock tree
-as                  none                                                     active sessions
-sqlst               "fsf84tsn20htr"                                          sql_id statistics total
-sqlsd               "fsf84tsn20htr"                                          sql_id statistics delta
-sqlsts              "fsf84tsn20htr" 208030                                   sql_id statistics total by snap_ip
-sqlsds              "fsf84tsn20htr" 208030                                   sql_id statistics delta by snap_ip
-sqls_perexec        "fsf84tsn20htr" 208030 208031                            sql_id statistics per execution between snap_ip
-snapr               10                                                       list of snapshots with limit rows
-snaps               62384                                                    list when snap_id start and stop
-sqlmon              sql_id inst_id child_num plan_hash                       sql plan for sql_id by sql_plan
-sqlmonh             "05v2954zu3jgs" "3603852551" 187370 187380               sql plan for sql_id by sql_plan between snap_id
-awth_sum            sql_id/event "05v2954zu3jgs" 208030 208031               ash wait tree history by sql_id without group by sessions, just summarize the events
-clinfo              sid serial# inst_id                                      Shows information about session by sid and serial#
-clinfoall           sid                                                      Shows all sessions by sid
-sqltext             "fsf84tsn20htr"                                          Shows sql text
-sqlbind             "fsf84tsn20htr" snap_id                                  Shows related valiables
-tmp_consume         none                                                     Shows how many temp space was consumed
-undo_consume        none                                                     Shows some undo information
-undo_stat           "05v2954zu3jgs"                                          Shows undo statistic for sql_id
-lc_pin              none                                                     library cache pin
-obj_stat            object_name sec in wait                                  Shows segment statistic for object
-time_model          inst_id                                                  Shows time model by system
-proc_mem            sid                                                      Shows consumed private memory
-top_sql_for_obj     object_name object_type operation                        Shows top sql for object for special operation from ASH
-blocks_inv_sql      object_name object_type sql_id between snaps             Shows top blocks involved after sql had access to object. Info from dba_hist
-rowid_from_block    schema.table fno block                                   Shows ordered rowid by object
-top_event_for_sql   sql_id b_snap e_snap                                     Shows top events from dba_hist for particular sql_id
-top_30_event                                                                 Shows top 30 events for last 30 minutes
-eventh              snap_begin snap_end event                                Shows events between snapshots. Be carefull with gap of snapshots, use one or two snapshots because there are to much information
-tab_stat            some table                                               Shows table and index statistics without partitions
-top_30_modules                                                               Shows top 30 modules from ASH
-sql_by_module       some module                                              Shows sql_id by module
-top_30_modulesh     snap_begin snap_end                                      Shows top modules between snaphots
-shared_cu           sql_id                                                   Shows some information about shared cursors
-shared_cu_sum       sql_id                                                   Shows versions of cursor
-purge_cu            sql_id                                                   Purge cursor from SGA by sql_id
-dbwr_bottleneck     num_row                                                  Shows dbwr bottleneck
-top_pga                                                                      Shows top pga
-pga_by_sid          sid inst_id                                              Shows pga by sid
-bl_create           sql_id plan_hash description                             Make base line for sql
-sql_patch_create    sql_id hint description                                  Make sql_patch for sql
-sql_patch_drop      patch name                                               Drop sql_patch
-sql_profile_create  sql_id plan_hash description                             Make SQL PROFILE for sql. You can take plan_hash from dba_hist_sql_plan
-sql_profile_drop    profile name                                             Drop sql_profile
-kill_sess_by_name   username                                                 Killing all user sessions by username
-kill_sess_by_sid    sid serial# inst_id                                      Killing particular session
-ind_col             index_name                                               Shows which columns are included in the index
-report_col_usage    OWNER TABLE                                              Shows usage column report from dbms_stats.report_col_usage
-ctas_ash                                                                     Cretae table as select * from ASH

