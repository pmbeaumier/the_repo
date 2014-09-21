#!/usr/bin/python

import time
import boto.ec2
import boto.ec2.elb

ami = 'ami-561bb33e'
key = 'pierre'
type = 't1.micro'
sec_g = 'launch-wizard-1'

# connections
ec2_conn = boto.ec2.connect_to_region("us-east-1")
elb_conn = boto.ec2.elb.connect_to_region("us-east-1")

print 'Launching a new',type,'instance using the',ami,'image and the',key,'key pair'
new_inst = ec2_conn.run_instances(ami,key_name=key,instance_type=type,security_groups=[sec_g])
inst = new_inst.instances

# check the instance is running
print 'Checking if the instance is running'
status = inst[0].update()
while status != 'running':
	time.sleep(5)
	status = inst[0].update()

# add instance to lb
print 'Adding the instance to the load balancer'
elb_conn.register_instances('http',inst[0].id)
