import shlex
import sys
import yaml
import time
import optparse
import json
import constants
from halo_errors import halo_error
from jinja import *
try:
    from troposphere import Parameter, Ref, Tags, Template, GetAtt, Join, Output
except ImportError:
    sys.stderr.write("troposhere python module not found")
    sys.exit(1)
from  constants import *

try:
    import boto
    import boto.cloudformation.connection
except ImportError:
    sys.stderr.write("python boto module not found")
    sys.exit(1)

LOWER_CASE_CLASS_MAP_DICT = {}
IMPORTED_CLASS = {}
SUPPORTED_AWS_FUNCS = ['ref', 'getatt', 'join']
vars = {}

def vvv(msg=None, type=None, notice=None):
    if constants.verbosity:
        if notice:
            sys.stdout.write("\n" + notice + "\n\n")
        if type == 'json':
            sys.stdout.write(json.dumps(msg, indent=3))
        else:
            sys.stdout.write(str(msg))

def boto_exception(err):
    '''generic error message handler'''
    if hasattr(err, 'error_message'):
        error = err.error_message
    elif hasattr(err, 'message'):
        error = err.message
    else:
        error = '%s: %s' % (Exception, err)

    return error



def convert_key_to_lower_case(d):
    for k,v in d.items():
        LOWER_CASE_CLASS_MAP_DICT[k.lower()] = [k,v]

def load_yaml_from_file(path=None):
    try:
        data = open(path).read()
    except IOError:
       halo_error("Could not load file %s\n" % path)
    try:
        return yaml.load(data)
    except yaml.YAMLError, exc:
        if hasattr(exc, 'problem_mark'):
            mark = exc.problem_mark
            halo_error("error loading yaml file %s in line %s and column %s" %(path, mark.line + 1, mark.column))

#Add here to support more aws fuctions in the yaml
def handle_funcs(v):
    if v.find('(') == -1:
        return v
    val = v.split('(')[0].lower()
    if val in SUPPORTED_AWS_FUNCS:
        if val == 'ref':
            ref_value = v.split('(')[1].split(')')[0]
            return Ref(ref_value)
        if val == 'getatt':
            getatt_value = v.split('(')[1].split(')')[0]
            logical_name = getatt_value.split(',')[0]
            attrib_name = getatt_value.split(',')[1]
            return GetAtt(logical_name.strip(), attrib_name.strip())
    else:
        halo_error("The function %s is not yet supported" %val)

# transforms functions in the dict to classes
def sanitize_dict(r):
    res = r
    resource_sanitized = {}
    for k,v in res.iteritems():
        if k == 'Tags':
           t = sanitize_dict(v)
           resource_sanitized[k] = Tags(**v)
           continue
        if isinstance(v, basestring):
           v = handle_funcs(v) 
        elif isinstance(v, list):
            for i in v:
                if isinstance(i, basestring):
                    v[v.index(i)] = handle_funcs(i)
                elif isinstance(i, dict):
                    for x,y in i.items():
                        if isinstance(y, basestring):
                            i[x] = handle_funcs(y)
        resource_sanitized[k] = v
    return resource_sanitized
    


def add_resource_to_template(res, template):
    
    try:
        res_type = res['type'].lower()
        res_name = res['name'].lower()
    except KeyError:
        halo_error("type/name: keys are mandatory for a resource")
    try:
        class_name = LOWER_CASE_CLASS_MAP_DICT[res_type][0]
        mod_name = LOWER_CASE_CLASS_MAP_DICT[res_type][1]
    except KeyError:
        halo_error("Resource type %s not found in our Dictinary pleaes check constants.py" %res_name)
    if not mod_name in IMPORTED_CLASS.keys():
        IMPORTED_CLASS[mod_name] = __import__("troposphere.%s" %mod_name, globals(), locals(), [''], -1)
    _temp = getattr(IMPORTED_CLASS[mod_name], class_name)
    
    #Pop name and type keys as they are added by us and not used in template
    res.pop('name')
    res.pop('type')
  
    #Here we check if any of the values have fucntions like Ref and if so make it a class
    resource_sanitized = sanitize_dict(res)
    try:
        resource = _temp(res_name, **resource_sanitized)
        template.add_resource(resource)
    except Exception as e:
        halo_error("error adding resource %s" %str(e))

def add_output_to_template(output, template):
    try:
        output_name = output['name'].lower()
    except KeyError:
        halo_erro( "name: key is mandatory for a output")

    #Pop name key as they are added by us and not used in template
    output.pop('name')

    #Here we check if any of the values have fucntions like Ref and if so make it a class
    outputs_sanitized = sanitize_dict(output)
    output_class = Output(output_name, **outputs_sanitized)
    template.add_output(output_class)

