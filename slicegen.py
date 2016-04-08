#!/usr/bin/env python3

from collections import defaultdict

from subprocess import PIPE,Popen,\
check_output,DEVNULL,call,CalledProcessError,\
TimeoutExpired

import os
import re
import random

class SliceGen:
    def generate_input_file(self,benchmark_folder):
        benchmarks = []
        for root,dir,files in os.walk(benchmark_folder):
            print(dir)
            for item in dir:
                benchmarks.append(root+item)
            break
        for benchmark in benchmarks:
            cfiles = []
            cfiles = self.get_c_files(benchmark)
            if len(cfiles) > 0:
                index = 0
                slice_per_file = 0
                slice_count = 0
                selected_slices= set()
                tried_slices = set()
                total_attempts = 0
                while slice_count < 100 and total_attempts < 3000:
                    total_attempts +=1
                    f_csurf_in = open(benchmark+'/input.txt','w')
                    #print('searching file - '+cfiles[index])
                    try:
                        cfile_reader = open(cfiles[index],'r')
                        cfile_name = cfiles[index].split('/')[-1]
                        lines = cfile_reader.readlines()
                        #print(cfile_name)
                    except (Exception) as e:
                        print(e)
                        index +=1
                        continue
                    rand_attempt = 0
                    rand = 0
                    if len(lines) > 1:
                        rand = random.randrange(1,len(lines),1)
                        rand_attempt += 1
                        while cfile_name+str(rand) in selected_slices:
                            if rand_attempt > 10:
                                break
                            rand = random.randrange(1,len(lines),1)
                            rand_attempt += 1
                    if rand_attempt > 0 and rand_attempt < 10:
                        slice_string = cfiles[index]+':'+str(rand)
                        f_csurf_in.write(slice_string+'\n')
                        f_csurf_in.close()
                        response = ''
                        try:
                            command = 'csurf -nogui -l /home/nishanth/Workspace/PyHelium/csurf/plugin '+benchmark+'/myproj'
                            print('Running cmd - '+command)
                            p = Popen(command,shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
                            response,_ = p.communicate(input=None)
                            response = response.decode('utf8')
                            #print('slice result '+response)
                            #p.kill()
                        except (Exception) as e:
                            p.kill()
                            print(e)
                        response_lines = response.split('\n')
                        for i in range(0,len(response_lines)):
                            if 'Slice set size' in response_lines[i]:
                                slice_set_size = int(response_lines[i].split(':')[1].strip())
                                #print('Slize set = '+str(slice_set_size))
                                if(slice_set_size > 0):
                                    #add result set to result file.
                                    print(slice_string)
                                    f_result_in = open(benchmark+'/'+'result_'+str(slice_count)+'.txt','w')
                                    f_result_in.write('Slice line - '+slice_string+'\n')
                                    f_result_in.write('Lines in Slice - \n')
                                    for j in range(i+1,len(response_lines)):
                                        f_result_in.write(response_lines[j]+'\n')
                                    f_result_in.close()
                                    slice_count += 1
                                    selected_slices.add(cfile_name+str(rand))
                                    break
                    cfile_reader.close()
                    index +=1
                    if index >= len(cfiles):
                        index = 0
                    #break # remove this break to create more slices per benchmark
            break #remove this break to iterate through all benchmarks
    def get_c_files(self,benchmark):
        cfiles = []
        print('Entering benchmark: '+benchmark)
        for root,dir,files in os.walk(benchmark):
            for f in files:
                if f.endswith('.c'):
                    cfiles.append(root+'/'+f)
        return cfiles
    def has_any_item(self,line,item_list):
        for item in item_list:
            if item in line:
                return True
        return False
self = SliceGen()
self.generate_input_file('/home/nishanth/Workspace/testprojects/test100/')
