# simple-workflow-manager

A very simple (data-oriented) jobs workflow manager written in a unique python script:

* □ Linear dependencies between jobs
* ✓ Complete or partial failures of the workflow
* ✓ Retry number specific for each job
* ✓ Time-out specific for each job
* ✓ Skip successful jobs in case of complete restart
* □ Single daily execution
* ✓ Data backend: anything that SQLAlchemy handle
* ✓ JSON external configuration file
* ✓ Templated delta dates (Talend oriented through --context_param)
* ✓ Allow delegation of job logging to Talend (StatCatcher), stderr is redirected to stdout

## Configuration

* Modify database backend (any compatible with SQLAlchemy), and eventually table schema.name
* Modify databse entry in workflow file
* Create target table

```sql
--- MS SQL dialect version in schema monitoring
--- This is the default Talend StatCatcher table

DROP TABLE IF EXISTS [monitoring].[ETL_jobs_execution_monitoring] ;
CREATE TABLE [monitoring].[ETL_jobs_execution_monitoring] (
	[moment] [datetime] NOT NULL,
	[pid] [varchar](20) NOT NULL,
	[father_pid] [varchar](20) NOT NULL,
	[root_pid] [varchar](20) NOT NULL,
	[system_pid] [bigint] NOT NULL,
	[project] [varchar](50) NOT NULL,
	[job] [varchar](255) NOT NULL,
	[job_repository_id] [varchar](255) NOT NULL,
	[job_version] [varchar](255) NOT NULL,
	[context] [varchar](50) NOT NULL,
	[origin] [varchar](255) NULL,
	[message_type] [varchar](255) NULL,
	[message] [varchar](255) NULL,
	[duration] [bigint] NULL
) ;
```

## Usage

### Workflow example

```json

{  
   
   "description":"This file describes a sequence of jobs",

   "retry_number":2,
   "package_dir":"/path_to_job_executable",
   "if_failed":"skip",
   "time_out":10,

   "monitoring_db":{
      "db_type":"mssql+pymssql",
      "db":"databasename",
      "server":"database_server",
      "table":"monitoring_table_name",
      "port":"database_port",
      "user":"database_user",
      "password":"user_password"
      },
      
   "jobs":[  
   
      {  
         "name":"Job_A",
         "job_executable":"sh /my_path/my_jobA.sh",
         "if_failed":"failed",
         "retry_number":5,
         "active":true,
         "time_out":120,
         "monitored_by_workflow":true
      },
      
       {  
         "name":"Talend_Job_B",
         "job_executable":"sh /my_path/Talend_Job_B/Talend_Job_B_run.sh",
         "if_failed":"failed",
         "retry_number":5,
         "active":true,
         "time_out":120,
         "monitored_by_workflow":false
      }
   
   ]
      
}
```

### Command line options