def stack_operation(conn, stack_name, wait, wait_timeout):
    if wait:
        timeout = time.time() + wait_timeout
    else:
        timeout = time.time + 1

    while timeout >  time.time():
        try:
            stack = conn.describe_stacks(stack_name)[0]
        except Exception as e:
            if 'does not exist' in e.message:
                result = "Stack Deleted:" +  stack_name
                return result
            halo_error("Exception while getting status of stack %s" %list(stack.describe_events()))
        print stack.stack_status
        if 'CREATE_COMPLETE' == stack.stack_status:
            result = dict(events = map(str, list(stack.describe_events())),
                          output = 'Stack Creation complete')
            return result
        if 'UPDATE_COMPLETE' == stack.stack_status:
            result = dict(events = map(str, list(stack.describe_events())),
                          output = 'Stack Update complete')
            return result
        if  'ROLLBACK_COMPLETE' == stack.stack_status or 'UPDATE_ROLLBACK_COMPLETE' == stack.stack_status:
            result = dict(events = map(str, list(stack.describe_events())),
                          output = 'Problem with CREATE or UPDATE Rollback complete')
            return result
        if 'UPDATE_FAILED'  == stack.stack_status:
            result = dict(events = map(str, list(stack.describe_events())),
                          output = 'Stack UPDATE failed')
            return result
        elif 'CREATE_FAILED'  == stack.stack_status:
            result = dict(events = map(str, list(stack.describe_events())),
                          output = 'Stack CREATE failed')
            return result
        else:
            time.sleep(5)
    halo_error("Timed Out while getting  status of stack" )

def validate_template(data):
    valid_template_keys = [ 'include_resources', 'resources', 'creds', 'stack_props', 'outputs']
    valid_stackprops_keys = ['state', 'region', 'rollback', 'stack_name', 'wait', 'wait_timeout']
    valid_creds_keys = ['access_key', 'secret_key']
    mandatory_template_keys = [ 'stack_props', 'resources' ]
    
    stackprops_stackname_set = False
    if not data['template'].get('stack_props'):
        halo_error("template needs the key 'stack_props'")
    state = data['template']['stack_props'].get('state', STACK_PROPS_DEFAULTS['state'])
    if state == 'absent':
        mandatory_template_keys.pop(1)
    if not isinstance(data, dict):
        halo_error("The template format seems wrong, we need a dictionary")
    if not 'template' in data.keys():
        halo_error("The template needs the key <template>")
    for i in mandatory_template_keys:
        if not data['template'].get(i):
            halo_error("The key %s is mandatory for template" %i)
    for i in data['template'].keys():
        if i not in valid_template_keys:
            halo_error("The key %s is not a valid template key" %i)
    for i in data['template']['stack_props'].keys():
        if i not in valid_stackprops_keys:
            halo_error("The key %s is not a valid template.stack_props key" %i)
        if i == 'stack_name':
            stackprops_stackname_set = True
    if not stackprops_stackname_set:
        halo_error("stack_name is mandatory key in stack_props")
    if data['template'].get('creds'):
        for i in data['template']['creds'].keys():
            if i not in valid_creds_keys:
                halo_error("The key %s is not a valid creds key" %i)

    
def connect_aws(aws_access_key=None, aws_secret_key=None, region=None):
    try:
        conn = boto.cloudformation.connect_to_region(
                      region,
                      aws_access_key_id=aws_access_key,
                      aws_secret_access_key=aws_secret_key,
              )  
    except boto.exception.NoAuthHandlerFound, e:
        halo_error("Error in connecting to aws %s" %str(e))
    return conn

#
#Try creating/updating the stack
#

def create_stack(conn=None, state='present', template=None, rollback=None, stack_name=None, wait=None, wait_timeout=None):
    if state.lower() == 'present':
        update = False
        try:
            conn.create_stack(stack_name, parameters=None,
                             template_body=template.to_json(),
                             stack_policy_body=None,
                             disable_rollback=rollback,
                             capabilities=['CAPABILITY_IAM'])
        except Exception, err:
            error_msg = boto_exception(err)
            if 'AlreadyExistsException' in error_msg or 'already exists' in error_msg:
                vvv("The template already exists, Trying to update")
                update = True
            else:
                halo_error("Failure in creating stack %s" %error_msg)
        if update:
            try:
                conn.update_stack(stack_name, parameters=None,
                                 template_body=template.to_json(),
                                 stack_policy_body=None,
                                 disable_rollback=rollback,
                                 capabilities=['CAPABILITY_IAM'])
            except Exception, err:
                error_msg = boto_exception(err)
                if 'No updates are to be performed' in error_msg:
                    halo_error(" Nothing to Update in stack ")
                halo_error("Failure in creating stack %s" %error_msg)
            vvv("stack is updated")
    
        stack_outputs = {}
        result = stack_operation(conn, stack_name, wait, wait_timeout)
        stack = conn.describe_stacks(stack_name)[0]
        for output in stack.outputs:
            stack_outputs[output.key] = output.value
        result['stack_outputs'] = stack_outputs
        return result

#
#Try deleting the stack
#
def stack_delete(conn=None, state='absent', stack_name=None, wait=None, wait_timeout=None):
    if state.lower() == 'absent':
        vvv("Trying to delete the stack")
        try:
            conn.describe_stacks(stack_name)
        except Exception, err:
            error_msg = boto_exception(err)
            if 'Stack:%s does not exist' % stack_name in error_msg:
                halo_error('Stack not found, so nothing to delete.')
        conn.delete_stack(stack_name)
        result = stack_operation(conn, stack_name, wait, wait_timeout)
        return result

    
