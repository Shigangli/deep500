import os
import subprocess
from typing import Dict
from deep500.utils.metric import TestMetric

# Adapted from Fred Cirera's human-readable file size printer
# https://web.archive.org/web/20111010015624/http://blogmag.net/blog/read/38/Print_human_readable_file_size
def _sizeof_fmt(num):
    for unit in ['B','KiB','MiB','GiB','TiB','PiB','EiB','ZiB']:
        if abs(num) < 1024.0:
            return "%3.1f%s" % (num, unit)
        num /= 1024.0
    return "%.1f%s" % (num, 'YiB')

class CommunicationVolume(TestMetric):
    """ Estimates communication volume of a node by checking transferred byte
        statistics on the NICs. Currently uses ifstat for Linux and Mac OS. """
        
    def __init__(self, tool_path='/usr/sbin/ifstat', prettyprint=True):
        if os.name == 'nt':
            raise NotImplementedError('Windows is not supported with CommunicationVolume')
        self._tool = tool_path
        self._pretty = prettyprint
    
    def runproc(self):
        process = subprocess.Popen([self._tool], stderr=subprocess.STDOUT, 
                                   stdout=subprocess.PIPE)
        output, _ = process.communicate()
        errcode = process.wait()
        if errcode != 0:
            raise ValueError('Process "%s" has encountered an exception '
                             '(exit code: %d). Output:\n%s' % (self._tool, 
                                errcode, output))
        return output
        
    def begin(self, *args):
        # Run tool once
        self._begin_m = self.runproc()
        
    def end(self, *args):
        # Run tool again to get the total bytes sent/received 
        self._end_m = self.runproc()
        
    def _parse_ifstat(self, output):
        # Parse an output ifstat string
        def _parsestring(value):
            if value.endswith('K'):
                return int(value[:-1]) * 1000
            elif value.endswith('M'):
                return int(value[:-1]) * 1000000
            return int(value)
                    
        
        if not isinstance(output, str):
            output = output.decode('utf-8')
        
        lines = output.split('\n')
        result = {}
        for line in lines[3:-1:2]: # Skip title, end newline, and irrelevant metrics
            tok = line.split() # Split to tokens
            result[tok[0]] = (_parsestring(tok[5]), _parsestring(tok[7]))
            
        return result
        
    def measure(self, *args) -> Dict[str, int]:
        """ Returns a dictionary of network interface name to (received, sent)
            bytes. """
        return self._parse_ifstat(self._end_m)
        
    def measure_summary(self, *args) -> str:
        """ Outputs the total number of bytes transferred from/to this node. """
        nics = self.measure()
        total_bytes = sum(v[0] + v[1] for v in nics.values())
        if not self._pretty:
            return str(total_bytes)
        
        # Pretty-print
        return _sizeof_fmt(total_bytes)
