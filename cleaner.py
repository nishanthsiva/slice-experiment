#!/usr/bin/env python3

from collections import defaultdict

from subprocess import PIPE,Popen,\
check_output,DEVNULL,call,CalledProcessError,\
TimeoutExpired

import os
import re
import random
import logging

logger = logging.getLogger('Cleaner')
logger.setLevel(logging.INFO)

class Cleaner:
	def clean_benchmarks(self,benchmark_folder):
		benchmarks = []
		f_log = open('cleaner_logs.txt','w')
		for root,dir,files in os.walk(benchmark_folder):
			print(dir)
			for item in dir:
				benchmarks.append(root+item)
			break
		for benchmark in benchmarks:
			print('entering '+benchmark)
			command = 'cd '+benchmark+';'
			#command += 'mkdir slice_results;'
			#command += 'mv result_* slice_results;'
			command += 'rm -rf my*;'
			command += 'rm -rf a.out;'
			command += 'make clean;'
			command += 'csurf hook-build myproj make;'
			command += 'echo "PRESET_BUILD_OPTIONS = highest" | cat >> myproj.csconf;'
			command += 'csurf hook-build myproj;'
			try:
			    #print('Running cmd - '+command)
			    p = Popen(command,shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
			    response,_ = p.communicate(input=None, timeout=900)
			    response = response.decode('utf8')
			    f_log.write('building benchmark '+benchmark)
			    response  = response.split('\n')
			    for response_line in response:
			    	if 'Summary Edges' in response_line:
			    		f_log.write(response_line)
			    #f_log.write(response)
			    print(response)
			    #p.kill()
			except (Exception) as e:
			    p.kill()
			    f_log.write('error in '+benchmark)
			    print(e)
self = Cleaner()
self.clean_benchmarks('/home/nishanth/Workspace/testprojects/test100/')