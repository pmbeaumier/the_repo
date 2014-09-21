# All about that FaaS !
It's up and running ! We can now sustain the log growth by resizing the root volume of the load balanced instances.
We can also easily spin new instances up if the need arises. 

We're on the road to great success !

## Deliverables
* A working FaaS endpoint
The AWS [loadbalancer](http://http-543346036.us-east-1.elb.amazonaws.com/) is the endpoint, I also created a CNAME in my zone (faas.kkdzo.org) but my DNS provider does not appear to be playing nice right now and is returning NXDOMAIN.

* Steps involved in spinning up FaaS
I used the provided AMI to build an instance with apache and a perl script calling fortune.
From this, I created the ami-561bb33e image which is then used by the add_faas_instance.py script to spin a new instance up and add it to the load balancer. This script uses boto.

* Python script that resizes root volumes
The resize_volumes.py script looks at the instances present in the load balancer and resizes the root volume one at a time.
It starts by removing the instance from the load balancer (unless it's the only one) and wait for the connection draining timeout before bringing the instance down.
It then takes a snapshot of the root volume and create an new volume based on the snapshot and 1GB bigger. After attaching the new volume to the instance, the script starts the instance and adds it back to the load balancer pool. It waits to make sure the the instance is in service before moving to the next one. This script uses boto

## Moving forward
There are a lot of things I'd like to add like error checking and handling, currently the script works when everything else works but it won't report python tracebacks of does not know how to deal with eventual connectivity issues for example.
I'd also look into the possibility of running more than one resize operation at a time while still making sure that we have enough capacity in the load balancer.
Other features I'm thinking of are the ability to choose by how much we want to grow the volume and how to deal with different sizes per instance
I'm also thinking that for this application, apache is overkilled, this could be replaced by a lighter webserver.
