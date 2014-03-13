import os
import inspect
import csv
import json
import requests
from zipfile import ZipFile

def make_abs_filename(file_name):
    return os.path.join(
            os.path.abspath(
                inspect.getfile(inspect.currentframe())
                ),
            '..',
            file_name
            )

class CertUnpacker:

    ARCHIVE_FILE = make_abs_filename('Institutions2.zip')
    DATA_FILE = 'INSTITUTIONS2.CSV'
    OUTPUT_FILE = make_abs_filename('fdic_certs.json')
    REMOTE_ARCHIVE = 'http://www2.fdic.gov/idasp/Institutions2.zip'

    @classmethod
    def _get_file(cls, file_name):
        return os.path.join(
            os.path.abspath(
                inspect.getfile(inspect.currentframe())
                ),
            '..',
            file_name
            )

    @classmethod
    def _unpack_zip(cls):
        if not os.path.exists(CertUnpacker.ARCHIVE_FILE):
            CertUnpacker._download_archive()
        return ZipFile(CertUnpacker.ARCHIVE_FILE, 'r')

    @classmethod
    def _need_update(cls):
        if not os.path.exists(CertUnpacker.ARCHIVE_FILE):
            raise IOError("Cannot locate %s" % CertUnpacker.ARCHIVE_FILE)
        if os.path.exists(CertUnpacker.OUTPUT_FILE):
            # outfile is more recent than source archive
            return (os.stat(CertUnpacker.OUTPUT_FILE).st_mtime <=
            os.stat(CertUnpacker.ARCHIVE_FILE).st_mtime)
        return True

    @classmethod
    def _download_archive(cls):
        print("Downloading FDIC master list at %s... " % 
            CertUnpacker.REMOTE_ARCHIVE),
        resp = requests.get(CertUnpacker.REMOTE_ARCHIVE)
        with open(CertUnpacker.ARCHIVE_FILE, 'wb') as outfile:
            outfile.write(resp.content)
        print("Done.")

    def __init__(self):
        self.headers = []
        self.companies = []
        self._unpack()
        self.write_json()

    def get_dict(self):
        return [company.get_dict() for company in self.companies]

    def write_json(self, file_name='fdic_certs.json'):
        if (CertUnpacker._need_update()):
            with open(file_name, 'w') as outfile:
                for company in self.get_dict():
                    json.dump(company, outfile)
                    outfile.write('\n')
        else:
            print("%s is more recently than %s. Skipping update." % 
                (CertUnpacker.ARCHIVE_FILE, CertUnpacker.OUTPUT_FILE))

    def _unpack(self):
        zip_file = CertUnpacker._unpack_zip()

        with zip_file.open(CertUnpacker.DATA_FILE, 'r') as infile:
            self._read_csv(infile)
            #self._parse_headers(infile)
            #self._parse_data(infile)

    def _read_csv(self, infile):
        inst_file = csv.DictReader(infile)
        for row in inst_file:
            self._add_company(self._make_inst(row))

    def _make_inst(self, csv_row):
        return Institution(
            csv_row.get('NAME'),
            self._parse_cert(csv_row),
            csv_row.get('STNAME'),
            csv_row.get('CITY'),
            self._get_active_status(csv_row)
            )

    def _get_active_status(self, csv_row):
        if csv_row.get('ACTIVE') == "1":
            return True
        else:
            return False

    def _parse_cert(self, csv_row):
        try:
            return int(csv_row.get('CERT'))
        except ValueError as e:
            print(e)
            return None

    def _add_company(self, company):
        self.companies.append(company)

    def __repr__(self):
        return ("<CertUnpacker()> Total Companies: %d>" % len(self.companies))

class Institution:
    def __init__(self, name, cert, state, city, active):
        self.name = name
        self.cert = cert
        self.state = state
        self.city = city
        self.active = active

    def get_dict(self):
        return {
            "Cert": self.cert,
            "Name": self.name,
            "City": self.city,
            "State": self.state,
            "Active": self.active
        }

    def __repr__(self):
        return ("<Institution(name=%s,cert=%d,state=%s,city=%s,active=%s)>" % 
            (self.name, self.cert, self.state, self.city, self.active))