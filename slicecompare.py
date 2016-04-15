#!/usr/bin/env python3

from PyHelium.helium.component import ctagscache
from collections import defaultdict

from subprocess import PIPE,Popen,\
check_output,DEVNULL,call,CalledProcessError,\
TimeoutExpired

from slicer import Slicer

import os
import re
import logging

logger = logging.getLogger('SliceCompare')
logger.setLevel(logging.CRITICAL)

class SliceCompare:
    def create_csurf_map(self,map_file):
        file_reader = open(map_file,'r')
        lines = file_reader.readlines()
        csurf_map = defaultdict()
        for line in lines:
            path,sep,build_name = line.partition('\t')
            csurf_map[path] = build_name.split('\n')[0]
        self.csurf_map = csurf_map
        self.slicer = Slicer()
    def merge_data_control_slices(self,benchmark_folder):
        benchmarks = []
        for root,dir,files in os.walk(benchmark_folder):
            #print(dir)
            for item in dir:
                benchmarks.append(root+item)
            break
        f_build_rate = open('assert_build_rate_ds.csv','w')
        f_slice_prop = open('assert_slice_property_ds.csv','w')
        f_build_rate.write('Benchmark,Slices,Size of smallest slice built,Size of largest slice built,Build Rate\n')
        f_slice_prop.write('Benchmark,Slices,Smallest slice size,Largest slice size,Average Slice size,Min procedure count, Max procedure count, Avg procedure count,Inter procedural slices, Inter file slices\n')
        f_result_csv = open('assert_result_ds.csv','w')
        f_result_csv.write('benchmark,slices,avg-data-slice-size,avg-full-slice-size,avg-slice-size,inter-procedural-slices,inter-file-slices,build_rate\n')
        build_rate = defaultdict(int)
        for benchmark in benchmarks:
            statements = 0
            bench_list = ['tj-histo', 'json-c-json-c', 'jonas-tig', 'Cyan4973-zstd', 'Phildo-pixQL', 'kr-beanstalkd', 'joyent-http-parser', 'yrutschle-sslh', 'rui314-8cc', 'udp-json-parser', 'cisco-thor']
            bench_list += [ 'libuv-libuv', 'patjak-bcwc_pcie', 'douban-beansdb', 'droe-sslsplit', 'orangeduck-mpc', 'machinezone-tcpkali', 'wg-wrk', 'karthick18-inception', 'vmg-houdini', 'antirez-disque']
            if benchmark.split('/')[-1] in bench_list:
                self.inter_procedural_slices = 0
                self.slice_size = 0
                self.inter_file_slices = 0
                self.min_slice_size = 0
                self.max_slice_size = 0
                self.min_slice_procedures = 0
                self.max_slice_procedures = 0
                self.avg_slice_procedures = 0
                self.min_built_slice_size = 0
                self.max_built_slice_size = 0

                result_data_files = []
                result_control_files = []
                result_data_files, result_control_files = self.get_slice_files(benchmark)
                statements = len(result_data_files)
                #logger.warn('Number of data files = '+str(len(result_data_files)))
                matching_sets = 0
                self.inter_procedural_slices = 0
                self.inter_file_slices = 0
                self.build_rate = 0
                avg_slice_size = 0
                avg_data_slice_size = 0
                avg_control_slice_size = 0
                if len(result_data_files) > 0 and len(result_control_files) > 0:
                    for data_file in result_data_files:
                        f_data_file = open(data_file,'r')
                        data_slice_lines = f_data_file.readlines()
                        f_data_file.close()
                        data_line_set = set()
                        files_in_slice = set()
                        for line in data_slice_lines:
                            if '.h' not in line:
                                if line not in data_line_set and line.strip() != '':
                                    if line.split('\t')[0] not in files_in_slice:
                                        files_in_slice.add(line.split('\t')[0])
                                    data_line_set.add(line)
                                    #self.get_wrapper_function(line)
                        control_file = data_file.replace('result_assert','result_assert_control')
                        f_control_file = open(control_file,'r')
                        control_slice_lines = f_control_file.readlines()
                        f_control_file.close()
                        control_line_set = set()
                        for line in control_slice_lines:
                            if '.h' not in line:
                                if line not in control_line_set and line.strip() != '':
                                    control_line_set.add(line)
                        logger.info(str(len(data_line_set)))
                        logger.info(str(len(control_line_set)))
                        if data_line_set.issubset(control_line_set):
                            matching_sets += 1
                            merged_slices = self.merge_slices(list(data_line_set),defaultdict(list), list(control_line_set),defaultdict(list),1)
                            
                            self.slice_size += len(merged_slices)
                            avg_slice_size += len(merged_slices)

                            if self.min_slice_size == 0:
                                self.min_slice_size = len(merged_slices)
                            if len(merged_slices) < self.min_slice_size:
                                self.min_slice_size = len(merged_slices)
                            if len(merged_slices) > self.max_slice_size:
                                self.max_slice_size = len(merged_slices)

                            avg_data_slice_size += len(data_line_set)
                            avg_control_slice_size += len(control_line_set)
                            if len(files_in_slice) > 1:
                                self.inter_file_slices += 1
                            logger.critical('Slice size for '+data_file+' :'+str(len(merged_slices)))
                            slice_file_location = self.slicer.get_file_path(data_slice_lines[0])
                            slice_code = self.slicer.get_slice_code(merged_slices)
                            self.slicer.generate_slice_file(slice_code)
                            if self.slicer.build_slice_file(slice_file_location) == True:
                                self.build_rate +=1

                                build_rate[benchmark.split('/')[-1]]+=1
                                if self.min_built_slice_size == 0:
                                    self.min_built_slice_size = len(slice_code)
                                if len(slice_code) < self.min_built_slice_size:
                                    self.min_built_slice_size = len(slice_code)
                                if len(slice_code) > self.max_built_slice_size:
                                    self.max_built_slice_size = len(slice_code)

                        else:
                            logger.warn('set mismatch!!')
                            return 0
                    logger.warn('Data slice is subset of control slice in '+benchmark)
                f_result_csv.write(benchmark.split('/')[-1]+','+str(statements)+','+str(avg_data_slice_size/100)+','+str(avg_control_slice_size/100)+','+str(avg_slice_size/100)+','+str(self.inter_procedural_slices)+','+str(self.inter_file_slices)+','+str(build_rate[benchmark.split('/')[-1]])+'\n')
                f_build_rate.write(benchmark.split('/')[-1]+','+str(statements)+','+str(self.min_built_slice_size)+','+str(self.max_built_slice_size)+','+str(build_rate[benchmark.split('/')[-1]])+'\n')
                f_slice_prop.write(benchmark.split('/')[-1]+','+str(statements)+','+str(self.min_slice_size)+','+str(self.max_slice_size)+','+str(self.slice_size/100)+','+str(self.min_slice_procedures)+','+str(self.max_slice_procedures)+','+str(self.avg_slice_procedures/100)+','+str(self.inter_procedural_slices)+','+str(self.inter_file_slices)+'\n')
        f_result_csv.close()
        f_build_rate.close()
        f_slice_prop.close()

    def merge_slices(self,data_slice_list,data_slice_fns,control_slice_list,control_slice_fns,depth):
        logger.info('data_slice_fns -'+str(data_slice_fns))
        merged_slices = []
        for data_slice in data_slice_list:
            if data_slice.strip() != '' and len(data_slice.split('\t')) == 2:
                function_decl,start_index,end_index = self.get_wrapper_function(data_slice)
                function_name = function_decl.split('(')[0].split(' ')[-1]
                if function_decl != '':
                    data_slice_fns[function_decl] = [function_name,start_index,end_index]
                else:
                    merged_slices.append(data_slice)
        resolve_call_sites = False
        for control_slice in control_slice_list:
            if control_slice.strip() != '' and len(control_slice.split('\t')) == 2:
                function_decl,start_index,end_index= self.get_wrapper_function(control_slice)
                function_name = function_decl.split('(')[0].split(' ')[-1]
                control_slice_fns[function_decl] = [function_name,start_index,end_index]
                if function_decl in data_slice_fns:
                    has_new_call_sites,data_slice_fns = self.get_new_call_sites(control_slice,data_slice_fns,control_slice_fns)
                    if  has_new_call_sites == True:
                        resolve_call_sites = True
                        logger.info('call site found - '+control_slice)
                    merged_slices.append(control_slice)
        if resolve_call_sites == True and depth < 5:
            return self.merge_slices(merged_slices,data_slice_fns,control_slice_list,control_slice_fns,depth+1)
        else:
            self.avg_slice_procedures += len(data_slice_fns)
            if self.min_slice_procedures == 0:
                self.min_slice_proceures = len(data_slice_fns)
            if len(data_slice_fns)< self.min_slice_procedures:
                self.min_slice_procedures = len(data_slice_fns)
            if len(data_slice_fns) > self.max_slice_procedures:
                self.max_slice_procedures = len(data_slice_fns)
            if len(data_slice_fns) > 1:
                self.inter_procedural_slices +=1
            logger.info('control slice fns - '+str(control_slice_fns))
            return merged_slices
    def get_new_call_sites(self,slice_line,data_slice_fns,control_slice_fns):
        keywords = ['if','switch','while']
        file_name = slice_line.split('\t')[0]
        line_number = int(slice_line.split('\t')[1])
        f_cfile = open(file_name,'r')
        lines = f_cfile.readlines()
        is_call_site = False
        line = lines[line_number-1]
        fns_called = []
        if re.search('[a-zA-Z]+\([^\)]*\)(\.[^\)]*\))?',line):
            fn_names  = line.split('(')
            index = 0
            for fn_name in fn_names:
                if index == len(fn_names) -1:
                    break
                temp = ''
                logger.info('splitting '+fn_name)
                for i in range(len(fn_name)-1, 0,-1):
                    if fn_name[i].isalnum() == True or fn_name[i]=='_': 
                        temp = fn_name[i] + temp
                    else:
                        break
                index += 1
                if self.has_any_item(temp,keywords) == False:
                    fns_called.append(temp)
                    is_call_site = True
                    logger.info('call site -'+line)
        has_new_call_sites = False
        if is_call_site == True:
            for fn_called in fns_called:
                for key,value in control_slice_fns.items():
                    if value[0] == fn_called:
                        if key not in data_slice_fns:
                            data_slice_fns[key] = value
                            has_new_call_sites = True
        f_cfile.close()
        return has_new_call_sites,data_slice_fns  
    def get_slice_files(self,benchmark):
        result_data_files = []
        result_control_files = []
        print('Entering benchmark: '+benchmark)
        for root,dir,files in os.walk(benchmark):
            for f in files:
                if f.startswith('result_assert') and 'result_assert_control' not in f:
                    result_data_files.append(root+'/'+f)
                if f.startswith('result_assert_control'):
                    result_control_files.append(root+'/'+f)
        return result_data_files, result_control_files
    def get_wrapper_function(self,slice_line):
        keywords = ['if','switch','while']
        special_char = [';','=','"']
        if len(slice_line.split('\t')) < 2:
            return '',0,0
        file_name = slice_line.split('\t')[0]
        line_number = int(slice_line.split('\t')[1])
        f_cfile = open(file_name,'r')
        lines = f_cfile.readlines()
        line_num = 1
        slice_found = False
        for line in lines:
            if re.search('\w\(',line)  and line.count('(') < 2 and line.count(')') <2:
                if self.has_any_item(line,keywords) == False and self.has_any_item(line,special_char) == False:
                    decl_end_index = self.find_decl_end_index(lines,line_num-1)
                    start,end = self.find_block_limits(lines,line_num-1)
                    if line_number >= start and line_number <= end+1:
                        slice_found = True
                        logger.info('Slice - '+slice_line)
                        logger.info('Slice found in function - '+line)
                        logger.info('limits - '+str(start)+' to '+str(end))
                        return line,start,end
            line_num +=1
        if slice_found == False:
            logger.info('Slice '+slice_line+' not found in any function')
        f_cfile.close()
        return '',0,0
    def has_any_item(self,line,item_list):
        for item in item_list:
            if item in line:
                return True
        return False
    def find_block_limits(self,lines,line_index):
        open_brace_count = 0
        close_brace_count = 0
        start_index = line_index
        end_index = line_index
        begin_found = False
        for i in range(line_index, len(lines)):
            open_brace_count += lines[i].count('{')
            close_brace_count += lines[i].count('}')
            if open_brace_count == 1 and begin_found != True:
                start_index = i
                begin_found = True
            if open_brace_count>0 and open_brace_count == close_brace_count:
                end_index = i
                break
        return start_index,end_index
    def find_decl_end_index(self,lines,line_number):
        for i in range(line_number,len(lines)):
            if ')' in lines[i]:
                return i;
    def create_control_slice(self,benchmark_folder):
        logger.warn(self.csurf_map)
        benchmarks = []
        for root,dir,files in os.walk(benchmark_folder):
            #print(dir)
            for item in dir:
                benchmarks.append(root+item)
            break
        for benchmark in benchmarks:
            f_used_in = open(benchmark+'/used_input.txt','r')
            for line in f_used_in.readlines():
                f_csurf_in = open(benchmark+'/input.txt','w')
                f_csurf_in.write(line)
                f_csurf_in.close()
                logger.warn(line)
                cfile_name = line.split(':')[0].split('/')[-1]
                line_num =  int(line.split(':')[1])
                try:
                    command = 'csurf -nogui -l /home/nishanth/Workspace/PyHelium/csurf/plugin '+benchmark+'/myproj'
                    #print('Running cmd - '+command)
                    p = Popen(command,shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
                    response,_ = p.communicate(input=None)
                    response = response.decode('utf8')
                    print(response)
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
                            f_result_in = open(benchmark+'/'+'result_assert_control'+cfile_name+str(line_num)+'.txt','w')
                            for j in range(i+1,len(response_lines)):
                                f_result_in.write(response_lines[j]+'\n')
                            f_result_in.close()
            f_used_in.close()


self = SliceCompare()
self.create_csurf_map('/home/nishanth/Workspace/csurf_map.txt')
#self.create_control_slice('/home/nishanth/Workspace/testprojects/test100/')
self.merge_data_control_slices('/home/nishanth/Workspace/testprojects/test100/')
