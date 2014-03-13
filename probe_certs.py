from __future__ import division
import sys
import json
import csv
import urlparse
import grequests
import argparse
from unpack_certs import CertUnpacker, make_abs_filename

BASE_URL = 'http://www2.fdic.gov/efr/instdetail.asp'
FILE_NAME = make_abs_filename("fdic_certs.json")
RESULTS_FILE_NAME = make_abs_filename('results.csv')

class RequestsGenerator:
    def __init__(self, data):
        self.certs = [d.get('Cert') for d in data]
        self.index = 0

    def __iter__(self):
        return self

    def __len__(self):
        return len(self.certs)

    def __getitem__(self, index):
        if index <= (len(self.certs) - 1):
            return grequests.post(BASE_URL,
                data=get_post_parameters(self.certs[index]))
        else:
            raise IndexError

    def next(self):
        if self.index == len(self.certs) - 1:
            raise StopIteration
        self.index += 1
        return grequests.post(BASE_URL,
            data=get_post_parameters(self.certs[self.index]))

class Result:
    def __init__(self, name, cert_num, status_code, content_length):
        self.name = name
        self.cert_num = cert_num
        self.status_code = status_code
        self.content_length = content_length

    def to_dict(self):
        return {
            "Name": self.name,
            "Cert": self.cert_num,
            "Status Code": self.status_code,
            "Content Length": self.content_length
        }

class ResultsGenerator:
    def __init__(self):
        self.results = []
        self.index = 0

    def __iter__(self):
        return self

    def __len__(self):
        return len(self.results)

    def __getitem__(self, index):
        if index <= (len(self.results) - 1):
            return self.results[index]
        else:
            raise IndexError         

    def next(self):
        if self.index == len(self.results) - 1:
            self.index = 0
            raise StopIteration
        self.index += 1
        return self.results[self.index]

    def append(self, result):
        self.results.append(result)

def get_certs(filename):
    with open(filename, 'r') as infile:
        return json.load(infile)

def get_status(i, total, resp, datum):
    out = ("%5d/%-5d - %s (%s): Response<%s> content-length:%s%50s" % (
        i, total, datum.get('Name'), datum.get('Cert'),
        resp.status_code, resp.headers.get('content-length'), " "
        )
    )
    return out

def get_post_parameters(cert_num):
    return {
        "CertNum": str(cert_num),
        "CertNum_INTEGER": "The FDIC Certificate Number must be a positive integer"
    }

def parse_cert(body):
    try:
        return ''.join(urlparse.parse_qs(body).get('CertNum'))
    except ValueError:
        return None

def get_cert_name(data, cert):
    for d in data:
        if str(d.get('Cert')) == cert:
            return d.get('Name')

def add_result(results, data, resp):
    cert = parse_cert(resp.request.body)
    results.append(
        Result(
            get_cert_name(data, cert),
            cert,
            resp.status_code, 
            resp.headers.get('content-length')
        )
    )

def do_requests(data, results, limit=None):
    if limit:
        total = limit
    else:
        total = len(data)
    i = 0
    for resp in grequests.imap(RequestsGenerator(data), stream=True):
        i += 1
        sys.stdout.write("\rCompleted %4d/%-4d [%-20s] %0d%%  " % (
            i, total,
            "=" * (int((i / total) * 20)), 
            i * 100 / total))
        sys.stdout.flush()
        add_result(results, data, resp)
        if limit and limit == i:
            return
    sys.stdout.write("\n")
    sys.stdout.flush()

def results_to_dicts(results, threshold=10051):
    return [r.to_dict() for r in results if r.content_length > threshold]

def do_output(result_dicts):
    try:
        with open(RESULTS_FILE_NAME, 'wb') as csv_out:
            writer = csv.DictWriter(csv_out, result_dicts[-1].keys())
            writer.writeheader()
            for r in result_dicts:
                writer.writerow(r)
    except IndexError:
        print("Missing results")
        exit(-1)

def get_data(args):
    try:
        c = CertUnpacker()
    except IOError as e:
        print(e)
        exit(-1)
    if args.all:
        return c.get_dict()
    else:
        return [data for data in c.get_dict() if data.get('Active')]

def probe(args):
    results = ResultsGenerator()
    do_requests(get_data(args), results, limit=args.limit)

    rd = results_to_dicts(results)

    if rd:
        do_output(rd)
        print("")
        print("Finished FDIC.gov probe. Results written to %s" % 
            RESULTS_FILE_NAME
            )
    else:
        print("No Filers Found")

    return rd

if __name__ == '__main__':
    probe()