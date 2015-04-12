## Introduction to Halo
-----------------------------------

Halo lets us create Cloud resources easily by defining them in simple human understandable yaml format. The template need not be one huge template, we can split resources into seperate logical files and include them in the main template file. We can also paramterize the resouces so that the templates are resuable with diffrent values.


### Installing Halo
----------------------------

- git clone https://github.com/bennojoy/halo.git 
- cd halo
- source hacking/env-setup

Halo requires a few more python packages to be installed they can be installed as follows:

- pip install troposhere
- pip install boto
- pip install jinja2

 
### Using Halo
----------------------------

Halo requires the stack to be defined in yaml format, Below is an example of a stack consisting of a vpc with a subnet and an instance in that subnet

```

template:
 stack_props:
   state: present
   region: us-east-1
   rollback: no
   stack_name: "mystack"
   wait: yes
   wait_timeout: 280
 resources:
    - type: vpc
      name: "myvpc"
      CidrBlock: '10.0.0.0/16'
      Tags: 
        application: "myapp"
        Name: joy
    - type: subnet
      name: subnet1 
      CidrBlock: '10.0.0.0/24'
      VpcId: ref(myvpc)
      Tags:
       Name: "Mysubnet1"
    - type: instance
      name: myinstance
      InstanceType: "t1.micro"
      KeyName: benkey
      ImageId: 'ami-8997afe0'
      SubnetId: ref(subnet1)
      AvailabilityZone: us-east-1c
      Tags:
        Name: "Ben_hello"
 outputs:
    - name: InstanceIP
      Description: IP of the Instance
      Value: getatt(myinstance, PrivateIp)

```


The templates can be executed via:

```

halo-aws examples/vpc_instance_without_params.yml 

```

Many a times we would want the templates to be resusable as only certain names would change, in that case we can have the changing values as paramters in the template.

```

template:
 stack_props:
   state: present
   region: us-east-1
   rollback: no
   stack_name: "{{ stack_name }}"
   wait: yes
   wait_timeout: 280
 resources:
    - type: vpc
      name: "{{ vpc_name }}"
      CidrBlock: "{{ cidr_block }}"
      Tags: 
        application: myapp
        Name: joy
    - type: subnet
      name: subnet1 
      CidrBlock: "{{ subnet_cidr }}"
      VpcId: ref({{ vpc_name }})
      Tags:
       Name: "Mysubnet1"
    - type: instance
      name: myinstance
      InstanceType: "t1.micro"
      KeyName: benkey
      ImageId: '{{ image_id }}'
      SubnetId: ref(subnet1)
      Tags:
        Name: "Ben_hello"
 outputs:
    - name: InstanceIP
      Description: IP of the Instance
      Value: getatt(myinstance, PrivateIp)

```

The variables are enclosed in "{{" and the values can be specified in a file in yaml format as below:

```

stack_name: benz
vpc_name: benz1
image_id: ami-8997afe0
cidr_block: "10.0.0.0/16"
subnet_cidr: "10.0.5.0/24"

```

and the template can be executed as follows:

```

halo-aws examples/vpc_instance_with_params.yml -p @examples/vars/vpc_instance.yml

we can also pass the values in commandline directly:

halo-aws examples/vpc_instance_with_params.yml -p "vpc_name=foo stack_name=foobar"

```

Many a times we dont want to specify our entire stack in big file and we may want to split it into diffrent files, Also we may want other users to defind the resources they want in thier respective files , in such cases we can include other templates. Here is an example.

```

The main template file:

template:
 stack_props:
   state: present
   region: us-east-1
   rollback: no
   stack_name: "{{ stack_name }}"
   wait: yes
   wait_timeout: 280
 resources:
    - type: vpc
      name: "{{ vpc_name }}"
      CidrBlock: "{{ cidr_block }}"
      Tags: 
        application: myapp
        Name: joy
 include_resources: 
   - examples/resources/subnet.yml
   - examples/resources/instance.yml

The included resource file would be like:


template:
 resources:
    - type: subnet
      name: subnet2
      CidrBlock: '10.0.1.0/24'
      VpcId: ref({{ vpc_name }})
      Tags:
       nem: getatt({{ vpc_name }}, DefaultNetworkAcl)
 outputs:
    - name: ben1
      Description: foobar1
      Value: getatt({{ vpc_name}}, DefaultNetworkAcl)



```



### Notes
-------------------


All the resources that can be created in the templates are listed in the references folder under thier respective groups. So for example if we need to create a vpc we need to define the  'type: vpc' a "name: foo" and the diffrent properties of a vpc.
The type vpc and the diffrent properties that it accepts are listed in references/ec2 as follows:

```

"VPC": {
      "'InstanceTenancy'": "(basestring, False),", 
      "'EnableDnsSupport'": "(boolean, False),", 
      "'EnableDnsHostnames'": "(boolean, False),", 
      "'CidrBlock'": "(basestring, True),", 
      "'Tags'": "(list, False),"
   }, 


```

Please note the properties are case senstive so please do make sure the case matches in the template.

 
