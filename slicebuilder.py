#!/usr/bin/env python3

from PyHelium.helium.component import ctagscache
from collections import defaultdict

from subprocess import PIPE,Popen,\
check_output,DEVNULL,call,CalledProcessError,\
TimeoutExpired

import os
import re
import logging

logger = logging.getLogger('Slicer')
logger.setLevel(logging.WARNING)

class Slicer:
    def init(self,path):
        ctagscache.build(path)
    def test_slicer(self):
        result = []
        result = ctagscache.parse('PredictorSetup')
        for i in range(0,len(result)):
            print(result[i])
    def __init__(self):
        self.inter_procedural_slices = 0
        self.slice_size = 0
        self.inter_file_slices = 0
        self.slice_procedures = 0
        self.min_slice_procedures = 0
        self.max_slice_procedures = 0
        self.avg_slice_procedures = 0
        self.min_slice_size = 0
        self.max_slice_size = 0
        self.min_built_slice_size = 0
        self.max_built_slice_size = 0
        self.error_files_count = 0
    def sort_slice_lines(self,slice_result_folder):
        f_build_rate = open('build_rate.csv','w')
        f_slice_prop = open('slice_property.csv','w')
        f_build_rate.write('Benchmark,Slices,Size of smallest slice built,Size of largest slice built,Build Rate\n')
        f_slice_prop.write('Benchmark,Slices,Smallest slice size,Largest slice size,Average Slice size,Min procedure count, Max procedure count, Avg procedure count,Inter procedural slices, Inter file slices\n')
        build_rate = defaultdict(int)
        benchmarks = []
        for root,dir,files in os.walk(slice_result_folder):
            #print(dir)
            for item in dir:
                benchmarks.append(root+item)
            break
        for benchmark in benchmarks:
            for benchmark_dir,_,result_files in os.walk(benchmark):
                self.inter_procedural_slices = 0
                self.slice_size = 0
                self.inter_file_slices = 0
                self.min_slice_size = 0
                self.max_slice_size = 0
                self.min_slice_procedures = 0
                self.max_slice_procedures = 0
                self.avg_slice_procedures = 0
                self.min_slice_size = 0
                self.max_slice_size = 0
                self.min_built_slice_size = 0
                self.max_built_slice_size = 0
                slice_result_files = []
                for file in result_files:
                    if file.startswith('result_control'):
                        slice_result_files.append(file)
                index = 0
                for result_file in slice_result_files:
                    index = index+1
                    fin = open(os.path.join(benchmark_dir,result_file))
                    logger.info('input file: '+result_file)
                    lines = fin.readlines()
                    slice_file_location = self.get_file_path(lines[0])
                    slice_code = self.get_slice_code(lines)
                    self.generate_slice_file(slice_code)
                    if self.build_slice_file(slice_file_location) == True:  # replace benchmark_dir with the slice input location
                        build_rate[benchmark_dir]+=1
                        if self.min_built_slice_size == 0:
                            self.min_built_slice_size = len(slice_code)
                        if len(slice_code) < self.min_built_slice_size:
                            self.min_built_slice_size = len(slice_code)
                        if len(slice_code) > self.max_built_slice_size:
                            self.max_built_slice_size = len(slice_code)
                if self.slice_size > 0:
                    f_build_rate.write(benchmark_dir+','+str(index)+','+str(self.min_built_slice_size)+','+str(self.max_built_slice_size)+','+str(build_rate[benchmark_dir])+'\n')
                    f_slice_prop.write(benchmark_dir+','+str(index)+','+str(self.min_slice_size)+','+str(self.max_slice_size)+','+str(self.slice_size/100)+','+str(self.min_slice_procedures)+','+str(self.max_slice_procedures)+','+str(self.avg_slice_procedures/100)+','+str(self.inter_procedural_slices)+','+str(self.inter_file_slices)+'\n')
        f_build_rate.close()
        f_slice_prop.close()
        logger.critical(build_rate)
    def get_slice_code(self,slice_result):
        filename = ''
        s = set()
        fnameset = set()
        input_map = defaultdict(list)
        for i in range(0,len(slice_result)):
            line = slice_result[i].split('\n')[0]
            if line != '\n' and line !='' and len(line.split('\t')) > 1:
                if(line not in s):
                    s.add(line)
                    filename= line.split('\t')[0]
                    if filename.endswith('.h'):
                        continue
                    line_num = line.split('\t')[-1]
                    line_num_list = input_map[filename]
                    if not line_num_list:
                        line_num_list = []
                    line_num_list.append(int(line_num))
                    input_map[filename] = line_num_list
        if self.min_slice_size == 0:
            self.min_slice_size = len(s)
        if len(s) < self.min_slice_size:
            self.min_slice_size = len(s)
        if len(s) > self.max_slice_size:
            self.max_slice_size = len(s)
        self.slice_size += len(s);
        slice_code = []
        self.slice_procedures = 0
        for key,value in input_map.items():
            #logger.info('key: '+key+' slice size: '+str(len(value)))
            slice_code.append('// Begin of file - '+key+'\n')
            slice_code = slice_code + self.get_slice_lines(key,value)
            slice_code.append('// end of file - '+key+'\n')
        self.avg_slice_procedures += self.slice_procedures
        if self.min_slice_procedures == 0:
            self.min_slice_proceures = self.slice_procedures
        if self.slice_procedures < self.min_slice_procedures:
            self.min_slice_procedures = self.slice_procedures
        if self.slice_procedures > self.max_slice_procedures:
            self.max_slice_procedures = self.slice_procedures
        if self.slice_procedures > 1:
            self.inter_procedural_slices +=1
        if len(input_map) > 1:
            self.inter_file_slices += 1
        return slice_code
    def get_file_path(self,slice_line):
        parts = slice_line.split('/')
        path = ''
        for i in range(0,len(parts)-1):
            path = path + parts[i]+'/'
        return path
    def build_slice_file(self,benchmark_dir):
        try:
            logger.info('moving to '+benchmark_dir)
            command = 'cp generate.c '+benchmark_dir+';gcc -I '+benchmark_dir+' '+benchmark_dir+'generate.c;'
            logger.warn('Running cmd - '+command)
            p = Popen(command,shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            #response,_ = p.communicate(input=None)
            #stdout = p.stdout.read()
            error = p.stderr.read()
            #compile_result = open(response).readlines()
            err_response = str(error)
            logger.info('error ' +str(len(error)))
            if len(error) < 10:
                #self.print_generated_file(index,error)
                logger.warn('successful build')
                return True
            else:
                self.print_generated_file(error)
            #logger.info('stdout '+str(stdout))
        except (Exception) as e:
            p.kill()
            print(e)
        return False
    def generate_slice_file(self,slice_result):
        fout = open('generate.c','w')
        main_found = False
        for line in slice_result:
            if 'int main' in line:
                main_found = True
            fout.write(line)
        if main_found == False:
            fout.write('int main(){return 1;}')
        fout.close()
    def print_generated_file(self,error):
        if self.error_files_count < 100:
            fin = open('generate.c','r')
            fout = open('uncompiled_files/generate'+str(self.error_files_count)+'.c','w')
            logger.info('generating file generate'+str(self.error_files_count)+'.c')
            lines = fin.readlines()
            for line in lines:
                fout.write(line)
            fout.close()
            self.error_files_count += 1
        #fout = open('error'+str(index)+'.txt','w')
        #lines = error.decode('utf8')
        #lines = lines.split('\n')
        #for line in lines:
        #    fout.write(line)
        #fout.close()
    def get_slice_lines(self,filename,line_numbers):
        splits = filename.split('/')
        name = splits[len(splits)-1].split('.')[0]
        file_output = []
        input_file = open(filename,'r')
        #logger.info('output file: '+name+str(index))
        lines = input_file.readlines()
        line_num = 1
        keyword_list = ['if(','if (','switch(','switch (','else','for(','for (','while(','while (','do']
        includes_set = set()
        for line in lines:
            line.strip()
            keyword_found = False
            #print(lines)
            if "#include" in line or '# include' in line:
                #fout.write(line)
                if line not in includes_set:
                    file_output.append(line)
                    includes_set.add(line)
            if '#if' in line.lower() and '#include' in lines[line_num]:
                i = line_num - 1
                logger.info('found :'+line)
                while i in range(line_num-1,len(lines)):
                    file_output.append(lines[i])
                    if '#include' in lines[i]:
                        includes_set.add(lines[i])
                    logger.info('appending '+lines[i])
                    if "#endif" in lines[i].lower():
                        break
                    i +=1
            if line.startswith('#define'):
                define_block = self.extract_define(lines,line_num-1)
                file_output = self.write_block(define_block,file_output)
            if 'goto' in line and ';' in line:
                if line_num in line_numbers:
                    line_numbers.remove(line_num)
            if 'struct' in line and ',' not in line and '(' not in line and ')' not in line:
                #if line.startswith('typedef') or line.startswith('static') or line.startswith('struct'):
                if '{' in line:
                    struct_block = self.extract_forward(lines,line_num-1)
                    file_output = self.write_block(struct_block,file_output)
            if (line.startswith('enum ') or ' enum ' in line)  and '{' in line:
                enum_block =  self.extract_forward(lines,line_num-1)
                file_output = self.write_block(enum_block,file_output)
            if line.startswith('typedef') and ';' in line and '{' not in line:
                file_output.append(line)
            if line_num in line_numbers:
                for i in range(0,len(keyword_list)):
                    if keyword_list[i] in line:
                        #print('found '+keyword_list[i]+' in line:'+line)
                        nextline = lines[line_num]
                        close_index = -1
                        if '{' in line:
                            close_index = self.find_close_index(lines,line_num,0)
                        elif '{' in nextline:
                            line_numbers.append(line_num+1)
                            close_index = self.find_close_index(lines, line_num,1)
                        if close_index == -1 and line_num+1 not in line_numbers and ';' not in line:
                            line = line + "{\n}\n"
                        line_numbers.append(close_index+1)
                        keyword_found = True
                        break
                #write logic to identify functions
                if keyword_found != True:
                    if re.search('\w\(',line) and ';' not in line and '=' not in line and line.count('(') < 2 and line.count(')') <2:
                        #print('function found in line :'+line)
                         # not a keyword => it is a function
                         # identify any return types and modifiers
                        before,sep,after = line.partition('(')
                        if len(before.split(' ')) == 1:
                            if (line_num-1) not in line_numbers:
                                file_output.append(lines[line_num-2])
                        #identify the end of the function declarations
                        decl_end_index = self.find_decl_end_index(lines,line_num-1)  # to identify fn decl across multiple lines
                        for i in range(line_num,decl_end_index+2): #need to add until line_num of line[decl_end_index]
                             line_numbers.append(i)
                        #identify function block begin & end
                        start,end = self.find_block_limits(lines,line_num-1)
                        line_numbers.append(start+1)
                        line_numbers.append(end+1)
                        self.slice_procedures += 1
                        #print('start fn: '+str(start+1)+' end fn: '+str(end+1))
                    if '[' in line and ']' in line and '=' in line and ('{' in line or '{' in lines[line_num]):
                        start,end = self.find_block_limits(lines,line_num-1)
                        for i in range(start+1,end+2):
                            line_numbers.append(i)
                file_output.append(line)
            #increase the line number
            line_num = line_num + 1
        return file_output

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
                #print('decl end '+lines[i])
                return i;
    def write_block(self,lines,file_output):
        for item in lines:
            #print(item)
            file_output.append(item)
        return file_output
    def extract_define(self,lines,line_number):
        line = lines[line_number]
        result = []
        result.append(line)
        while line.strip().endswith('\\'):
            line_number += 1
            line = lines[line_number]
            result.append(line)
        return result
    def extract_forward(self,lines, line_number):
        result = []
        open_brace_count = 0
        close_brace_count = 0
        while True:
            if line_number+1 > len(lines): return result
            line = lines[line_number]
            line_number += 1
            result.append(line)
            open_brace_count += line.count('{')
            close_brace_count += line.count('}')
            if open_brace_count>0 and open_brace_count == close_brace_count:
                return result
    def find_close_index(self,lines, line_number, braces_flag):
        #print('finding close brace from '+str(line_number))
        close_brace_count = 0
        if braces_flag == 0:
            open_brace_count = 1
        else:
            open_brace_count = 0
        #print('obc '+str(open_brace_count)+' cbc '+str(close_brace_count))
        for i in range(line_number, len(lines)):
            #print(lines[i])
            open_brace_count += lines[i].count('{')
            close_brace_count += lines[i].count('}')
            if open_brace_count>0 and open_brace_count == close_brace_count:
                return i
        return -1

self = Slicer()
#self.init('/home/nishanth/Workspace/testprojects/libtiff/')
#self.test_slicer()
self.sort_slice_lines('/home/nishanth/Workspace/testprojects/test100/')
