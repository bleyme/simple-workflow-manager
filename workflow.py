#!/usr/bin/python2.7 -u

# Import required packages 
from jinja2 import Template
import subprocess
from time import sleep
import json
from datetime import date, tzinfo, timedelta, datetime
from dateutil.relativedelta import relativedelta
from pytz import timezone
import pytz
import shlex
import threading
import argparse
import random
import string
import time
import re

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import and_
from sqlalchemy_repr import RepresentableBase
from sqlalchemy.pool import NullPool

# Monitoring table abstraction definition
Base = declarative_base(cls=RepresentableBase)

class execution_monitoring(Base):

	__tablename__ = 'ETL_jobs_execution_monitoring' # Needs to be changed manually
	__table_args__ = {"schema": 'monitoring'} # Depends on database backend
	moment = Column(Date)
	pid = Column(String(20), nullable=False, primary_key=True)
	father_pid = Column(String(20), nullable=False)
	root_pid = Column(String(20), nullable=False)
	system_pid = Column(Integer, nullable=False)
	project = Column(String(50), nullable=False)
	job = Column(String(255), nullable=False)
	job_repository_id = Column(String(255), nullable=False)
	job_version = Column(String(255), nullable=False)
	context = Column(String(50), nullable=False)
	origin = Column(String(255), nullable=True)
	message_type = Column(String(255), nullable=True)
	message = Column(String(255), nullable=True)
	duration = Column(Integer)


# Function definitions 

# Run a job in a separated thread 
class Command(object):
    command = None
    process = None
    status = None
    output, error = '', ''

    def __init__(self, command):
        #if isinstance(command, basestring):
        #    command = shlex.split(command)
        self.command = command

    def run(self, timeout=None, **kwargs):
        """ Run a command then return: (status, output, error). """
        def target(**kwargs):
            try:
                self.process = subprocess.Popen(self.command, **kwargs)
                self.output, self.error = self.process.communicate()
                self.status = self.process.returncode
            except:
                self.error = traceback.format_exc()
                self.status = -1
        # default stdout and stderr
        if 'stdout' not in kwargs:
            kwargs['stdout'] = subprocess.PIPE
        if 'stderr' not in kwargs:
            kwargs['stderr'] = subprocess.PIPE
        # thread
        thread = threading.Thread(target=target, kwargs=kwargs)
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            self.process.terminate()
            print "time out"
            thread.join()
        return self.status, self.output, self.error

# Read the job definition file and return a dictionnary of it
def read_job_description(file_path):
    with open(file_path) as json_data:
        d = json.load(json_data)
        json_data.close()
        return d

# Initiate the connection to the monitoring DB
def init_connection_to_db(connection_details):
  # Needs to be changed manually, map credentials to external JSON file
	url_engine = 'mssql+pyodbc://%s:%s@%s' % (connection_details["user"], connection_details["password"], connection_details["db"])
	engine = create_engine(url_engine, echo=False, poolclass=NullPool, legacy_schema_aliasing=False)
	Session = sessionmaker(bind=engine)
	return Session() 	

# Close the connection
def close_connection_to_db(session):
	session.close()

# Persist job start information
def monitor_job_start(session,job_name,workflow_pid):
	job_execution = execution_monitoring(moment=datetime.now(), 
		pid=workflow_pid, 
		father_pid=workflow_pid, 
		root_pid=workflow_pid,
		system_pid=-1,
		job=job_name, 
		origin=None, 
		project='Workflow manager',
		context='NA',
		job_repository_id='NA',
		job_version='NA',
		message_type='begin')
	session.add(job_execution)
	session.commit() 

# Update the system pid of a job after execution
def monitor_update_job_pid(session, workflow_pid, pid):
	job_execution = session.query(execution_monitoring).filter(and_(execution_monitoring.pid == workflow_pid, execution_monitoring.message_type == 'begin')).first()
	job_execution.system_pid = pid
	session.commit()

# Persist job stop information
def monitor_job_stop(session, job_name, pid, workflow_pid, status, duration):
	job_execution = execution_monitoring(moment=datetime.now(), 
		pid=workflow_pid, 
		father_pid=workflow_pid, 
		root_pid=workflow_pid,
		system_pid=pid,
		job=job_name, 
		origin=None, 
		message_type='end', 
		message=status,
		duration=duration,
		project='Workflow manager',
		context='NA',
		job_repository_id='NA',
		job_version='NA',)
	session.add(job_execution)
	session.commit() 

# Check if a job has been sucessfully executed today
def is_job_execution_today_successful(job_name,session,date_in):
	query_result = session.query(execution_monitoring).filter(and_(execution_monitoring.moment>date_in, 
	execution_monitoring.job == job["name"], 
	execution_monitoring.origin == None,
	execution_monitoring.message_type == "end",
	execution_monitoring.message == "success")).first()
	
	if query_result is None:
		return False
	else:
		return True

