#!/usr/bin/env python3

from collections import defaultdict

from subprocess import PIPE,Popen,\
check_output,DEVNULL,call,CalledProcessError,\
TimeoutExpired

import os
import re
import random
import csv

class ClocTool:
    def getBenchmarkFolders(self,benchmark_path):
        benchmarks = []
        for root,dir,files in os.walk(benchmark_path):
            print(dir)
            for item in dir:
                benchmarks.append(root+item)
            break
        self.benchmarks = benchmarks
    def getLOCReport(self):
        f_cloc = open('cloc_report.csv','w')
        f_cloc.write('benchmark,LOC\n')
        for benchmark in self.benchmarks:
            lines_of_code = self.getLOCForBenchmark(benchmark)
            f_cloc.write(benchmark.split('/')[-1]+','+str(lines_of_code)+'\n')
        f_cloc.close()
    def getLOCForBenchmark(self,benchmark):
        lines_of_code = 0
        try:
            command = 'cloc --quiet --csv --out=cloc.csv '+benchmark
            print('Running cmd - '+command)
            p = Popen(command,shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            response,_ = p.communicate(input=None, timeout=600)
            response = response.decode('utf8')
            #p.kill()
        except (Exception) as e:
            p.kill()
            print(e)
        with open('cloc.csv', 'rt') as f:
            reader = csv.reader(f)
            for row in reader:
                if row[1] == 'C' or row[1] == 'C/C++ Header':
                    if row[-1].isnumeric() == True:
                        lines_of_code += int(row[-1])
        f.close()
        return lines_of_code

self = ClocTool()
self.getBenchmarkFolders('/home/nishanth/Workspace/testprojects/test100/')
self.getLOCReport()
