#!/usr/bin/python

import sys
import time
import boto.ec2
import boto.ec2.elb

# connections
ec2_conn = boto.ec2.connect_to_region("us-east-1")
elb_conn = boto.ec2.elb.connect_to_region("us-east-1")

# list instances from the load balancer, the others are not serving traffic so log is not growing
lb_inst = elb_conn.get_all_load_balancers('http')[0].instances
lb_inst_ids = []
for it in lb_inst:
	lb_inst_ids.append(it.id)

# gather data for the instances in the LB
reservations = ec2_conn.get_all_reservations(lb_inst_ids)

# gather the number of instances
elem = len(reservations)
if elem == 1:
	sys.exit('Only one instance in the load balancer')

it = 0
while it < elem:
	instances = reservations[it].instances
	inst = instances[0]

	# remove instance from lb
	elb_conn.deregister_instances('http',inst.id)

	# wait the connection draining timeout (set to 10s, FaaS is fast!)
	time.sleep(10)

	# stop instance
	print 'Stopping',inst.id
	ec2_conn.stop_instances(instance_ids=[inst.id])
	
	# let's wait until we know the instance is stopped
	status = inst.update()
	while status != 'stopped':
		time.sleep(5)
		status = inst.update()
	
	# get volume of instance
	inst_vol = ec2_conn.get_all_volumes(filters={'attachment.instance-id': inst.id})
	
	# gather some information about the current volume
	vol_size = inst_vol[0].size
	vol_type = inst_vol[0].type
	root_dev = inst.root_device_name
	
	# take snapshot
	snap = ec2_conn.create_snapshot(inst_vol[0].id, 'temp-snap')
	
	# making sure the snapshot is complete before continuing
	status = snap.update()
	while status != '100%':
		time.sleep(5)
		status = snap.update()
		
	# detach the existing volume
	ec2_conn.detach_volume(inst_vol[0].id)
	
	# increase the size of the volume	
	vol_size = vol_size + 1

	# create new volume from snapshot
	new_vol = ec2_conn.create_volume(vol_size,inst.placement,snapshot=snap.id,volume_type=vol_type)
	
	# wait for the new volume to be available
	status = new_vol.update()
	while status != 'available':
		time.sleep(5)
		status = new_vol.update()
		
	# attach new volume to instance and cleanup
	ec2_conn.attach_volume(new_vol.id,inst.id,root_dev)
	ec2_conn.delete_snapshot(snap.id)
	ec2_conn.delete_volume(inst_vol[0].id)
	
	# start instance
	print 'Starting',inst.id
	ec2_conn.start_instances(instance_ids=[inst.id])
	
	# wait for the instance to be running before moving forward
	status = inst.update()
	while status != 'running':
		time.sleep(5)
		status = inst.update()
	
	# add instance to lb
	elb_conn.register_instances('http',inst.id)
	
	# check that elb has instance as active
	inst_state_in_lb = elb_conn.describe_instance_health('http',inst.id)[0].state
	print 'Waiting for',inst.id,'to be back in service'
	while inst_state_in_lb != 'InService':
		time.sleep(3)
		# sadly update() is not supported here
		inst_state_in_lb = elb_conn.describe_instance_health('http',inst.id)[0].state
	print inst.id,'is now in service'
	
	it = it + 1
