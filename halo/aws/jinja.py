import json
try:
    from jinja2 import Environment
    from jinja2.runtime import StrictUndefined
    from jinja2.exceptions import TemplateSyntaxError
except ImportError:
    sys.stderr.write("jinja2 python module not found")
    sys.exit(1)
from halo_errors import halo_error

def template_dict_variables(data, **kwargs):
    vars = kwargs
    for t in data['template'].keys():
        if t in [ 'resources', 'outputs']:
            tmp_list = []
            for i in data['template'][t]:
                tmp_dict = {}
                for k,v in i.items():
                    if isinstance(v, basestring) and v.find("{{") >= 0 :
                        v = template_string(v, **vars)
                    if isinstance(v, list):
                        for j in v:
                            if isinstance(j, basestring) and j.find("{{") >= 0:
                                v[v.index(j)] = template_string(j, **vars)
                            elif isinstance(j, dict):
                                tmp = {}
                                for x,y in j.items():
                                    if isinstance(y, basestring) and y.find("{{") >= 0:
                                        tmp[x] = template_string(y, **vars)
                                        break;
                                tmp[x] = y
                            v[index(j)] = tmp
                    if isinstance(v, dict):
                        for x,y in v.items():
                            if isinstance(y, basestring) and y.find("{{") >= 0:
                                v[x] = template_string(y, **vars)
                                break;
                    tmp_dict[k] = v
                tmp_list.append(tmp_dict)
            data['template'][t] = tmp_list
        elif t == 'include_resources':
            if isinstance(data['template'][t], basestring):
                v = data['template'][t]
                if v.find('{{') >= 0:
                    fpath = template_string(v, **vars)
                    data['template'][t] = fpath
            elif isinstance(data['template'][t], list):
                tmp_lst = []
                for l in data['template'][t]:
                    if l.find("{{") >= 0:
                        tmp_str = template_string(l, **vars)
                        tmp_lst.append(tmp_str)
                    else:
                        tmp_lst.append(l)
                data['template'][t] = tmp_lst
        else:
            for k,v in data['template'][t].items():
                if isinstance(v, basestring) and v.find("{{") >=0 :
                    data['template'][t][k] = template_string(v, **vars)
                    break                

def template_string(data, **vars):
    if type(data) == str:
        data = unicode(data, 'utf-8')
    environment = Environment(trim_blocks=True, undefined=StrictUndefined)
    if isinstance(data, unicode):
        try:
            data = data.decode('utf-8')
        except UnicodeEncodeError, e:
            pass
    try:
        t = environment.from_string(data)
    except TemplateSyntaxError, e:
        halo_error("template error while templating string: %s" % str(e))
    except Exception, e:
        if 'recursion' in str(e):
            halo_error("recursive loop detected in template string: %s" % data)
        else:
            halo_error(str(e))
    try:
       return t.render(**vars)
    except Exception as e:
        halo_error("Error in rendering templated parameter: %s" %str(e) )
