import scipy.stats
import numpy

"""
from thclient import TreeherderClient

client = TreeherderClient(protocol='https', host='treeherder.mozilla.org')

resultsets = client.get_resultsets('mozilla-central') # gets last 10 by default
for resultset in resultsets:
    jobs = client.get_jobs('mozilla-central', result_set_id=resultset['id'])
    for job in jobs:
        print job['start_timestamp']
"""

import thclient
import json

# Figuring out why this is bad, despite tons of retriggers:
# https://treeherder.allizom.org/perf.html#/comparesubtest?originalProject=mozilla-inbound&originalRevision=4d0818791d07&newProject=mozilla-inbound&newRevision=5e130ad70aa7&originalSignature=72f4651f24362c87efb15d5f4113b9ca194d8e3f&newSignature=72f4651f24362c87efb15d5f4113b9ca194d8e3f

BASE_REVISION = '4d0818791d07'
NEW_REVISION = '5e130ad70aa7'
TRESIZE_SUBTEST_SIGNATURE = '61f6b38023425efa219d03f69e8fb39fbec6577f'

# revisions from July 30th, need a wide enough range (soon we will be able 
# to look up datums by result set id, and this will be irrelevant)
INTERVAL = thclient.PerformanceTimeInterval.SIXTY_DAYS 

cli = thclient.PerfherderClient()
original_result_set_id = cli.get_resultsets('mozilla-inbound', revision=BASE_REVISION)[0]['id']
new_result_set_id = cli.get_resultsets('mozilla-inbound', revision=NEW_REVISION)[0]['id']
print 'orig set id: %d   new set id: %d' % (original_result_set_id, new_result_set_id)

series = cli.get_performance_series('mozilla-inbound', TRESIZE_SUBTEST_SIGNATURE, time_interval=INTERVAL)
print('got series')

''' --------------- '''

base_results = sorted(filter(lambda d: d['result_set_id'] == original_result_set_id, series), key=lambda a: a['job_id'])
new_results = sorted(filter(lambda d: d['result_set_id'] == new_result_set_id, series), key=lambda a: a['job_id'])
print 'got base + new result'

base_results_job_ids = map(lambda d: d['job_id'], base_results)
new_results_job_ids = map(lambda d: d['job_id'], new_results)
print 'got base + new result IDs'

''' --------------- '''
'''import pandas as pd'''
'''import datetime'''
import requests
import re

def get_replicates(job_id):
    RE_TALOSDATA = re.compile(r'.*?TALOSDATA:\s+(\[.*\])')
    log_url = cli.get_job_log_url('mozilla-inbound', job_id=job_id)[0]['url']
    for line in requests.get(log_url).iter_lines():
        match = RE_TALOSDATA.match(line)
        if match:
            return json.loads(match.group(1))[0]['results']['tresize']

base_replicate_sets = map(get_replicates, base_results_job_ids)
print 'base replicates:'
print base_replicate_sets
new_replicate_sets = map(get_replicates, new_results_job_ids)
print 'new replicates:'
print new_replicate_sets


''' --------------- '''
import scipy.stats
import numpy

def contrast_median_pvalue(results, replicate_sets):
    valid_results = []
    valid_replicate_sets = []
    for (idx, replicate_set) in enumerate(replicate_sets):
        other_replicates = []
        comparison_set = []
        for (idx2, replicate_set2) in enumerate(base_replicate_sets):
            if idx != idx2:
                comparison_set += replicate_set2
            # use welch's ttest, which does not assume equal variance between
            # populations
        pvalue = scipy.stats.ttest_ind(replicate_set, comparison_set, equal_var=False)[1]
        #print (results[idx]['median'], pvalue)
        if pvalue < 0.1:
            valid_results.append(results[idx])
            valid_replicate_sets.append(replicate_set)
        else:
            print "DROPPING (%s, %s, %s)" % (results[idx]['median'], results[idx]['job_id'], pvalue)
    return valid_results, valid_replicate_sets
        
print "BASE"
base_results1, base_replicate_sets1 = contrast_median_pvalue(base_results, base_replicate_sets)
base_results2, base_replicate_sets2 = contrast_median_pvalue(base_results1, base_replicate_sets1)
print "No dropping: %s (%s)" % (numpy.median(map(lambda d: d['median'], base_results)), len(base_results))
print "Drop different ones (pass 1): %s (%s)" % (numpy.median(map(lambda d: d['median'], base_results1)), len(base_results1))
print "Drop different ones (pass 2): %s (%s)" % (numpy.median(map(lambda d: d['median'], base_results2)), len(base_results2))
print map(lambda d: d['median'], base_results)
print "NEW"
new_results1, new_replicate_sets1 = contrast_median_pvalue(new_results, new_replicate_sets)
new_results2, new_replicate_sets2 = contrast_median_pvalue(new_results1, new_replicate_sets1)
print "No dropping: %s (%s mean) (%s)" % (numpy.median(map(lambda d: d['median'], new_results)), numpy.mean(map(lambda d: d['median'], new_results)), len(new_results))
print "Drop different ones (pass 1): %s (%s)" % (numpy.median(map(lambda d: d['median'], new_results1)), len(new_results1))
print "Drop different ones (pass 2): %s (%s)" % (numpy.median(map(lambda d: d['median'], new_results2)), len(new_results2))
print map(lambda d: d['median'], new_results)