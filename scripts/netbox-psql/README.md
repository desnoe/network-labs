# Netbox postgresql database dump & restore

The principle of the labs is :
1) to store a dump of the postresql database in a file and committing it in the repo
2) then restore this file to the database when restoring the lab 

Two shell scripts may be used to ease these 2 operations:
1) `dump.sh` that relies on the `pg_dump` command
2) `restore.sh` that on `psql` commands

## Examples

Dump the current database state:

```
dump.sh dump.sql postgres://netbox:J5brHrAXFLQSif0K@gns3.example.com/netbox
```

and

```
restore.sh dump.sql postgres://netbox:J5brHrAXFLQSif0K@gns3.example.com/netbox
```