# Main part of the script
if __name__ == "__main__":

	parser = argparse.ArgumentParser(description='DeinDeal simple workflow manager')

	parser.add_argument('--job_file', required=True)
	parser.add_argument('--delta', required=False, default="3 days")
	parser.add_argument('--job_names', required=False, help="Comma separated list of specific job to run")
	parser.add_argument('--force', required=False, action='store_true')

	cmd_arg = parser.parse_args()

	job_definition_file = cmd_arg.job_file
	is_force_reload = cmd_arg.force

	if cmd_arg.job_names is not None:
		job_names = cmd_arg.job_names.split(',')
	else:
		job_names = None

	periods = ["days","months","years"]

	expression = re.search(r'(\d+)\s*(\w+)', cmd_arg.delta)
	delta_period = expression.group(2).lower()
	delta_value  = int(expression.group(1))

	for test_period in periods:
		periods_lkp_idx = test_period.find(delta_period)
		if periods_lkp_idx != -1:
			delta_period = test_period

	# Work with local zurich time
	zurich_time = timezone('Europe/Zurich')

	# Read job definition JSON file
	job_definition = read_job_description(job_definition_file)

	# Set default variable for all job from definition 
	Packages_dir = job_definition["package_dir"]
	Retry_number = job_definition["retry_number"]
	If_Failed = job_definition["if_failed"]
	Time_Out = job_definition["time_out"]
	
	# Get jobs list 
	# Jobs is an ordered list of dictionnary
	Jobs = job_definition["jobs"]

	today=zurich_time.localize(datetime.today().replace(hour=0,minute=0,second=0,microsecond=0))

	if delta_period == "days":
		lower_date_limit=date.today() + relativedelta(days=-delta_value)
	elif delta_period == "months":
		lower_date_limit=date.today() + relativedelta(months=-delta_value)
	elif delta_period == "years":
		lower_date_limit=date.today() + relativedelta(years=-delta_value)
	else:
		print delta_period+ "unknown"
		exit(1)
	
	fmt = '%Y-%m-%d'

	notify_scheduler_of_failure = False 

	if is_force_reload:
		print("Force reloading, previous executions will be ignored")

	# If specific jobs are passed through the command line, use the active flag to desactivate all others
	if job_names is not None:
		print("Executing specific jobs: ")+", ".join(job_names)
		for job in Jobs:
			if job["name"] not in job_names:
				job["active"]=False

	# Loop over job to run 
	for job in Jobs:

		# connection is legacy and will be replaced with session
		session = init_connection_to_db(job_definition["monitoring_db"]) # MySQL has strict timeout on connection, better using a new one for each job

		if job["active"]:

			print "Now running: "+job["name"]
			
			# Set local job variables if set otherwise use global
			job_executable_complete_path = job["job_executable"]
			job_retry_number = job.get("retry_number",Retry_number)
			job_if_failed = job.get("if_failed",If_Failed)
			job_time_out = job.get("time_out",Time_Out)*60 # Defined in minutes but need seconds

			job_status = 1
			attempt = 0

			if not is_force_reload:
				# Check if the job was already successfully today

				if is_job_execution_today_successful(job["name"],session,today):
					print job["name"]+" executed today, skipping it"
					job_status = 0
				
			command_string=job_executable_complete_path+" "+job.get("parameters","")
			templated_command = Template(command_string)
			command_string = templated_command.render(EndDate=today.strftime(fmt),StartDate=lower_date_limit.strftime(fmt))
			print "command: "+command_string

			# Retry on error logic block
			while (job_status !=0 and attempt < job_retry_number):
				workflow_pid = ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(20)])
				
				if attempt > 0:
					print "Restarting failed job: "+job["name"]

				#p = subprocess.Popen(command, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.PIPE)

				start = time.time()

				if job.get("monitored_by_workflow",False):
					print "The workflow manager should monitor this job"
					monitor_job_start(session, job["name"], workflow_pid)

				command = Command(command_string)
				job_status, job_out, job_error = command.run(timeout=job_time_out, shell=True, executable='/bin/bash')
				end = time.time()

				job_pid=str(command.process.pid)
				print job["name"]+ " started with PID "+job_pid

				if job.get("monitored_by_workflow",False):
					monitor_update_job_pid(session, workflow_pid, job_pid)

					status = "failure"
					if job_status == 0:
						status = "success"
					monitor_job_stop(session, job["name"], job_pid, workflow_pid, status, (end - start)*1000) # Duration needs to be in ms

				if job_out is not None:
					print job_out
				if job_error is not None:
					print job_error

				attempt += 1

			# End of retry block, no new attempt will be performed
			if job_status !=0:
				print job["name"]+" failed after maximum attempt"
				notify_scheduler_of_failure = True
				if job_if_failed != "skip":
					print job["name"]+" failure : failling complete flow"
					exit(1)

		else:
			print job["name"]+" not active, skipping it"

		close_connection_to_db(session)

	if notify_scheduler_of_failure:
		exit(1)
