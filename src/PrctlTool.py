 
try:
  from prctl import set_name as prctl_set_name
  from prctl import get_name as prctl_get_name
except ImportError:
  prctl_set_name = lambda x:None
  prctl_get_name = lambda :""

def set_title(name):
  """ Set the process name shown in ps, proc, or /proc/self/cmdline """
  prctl_set_name(name)

def get_title():
  """ Get the process name shown in ps, proc or /proc/self/cmdline """
  return prctl_get_name()
