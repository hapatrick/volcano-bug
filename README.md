The script can be used to reproduce a bug in Volcano where Volcano controller 
fails to update a vcjob's state because the resource's version has changed.
The script creates 500 vcjobs. Each vcjob contains one task, which is just 
"sleep 5." After creating each vcjob, the script waits a short period of time
and then adds an annotation to the vcjob's metadata. 

The script waits 120s for all vcjobs to complete, and then deletes any vcjobs
that do not have phase == 'Completed.' This is successful in creating the error
about in about 5 to 15 vcjobs per 500. Success rate of reproducing the bug seems
to depend on the time gap between creating the vcjob and adding the annotation.
This is hard-coded to 0.45 seconds in function create_job(). This value seems to
maximize the occurrence of this condition in our cluster.

To run:
* pip install -r requirements.txt
* python vcjob_bug.py

The above creates the jobs in the "default" namespace. To specify a different
namespace run as:
* python vcjob_by.py -n NAMESPACE
