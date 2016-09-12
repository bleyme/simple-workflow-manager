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

## Configuration

* Modify database backend (any compatible with SQLAlchemy), and eventually table schema.name
* Modify databse entry in workflow file
* Create target table

```sql
--- MS SQL dialect version in schema monitoring
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
```

### Command line options
